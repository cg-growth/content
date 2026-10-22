"""Mock-HTTP checks for liquidity events, paper marks, NSFW discard, and anomalous trades."""
import json, os, sys, tempfile, time, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("MEMESCAN_HOME", ROOT)
os.environ.setdefault("DISCOVERY_DRY", "1")
sys.path.insert(0, os.path.join(ROOT, "lib"))
sys.path.insert(0, os.path.join(ROOT, "telegram"))
sys.path.insert(0, os.path.join(ROOT, "discovery"))

import common as C
import liquidity as L
import trades as TR
import clips


def _iso(seconds_ago):
    import datetime as D
    t = D.datetime.now(D.timezone.utc) - D.timedelta(seconds=seconds_ago)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


class LiquidityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._market = C.MARKET
        self._cg = C.cg
        self._env = {k: os.environ.get(k) for k in (
            "CG_TIER", "COINGECKO_DEMO_API_KEY", "COINGECKO_PRO_API_KEY",
            "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "MEMESCAN_NOTICES_FILE", "BOOK")}
        C.MARKET = os.path.join(self.tmp.name, "market.db")
        os.environ["MEMESCAN_NOTICES_FILE"] = os.path.join(self.tmp.name, "pending.json")
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        os.environ.pop("TELEGRAM_CHAT_ID", None)
        os.environ.pop("BOOK", None)
        self.calls = []

    def tearDown(self):
        C.cg = self._cg
        C.MARKET = self._market
        for k, v in self._env.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v
        self.tmp.cleanup()

    def _cg_routes(self, events=None):
        def fake(path, params=None, mc=None, timeout=25):
            self.calls.append((path, params))
            if "liquidity_events" in path:
                return {"data": events or []}
            return {"data": []}
        C.cg = fake

    def test_unsupported_chain_and_dex_skip_the_call(self):
        os.environ["CG_TIER"] = "analyst"
        os.environ["COINGECKO_PRO_API_KEY"] = "simulated-pro"
        os.environ.pop("COINGECKO_DEMO_API_KEY", None)
        self._cg_routes()
        for net, dex in (("base", "uniswap-v3"), ("bsc", "pancakeswap"), ("solana", ""), ("solana", "raydium")):
            hit = L.research_events(net, "pool", dex, "Dev", 50000)
            self.assertEqual(hit["skipped"], "unsupported")
            self.assertFalse(hit["called"])
            self.assertEqual(hit["reason"], "")
        self.assertEqual(self.calls, [])

    def test_demo_and_basic_skip_events_and_tip_once_on_a_solana_drop(self):
        dev = "DevWallet11111111111111111111111111111111"
        drop = {"pct": 62, "before": 100000, "after": 38000, "kind": "pool", "window_min": 5}
        for tier, key_env in (("demo", "COINGECKO_DEMO_API_KEY"), ("basic", "COINGECKO_PRO_API_KEY")):
            self.calls.clear()
            C.MARKET = os.path.join(self.tmp.name, tier + ".db")
            os.environ["CG_TIER"] = tier
            os.environ[key_env] = "simulated-" + tier
            if tier == "demo": os.environ.pop("COINGECKO_PRO_API_KEY", None)
            else: os.environ.pop("COINGECKO_DEMO_API_KEY", None)
            self._cg_routes()
            skipped = L.research_events("solana", "POOL", "pumpswap", dev, 100000)
            self.assertEqual(skipped["skipped"], "plan")
            self.assertFalse(skipped["called"])
            notes = []
            L.handle_drop({"network": "solana", "pool": "POOL", "ca": "ca-" + tier}, drop, "pumpswap", dev, C.mdb(), notes.append)
            self.assertTrue(notes)
            self.assertIn("pool reserve fell", notes[0])
            self.assertNotIn("liquidity_events", " ".join(p for p, _ in self.calls))
            import plan_tips
            q = plan_tips.pending()
            self.assertEqual(len(q), 1)
            self.assertEqual(q[0]["trigger"], "liquidity_gap")
            self.assertIn("who removed it and how much", q[0]["text"])
            self.assertIn("a CoinGecko API Analyst plan or higher", q[0]["text"])
            self.assertIn("utm_source=grokbot", q[0]["text"])
            self.assertIn("utm_content=tg-plan-tip", q[0]["text"])
            self.assertIn("https://www.coingecko.com/en/api/pricing", q[0]["text"])
            L.handle_drop({"network": "solana", "pool": "POOL", "ca": "ca-" + tier}, drop, "pumpswap", dev, C.mdb(), notes.append)
            self.assertEqual(len(plan_tips.pending()), 1)
            self.assertEqual(self.calls, [])

    def test_base_drop_alerts_without_events_or_a_plan_tip(self):
        os.environ["CG_TIER"] = "demo"
        os.environ["COINGECKO_DEMO_API_KEY"] = "simulated-demo"
        os.environ.pop("COINGECKO_PRO_API_KEY", None)
        self._cg_routes()
        notes = []
        drop = {"pct": 55, "before": 80000, "after": 20000, "kind": "pool", "window_min": 5}
        L.handle_drop({"network": "base", "pool": "0xpool", "ca": "0xca"}, drop, "uniswap-v3", "", C.mdb(), notes.append)
        self.assertIn("pool reserve fell", notes[0])
        self.assertIn("geckoterminal.com", notes[0])
        self.assertIn("utm_content=tg-liq-alert", notes[0])
        self.assertEqual(self.calls, [])
        import plan_tips
        self.assertEqual(plan_tips.pending(), [])

    def test_deployer_removal_is_a_discard_reason(self):
        os.environ["CG_TIER"] = "analyst"
        os.environ["COINGECKO_PRO_API_KEY"] = "simulated-pro"
        os.environ.pop("COINGECKO_DEMO_API_KEY", None)
        dev = "SoLanaDevAddress111111111111111111111111"
        self._cg_routes([{"attributes": {
            "kind": "remove", "volume_in_usd": "38000", "tx_from_address": dev,
            "block_timestamp": _iso(120), "tx_hash": "tx1",
        }}])
        hit = L.research_events("solana", "POOL", "pump-swap", dev, 100000)
        self.assertTrue(hit["called"])
        self.assertEqual(hit["reason"], "deployer removed $38k")
        self.assertEqual(self.calls[0][1]["kind"], "remove")
        self.assertNotIn("include_anomalous", self.calls[0][1])
        text = L.alert_text("solana", "POOL", {"pct": 40, "before": 100000, "after": 60000, "kind": "pool", "window_min": 5},
                            {"volume": 38000, "deployer": True, "at": _iso(120), "address": dev})
        self.assertEqual(text, "Liquidity removed: $38k by the deployer wallet 2 min ago. Exit may not fill.")
        html = L.alert_html("solana", "POOL", None, {"volume": 38000, "deployer": True, "at": _iso(120), "address": dev})
        self.assertIn("utm_content=tg-liq-alert", html)
        self.assertIn("https://www.geckoterminal.com/", html)
        import scout
        ok, _cav, hard = scout.classify({
            "fail_reasons": [hit["reason"]], "ca": "ca", "token": {"name": "T", "symbol": "T"},
            "metrics": {"liq": 50000, "h1_change": 80, "buyers_h1": 80, "vol_h1": 9000, "buys_h1": 40, "sells_h1": 10, "m5_change": 5, "age_min": 30},
            "wallet_score": {"human_participation": 90, "read": "ok"}, "holders": {"top10_pct_ex_pools": 10}, "score": 80, "flow_buy_share": 0.8,
        })
        self.assertFalse(ok)
        self.assertIn("deployer removed", hard or "")

    def test_large_removal_versus_reserve(self):
        rows = [{"volume_in_usd": 40000, "tx_from_address": "OtherWallet", "block_timestamp": _iso(60)}]
        hit = L.assess_removes(rows, "DevWallet", 100000, "solana")
        self.assertEqual(hit["reason"], "removed $40k (40% of reserve)")
        small = L.assess_removes([{"volume_in_usd": 100, "tx_from_address": "OtherWallet"}], "DevWallet", 100000, "solana")
        self.assertEqual(small["reason"], "")

    def test_total_loss_write_off_and_partial_pull_valuation(self):
        import core
        rugged = L.mark(5000, 1, 1000, "solana")
        self.assertEqual(rugged["status"], "illiquid / rugged")
        self.assertEqual(rugged["value"], 0.0)
        partial = L.mark(1000, 1, 4000, "solana")
        paid = clips.fill(1000, 4000, "solana")
        self.assertEqual(partial["status"], "partial liquidity")
        self.assertEqual(partial["value"], paid["net"])
        self.assertNotEqual(partial["value"], 1000)
        self.assertGreater(partial["value"], 0)
        dust = L.mark(0.01, 1, 100000, "solana")
        self.assertNotEqual(dust["status"], "illiquid / rugged")
        self.assertFalse(L.should_auto_exit("human", 1, "illiquid / rugged"))
        self.assertFalse(L.should_auto_exit("auto", 0, "illiquid / rugged"))
        self.assertTrue(L.should_auto_exit("auto", 1, "illiquid / rugged"))
        orig_cfg = C.risk_cfg
        C.risk_cfg = lambda: {"liquidity": {"exit_max_impact_pct": 95}}
        try:
            kept = L.mark(5000, 1, 1000, "solana")
            self.assertNotEqual(kept["status"], "illiquid / rugged")
            self.assertGreater(kept["value"], 0)
        finally:
            C.risk_cfg = orig_cfg
        prev_db = core.DB
        core.DB = os.path.join(self.tmp.name, "paper.db")
        prev_quote = core.quote
        ca = "SoLanaCA1111111111111111111111111111111111"
        pool = "Pool111111111111111111111111111111111111"
        def quote(ca_, chain=None):
            return {"network": "solana", "ca": ca_, "symbol": "RUG", "name": "Rug", "price": 1.0, "liquidity": 1000, "pool": pool}
        core.quote = quote
        try:
            c = core.db()
            t = core.now()
            c.execute("insert into positions values(?,?,?,?,?,?,?,?,?,?,?)",
                      (ca, "solana", pool, "RUG", 5000, 5000, "Watch", "low", 70, t, t))
            c.commit()
            rows = core.mtm(c)
            self.assertEqual(rows[0]["liq_status"], "illiquid / rugged")
            self.assertEqual(rows[0]["value"], 0.0)
            shown = core.handle(c, "/positions")
            self.assertIn("illiquid / rugged", shown)
            out = core.sell(c, ca, "all", source="cmd")
            self.assertIn("illiquid / rugged", out)
            self.assertIn("total loss", out)
            self.assertIsNone(c.execute("select 1 from positions where ca=?", (ca,)).fetchone())
            trade = c.execute("select realized_pnl, source, usd_notional from trades where side='sell'").fetchone()
            self.assertEqual(trade["usd_notional"], 0)
            self.assertLess(trade["realized_pnl"], 0)
            self.assertIn("illiquid / rugged", trade["source"])
            sys.path.insert(0, os.path.join(ROOT, "alerts"))
            import report
            self.assertEqual(report.reason(trade["source"]), "ILLIQUID")
            self.assertEqual(report.reason("risk-liq_pull"), "DANGER")
            c.execute("insert into positions values(?,?,?,?,?,?,?,?,?,?,?)",
                      (ca, "solana", pool, "PART", 1000, 1000, "Watch", "low", 70, t, t))
            c.commit()
            core.quote = lambda ca_, chain=None: {"network": "solana", "ca": ca_, "symbol": "PART", "price": 1.0, "liquidity": 4000, "pool": pool}
            mid = core.mtm(c)[0]
            self.assertEqual(mid["liq_status"], "partial liquidity")
            self.assertEqual(mid["value"], clips.fill(1000, 4000, "solana")["net"])
            self.assertIn("partial liquidity", core.handle(c, "/positions"))
            c.close()
        finally:
            core.quote = prev_quote
            core.DB = prev_db

    def test_nsfw_discard_and_toggle(self):
        os.environ["CG_TIER"] = "demo"
        os.environ["COINGECKO_DEMO_API_KEY"] = "simulated-demo"
        os.environ.pop("COINGECKO_PRO_API_KEY", None)
        import discovery
        calls = []
        def fake_cg(path, params=None, mc=None, timeout=25):
            calls.append(path.split("?")[0])
            if path.endswith("/info"):
                return {"data": {"attributes": {"name": "Test", "symbol": "NSFW", "is_honeypot": False,
                                                 "is_nsfw": True, "developer_holding_percentage": 0, "holders": {}}}}
            return {"data": []}
        orig = C.cg
        C.cg = fake_cg
        import subprocess
        orig_run = subprocess.run
        def fake_run(cmd, input=None, capture_output=True, text=True, timeout=60):
            class R:
                stdout = "{}"
                returncode = 0
            if cmd and "score-token" in " ".join(cmd):
                R.stdout = json.dumps({"human_participation": 100, "mix": {"human": 4}, "bundles": [], "read": "ok"})
            return R()
        subprocess.run = fake_run
        discovery.subprocess.run = fake_run
        m = {"liq": 20000, "fdv": 80000, "age_min": 30, "h1_change": 400, "buyers_h1": 80, "sellers_h1": 20,
             "buys_h1": 100, "sells_h1": 40, "vol_h1": 5000, "m5_change": 5, "pool_created_at": "2026-01-01T00:00:00Z",
             "name": "Test", "price": 0.001}
        ca = "0x" + "ab" * 20
        key = "base_" + ca
        os.makedirs(os.path.join(ROOT, "research"), exist_ok=True)
        path = os.path.join(ROOT, "research", f"base_{ca}.json")
        try:
            discovery.mc.execute("insert or replace into discoveries(key, ca, network, pool, seen_at, stage) values(?,?,?,?,?,?)",
                                 (key, ca, "base", "0x" + "22" * 20, C.now_iso(), "new"))
            discovery.mc.commit()
            discovery._deep(key, "base", "0x" + "22" * 20, ca, m)
            payload = json.load(open(path))
            self.assertEqual(payload["prelim_verdict"], "discard")
            self.assertTrue(payload["token"]["is_nsfw"])
            self.assertIn("NSFW token (name or symbol flagged)", payload["fail_reasons"])
            self.assertIn("NSFW", payload.get("reason_line") or "")
            self.assertEqual(payload["liquidity_events"]["called"], False)
            self.assertFalse(any("liquidity_events" in p for p in calls))
            import scout
            ok, _c, hard = scout.classify(payload)
            self.assertFalse(ok)
            self.assertIn("nsfw", (hard or "").lower())
        finally:
            C.cg = orig
            subprocess.run = orig_run
            discovery.subprocess.run = orig_run
            try: os.remove(path)
            except OSError: pass
            discovery.mc.execute("delete from discoveries where key=?", (key,))
            discovery.mc.commit()

    def test_anomalous_trades_are_not_buyers(self):
        rows = [
            {"attributes": {"kind": "buy", "volume_in_usd": "25", "tx_from_address": "HumanWallet", "is_anomalous": False,
                            "block_number": 1, "block_timestamp": "2026-06-01T00:00:00Z"}},
            {"attributes": {"kind": "buy", "volume_in_usd": "9000", "tx_from_address": "AnomWallet", "is_anomalous": True,
                            "block_number": 2, "block_timestamp": "2026-06-01T00:00:01Z"}},
            {"attributes": {"kind": "buy", "volume_in_usd": "10", "tx_from_address": "Plain", "block_number": 3, "block_timestamp": "2026-06-01T00:00:02Z"}},
        ]
        ws, skipped = TR.accumulate(rows, "solana", lambda addr, net: addr)
        self.assertEqual(skipped, 1)
        self.assertNotIn("AnomWallet", ws)
        self.assertEqual(ws["HumanWallet"]["buy"], 25)
        self.assertEqual(ws["Plain"]["buy"], 10)


if __name__ == "__main__":
    unittest.main()
