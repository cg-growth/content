"""Offline checks for plan detection, plan tips, X-first chains, and key redaction. No network."""
import io, json, os, sys, tempfile, time, unittest, urllib.error
from urllib.request import Request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.environ["MEMESCAN_HOME"] = ROOT
os.environ["DISCOVERY_DRY"] = "1"
sys.path.insert(0, os.path.join(ROOT, "lib"))
sys.path.insert(0, os.path.join(ROOT, "xfirst"))
sys.path.insert(0, os.path.join(ROOT, "discovery"))

import cgtier
import common as C


def _http(url, status, payload):
    body = json.dumps(payload).encode()
    if status >= 400:
        raise urllib.error.HTTPError(url, status, "err", {}, io.BytesIO(body))
    class Resp:
        def __init__(self):
            self.status = status
        def read(self):
            return body
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
    return Resp()


class Opener:
    def __init__(self, routes):
        self.routes = routes
        self.seen = []
    def __call__(self, req, timeout=20):
        url = req.full_url
        header_names = {k.lower() for k, _v in req.header_items()}
        self.seen.append((url, header_names))
        for pred, status, payload in self.routes:
            if pred(url):
                return _http(url, status, payload)
        return _http(url, 401, {"status": {"error_code": 10002, "error_message": "API Key Missing"}})


class TierTests(unittest.TestCase):
    def test_pro_basic(self):
        op = Opener([(lambda u: u.endswith("/key"), 200, {"plan": "Basic", "monthly_call_credit": 100000, "rate_limit_request_per_minute": 300})])
        hit = cgtier.detect("paid-key", "", op)
        self.assertEqual(hit["tier"], "basic")
        self.assertEqual(hit["header"], "x-cg-pro-api-key")
        self.assertTrue(cgtier.cg_has("ws", hit["tier"]))
        self.assertFalse(cgtier.cg_has("wallets", hit["tier"]))
        self.assertFalse(cgtier.cg_has("megafilter", hit["tier"]))
        self.assertFalse(cgtier.cg_has("top_traders", hit["tier"]))

    def test_pro_analyst_and_higher_names(self):
        for plan in ("Analyst", "Lite", "Pro", "Enterprise", "Other"):
            op = Opener([(lambda u: "/key" in u, 200, {"plan": plan})])
            hit = cgtier.detect("paid-key", "", op)
            self.assertEqual(hit["tier"], "analyst", plan)
            self.assertTrue(cgtier.cg_has("wallets", "analyst"))
            self.assertTrue(cgtier.cg_has("top_holders", "analyst"))

    def test_demo_key(self):
        op = Opener([(lambda u: "/onchain/networks" in u, 200, {"data": []})])
        hit = cgtier.detect("", "demo-key", op)
        self.assertEqual(hit["tier"], "demo")
        self.assertEqual(hit["base"], cgtier.DEMO_ROOT)
        self.assertEqual(hit["header"], "x-cg-demo-api-key")
        self.assertIn("x-cg-demo-api-key", op.seen[0][1])

    def test_demo_key_stored_in_pro_var(self):
        def pred_key(u):
            return u.endswith("/key")
        def pred_demo(u):
            return "/onchain/networks" in u
        op = Opener([(pred_key, 400, {"error_code": 10011}), (pred_demo, 200, {"data": []})])
        hit = cgtier.detect("demo-in-pro", "", op)
        self.assertEqual(hit["tier"], "demo")
        self.assertIn("COINGECKO_DEMO_API_KEY", hit["note"])

    def test_paid_key_stored_in_demo_var(self):
        op = Opener([
            (lambda u: "/onchain/networks" in u, 400, {"error_code": 10010}),
            (lambda u: u.endswith("/key"), 200, {"plan": "Analyst"}),
        ])
        hit = cgtier.detect("", "paid-in-demo", op)
        self.assertEqual(hit["tier"], "analyst")
        self.assertEqual(hit["key_env"], "COINGECKO_DEMO_API_KEY")
        self.assertIn("COINGECKO_PRO_API_KEY", hit["note"])

    def test_rejected_and_missing(self):
        op = Opener([])
        with self.assertRaises(cgtier.ProbeError) as ctx:
            cgtier.detect("nope", "also-nope", op)
        self.assertEqual(ctx.exception.code, 3)
        with self.assertRaises(cgtier.ProbeError) as ctx2:
            cgtier.detect("", "", op)
        self.assertEqual(ctx2.exception.code, 2)

    def test_rate_limit_does_not_guess(self):
        op = Opener([(lambda u: True, 429, {"status": {"error_message": "rate"}})])
        with self.assertRaises(cgtier.ProbeError) as ctx:
            cgtier.detect("paid-key", "demo-key", op)
        self.assertEqual(ctx.exception.code, 4)

    def test_assumed_tier_skips_network(self):
        old = {k: os.environ.get(k) for k in ("MEMESCAN_CG_TIER", "COINGECKO_DEMO_API_KEY", "COINGECKO_PRO_API_KEY")}
        try:
            os.environ["MEMESCAN_CG_TIER"] = "demo"
            os.environ["COINGECKO_DEMO_API_KEY"] = "simulated"
            os.environ.pop("COINGECKO_PRO_API_KEY", None)
            hit = cgtier.assumed_result()
            self.assertEqual(hit["tier"], "demo")
            self.assertEqual(hit["header"], "x-cg-demo-api-key")
            text = cgtier.export_sh(hit)
            self.assertIn("export CG_TIER=demo", text)
            self.assertNotIn("simulated", text)
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


class TipTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._market = C.MARKET
        C.MARKET = os.path.join(self.tmp.name, "market.db")
        self._risk = C.risk_cfg
        self._notices = os.environ.get("MEMESCAN_NOTICES_FILE")
        os.environ["MEMESCAN_NOTICES_FILE"] = os.path.join(self.tmp.name, "pending.json")
        import plan_tips
        self.tips = plan_tips

    def tearDown(self):
        C.MARKET = self._market
        C.risk_cfg = self._risk
        if self._notices is None: os.environ.pop("MEMESCAN_NOTICES_FILE", None)
        else: os.environ["MEMESCAN_NOTICES_FILE"] = self._notices
        self.tmp.cleanup()

    def test_dedupe_per_trigger(self):
        now = 1_700_000_000.0
        self.assertTrue(self.tips.due("rate_limit", now))
        self.assertTrue(self.tips.due("wallet_gap", now))
        self.tips.mark("rate_limit", now)
        self.assertFalse(self.tips.due("rate_limit", now + 3600))
        self.assertTrue(self.tips.due("wallet_gap", now + 3600))
        self.assertTrue(self.tips.due("rate_limit", now + 8 * 86400))

    def test_disabled_by_config_and_flag(self):
        C.risk_cfg = lambda: {"plan_tips": {"enabled": False}}
        self.assertFalse(self.tips.due("weekly", time.time()))
        C.risk_cfg = lambda: {"plan_tips": {"enabled": True}}
        self.tips.set_enabled(False)
        self.assertFalse(self.tips.enabled())
        self.assertFalse(self.tips.due("rate_limit", time.time()))
        self.tips.set_enabled(True)
        self.assertTrue(self.tips.due("rate_limit", time.time()))

    def test_notify_queues_once_and_telegrams_when_chat_is_set(self):
        sent = []
        class Fake:
            @staticmethod
            def send(chat, text):
                sent.append((chat, text))
                return {"ok": True}
        sys.modules["core"] = Fake
        os.environ.pop("TELEGRAM_CHAT_ID", None)
        os.environ["TELEGRAM_BOT_TOKEN"] = "token"
        self.assertTrue(self.tips.notify("rate_limit"))
        self.assertEqual(sent, [])
        self.assertEqual(len(self.tips.pending()), 1)
        self.assertFalse(self.tips.due("rate_limit", time.time()))
        os.environ["TELEGRAM_CHAT_ID"] = "4242"
        self.assertTrue(self.tips.notify("wallet_gap"))
        self.assertEqual(sent[0][0], "4242")
        self.assertIn("utm_source=grokbot", sent[0][1])
        self.assertIn("utm_medium=referral", sent[0][1])
        self.assertIn("utm_campaign=grokbot-memecoin-scanner", sent[0][1])
        self.assertIn("utm_content=tg-plan-tip", sent[0][1])
        self.assertIn("Plans", sent[0][1])
        os.environ.pop("TELEGRAM_CHAT_ID", None)
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)

    def test_critical_sends_when_tips_are_off(self):
        self.tips.set_enabled(False)
        self.assertFalse(self.tips.notify("wallet_gap"))
        self.assertTrue(self.tips.notify("invalid_key", signature="10010"))
        self.assertFalse(self.tips.notify("invalid_key", signature="10010"))
        self.tips.clear_event("invalid_key")
        self.assertTrue(self.tips.notify("credits_exhausted", signature="2026-10:0"))
        self.assertFalse(self.tips.notify("credits_exhausted", signature="2026-10:0"))
        kinds = [n["trigger"] for n in self.tips.pending()]
        self.assertEqual(kinds, ["invalid_key", "credits_exhausted"])


class ChainTests(unittest.TestCase):
    def test_xfirst_respects_networks(self):
        import xfirst
        orig = C.risk_cfg
        calls = []
        def fake_cg(path, params=None, mc=None, timeout=25):
            calls.append(path)
            ca = params["query"]
            return {"data": [
                {"id": "solana_pool", "relationships": {"base_token": {"data": {"id": "solana_" + ca}}}, "attributes": {"reserve_in_usd": 90000}},
                {"id": "base_pool", "relationships": {"base_token": {"data": {"id": "base_" + ca}}}, "attributes": {"reserve_in_usd": 10}},
            ]}
        orig_cg = C.cg
        C.cg = fake_cg
        try:
            C.risk_cfg = lambda: {"discovery": {"networks": ["base"]}, "xfirst": {}}
            self.assertEqual(xfirst.nets(), ["base"])
            ca = "0x" + "ab" * 20
            out = xfirst.resolve(ca, None)
            self.assertEqual([p["id"] for p in out], ["base_pool"])
            self.assertEqual(calls, ["/search/pools"])
            C.risk_cfg = lambda: {"discovery": {"networks": ["solana", "base"]}, "xfirst": {"networks": ["solana"]}}
            self.assertEqual(xfirst.nets(), ["solana"])
        finally:
            C.risk_cfg = orig
            C.cg = orig_cg


