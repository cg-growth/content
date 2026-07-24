import hmac
import hashlib


def verify_signature(
    raw_body: bytes,
    timestamp: str,
    event_id: str,
    signature_header: str,
    secret: str,
) -> bool:
    # Build the signing string exactly as CoinGecko does.
    # The body MUST be the raw bytes received, not a re-serialised
    # version, or the hash will not match.
    signing_string = f"{timestamp}:{event_id}:".encode("utf-8") + raw_body

    expected = hmac.new(
        secret.encode("utf-8"),
        signing_string,
        hashlib.sha256,
    ).hexdigest()

    # Constant-time compare to avoid timing attacks
    return hmac.compare_digest(expected, signature_header or "")
