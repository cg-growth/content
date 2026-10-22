# Telegram paper-trading bridge
- Started by the top-level `./start.sh` supervisor (restart loop `memescan-telegram-loop`) when `TELEGRAM_BOT_TOKEN` is set; passes through optional `TELEGRAM_CHAT_ID`, `TELEGRAM_FORWARD_URL` / `TELEGRAM_FORWARD_KEY`. Secrets are inherited only, never written/logged.
  Owner: `TELEGRAM_CHAT_ID` if set, otherwise the first private chat that sends `/start` (saved to `owner.json`, git-ignored). Other chats get "unauthorized".
  To pick up new env vars: `./stop.sh && ./start.sh`.
- `send_alert.py` — sends alerts with inline buttons (Buy $50/$100/$250/Custom · Sell 25%/50%/All · Positions/Mute).
- `daemon.py` — long-poll handler: commands, buttons (callback_query), natural language (`nl.py`, confirm with Yes/No), voice notes (`voice.py`, faster-whisper base.en CPU int8), fallback forwarding.
- **muted.json** — `{ "<ca lowercase>": {"symbol": "...", "muted_at": "..."} }`. Written by the alert Mute button or `/mute <CA|ticker>` (`/unmute`, `/muted`). `send_alert.py` exits 0 printing `muted: ...` for a muted CA, so the scanner should also skip muted CAs (`core.is_muted(ca)`).
- Forwarding: unparsed text/transcripts are POSTed as JSON `{text, chat_id, message_id, reply_to_ca, source}` with `Authorization: Bearer <key>` and `X-Api-Key: <key>`; bot replies instantly "⏳ On it, researching… ~1–3 min"; the routine must check `core.py recent-trade <ca> <side> 10` before any trade. Without the URL it replies with a usage hint.
- Tests (throwaway DB, Telegram + prices mocked, no network): `../.venv/bin/python tests/test_bridge.py` from this folder.