class GateTests(unittest.TestCase):
    def setUp(self):
        self._env = {k: os.environ.get(k) for k in ("CG_TIER", "COINGECKO_DEMO_API_KEY", "COINGECKO_PRO_API_KEY", "CG_AUTH_HEADER", "CG_BASE", "CG_KEY_ENV")}

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_demo_does_not_request_paid_paths(self):
        os.environ["CG_TIER"] = "demo"
        os.environ["COINGECKO_DEMO_API_KEY"] = "simulated-demo"
        os.environ.pop("COINGECKO_PRO_API_KEY", None)
        os.environ.pop("CG_AUTH_HEADER", None)
        import sol_profile
        calls = []
        orig = C.cg
        def fake_cg(path, params=None, mc=None, timeout=25):
            calls.append(path)
            return {"data": {"attributes": {}}}
        C.cg = fake_cg
        try:
            self.assertFalse(C.cg_has("wallets"))
            self.assertFalse(C.cg_has("top_traders"))
            self.assertFalse(C.cg_has("ws"))
            self.assertEqual(C.auth_header_name(), "x-cg-demo-api-key")
            self.assertIn("api.coingecko.com", C.onchain_root())
            skipped = sol_profile.profile_many(["So11111111111111111111111111111111111111112"])
            self.assertTrue(all("skipped" in v for v in skipped.values()))
            self.assertEqual(calls, [])
            self.assertEqual(cgtier.unavailable(), "not included with a CoinGecko API Demo (free) key")
        finally:
            C.cg = orig

    def test_redact_both_keys(self):
        os.environ["COINGECKO_DEMO_API_KEY"] = "demo-secret-value"
        os.environ["COINGECKO_PRO_API_KEY"] = "pro-secret-value"
        text = C.redact("headers demo-secret-value and pro-secret-value")
        self.assertNotIn("demo-secret-value", text)
        self.assertNotIn("pro-secret-value", text)

    def test_limit_kind_and_no_pause(self):
        self.assertEqual(C.limit_kind(429, {"error": "monthly credit quota exceeded"}), "credits")
        self.assertEqual(C.limit_kind(429, {"status": {"error_message": "throttled"}}), "rate")
        os.environ["CG_TIER"] = "demo"
        os.environ["COINGECKO_DEMO_API_KEY"] = "simulated-demo"
        os.environ.pop("COINGECKO_PRO_API_KEY", None)
        tmp = tempfile.TemporaryDirectory()
        old = C.MARKET
        C.MARKET = os.path.join(tmp.name, "market.db")
        notes = []
        import plan_tips
        orig_notify = plan_tips.notify
        def _note(trigger, signature=None):
            notes.append(trigger)
            return False
        plan_tips.notify = _note
        def boom(req, timeout=25):
            raise urllib.error.HTTPError(req.full_url, 429, "limit", {}, io.BytesIO(b'{"error":"monthly credit quota exceeded"}'))
        orig_open = urllib.request.urlopen
        urllib.request.urlopen = boom
        try:
            self.assertIsNone(C.cg("/networks/base/new_pools"))
            self.assertEqual(notes, ["credits_exhausted"])
            row = C.kv_get(C.mdb(), "cg_limit_status")
            self.assertEqual(row["kind"], "credits")
        finally:
            urllib.request.urlopen = orig_open
            plan_tips.notify = orig_notify
            C.MARKET = old
            tmp.cleanup()


class TreeTests(unittest.TestCase):
    def test_no_keyless_request_urls(self):
        bad = []
        skip = {".git", ".venv", "research", "logs", "__pycache__", "uploads"}
        for dirpath, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in skip and not d.startswith(".")]
            for name in files:
                path = os.path.join(dirpath, name)
                if os.path.splitext(name)[1] in {".png", ".db", ".pyc"}:
                    continue
                try:
                    text = open(path, encoding="utf-8", errors="ignore").read()
                except Exception:
                    continue
                rel = os.path.relpath(path, ROOT)
                if rel.startswith("tests" + os.sep) or rel == "lib/utm.py":
                    continue
                if "https://mcp.api.coingecko.com" in text or "http://mcp.api.coingecko.com" in text or "https://api.geckoterminal.com" in text or "http://api.geckoterminal.com" in text:
                    bad.append(rel)
        self.assertEqual(bad, [])


