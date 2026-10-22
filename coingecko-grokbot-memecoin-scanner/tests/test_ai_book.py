"""Phase-1 AI paper book: verdicts, human score, artificial chart, tuner, feature snapshot. Mock HTTP only."""
import io, json, os, shutil, sqlite3, sys, tempfile, time, unittest, urllib.error
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from urllib.request import Request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "lib"))
sys.path.insert(0, os.path.join(ROOT, "telegram"))
sys.path.insert(0, os.path.join(ROOT, "auto"))

import common as C
import human_pattern as HP
import artificial as ART
import features


def _http(status, payload):
    body = json.dumps(payload).encode()
    if status >= 400:
        raise urllib.error.HTTPError("https://api.coingecko.com/mock", status, "err", {}, io.BytesIO(body))
    class Resp:
        def read(self):
            return body
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
    return Resp()


class MockHTTP:
    """urlopen stand-in. `routes` is (predicate(url), status, payload)."""
    def __init__(self, routes):
        self.routes = routes
        self.urls = []
    def __call__(self, req, timeout=20):
        url = req.full_url if isinstance(req, Request) else str(req)
        self.urls.append(url)
        for pred, status, payload in self.routes:
            if pred(url):
                return _http(status, payload)
        return _http(404, {"status": {"error_code": 404, "error_message": "no route"}})


def _trade(addr, usd, ts, kind="buy", anomalous=False):
    return {"attributes": {
        "tx_from_address": addr, "kind": kind, "volume_in_usd": usd,
        "block_timestamp": ts, "block_number": 1, "is_anomalous": anomalous,
    }}


def _iso(i):
    return (datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc) + timedelta(seconds=i)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _diverse(n=12):
    sizes = [11, 37, 80, 19, 64, 28, 150, 7, 91, 44, 22, 130]
    gaps = [0, 4, 19, 27, 70, 71, 140, 260, 261, 500, 900, 1600]
    return [_trade("0x" + f"{i + 1:040x}", sizes[i], _iso(gaps[i])) for i in range(n)]


def _clock(n=12):
    addrs = ["0x" + "aa" * 20, "0x" + "bb" * 20]
    return [_trade(addrs[i % 2], 100, _iso(i * 10)) for i in range(n)]


def _staircase(n=12, dup=False):
    rows = []
    px = 1.0
    t0 = 1700000000
    for i in range(n):
        o = px
        c = round(px * 1.02, 8)
        t = t0 + i
        if dup:
            rows.append([t, o, round(o * 1.001, 8), round(o * 0.99, 8), round(o * 0.995, 8), 10])
            rows.append([t, round(o * 0.995, 8), c, round(o * 0.99, 8), c, 12])
        else:
            rows.append([t, o, max(o, c), min(o, c), c, 100])
        px = c
    return rows


def _noisy():
    spec = [
        (1.00, 1.20, 0.90, 1.04),
        (1.04, 1.08, 0.80, 0.92),
        (0.92, 1.30, 0.85, 1.15),
        (1.15, 1.18, 0.70, 0.88),
        (0.88, 1.40, 0.80, 1.22),
        (1.22, 1.25, 0.95, 1.01),
        (1.01, 1.50, 0.90, 1.35),
        (1.35, 1.36, 0.80, 0.97),
        (0.97, 1.10, 0.85, 1.08),
        (1.08, 1.40, 0.90, 0.93),
    ]
    rows = []
    t0 = 1700000000
    for i, (o, h, l, c) in enumerate(spec):
        rows.append([t0 + i * 37, o, h, l, c, 50 + i * 17])
    return rows


def _ohlcv_body(rows):
    return {"data": {"attributes": {"ohlcv_list": rows}}}


