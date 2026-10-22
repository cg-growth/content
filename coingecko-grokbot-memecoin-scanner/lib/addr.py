"""Per-chain address normalisation. EVM (0x + 40 hex) -> lowercase. Solana / other base58 -> case preserved
(base58 is case-sensitive: lowercasing makes a different, usually invalid, address; CoinGecko then returns empty data)."""
import re
EVM_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
SOL_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
EVM_FIND = re.compile(r"(?<![0-9a-zA-Z])0x[0-9a-fA-F]{40}(?![0-9a-fA-F])")
SOL_FIND = re.compile(r"(?<![1-9A-HJ-NP-Za-km-z/=.])[1-9A-HJ-NP-Za-km-z]{32,44}(?![1-9A-HJ-NP-Za-km-z])")
EVM_NETS = {"robinhood", "base", "bsc", "eth", "arbitrum", "polygon_pos", "optimism", "avax", "linea"}
NON_EVM_NETS = {"solana"}
def is_evm(a): return bool(EVM_RE.match((a or "").strip()))
def is_sol(a):
    a = (a or "").strip(); return bool(SOL_RE.match(a)) and not a.startswith("0x")
def norm(a, chain=None):
    """EVM -> lower; base58 -> unchanged. chain hint wins when given (solana never lowercased)."""
    a = (a or "").strip()
    if not a: return a
    if chain in NON_EVM_NETS: return a
    return a.lower() if a.lower().startswith("0x") else a
def same(a, b): return norm(a) == norm(b)
def chain_family(a): return "evm" if is_evm(a) else "solana" if is_sol(a) else None
def find_cas(text):
    """-> list of CAs in text (EVM lowercased, base58 as-is; base58 needs a digit and mixed case to avoid words)."""
    t = re.sub(r"https?://\S+", " ", text or ""); out = [m.lower() for m in EVM_FIND.findall(t)]; t = EVM_FIND.sub(" ", t)
    out += [m for m in SOL_FIND.findall(t) if re.search(r"\d", m) and re.search(r"[a-z]", m) and re.search(r"[A-Z]", m)]
    return list(dict.fromkeys(out))