class DiscoveryTests(unittest.TestCase):
    def test_demo_prelim_can_be_organic_without_paid_calls(self):
        os.environ["CG_TIER"] = "demo"
        os.environ["COINGECKO_DEMO_API_KEY"] = "simulated-demo"
        os.environ.pop("COINGECKO_PRO_API_KEY", None)
        os.environ["DISCOVERY_DRY"] = "1"
        import discovery
        calls = []
        orig_cg = C.cg
        def fake_cg(path, params=None, mc=None, timeout=25):
            calls.append(path.split("?")[0])
            if path.endswith("/info"):
                return {"data": {"attributes": {"name": "Test", "symbol": "TEST", "is_honeypot": False, "developer_holding_percentage": 0, "holders": {}}}}
            if path.endswith("/trades"):
                return {"data": []}
            return {"data": []}
        C.cg = fake_cg
        import subprocess
        orig_run = subprocess.run
        def fake_run(cmd, input=None, capture_output=True, text=True, timeout=60):
            class R:
                stdout = "{}"
                returncode = 0
            if cmd and "score-token" in cmd:
                R.stdout = json.dumps({"human_participation": 100, "mix": {"human": 4}, "bundles": [], "read": "ok"})
            elif cmd and "lookup" in cmd:
                R.stdout = "{}"
            return R()
        subprocess.run = fake_run
        discovery.subprocess.run = fake_run
        ca = "0x" + "cd" * 20
        key = "base_" + ca
        m = {"liq": 20000, "fdv": 80000, "age_min": 30, "h1_change": 400, "buyers_h1": 80, "sellers_h1": 20,
             "buys_h1": 100, "sells_h1": 40, "vol_h1": 5000, "m5_change": 5, "pool_created_at": "2026-01-01T00:00:00Z",
             "name": "Test", "price": 0.001}
        try:
            discovery.mc.execute("insert or replace into discoveries(key, ca, network, pool, seen_at, stage) values(?,?,?,?,?,?)",
                                 (key, ca, "base", "0x" + "11" * 20, C.now_iso(), "new"))
            discovery.mc.commit()
            discovery._deep(key, "base", "0x" + "11" * 20, ca, m)
            payload = json.load(open(os.path.join(ROOT, "research", f"base_{ca}.json")))
            self.assertEqual(payload["prelim_verdict"], "Organic Hype?")
            self.assertFalse(any("unverified" in r for r in payload["fail_reasons"]))
            self.assertTrue(payload.get("top_traders_note"))
            joined = " ".join(calls)
            for banned in ("top_traders", "top_holders", "holders_chart", "/wallets/", "liquidity_events"):
                self.assertNotIn(banned, joined)
        finally:
            C.cg = orig_cg
            subprocess.run = orig_run
            try:
                os.remove(os.path.join(ROOT, "research", f"base_{ca}.json"))
            except OSError:
                pass
            discovery.mc.execute("delete from discoveries where key=?", (key,))
            discovery.mc.commit()


class UsageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._market = C.MARKET
        C.MARKET = os.path.join(self.tmp.name, "market.db")
        self._notices = os.environ.get("MEMESCAN_NOTICES_FILE")
        os.environ["MEMESCAN_NOTICES_FILE"] = os.path.join(self.tmp.name, "pending.json")
        self._env = {k: os.environ.get(k) for k in ("CG_TIER", "COINGECKO_DEMO_API_KEY", "COINGECKO_PRO_API_KEY")}
        import usage, plan_tips
        self.usage = usage
        self.tips = plan_tips

    def tearDown(self):
        C.MARKET = self._market
        if self._notices is None: os.environ.pop("MEMESCAN_NOTICES_FILE", None)
        else: os.environ["MEMESCAN_NOTICES_FILE"] = self._notices
        for k, v in self._env.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v
        self.tmp.cleanup()

    def test_parse_account_and_per_key(self):
        account = self.usage.parse_key_body({
            "plan": "Analyst", "rate_limit_request_per_minute": 500,
            "monthly_call_credit": 500000, "current_total_monthly_calls": 100,
            "current_remaining_monthly_calls": 499900,
        })
        self.assertEqual(account["source"], "api")
        self.assertEqual(account["used"], 100)
        self.assertEqual(account["remaining"], 499900)
        self.assertEqual(account["monthly_limit"], 500000)
        per = self.usage.parse_key_body({
            "plan": "Analyst", "monthly_call_credit": 500000, "current_total_monthly_calls": 10,
            "current_remaining_monthly_calls": 499990,
            "api_key_monthly_call_credit": 1000, "api_key_current_total_monthly_calls": 900,
            "api_key_rate_limit_request_per_minute": 100,
        })
        self.assertEqual(per["monthly_limit"], 1000)
        self.assertEqual(per["used"], 900)
        self.assertEqual(per["remaining"], 100)
        self.assertEqual(per["rate_limit_request_per_minute"], 100)
        self.assertAlmostEqual(per["pct"], 0.9)

    def test_low_once_per_crossing_and_exhausted_is_critical(self):
        low = {"source": "api", "plan": "Analyst", "monthly_limit": 100, "used": 91, "remaining": 9, "pct": 0.91}
        self.usage.evaluate(low)
        self.usage.evaluate(low)
        self.assertEqual([n["trigger"] for n in self.tips.pending()], ["credits_low"])
        self.usage.evaluate({"source": "api", "monthly_limit": 100, "used": 70, "remaining": 30, "pct": 0.70})
        self.usage.evaluate(low)
        self.assertEqual([n["trigger"] for n in self.tips.pending()], ["credits_low", "credits_low"])
        self.tips.set_enabled(False)
        self.usage.evaluate({"source": "api", "monthly_limit": 100, "used": 100, "remaining": 0, "pct": 1})
        self.usage.evaluate({"source": "api", "monthly_limit": 100, "used": 100, "remaining": 0, "pct": 1})
        kinds = [n["trigger"] for n in self.tips.pending()]
        self.assertEqual(kinds.count("credits_exhausted"), 1)
        self.assertNotIn("credits_low", kinds[2:])

    def test_demo_refresh_does_not_call_key(self):
        os.environ["CG_TIER"] = "demo"
        os.environ["COINGECKO_DEMO_API_KEY"] = "simulated"
        os.environ.pop("COINGECKO_PRO_API_KEY", None)
        called = []
        snap = self.usage.refresh(force=True, opener=lambda *a, **k: called.append(1))
        self.assertEqual(called, [])
        self.assertEqual(snap["source"], "estimate")
        self.assertIn("estimate", snap["note"])
        os.environ["CG_TIER"] = "analyst"
        os.environ["COINGECKO_PRO_API_KEY"] = "simulated"
        self.assertIsNone(self.usage.cached())


