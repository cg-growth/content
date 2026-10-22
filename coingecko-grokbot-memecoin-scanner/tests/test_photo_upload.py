"""Telegram card upload: stale-session retry, ok:false, text fallback, card size, cards/ cleanup."""
import os, sys, tempfile, time, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("MEMESCAN_HOME", ROOT)
sys.path.insert(0, os.path.join(ROOT, "lib"))
sys.path.insert(0, os.path.join(ROOT, "telegram"))
sys.path.insert(0, os.path.join(ROOT, "alerts"))

import requests
import core
import portfolio
import tg_ext
import pf_html as H


class JsonResp:
    def __init__(self, body, status=200):
        self._body = body
        self.status_code = status
    def json(self):
        return self._body


class _Sess:
    def __init__(self, test):
        self.test = test
        self.posts = []
        test.made.append(self)
    def post(self, url, data=None, files=None, timeout=None):
        fh = files["photo"]
        fh.read(8)
        self.posts.append({"timeout": timeout, "fh": fh, "url": url, "data": data})
        item = self.test.script.pop(0)
        if isinstance(item, BaseException): raise item
        return item


class PhotoUploadTests(unittest.TestCase):
    def setUp(self):
        self.token = "999:SHOULDNOTLEAK"
        os.environ["TELEGRAM_BOT_TOKEN"] = self.token
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "card.png")
        with open(self.path, "wb") as f: f.write(b"\x89PNG\r\n\x1a\nfake-card")
        self.sent = []
        self.made = []
        self.script = []
        core._SESS.s = None
        self._send, self._session = core.send, core.session
        def send(chat_id, text, parse_mode="HTML", reply_to=None, reply_markup=None):
            self.sent.append({"chat_id": chat_id, "text": text, "reply_to": reply_to, "reply_markup": reply_markup})
            return {"ok": True, "result": {"message_id": 1}}
        def session():
            s = getattr(core._SESS, "s", None)
            if s is None:
                s = _Sess(self); core._SESS.s = s
            return s
        core.send = send
        core.session = session

    def tearDown(self):
        core.send = self._send
        core.session = self._session
        core._SESS.s = None
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)

    def test_connection_error_retries_fresh_session_then_text(self):
        err = requests.exceptions.ConnectionError(
            "('Connection aborted.', TimeoutError('The write operation timed out')) /bot%s/sendPhoto" % self.token)
        self.script = [err, err]
        kb = {"inline_keyboard": [[{"text": "🔄 Refresh", "callback_data": "arf"}]]}
        r = portfolio.send_photo(7, self.path, "📈 <b>AI</b> card", kb, reply_to=3)
        self.assertFalse(r["ok"])
        self.assertNotIn(self.token, r["description"])
        self.assertIn("<redacted>", r["description"])
        self.assertEqual(len(self.made), 2)
        self.assertIsNot(self.made[0], self.made[1])
        self.assertEqual(self.made[0].posts[0]["timeout"], (20, 90))
        self.assertTrue(self.made[0].posts[0]["fh"].closed)
        self.assertTrue(self.made[1].posts[0]["fh"].closed)
        self.assertEqual(len(self.sent), 1)
        self.assertIn("📈 <b>AI</b> card", self.sent[0]["text"])
        self.assertIn("Card image failed to upload.", self.sent[0]["text"])
        self.assertEqual(self.sent[0]["reply_markup"], kb)
        self.assertEqual(self.sent[0]["reply_to"], 3)
        self.assertNotIn(self.token, self.sent[0]["text"])

    def test_retry_succeeds_on_fresh_session_without_fallback(self):
        err = requests.exceptions.ConnectionError("Connection aborted.", TimeoutError("The write operation timed out"))
        self.script = [err, JsonResp({"ok": True, "result": {"message_id": 9}})]
        r = portfolio.send_photo(7, self.path, "cap")
        self.assertTrue(r["ok"])
        self.assertEqual(r["result"]["message_id"], 9)
        self.assertEqual(len(self.made), 2)
        self.assertEqual(self.sent, [])

    def test_ok_false_retries_then_text_fallback(self):
        self.script = [
            JsonResp({"ok": False, "description": "Bad Request"}),
            JsonResp({"ok": False, "description": "still no %s" % self.token}),
        ]
        kb = {"inline_keyboard": [[{"text": "🔄 Refresh", "callback_data": "rc"}]]}
        r = portfolio.send_photo(1, self.path, "Report card", kb)
        self.assertFalse(r["ok"])
        self.assertNotIn(self.token, r["description"])
        self.assertIn("<redacted>", r["description"])
        self.assertIn("still no", r["description"])
        self.assertEqual(len(self.made), 2)
        self.assertEqual(len(self.sent), 1)
        self.assertIn("Report card", self.sent[0]["text"])
        self.assertIn("Card image failed to upload.", self.sent[0]["text"])
        self.assertEqual(self.sent[0]["reply_markup"], kb)

    def test_ok_false_then_success_skips_fallback(self):
        self.script = [JsonResp({"ok": False, "description": "fail"}), JsonResp({"ok": True, "result": {"message_id": 5}})]
        r = portfolio.send_photo(1, self.path, "cap")
        self.assertEqual(r["result"]["message_id"], 5)
        self.assertEqual(self.sent, [])

    def test_non_json_retries_on_fresh_session(self):
        class Bad:
            status_code = 502
            def json(self): raise ValueError("Expecting value")
        self.script = [Bad(), JsonResp({"ok": True, "result": {"message_id": 4}})]
        r = portfolio.send_photo(1, self.path, "x")
        self.assertTrue(r["ok"])
        self.assertEqual(len(self.made), 2)
        self.assertEqual(self.sent, [])


