"""Link tracking parameters for user-facing links to CoinGecko-owned sites
(coingecko.com, docs.coingecko.com, geckoterminal.com). API base URLs the code calls are never tagged.
Set MEMESCAN_UTM=0 to disable tagging.

`source` defaults to "github" for repo docs. Messages the running scanner shows pass source="grokbot".
"""
import os
from urllib.parse import urlsplit, urlunsplit
UTM_MEDIUM = "referral"
UTM_CAMPAIGN = "grokbot-memecoin-scanner"
PRICING_URL = "https://www.coingecko.com/en/api/pricing"
DEVELOPER_DASHBOARD_URL = "https://www.coingecko.com/en/developers/dashboard"
_HOSTS = ("coingecko.com", "geckoterminal.com")
_API = ("pro-api.coingecko.com", "api.coingecko.com", "stream.coingecko.com", "api.geckoterminal.com",
        "mcp.pro-api.coingecko.com", "mcp.api.coingecko.com")
def query(placement, source="github"):
    """-> 'utm_source=...&utm_content=<placement>' (no leading ?/&)."""
    params = {"utm_source": source, "utm_medium": UTM_MEDIUM, "utm_campaign": UTM_CAMPAIGN, "utm_content": placement}
    return "&".join(f"{k}={v}" for k, v in params.items())
def tag(url, placement, source="github"):
    """Append link tracking parameters to a CoinGecko-owned link (before any #anchor). Other links are unchanged."""
    if os.environ.get("MEMESCAN_UTM", "1") == "0": return url
    p = urlsplit(url); host = (p.hostname or "").lower()
    if host in _API or not any(host == h or host.endswith("." + h) for h in _HOSTS): return url
    q = (p.query + "&" if p.query else "") + query(placement, source)
    return urlunsplit((p.scheme, p.netloc, p.path, q, p.fragment))
def pricing(placement, source="grokbot"):
    return tag(PRICING_URL, placement, source)
def developer_dashboard(placement, source="grokbot"):
    """Developer Dashboard API keys section. The fragment stays after the query string."""
    return tag(DEVELOPER_DASHBOARD_URL + "#api-keys", placement, source)
def pool_url(network, pool_address, placement="tg-alert-pool", source="grokbot"):
    """GeckoTerminal pool page. placement examples: tg-alert-pool, dashboard-pool."""
    return tag(f"https://www.geckoterminal.com/{network}/pools/{pool_address}", placement, source)
def token_url(network, ca, placement="tg-alert-token", source="grokbot"):
    """GeckoTerminal token page. placement examples: tg-alert-token, dashboard-token."""
    return tag(f"https://www.geckoterminal.com/{network}/tokens/{ca}", placement, source)
def html_href(url):
    """Escape & for an HTML href. The URL itself is already tagged."""
    return str(url).replace("&", "&amp;")