class LinkTests(unittest.TestCase):
    def test_pool_and_token_and_alert_caption(self):
        import utm
        os.environ.pop("MEMESCAN_UTM", None)
        net, pool, ca = "base", "0x" + "11" * 20, "0x" + "ab" * 20
        pool_u = utm.pool_url(net, pool, "tg-alert-pool")
        token_u = utm.token_url(net, ca, "tg-alert-token")
        for url, place in ((pool_u, "tg-alert-pool"), (token_u, "tg-alert-token")):
            self.assertIn("utm_source=grokbot", url)
            self.assertIn("utm_medium=referral", url)
            self.assertIn("utm_campaign=grokbot-memecoin-scanner", url)
            self.assertIn("utm_content=" + place, url)
            self.assertIn("www.geckoterminal.com", url)
        self.assertIn("/pools/", pool_u)
        self.assertIn("/tokens/", token_u)
        msg = f'<a href="{utm.html_href(pool_u)}">Pool</a> · <a href="{utm.html_href(token_u)}">Token</a>'
        self.assertIn("&amp;", msg)
        self.assertIn("utm_content=tg-alert-pool", msg)
        self.assertIn("utm_content=tg-alert-token", msg)
        for raw in ("https://api.coingecko.com/api/v3/key", "https://pro-api.coingecko.com/api/v3/key",
                    "https://mcp.pro-api.coingecko.com/mcp", "wss://stream.coingecko.com/v1"):
            self.assertEqual(utm.tag(raw, "should-not-apply"), raw)
        sys.path.insert(0, os.path.join(ROOT, "telegram"))
        sys.path.insert(0, os.path.join(ROOT, "alerts"))
        import send_card
        cap = send_card.caption({
            "ca": ca, "network": net, "pool": pool, "symbol": "T", "tag": "Watch", "confidence": "low",
            "score": 10, "narrative": "n", "human_score": 10, "plan_tip": "wallet_gap",
            "metrics": {"liq": 1, "fdv": 1, "age_min": 1},
        }, {"line": "size $10"})
        self.assertIn("utm_content=tg-alert-pool", cap)
        self.assertIn("utm_content=tg-alert-token", cap)
        self.assertNotIn("this scan skipped them", cap)
        kb = send_card.kb(ca, net, pool, {"rec": 10, "half": 5, "double": 20})
        button = kb["inline_keyboard"][-1][0]["url"]
        self.assertIn("utm_content=tg-alert-pool", button)
        self.assertNotIn("&amp;", button)


ANALYST_ONLY = {"status": {"error_code": 401, "error_message": "This request is exclusive to Analyst plan or above subscribers only. Upgrade to Analyst plan or above to access this endpoint."}}
KEY_ON_DEMO = {"status": {"error_code": 10005, "error_message": "This request is limited to PRO API subscribers only."}}


class ErrorShapeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._market = C.MARKET
        C.MARKET = os.path.join(self.tmp.name, "market.db")
        self._notices = os.environ.get("MEMESCAN_NOTICES_FILE")
        os.environ["MEMESCAN_NOTICES_FILE"] = os.path.join(self.tmp.name, "pending.json")
        self._env = {k: os.environ.get(k) for k in ("CG_TIER", "COINGECKO_DEMO_API_KEY", "COINGECKO_PRO_API_KEY")}
        os.environ["CG_TIER"] = "demo"
        os.environ["COINGECKO_DEMO_API_KEY"] = "simulated-demo"
        os.environ.pop("COINGECKO_PRO_API_KEY", None)
        C._RESTRICTED.clear()
        import plan_tips
        self.tips = plan_tips
        self._notify = plan_tips.notify
        self.notes = []
        def _note(trigger, signature=None):
            self.notes.append((trigger, signature))
            return False
        plan_tips.notify = _note
        self._open = urllib.request.urlopen

    def tearDown(self):
        urllib.request.urlopen = self._open
        self.tips.notify = self._notify
        C.MARKET = self._market
        C._RESTRICTED.clear()
        if self._notices is None: os.environ.pop("MEMESCAN_NOTICES_FILE", None)
        else: os.environ["MEMESCAN_NOTICES_FILE"] = self._notices
        for k, v in self._env.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v
        self.tmp.cleanup()

    def _body(self, status, payload):
        raw = json.dumps(payload).encode()
        def boom(req, timeout=25):
            raise urllib.error.HTTPError(req.full_url, status, "err", {}, io.BytesIO(raw))
        urllib.request.urlopen = boom

    def test_err_code_reads_top_level(self):
        self.assertEqual(C._err_code({"error_code": 10010}), 10010)
        self.assertEqual(C._err_code({"error_code": "10011"}), 10011)
        self.assertEqual(cgtier.err_code({"status": {"error_message": "x"}, "error_code": 10010}), 10010)
        self.assertEqual(C._err_code(ANALYST_ONLY), 401)
        self.assertEqual(C._err_code(KEY_ON_DEMO), 10005)

    def test_analyst_only_401_is_a_missing_feature(self):
        self._body(401, ANALYST_ONLY)
        self.assertIsNone(C.cg("/networks/base/tokens/abc/top_traders"))
        self.assertEqual([n[0] for n in self.notes], ["wallet_gap"])
        self.assertNotIn("invalid_key", [n[0] for n in self.notes])

    def test_key_10005_is_a_missing_feature(self):
        self._body(401, KEY_ON_DEMO)
        self.assertTrue(C.plan_restricted(401, KEY_ON_DEMO))
        self.assertFalse(C.invalid_key_error(401, KEY_ON_DEMO))
        self.assertIsNone(C.cg("/key"))

    def test_bad_key_shapes_are_invalid(self):
        shapes = [
            (401, {"status": {"error_code": 10002, "error_message": "API Key Missing"}}),
            (400, {"error_code": 10010}),
            (400, {"error_code": 10011}),
            (401, {"status": {"error_message": "nope"}}),
        ]
        for status, payload in shapes:
            self.notes.clear()
            self._body(status, payload)
            self.assertTrue(C.invalid_key_error(status, payload), payload)
            self.assertIsNone(C.cg("/networks/base/new_pools"))
            self.assertEqual(self.notes[-1][0], "invalid_key", payload)

    def test_usage_10005_does_not_mark_the_key_invalid(self):
        import usage
        os.environ["CG_TIER"] = "analyst"
        os.environ["COINGECKO_PRO_API_KEY"] = "simulated-pro"
        def opener(req, timeout=20):
            raw = json.dumps(KEY_ON_DEMO).encode()
            raise urllib.error.HTTPError(req.full_url, 401, "err", {}, io.BytesIO(raw))
        usage.refresh(force=True, opener=opener)
        self.assertNotIn("invalid_key", [n[0] for n in self.notes])


class CreditEstimateTests(unittest.TestCase):
    def test_defaults_match_measured_demo_use(self):
        import credits
        e = credits.estimate(60, 4)
        self.assertAlmostEqual(e["per_cycle"], 17)
        self.assertAlmostEqual(e["per_minute"], 17)
        self.assertAlmostEqual(e["hours"], 10, delta=0.3)
        text = credits.sentence(60, 4)
        self.assertIn("10,000", text)
        self.assertIn("CoinGecko API Demo (free)", text)
        self.assertIn("credits a day", text)
        self.assertIn("about 10 hours", text)
        self.assertIn("does not change it", text)
        slower = credits.estimate(600, 4)
        self.assertGreater(slower["days"], e["days"])
        self.assertEqual(credits.estimate(60, 4)["interval_s"], 60)


class WsRefusalTests(unittest.TestCase):
    def test_first_unauthorized_message_selects_polling(self):
        sys.path.insert(0, os.path.join(ROOT, "stream"))
        import stream
        body = {"message": "Unauthorized access, invalid API key"}
        self.assertEqual(stream.ws_first_action(body), "poll")
        self.assertEqual(stream.ws_first_action(json.dumps(body)), "poll")
        self.assertEqual(stream.ws_first_action({"type": "confirm_subscription"}), "ws")


