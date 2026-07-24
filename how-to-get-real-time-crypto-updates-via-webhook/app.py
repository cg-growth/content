import os
import json
import time
from flask import Flask, request, abort
from dotenv import load_dotenv
from verify import verify_signature

load_dotenv()
SECRET = os.getenv("COINGECKO_WEBHOOK_SECRET", "")
MAX_AGE_SECONDS = 300  # Reject deliveries older than 5 minutes (replay window)

app = Flask(__name__)

# Idempotency store: tracks event_ids already processed so retries do not
# double-fire downstream actions. In-memory set works for a single-instance
# dev server. Production deployments should swap this for a shared store
# (Redis, DynamoDB, or a database table with a TTL) so multiple workers stay
# consistent and the set survives restarts.
seen_event_ids = set()
SEEN_MAX = 10_000  # Cap memory in the dev server


@app.post("/")
def coingecko_webhook():
    raw_body = request.get_data()
    signature = request.headers.get("x-cg-signature", "")
    timestamp = request.headers.get("x-cg-timestamp", "")
    event_id = request.headers.get("x-cg-event-id", "")

    # 1. Required headers present
    if not (signature and timestamp and event_id):
        abort(400)

    # 2. Replay protection: drop deliveries with an old timestamp
    try:
        if abs(time.time() - int(timestamp)) > MAX_AGE_SECONDS:
            abort(401)
    except ValueError:
        abort(400)

    # 3. HMAC signature verification
    if not verify_signature(raw_body, timestamp, event_id, signature, SECRET):
        # Do not 200 a bad request — CoinGecko will retry on non-2xx,
        # which is correct behaviour for legitimate transient failures.
        abort(401)

    # 4. Idempotency: skip events already processed.
    # CoinGecko retries up to 14 times on failure, and the event_id is a
    # unique UUID per delivery. Without this check, the same change can
    # fire your downstream actions multiple times.
    if event_id in seen_event_ids:
        return ("", 204)  # Acknowledge the retry; we already handled it
    seen_event_ids.add(event_id)
    if len(seen_event_ids) > SEEN_MAX:
        seen_event_ids.clear()  # Crude eviction; production: use TTL store

    # 5. Parse + 6. Dispatch — wrapped together so a malformed payload or
    # downstream exception still returns 204 instead of cascading into
    # a 5xx retry storm.
    try:
        payload = json.loads(raw_body)
        event_type = payload.get("event_type")

        if event_type == "cg.coin.info.updated":
            handle_coin_info_updated(payload, event_id=event_id)
        else:
            app.logger.warning("Unhandled event_type: %s", event_type)

    except Exception:
        # Log the raw body for forensic review, then ack so CoinGecko
        # does not retry a delivery we cannot process. Reserve real 5xx
        # responses for cases where retry is genuinely useful.
        app.logger.exception("Failed to process delivery %s: %s", event_id, raw_body)

    return ("", 204)


def handle_coin_info_updated(payload: dict, event_id: str) -> None:
    # Routing logic lives in the next section
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