class HumanScoreTests(unittest.TestCase):
    def test_all_unknown_wallets_are_null_not_60(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        os.environ["WALLETDB"] = os.path.join(tmp.name, "wallets.db")
        import walletdb
        walletdb.DB = os.environ["WALLETDB"]
        wallets = [{"address": "0x" + f"{i:040x}", "chain": "base"} for i in range(1, 5)]
        buf = io.StringIO()
        with redirect_stdout(buf):
            walletdb.score_token({"token": "0x" + "cd" * 20, "chain": "base", "wallets": wallets})
        res = json.loads(buf.getvalue())
        self.assertIsNone(res["human_participation"])
        self.assertEqual(res["read"], "unknown")
        self.assertNotEqual(res["human_participation"], 60)
        c = walletdb.conn()
        c.execute("INSERT INTO wallets(address, chains, label, confidence) VALUES(?,?,?,?)",
                  (wallets[0]["address"], "base", "human", "high"))
        c.commit()
        buf = io.StringIO()
        with redirect_stdout(buf):
            walletdb.score_token({"token": "0x" + "cd" * 20, "chain": "base", "wallets": wallets[:3]})
        mixed = json.loads(buf.getvalue())
        self.assertEqual(mixed["human_participation"], 33.3)
        self.assertNotEqual(mixed["human_participation"], 60)
        buf = io.StringIO()
        with redirect_stdout(buf):
            walletdb.score_token({"token": "0x" + "cd" * 20, "chain": "base", "wallets": []})
        self.assertIsNone(json.loads(buf.getvalue())["human_participation"])

    def test_unknown_human_is_left_out_of_the_weighted_score(self):
        score, used = HP.weighted(
            {"human": None, "safety": 100, "momentum": 56},
            {"human": 0.35, "safety": 0.25, "momentum": 0.2},
        )
        self.assertEqual(score, 80.4)
        self.assertNotIn("human", used)
        self.assertAlmostEqual(sum(used.values()), 1.0, places=2)
        placeholder, _ = HP.weighted(
            {"human": 60, "safety": 100, "momentum": 56},
            {"human": 0.35, "safety": 0.25, "momentum": 0.2},
        )
        self.assertNotEqual(score, placeholder)

    def test_trade_pattern_estimate_over_mock_http(self):
        os.environ["CG_TIER"] = "demo"
        os.environ["COINGECKO_DEMO_API_KEY"] = "simulated-demo"
        os.environ.pop("COINGECKO_PRO_API_KEY", None)
        bot = _clock()
        human = _diverse()
        # Anomalous rows would dominate the score if they were counted.
        poisoned = [_trade("0x" + "11" * 20, 100, _iso(i), anomalous=True) for i in range(12)] + human
        routes = {
            "bot": bot, "human": human, "few": human[:5], "poison": poisoned,
        }
        seen = {}
        def urlopen(req, timeout=20):
            url = req.full_url
            seen.setdefault("urls", []).append(url)
            key = "bot"
            if "human-pool" in url: key = "human"
            elif "few-pool" in url: key = "few"
            elif "poison-pool" in url: key = "poison"
            self.assertIn("/pools/", url)
            self.assertIn("/trades", url)
            self.assertNotIn("simulated-demo", url)
            return _http(200, {"data": routes[key]})
        with patch("urllib.request.urlopen", urlopen):
            low = HP.from_pool("base", "bot-pool", liquidity=20000)
            high = HP.from_pool("base", "human-pool", liquidity=20000)
            few = HP.from_pool("base", "few-pool", liquidity=20000)
            clean = HP.from_pool("base", "poison-pool", liquidity=20000)
        self.assertEqual(low["source"], "trade-pattern estimate")
        self.assertLess(low["human_participation"], 40)
        self.assertTrue(any("clock" in r or "concentrated" in r or "uniform" in r for r in low["reasons"]))
        self.assertEqual(high["source"], "trade-pattern estimate")
        self.assertGreaterEqual(high["human_participation"], 80)
        self.assertIsNone(few["human_participation"])
        self.assertIsNone(few["source"])
        self.assertGreaterEqual(clean["human_participation"], 80)
        self.assertEqual(clean["n"], 12)
        wallet = {"human_participation": 90, "n_wallets": 4, "mix": {"human": 4, "unknown": 0}}
        hp, src = HP.choose(wallet, low, wallets_on=True)
        self.assertEqual((hp, src), (90, "wallet data"))
        hp, src = HP.choose(wallet, high, wallets_on=False)
        self.assertEqual(src, "trade-pattern estimate")
        self.assertEqual(hp, high["human_participation"])
        unknown = {"human_participation": None, "n_wallets": 4, "mix": {"unknown": 4}}
        hp, src = HP.choose(unknown, high, wallets_on=True)
        self.assertEqual(src, "trade-pattern estimate")


class ArtificialChartTests(unittest.TestCase):
    def setUp(self):
        os.environ["CG_TIER"] = "demo"
        os.environ["COINGECKO_DEMO_API_KEY"] = "simulated-demo"
        os.environ.pop("COINGECKO_PRO_API_KEY", None)

    def test_merge_duplicate_timestamps(self):
        rows = [
            [100, 1.0, 1.1, 0.9, 1.05, 10],
            [100, 1.05, 1.4, 0.8, 1.2, 5],
            [101, 1.2, 1.3, 1.15, 1.25, 3],
        ]
        candles, folded = ART.merge_ohlcv(rows)
        self.assertEqual(folded, 1)
        self.assertEqual(len(candles), 2)
        self.assertEqual(candles[0][1], 1.0)
        self.assertEqual(candles[0][2], 1.4)
        self.assertEqual(candles[0][3], 0.8)
        self.assertEqual(candles[0][4], 1.2)
        self.assertEqual(candles[0][5], 15)

    def test_staircase_clear_noisy_not_and_second_falls_back(self):
        dups = _staircase(dup=True)
        noisy = _noisy()
        plain = _staircase()
        def urlopen(req, timeout=20):
            url = req.full_url
            urlopen.urls.append(url)
            if "/ohlcv/second" in url and "aggregate=1" in url:
                return _http(200, _ohlcv_body(dups))
            if "/ohlcv/second" in url:
                return _http(400, {"status": {"error_code": 400, "error_message": "no second candles"}})
            if "/ohlcv/minute" in url and "noisy" in url:
                return _http(200, _ohlcv_body(noisy))
            if "/ohlcv/minute" in url:
                return _http(200, _ohlcv_body(plain))
            return _http(404, {})
        urlopen.urls = []
        with patch("urllib.request.urlopen", urlopen):
            young = ART.assess("base", "young-pool", age_min=5, liquidity=20000)
            old = ART.assess("base", "noisy-pool", age_min=90, liquidity=20000)
            seen = list(urlopen.urls)
            # Both second aggregates fail (4xx, no retry sleep). Minute candles are the fallback.
            def fallback(req, timeout=20):
                url = req.full_url
                fallback.urls.append(url)
                if "/ohlcv/second" in url:
                    return _http(400, {"status": {"error_code": 400, "error_message": "no second candles"}})
                if "/ohlcv/minute" in url:
                    return _http(200, _ohlcv_body(plain))
                return _http(404, {})
            fallback.urls = []
            with patch("urllib.request.urlopen", fallback):
                fell = ART.assess("base", "fallback-pool", age_min=2, liquidity=20000)
        self.assertEqual(young["band"], "clear")
        self.assertIn("staircase", " ".join(young["reasons"]))
        self.assertGreater(young["merged_duplicates"], 0)
        self.assertEqual(young["timeframe"], "1s")
        self.assertNotEqual(old["band"], "clear")
        self.assertLess(old.get("score") or 0, 55)
        self.assertTrue(any("/ohlcv/minute" in u and "noisy-pool" in u for u in seen))
        self.assertFalse(any("/ohlcv/second" in u and "noisy-pool" in u for u in seen))
        self.assertEqual(fell["band"], "clear")
        self.assertEqual(fell["timeframe"], "1m")
        self.assertTrue(any("/ohlcv/minute" in u for u in fallback.urls))
        self.assertGreaterEqual(sum("/ohlcv/second" in u for u in fallback.urls), 2)
        # Unmerged duplicates are not a clean staircase: the merge is what makes the score clear.
        raw, _ = ART.merge_ohlcv(dups)
        self.assertEqual(len(raw), 12)
        hit = ART.score_candles(raw)
        self.assertGreaterEqual(hit["score"], 75)

    def test_clock_rhythm_and_volume_without_buyers(self):
        pts, reasons = ART.score_trades(_clock(), liquidity=50000)
        self.assertTrue(any("clock-like" in r for r in reasons))
        self.assertGreaterEqual(pts, 20)
        fat = []
        for i in range(10):
            fat.append(_trade("0x" + ("aa" if i % 2 == 0 else "bb") * 20, 5000, _iso(i * i * 30)))
        pts, reasons = ART.score_trades(fat, liquidity=10000)
        self.assertTrue(any("volume without buyers" in r for r in reasons))
        self.assertGreaterEqual(pts, 30)


class TunerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = os.path.join(self.tmp.name, "auto.db")
        self.policy = os.path.join(self.tmp.name, "policy.json")
        shutil.copy(os.path.join(ROOT, "auto", "policy.json"), self.policy)
        os.environ["MEMESCAN_POLICY"] = self.policy
        os.environ["MEMESCAN_AUTO_DB"] = self.db
        self.c = sqlite3.connect(self.db)
        self.c.row_factory = sqlite3.Row
        self.c.executescript("""
            create table trades(id integer primary key, ts text, side text, ca text, tier text, qty real, realized_pnl real, source text);
            create table positions(ca text primary key);
            create table trade_features(buy_trade_id integer, human_source text);
        """)

    def _trip(self, n, pnl_each, source="wallet data", sell_source="risk-time", when="2026-10-20T12:00:00+00:00"):
        buy = n * 3
        self.c.execute("insert into trades values(?,?,?,?,?,?,?,?)", (buy, when, "buy", f"0x{n:040x}", "organic", 1, None, "auto"))
        self.c.execute("insert into trades values(?,?,?,?,?,?,?,?)", (buy + 1, when, "sell", f"0x{n:040x}", "organic", 0.4, pnl_each[0], sell_source))
        self.c.execute("insert into trades values(?,?,?,?,?,?,?,?)", (buy + 2, when, "sell", f"0x{n:040x}", "organic", 0.6, pnl_each[1], sell_source))
        self.c.execute("insert into trade_features(buy_trade_id, human_source) values(?,?)", (buy, source))
        self.c.commit()

    def _load(self):
        return json.load(open(self.policy))

    def _save(self, pol):
        json.dump(pol, open(self.policy, "w"), indent=1)

    def test_only_new_measured_positions_and_persists(self):
        import tuner
        for i in range(1, 6):
            self._trip(i, (10, 5))
        self.assertEqual(self.c.execute("select count(*) from trades where side='sell'").fetchone()[0], 10)
        pol = self._load()
        result = tuner.run(pol, tuner.round_trips(self.c))
        self.assertIsNone(result["skipped"])
        self.assertEqual(result["n"], 5)
        self.assertEqual(pol["tiers"]["organic"]["mult"], 1.1)
        self.assertEqual(pol["risk_overrides"]["time_stop"]["hours"], 3.5)
        self.assertEqual(len(pol["tuned_buy_ids"]), 5)
        self.assertIsNotNone(pol["last_tuned"])
        self.assertIsNotNone(pol["last_tune_check"])
        stamp = pol["last_tuned"]
        self._save(pol)
        # Restart: the watermark is the file, not process memory.
        pol2 = self._load()
        again = tuner.run(pol2, tuner.round_trips(self.c))
        self.assertIn("no new closed positions", again["skipped"])
        self.assertEqual(pol2["tiers"]["organic"]["mult"], 1.1)
        self.assertEqual(pol2["last_tuned"], stamp)
        self._trip(6, (10, 5), when="2026-10-21T12:00:00+00:00")
        pol3 = self._load()
        short = tuner.run(pol3, tuner.round_trips(self.c))
        self.assertEqual(short["skipped"], "fewer than 5 new closed positions")
        self.assertEqual(pol3["tiers"]["organic"]["mult"], 1.1)
        self.assertEqual(pol3["last_tuned"], stamp)
        self.assertEqual(len(pol3["tuned_buy_ids"]), 5)

    def test_unknown_human_source_does_not_move_sizes(self):
        import tuner
        for i in range(1, 7):
            self._trip(i, (-5, -5), source=None, sell_source="risk-stop")
        pol = self._load()
        result = tuner.run(pol, tuner.round_trips(self.c))
        self.assertEqual(result["skipped"], "no new closed positions with a measured human score")
        self.assertEqual(pol["tiers"]["organic"]["mult"], 1.0)
        self.assertIsNone(pol["last_tuned"])
        self.assertIsNotNone(pol["last_tune_check"])

    def test_legacy_watermark_is_not_applied_twice(self):
        import tuner
        for i in range(1, 5):
            self._trip(i, (10, 5), when="2026-10-01T00:00:00+00:00")
        self._trip(5, (10, 5), when="2026-10-22T00:00:00+00:00")
        pol = self._load()
        pol["last_tuned"] = "2026-10-15T00:00:00+00:00"
        pol["tuned_buy_ids"] = []
        result = tuner.run(pol, tuner.round_trips(self.c))
        self.assertEqual(result["n"], 1)
        self.assertEqual(result["skipped"], "fewer than 5 new closed positions")
        self.assertEqual(pol["tiers"]["organic"]["mult"], 1.0)


PROFILE = {"score": 0.9, "nondust_trades_10m": 30, "nondust_vol_10m": 8000, "green_share": 0.8,
           "largest_bar_share_of_gain": 0.2, "bars": 8}


class BookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._env = {k: os.environ.get(k) for k in (
            "MEMESCAN_HOME", "MEMESCAN_POLICY", "PAPER_DB", "BOOK", "PAPER_START_CASH",
            "CG_TIER", "COINGECKO_DEMO_API_KEY", "COINGECKO_PRO_API_KEY", "AUTO_DRY")}
        cls.tmp = tempfile.TemporaryDirectory()
        cls.home = cls.tmp.name
        os.environ["MEMESCAN_HOME"] = cls.home
        os.environ["BOOK"] = "auto"
        os.environ["PAPER_START_CASH"] = "10000"
        os.environ["CG_TIER"] = "demo"
        os.environ["COINGECKO_DEMO_API_KEY"] = "simulated-demo"
        os.environ.pop("COINGECKO_PRO_API_KEY", None)
        os.environ.pop("AUTO_DRY", None)
        import autotrader
        import core
        import entryfilters
        import sizing
        cls.auto = autotrader
        cls.core = core
        cls.entryfilters = entryfilters
        cls.sizing = sizing

    @classmethod
    def tearDownClass(cls):
        for k, v in cls._env.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v
        cls.tmp.cleanup()

    def setUp(self):
        self.home = self.tmp.name
        os.environ["MEMESCAN_HOME"] = self.home
        os.environ["MEMESCAN_POLICY"] = os.path.join(self.home, "policy.json")
        self.db_path = os.path.join(self.home, "auto.db")
        os.environ["PAPER_DB"] = self.db_path
        os.environ["BOOK"] = "auto"
        os.environ.pop("AUTO_DRY", None)
        for name in ("auto.db", "auto.db-wal", "auto.db-shm", "market.db", "market.db-wal", "market.db-shm"):
            p = os.path.join(self.home, name)
            if os.path.exists(p): os.remove(p)
        shutil.copy(os.path.join(ROOT, "auto", "policy.json"), os.environ["MEMESCAN_POLICY"])
        self.core.DB = self.db_path
        self.market = sqlite3.connect(os.path.join(self.home, "market.db"))
        self.market.execute("create table discoveries(key text primary key, ca text, network text, pool text, symbol text, seen_at text, stage text, reason text, score real, payload text)")
        self.market.commit()
        os.makedirs(os.path.join(self.home, "research"), exist_ok=True)
        self.state_path = os.path.join(self.home, "state.json")
        json.dump({"assessed": {}}, open(self.state_path, "w"))
        self.buy_calls = 0
        self.sell_calls = 0
        orig_buy, orig_sell = self.core.buy, self.core.sell
        def buy(*a, **k):
            self.buy_calls += 1
            return orig_buy(*a, **k)
        def sell(*a, **k):
            self.sell_calls += 1
            return orig_sell(*a, **k)
        self.patches = [
            patch.object(self.core, "quote", side_effect=self._quote),
            patch.object(self.core, "buy", buy),
            patch.object(self.core, "sell", sell),
            patch.object(self.entryfilters, "profile", return_value=dict(PROFILE)),
            patch.object(self.entryfilters, "ca_buzz", return_value={"authors": 2, "posts": 1, "src": ["test"]}),
            patch.object(self.entryfilters, "impersonation", return_value=None),
            patch.object(self.sizing, "recommend", return_value={}),
        ]
        for p in self.patches: p.start()
        self.addCleanup(self._stop)
        self.quote = {}

    def _stop(self):
        for p in self.patches: p.stop()
        self.market.close()

    def _quote(self, ca, chain=None):
        return dict(self.quote)

    def _research(self, n, **over):
        ca = "0x" + f"{n:040x}"
        pool = "0x" + f"{1000 + n:040x}"
        body = {
            "ca": ca, "network": "base", "pool": pool,
            "prelim_verdict": "Organic Hype?", "score": 82,
            "metrics": {"liq": 20000, "fdv": 80000, "age_min": 40, "h1_change": 40, "m5_change": 5,
                        "buyers_h1": 80, "sellers_h1": 20, "buys_h1": 100, "sells_h1": 30,
                        "vol_h1": 8000, "price": 0.001},
            "token": {"symbol": "TEST", "name": "Test", "is_honeypot": False, "is_nsfw": False,
                      "developer_holding_percentage": 1, "gt_score": 70, "gt_score_details": {"pool": 80},
                      "holders": 400, "categories": ["pump.fun"]},
            "holders": {"top10_pct_ex_pools": 22},
            "wallet_score": {"human_participation": 72, "human_source": "trade-pattern estimate", "read": "mostly human", "mix": {"human": 3}},
            "human_score_source": "trade-pattern estimate",
            "artificial_chart": {"score": 10, "band": "ok", "reasons": []},
            "flow_buy_share": 0.7, "fail_reasons": [], "dex": "uniswap",
            "buzz": {"unique_authors": 3, "quality": "mixed"},
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        body.update(over)
        path = os.path.join(self.home, "research", f"base_{ca}.json")
        json.dump(body, open(path, "w"))
        self.market.execute("insert into discoveries values(?,?,?,?,?,?,?,?,?,?)",
                            (f"base_{ca}", ca, "base", pool, "TEST", C.now_iso(), "deep:Organic Hype?", "", 82, path))
        self.market.commit()
        self.quote = {"network": "base", "ca": ca, "symbol": "TEST", "price": 0.001, "liquidity": 20000, "pool": pool}
        return ca, pool

    def _state(self, ca, verdict, rule="rule text"):
        st = json.load(open(self.state_path))
        st["assessed"][f"base_{ca}"] = {"ca": ca, "network": "base", "verdict": verdict, "rule": rule}
        json.dump(st, open(self.state_path, "w"))

    def _cycle(self):
        c = self.auto.adb()
        try:
            return c, self.auto.cycle(c)
        except Exception:
            c.close()
            raise

    def test_ai_discard_is_never_bought(self):
        ca, _ = self._research(1)
        self._state(ca, "discard", "wash volume")
        c, n = self._cycle()
        self.assertEqual(n, 0)
        self.assertEqual(self.buy_calls, 0)
        self.assertIsNone(c.execute("select 1 from positions").fetchone())
        seen = c.execute("select decision, why from auto_seen").fetchone()
        self.assertEqual(seen["decision"], "skip-hard")
        self.assertIn("AI discard", seen["why"])
        row = c.execute("select * from trade_features").fetchone()
        self.assertEqual(row["kind"], "discard")
        self.assertEqual(row["verdict_source"], "ai")
        self.assertIn("wash volume", row["ai_reason"])
        frozen = json.loads(row["research_json"])
        self.assertNotIn("_verdict_source", frozen)
        c.close()

    def test_pre_verdict_entry_exits_when_ai_later_discards(self):
        ca, _ = self._research(2)
        c, n = self._cycle()
        self.assertEqual(n, 1)
        self.assertEqual(self.buy_calls, 1)
        buy = c.execute("select * from trades where side='buy'").fetchone()
        self.assertEqual(buy["tier"], "pre_verdict")
        self.assertEqual(buy["verdict_source"], "early")
        self.assertLess(buy["usd_notional"], 100)
        feat = c.execute("select * from trade_features where kind='trade'").fetchone()
        self.assertEqual(feat["buy_trade_id"], buy["id"])
        self.assertEqual(feat["verdict_source"], "early")
        self.assertEqual(feat["human_source"], "trade-pattern estimate")
        self.assertEqual(feat["human_score"], 72)
        self.assertEqual(feat["artificial_score"], 10)
        self.assertEqual(feat["liq"], 20000)
        self.assertEqual(feat["fdv"], 80000)
        self.assertAlmostEqual(feat["liq_fdv"], 0.25)
        self.assertEqual(feat["chain"], "base")
        self.assertEqual(feat["dex"], "uniswap")
        self.assertIn("pump.fun", feat["launchpad"])
        self.assertEqual(feat["gt_score"], 70)
        self.assertEqual(feat["is_honeypot"], 0)
        self.assertEqual(feat["is_nsfw"], 0)
        self.assertEqual(feat["x_authors"], 2)
        self.assertIn("3", feat["x_fields"])
        self.assertIn("mixed", feat["x_fields"])
        self.assertEqual(feat["top10_pct"], 22)
        frozen = json.loads(feat["research_json"])
        self.assertEqual(frozen["ca"], ca)
        self.assertNotIn("_verdict_source", frozen)
        features.update_hold(c, ca, feat["entry_px"], feat["entry_px"] * 1.4, peak_px=feat["entry_px"] * 1.4,
                             opened_at=feat["decided_at"], liq=12000)
        c.commit()
        c.close()
        self._state(ca, "discard", "later wash")
        c, _ = self._cycle()
        self.assertEqual(self.sell_calls, 1)
        self.assertIsNone(c.execute("select 1 from positions where ca=?", (ca,)).fetchone())
        sell = c.execute("select * from trades where side='sell'").fetchone()
        self.assertEqual(sell["verdict_source"], "early")
        row = c.execute("select * from trade_features where kind='trade'").fetchone()
        self.assertIn("AI discard", row["exit_reason"])
        self.assertIsNotNone(row["exit_ts"])
        self.assertGreater(row["peak_px"], row["entry_px"])
        self.assertGreater(row["max_gain_pct"], 0)
        c.close()

    def test_keep_records_ai_disagreed(self):
        ca, _ = self._research(3)
        c, n = self._cycle()
        self.assertEqual(n, 1)
        c.close()
        pol = json.load(open(os.environ["MEMESCAN_POLICY"]))
        pol["on_ai_discard"] = "keep"
        json.dump(pol, open(os.environ["MEMESCAN_POLICY"], "w"))
        self._state(ca, "Discard", "bots")
        c, _ = self._cycle()
        self.assertEqual(self.sell_calls, 0)
        self.assertIsNotNone(c.execute("select 1 from positions where ca=?", (ca,)).fetchone())
        row = c.execute("select ai_later from trade_features where kind='trade'").fetchone()
        self.assertEqual(row["ai_later"], "AI disagreed")
        c.close()

    def test_ai_organic_is_not_tagged_pre_verdict(self):
        ca, _ = self._research(4)
        self._state(ca, "Organic Hype", "real buyers")
        c, n = self._cycle()
        self.assertEqual(n, 1)
        buy = c.execute("select tier, verdict_source, usd_notional from trades where side='buy'").fetchone()
        self.assertEqual(buy["tier"], "organic")
        self.assertEqual(buy["verdict_source"], "ai")
        self.assertGreater(buy["usd_notional"], 100)
        c.close()

    def test_clear_artificial_chart_is_not_bought(self):
        self._research(5, artificial_chart={"score": 90, "band": "clear", "reasons": ["staircase climb"]},
                       fail_reasons=["artificial chart: staircase climb"])
        c, n = self._cycle()
        self.assertEqual(n, 0)
        self.assertEqual(self.buy_calls, 0)
        why = c.execute("select why from auto_seen").fetchone()["why"]
        self.assertIn("artificial chart", why)
        c.close()


class FeatureFollowTests(unittest.TestCase):
    def test_post_exit_checkpoints_and_liquidity_writeoff(self):
        c = sqlite3.connect(":memory:")
        c.row_factory = sqlite3.Row
        features.ensure(c)
        past = (datetime.now().astimezone() - timedelta(hours=2)).isoformat(timespec="seconds")
        c.execute("""insert into trade_features(ca, network, kind, decided_at, ref_ts, ref_px, entry_px)
                     values(?,?,?,?,?,?,?)""", ("0x" + "ab" * 20, "base", "skip", past, past, 1.0, 1.0))
        c.commit()
        calls = []
        def fetch(net, cas):
            calls.append((net, list(cas)))
            return {cas[0]: 2.0}
        with patch.object(C, "last_price", return_value=None):
            n = features.follow_up(c, now=time.time(), fetch=fetch)
        self.assertEqual(n, 1)
        row = c.execute("select * from trade_features").fetchone()
        self.assertEqual(row["px_1h"], 2.0)
        self.assertAlmostEqual(row["ret_1h"], 1.0)
        self.assertIsNone(row["px_6h"])
        self.assertEqual(len(calls), 1)
        earlier = (datetime.now().astimezone() - timedelta(hours=7)).isoformat(timespec="seconds")
        c.execute("update trade_features set ref_ts=?, decided_at=?", (earlier, earlier))
        c.commit()
        with patch.object(C, "last_price", return_value=None):
            features.follow_up(c, now=time.time(), fetch=fetch)
        row = c.execute("select px_6h, px_24h from trade_features").fetchone()
        self.assertEqual(row["px_6h"], 2.0)
        self.assertIsNone(row["px_24h"])
        # Nothing due: no extra HTTP.
        fresh = datetime.now().astimezone().isoformat(timespec="seconds")
        c.execute("insert into trade_features(ca, network, kind, decided_at, ref_ts, ref_px) values(?,?,?,?,?,?)",
                  ("0x" + "cd" * 20, "base", "discard", fresh, fresh, 1))
        before = len(calls)
        with patch.object(C, "last_price", return_value=None):
            features.follow_up(c, now=time.time(), fetch=fetch)
        self.assertEqual(len(calls), before)
        c.execute("""insert into trade_features(ca, network, kind, entry_px, exit_ts, max_drawdown_pct)
                     values(?,?,?,?,?,?)""", ("0x" + "ef" * 20, "base", "trade", 1, None, -10))
        # Open the row the way record_exit finds it: exit_ts null.
        features.record_exit(c, "0x" + "ef" * 20, "liquidity collapse", "rug")
        rug = c.execute("select exit_return_pct, max_drawdown_pct, peak_px from trade_features where ca=?",
                        ("0x" + "ef" * 20,)).fetchone()
        self.assertEqual(rug["exit_return_pct"], -100)
        self.assertEqual(rug["max_drawdown_pct"], -100)

    def test_peak_is_archived_on_close(self):
        import importlib.util
        os.environ["BOOK"] = "auto"
        spec = importlib.util.spec_from_file_location("risk_engine", os.path.join(ROOT, "risk", "risk.py"))
        risk = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(risk)
        risk.BOOK = "auto"
        c = sqlite3.connect(":memory:")
        c.row_factory = sqlite3.Row
        C.pinit(c)
        risk.ensure_plan_cols(c)
        features.ensure(c)
        opened = datetime.now().astimezone().isoformat(timespec="seconds")
        c.execute("""insert into risk_plans(ca, network, pool, entry_px, opened_at, peak_px, trough_px, peak_at)
                     values(?,?,?,?,?,?,?,?)""", ("0x" + "11" * 20, "base", "0x" + "22" * 20, 1.0, opened, 1.8, 0.7, opened))
        c.execute("""insert into trade_features(ca, network, kind, entry_px, exit_ts) values(?,?,?,?,?)""",
                  ("0x" + "11" * 20, "base", "trade", 1.0, None))
        c.commit()
        risk.retire_plans(c, live=set())
        self.assertIsNone(c.execute("select 1 from risk_plans").fetchone())
        arch = c.execute("select peak_px, trough_px from risk_plan_archive").fetchone()
        self.assertEqual(arch["peak_px"], 1.8)
        self.assertEqual(arch["trough_px"], 0.7)
        row = c.execute("select peak_px, max_gain_pct from trade_features").fetchone()
        self.assertEqual(row["peak_px"], 1.8)
        self.assertGreater(row["max_gain_pct"], 0)


if __name__ == "__main__":
    unittest.main()