class PlanWordingTests(unittest.TestCase):
    def setUp(self):
        self._env = {k: os.environ.get(k) for k in ("CG_TIER", "COINGECKO_DEMO_API_KEY", "COINGECKO_PRO_API_KEY")}
        self.tmp = tempfile.TemporaryDirectory()
        self._market = C.MARKET
        C.MARKET = os.path.join(self.tmp.name, "market.db")

    def tearDown(self):
        C.MARKET = self._market
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tmp.cleanup()

    def test_plan_labels_and_owner_messages(self):
        self.assertEqual(cgtier.PLAN_LABELS["demo"], "CoinGecko API Demo (free)")
        self.assertEqual(cgtier.PLAN_LABELS["basic"], "CoinGecko API Basic")
        self.assertEqual(cgtier.PLAN_LABELS["analyst"], "CoinGecko API Analyst")
        self.assertEqual(cgtier.plan_label("demo"), "CoinGecko API Demo (free) plan")
        self.assertEqual(cgtier.plan_label("demo", "key"), "CoinGecko API Demo (free) key")
        self.assertEqual(cgtier.plan_label("basic"), "CoinGecko API Basic plan")
        self.assertEqual(cgtier.plan_label("analyst"), "CoinGecko API Analyst plan")
        self.assertEqual(cgtier.needs_plan("analyst"), "a CoinGecko API Analyst plan or higher")
        self.assertEqual(cgtier.needs_plan("basic"), "a CoinGecko API Basic plan or higher")
        self.assertEqual(cgtier.display_api_plan("Lite"), "CoinGecko API Lite plan")
        self.assertEqual(cgtier.display_api_plan("Analyst"), "CoinGecko API Analyst plan")
        self.assertEqual(cgtier.display_api_plan(""), cgtier.plan_label("analyst"))
        os.environ["CG_TIER"] = "demo"
        os.environ["COINGECKO_DEMO_API_KEY"] = "simulated-demo"
        os.environ.pop("COINGECKO_PRO_API_KEY", None)
        self.assertEqual(cgtier.unavailable(), "not included with a CoinGecko API Demo (free) key")
        import plan_tips, usage
        gap = plan_tips._body("wallet_gap")
        self.assertIn("spotting smart money vs bots", gap)
        self.assertIn("a CoinGecko API Analyst plan or higher", gap)
        self.assertIn("Holder history and Megafilter need that plan too", gap)
        weekly = plan_tips._body("weekly")
        self.assertIn("CoinGecko API Demo (free) plan", weekly)
        self.assertIn("a CoinGecko API Basic plan or higher", weekly)
        tip = plan_tips.message("wallet_gap")
        self.assertIn("utm_content=tg-plan-tip", tip)
        self.assertIn("https://www.coingecko.com/en/api/pricing", tip)
        self.assertIn("CoinGecko API Demo (free) plan", plan_tips.status_text())
        self.assertIn("not included with a CoinGecko API Demo (free) key", plan_tips.status_text())
        html = usage.telegram_html()
        self.assertIn("CoinGecko API Demo (free) key", html)
        self.assertIn("utm_content=tg-usage", html)
        os.environ["CG_TIER"] = "basic"
        self.assertEqual(cgtier.unavailable(), "needs a CoinGecko API Analyst plan or higher")
        snap = {"source": "api", "plan": "Analyst", "used": 10, "monthly_limit": 500000, "remaining": 499990, "rate_limit_request_per_minute": 500}
        usage.store(snap)
        paid_html = usage.telegram_html()
        self.assertIn("CoinGecko API Analyst plan", paid_html)
        self.assertNotIn(">Analyst<", paid_html)

    def test_no_bare_plan_names_in_user_facing_text(self):
        import re
        pat = re.compile(r"(?<!CoinGecko API )(Analyst|Basic|Demo)\b")
        roots = [
            "README.md", "AGENTS.md", ".env.example", "start.sh", "install.sh", "status.sh", "risk.json",
            "docs", "grokbot", "dashboard", "telegram", "lib", "discovery", "stream",
        ]
        bad = []
        for rel in roots:
            path = os.path.join(ROOT, rel)
            files = []
            if os.path.isdir(path):
                for dirpath, dirs, names in os.walk(path):
                    dirs[:] = [d for d in dirs if d not in (".git", ".venv", "__pycache__")]
                    for name in names:
                        if name.endswith((".py", ".md", ".sh", ".html", ".json", ".example")):
                            files.append(os.path.join(dirpath, name))
            else:
                files.append(path)
            for fp in files:
                for i, line in enumerate(open(fp, encoding="utf-8"), 1):
                    if "exclusive to Analyst plan" in line:
                        continue
                    if pat.search(line):
                        bad.append(f"{os.path.relpath(fp, ROOT)}:{i}: {line.strip()[:160]}")
        self.assertEqual(bad, [])

    def test_invalid_key_sends_new_accounts_to_pricing_first(self):
        import plan_tips
        text = plan_tips.message("invalid_key")
        self.assertIn("New to CoinGecko API", text)
        self.assertIn("Already have a CoinGecko API account", text)
        self.assertIn("utm_source=grokbot", text)
        self.assertIn("utm_medium=referral", text)
        self.assertIn("utm_campaign=grokbot-memecoin-scanner", text)
        self.assertIn("utm_content=tg-invalid-key-pricing", text)
        self.assertIn("utm_content=tg-invalid-key", text)
        self.assertLess(text.find("/en/api/pricing"), text.find("/en/developers/dashboard"))
        self.assertIn("#api-keys", text)

    def test_onboarding_template_and_readme_key_sequence(self):
        template = open(os.path.join(ROOT, "grokbot/template/getting-started.md"), encoding="utf-8").read()
        self.assertIn("From your CoinGecko developer dashboard. New to CoinGecko API? Sign up on the CoinGecko API pricing page first.", template)
        self.assertIn("No CoinGecko API account yet", template)
        self.assertIn("Already have a CoinGecko API account", template)
        self.assertIn("utm_source=grokbot", template)
        self.assertIn("utm_content=chat-onboarding", template)
        self.assertIn("Do not shorten a plan name", template)
        self.assertIn("PAPER_START_CASH", template)
        self.assertNotIn("AI `start_cash` in `auto/policy.json`", template)
        self.assertLess(template.find("https://www.coingecko.com/en/api/pricing?"), template.find("https://www.coingecko.com/en/developers/dashboard?"))
        readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
        section = readme.split("## Get your keys", 1)[1].split("\n## ", 1)[0]
        self.assertIn("utm_source=github", section)
        self.assertIn("No CoinGecko API account yet", section)
        self.assertLess(section.find("/en/api/pricing"), section.find("/en/developers/dashboard"))


class BankrollTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._cash = os.environ.get("PAPER_START_CASH")
        sys.path.insert(0, os.path.join(ROOT, "telegram"))
        import core
        self.core = core
        self._db = core.DB
        os.environ["PAPER_START_CASH"] = "1000"

    def tearDown(self):
        self.core.DB = self._db
        if self._cash is None:
            os.environ.pop("PAPER_START_CASH", None)
        else:
            os.environ["PAPER_START_CASH"] = self._cash
        self.tmp.cleanup()

    def test_fresh_book_adopts_configured_cash_and_a_traded_book_does_not(self):
        path = os.path.join(self.tmp.name, "paper.db")
        self.core.DB = path
        os.environ["PAPER_START_CASH"] = "10000"
        c = self.core.db()
        self.assertEqual(c.execute("select v from account where k='cash'").fetchone()[0], 10000)
        c.close()
        os.environ["PAPER_START_CASH"] = "1000"
        c = self.core.db()
        self.assertEqual(c.execute("select v from account where k='cash'").fetchone()[0], 1000)
        c.execute("insert into trades(side,ca,symbol) values('buy','ca','S')")
        c.commit()
        c.close()
        os.environ["PAPER_START_CASH"] = "50"
        c = self.core.db()
        self.assertEqual(c.execute("select v from account where k='cash'").fetchone()[0], 1000)
        self.assertEqual(self.core.book_start(c), 1000)
        c.close()

    def test_both_books_use_one_setting_until_a_trade(self):
        import sqlite3
        import bankroll
        sys.path.insert(0, os.path.join(ROOT, "auto"))
        import book
        human = os.path.join(self.tmp.name, "paper.db")
        auto = os.path.join(self.tmp.name, "auto.db")
        pol = os.path.join(self.tmp.name, "policy.json")
        open(pol, "w", encoding="utf-8").write('{\n "start_cash": 10000,\n "version": 1\n}\n')
        self.core.DB = human
        os.environ["PAPER_START_CASH"] = "1000"
        c = self.core.db()
        c.close()
        c = sqlite3.connect(auto)
        c.executescript(self.core.SCHEMA)
        c.execute("insert into account(k,v) values('cash',10000)")
        c.commit()
        self.assertTrue(bankroll.apply(c, sync_policy_path=pol))
        self.assertEqual(c.execute("select v from account where k='cash'").fetchone()[0], 1000)
        text = open(pol, encoding="utf-8").read()
        self.assertIn('"version": 1', text)
        self.assertEqual(json.load(open(pol, encoding="utf-8"))["start_cash"], 1000)
        saved = book.DBS
        saved_policy = book._policy_start
        try:
            book.DBS = {"human": human, "auto": auto}
            book._policy_start = lambda: 1000.0
            self.assertEqual(book.start_cash("human"), 1000)
            self.assertEqual(book.start_cash("auto"), 1000)
        finally:
            book.DBS = saved
            book._policy_start = saved_policy
        c.execute("insert into trades(side,ca) values('buy','z')")
        c.commit()
        os.environ["PAPER_START_CASH"] = "250"
        self.assertFalse(bankroll.apply(c, sync_policy_path=pol))
        self.assertEqual(c.execute("select v from account where k='cash'").fetchone()[0], 1000)
        self.assertEqual(json.load(open(pol, encoding="utf-8"))["start_cash"], 1000)
        c.close()


class ForwardPauseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._env = {k: os.environ.get(k) for k in ("MEMESCAN_HOME", "FWDQ_DB", "TELEGRAM_FORWARD_URL", "TELEGRAM_FORWARD_KEY")}
        os.environ["MEMESCAN_HOME"] = self.tmp.name
        os.environ["FWDQ_DB"] = os.path.join(self.tmp.name, "fwdq.db")
        os.environ["TELEGRAM_FORWARD_URL"] = "https://example.invalid/hook"
        os.environ.pop("TELEGRAM_FORWARD_KEY", None)
        import importlib
        import fwdq
        self.fwdq = importlib.reload(fwdq)
        self._importlib = importlib

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._importlib.reload(self.fwdq)
        self.tmp.cleanup()

    def test_disabled_automation_is_logged_once_and_then_paused(self):
        fq = self.fwdq
        self.assertFalse(fq.automation_disabled(400, "bad json"))
        self.assertFalse(fq.automation_disabled(500, "Automation abc is disabled"))
        self.assertTrue(fq.automation_disabled(400, "Automation abc is disabled"))
        self.assertTrue(fq.automation_disabled("400", '{"error":"The automation is disabled"}'))
        calls = []

        def fake(body, timeout=15):
            calls.append(body)
            return False, 400, '{"message":"Automation abc is disabled"}'

        fq.post = fake
        now = time.time()
        fq.enqueue("research", {"ca": "abc", "network": "solana", "token": {"symbol": "A"}}, "research:abc:p1", "x", created=now)
        fq.enqueue("research", {"ca": "def", "network": "solana", "token": {"symbol": "B"}}, "research:def:p2", "x", created=now)
        c = fq._c()
        c.execute("update q set next_at=0")
        c.commit()
        c.close()
        logs = []
        fq.drain(log=lambda *a: logs.append(" ".join(str(x) for x in a)))
        self.assertEqual(len(calls), 1)
        paused_logs = [line for line in logs if "pausing forwards" in line]
        self.assertEqual(len(paused_logs), 1)
        self.assertNotIn("fwdq retry fail", " ".join(logs))
        fq.drain(log=lambda *a: logs.append(" ".join(str(x) for x in a)))
        self.assertEqual(len(calls), 1)
        self.assertTrue(fq.forwarding_paused())
        self.assertEqual(len([line for line in logs if "pausing forwards" in line]), 1)


if __name__ == "__main__":
    unittest.main()
