"""Single place for the UTM tags appended to user-facing links that point at CoinGecko-owned sites
(coingecko.com, docs.coingecko.com, geckoterminal.com). API base URLs the code *calls* are never tagged.
Set MEMESCAN_UTM=0 to disable tagging."""
import os
from urllib.parse import urlsplit, urlunsplit
UTM_PARAMS = {"utm_source": "github", "utm_medium": "referral", "utm_campaign": "grokbot-memecoin-scanner"}
_HOSTS = ("coingecko.com", "geckoterminal.com")
_API = ("pro-api.coingecko.com", "api.coingecko.com", "stream.coingecko.com", "api.geckoterminal.com")
def query(placement):
    """-> 'utm_source=...&utm_content=<placement>' (no leading ?/&)."""
    return "&".join(f"{k}={v}" for k, v in {**UTM_PARAMS, "utm_content": placement}.items())
def tag(url, placement):
    """Append UTM params to a CoinGecko-owned link (before any #anchor). Other links are returned unchanged."""
    if os.environ.get("MEMESCAN_UTM", "1") == "0": return url
    p = urlsplit(url); host = (p.hostname or "").lower()
    if host in _API or not any(host == h or host.endswith("." + h) for h in _HOSTS): return url
    q = (p.query + "&" if p.query else "") + query(placement)
    return urlunsplit((p.scheme, p.netloc, p.path, q, p.fragment))