class CardFileTests(unittest.TestCase):
    def test_prune_keeps_newest_per_kind_and_cached(self):
        d = tempfile.mkdtemp()
        for kind in ("portfolio", "autoreport", "AbCdEf1234"):
            for i in range(5):
                p = os.path.join(d, "%s_%s.png" % (kind, i))
                with open(p, "wb") as f: f.write(b"png")
                os.utime(p, (i, 1000 + i))
        for day, stamp in (("2026-10-01", 1), ("2026-10-02", 2), ("2026-10-03", 3), ("2026-10-04", 4)):
            p = os.path.join(d, "recap_%s.png" % day)
            with open(p, "wb") as f: f.write(b"png")
            os.utime(p, (stamp, 2000 + stamp))
        tg_ext._CACHE["portfolio"] = (os.path.join(d, "portfolio_0.png"), "cap", time.time())
        try:
            tg_ext.prune_cards(d, keep=3)
            left = set(os.listdir(d))
        finally:
            tg_ext._CACHE.pop("portfolio", None)
        self.assertEqual(left & {n for n in left if n.startswith("portfolio_")},
                         {"portfolio_0.png", "portfolio_2.png", "portfolio_3.png", "portfolio_4.png"})
        self.assertIn("autoreport_4.png", left)
        self.assertNotIn("autoreport_1.png", left)
        self.assertIn("recap_2026-10-04.png", left)
        self.assertIn("recap_2026-10-02.png", left)
        self.assertNotIn("recap_2026-10-01.png", left)
        self.assertNotIn("AbCdEf1234_0.png", left)
        self.assertIn("AbCdEf1234_4.png", left)

    def test_tighten_caps_a_large_card_and_leaves_a_small_png(self):
        from PIL import Image
        import random
        big = os.path.join(tempfile.mkdtemp(), "big.png")
        im = Image.new("RGB", (1080, 3600), (11, 14, 26))
        px = im.load(); rnd = random.Random(1)
        for y in range(0, 3600, 2):
            for x in range(0, 1080, 2):
                px[x, y] = (rnd.randrange(40), rnd.randrange(40), rnd.randrange(80))
        im.save(big, format="PNG")
        self.assertGreater(os.path.getsize(big), 300_000)
        H.tighten(big, limit=300_000)
        self.assertLessEqual(os.path.getsize(big), 300_000)
        small = os.path.join(tempfile.mkdtemp(), "small.png")
        Image.new("RGB", (40, 40), (7, 9, 16)).save(small)
        H.tighten(small, limit=300_000)
        with open(small, "rb") as f: self.assertEqual(f.read(8), b"\x89PNG\r\n\x1a\n")

    def test_shoot_uses_device_scale_one(self):
        import subprocess
        from PIL import Image
        seen = {}
        def run(cmd, **kw):
            seen["cmd"] = cmd
            out = [a.split("=", 1)[1] for a in cmd if str(a).startswith("--screenshot=")][0]
            Image.new("RGB", (30, 30), (10, 12, 20)).save(out)
            return subprocess.CompletedProcess(cmd, 0)
        old_run, old_bin = H.subprocess.run, H.chrome_bin
        H.subprocess.run = run
        H.chrome_bin = lambda: "chrome"
        try:
            dest = os.path.join(tempfile.mkdtemp(), "card.png")
            H.shoot("<html></html>", dest, 400)
        finally:
            H.subprocess.run, H.chrome_bin = old_run, old_bin
        joined = " ".join(seen["cmd"])
        self.assertIn("--force-device-scale-factor=1", joined)
        self.assertNotIn("--force-device-scale-factor=2", joined)
        self.assertTrue(os.path.isfile(dest))


if __name__ == "__main__":
    unittest.main()
