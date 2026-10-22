#!/usr/bin/env python3
"""Send a scanner alert to the registered owner chat and remember message_id -> CA for reply-trading.
Usage:
  echo "<b>ORGANIC HYPE</b> ..." | send_alert.py --ca 0x.. --network robinhood --pool 0x.. --token SYM --tag "Organic Hype" --confidence high --human-score 72
  send_alert.py --ca 0x.. ... "alert text"          (text via args)
Text is HTML by default (--markdown for Markdown). A footer with the CA and suggested commands is appended.
Muted CAs (telegram/muted.json, toggled by the alert's Mute button or /mute) are skipped: exits 0 printing "muted: ...".
Exits 0 with a message if no owner has /start-ed the bot yet."""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")); import utm
ap = argparse.ArgumentParser()
ap.add_argument("text", nargs="*"); ap.add_argument("--ca"); ap.add_argument("--network", default="robinhood"); ap.add_argument("--pool")
ap.add_argument("--token"); ap.add_argument("--tag"); ap.add_argument("--confidence"); ap.add_argument("--human-score", type=float)
ap.add_argument("--markdown", action="store_true"); ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()
if a.ca and core.is_muted(a.ca): print(f"muted: {a.ca.lower()} is in telegram/muted.json - alert not sent."); sys.exit(0)
body = " ".join(a.text) if a.text else ("" if sys.stdin.isatty() else sys.stdin.read())
if not body.strip() and not a.ca: sys.exit("no alert text given")
md = a.markdown
if a.ca:
    ca = core.nca(a.ca, a.network); sym = a.token or "TOKEN"
    if md:
        pool = f" · [Pool]({utm.pool_url(a.network, a.pool, 'tg-alert-pool')})" if a.pool else ""
        token = f" · [Token]({utm.token_url(a.network, ca, 'tg-alert-token')})"
        foot = (f"\n\nCA: `{ca}`\nChain: {a.network}{pool}{token}" +
                f"\nPaper trade: `/buy {ca} 100 {a.network}`  ·  reply `buy 100` / `sell 50%`")
    else:
        pool = f" · <a href=\"{utm.html_href(utm.pool_url(a.network, a.pool, 'tg-alert-pool'))}\">Pool</a>" if a.pool else ""
        token = f" · <a href=\"{utm.html_href(utm.token_url(a.network, ca, 'tg-alert-token'))}\">Token</a>"
        foot = (f"\n\nCA: <code>{ca}</code>\nChain: {a.network}{pool}{token}" +
                f" · <a href=\"https://x.com/search?q={ca}&amp;f=live\">X</a>\n"
                "Tap a button, or reply in words / voice (e.g. <i>buy $100</i>, <i>sell half</i>).")
    body = body.rstrip() + foot
kb = core.alert_kb(a.ca.lower()) if a.ca else None
if a.dry_run: print(body); print("reply_markup:", __import__("json").dumps(kb)); sys.exit(0)
own = core.owner()
if not own: print("No Telegram owner registered yet (nobody has sent /start to the bot) - alert not sent."); sys.exit(0)
r = core.send(own["chat_id"], body, parse_mode="Markdown" if md else "HTML", reply_markup=kb)
if not r.get("ok"): print("Telegram send failed:", core.redact(r.get("description"))); sys.exit(1)
mid = r["result"]["message_id"]
if a.ca:
    c = core.db()
    c.execute("insert or replace into alerts values(?,?,?,?,?,?,?,?,?,?,?)", (mid, own["chat_id"], a.ca.lower(), a.network, a.pool, a.token,
              a.tag, a.confidence, a.human_score, body, core.now())); c.commit(); c.close()
print(f"sent alert message_id={mid}")
