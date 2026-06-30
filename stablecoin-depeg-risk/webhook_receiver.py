from fastapi import FastAPI, Request, HTTPException
from datetime import datetime
import hmac, hashlib, os

app = FastAPI()
SECRET = os.environ["CG_WEBHOOK_SECRET"]
WATCHLIST = set()  # populate from your /coins/markets stablecoin list


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def fmt(value):
    # Compact contract addresses, mark removed fields, leave other values intact
    if value is None:
        return "<removed>"
    s = str(value)
    return f"{s[:8]}...{s[-6:]}" if s.startswith("0x") and len(s) > 20 else s


@app.post("/cg-webhook")
async def handle(req: Request):
    body = await req.body()  # raw bytes are required for signature verification
    ts, eid, sig = (req.headers.get(h, "") for h in ("x-cg-timestamp", "x-cg-event-id", "x-cg-signature"))
    if not (ts and eid and sig):
        raise HTTPException(400, "Missing CoinGecko headers")

    expected = hmac.new(SECRET.encode(), f"{ts}:{eid}:{body.decode()}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(401, "Invalid signature")

    data = (await req.json()).get("data", {})
    if data.get("id") not in WATCHLIST:  # filter the global event firehose to stablecoins
        return {"status": "ignored"}

    log(f"Event: cg.coin.info.updated  coin: {data.get('id')} ({data.get('name')})")
    for change in data.get("changes", []):
        field = change.get("field", "")
        if field == "public_notices" or field.startswith("platforms."):
            ct = change.get("change_type", "update")
            log(f"  {field:<20} | {ct:<8} | {fmt(change.get('new_value'))}")
    return {"status": "ok"}
