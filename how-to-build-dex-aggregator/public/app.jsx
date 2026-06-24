const { useEffect, useMemo, useState } = React;

const USAGE_LIMIT = 5;
const USAGE_STORAGE_KEY = 'dexAggregator.usageCount';
const PAYWALL_STORAGE_KEY = 'dexAggregator.paywallUnlocked';

// Minimal curated token directory for easier UX (symbol -> address per network)
const TOKEN_DIRECTORY = {
  eth: [
    { symbol: 'WETH', address: '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2' },
    { symbol: 'USDC', address: '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48' },
    { symbol: 'USDT', address: '0xdAC17F958D2ee523a2206206994597C13D831ec7' },
  ],
  base: [
    { symbol: 'WETH', address: '0x4200000000000000000000000000000000000006' },
    { symbol: 'USDC', address: '0x833589fCD6EDB6E08f4c7C32D4f71B54B68c7f0b' },
  ],
  arbitrum: [
    { symbol: 'WETH', address: '0x82aF49447D8a07e3bd95BD0d56f35241523FbAB1' },
    { symbol: 'USDC', address: '0xaf88d065e77c8cC2239327C5EDb3A432268e5831' },
    { symbol: 'USDT', address: '0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9' },
  ],
  polygon_pos: [
    { symbol: 'WETH', address: '0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619' },
    { symbol: 'USDC', address: '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174' },
    { symbol: 'USDT', address: '0xc2132D05D31c914a87C6611C10748AEb04B58e8F' },
  ],
  optimism: [
    { symbol: 'WETH', address: '0x4200000000000000000000000000000000000006' },
    { symbol: 'USDC.e', address: '0x7F5c764cBc14f9669B88837ca1490cCa17c31607' },
    { symbol: 'USDT', address: '0x94b008aA00579c1307B0EF2c499aD98a8ce58e58' },
  ],
};

function parseFeePercentFromName(name) {
  if (!name) return null;
  const m = name.match(/(\d+(?:\.\d+)?)%/);
  return m ? parseFloat(m[1]) : null;
}

function safeNum(x) {
  const n = Number(x);
  return Number.isFinite(n) ? n : null;
}

// Estimated Output = Input Amount * price_factor * (1 - fee%)
function estimateOutput({ amountIn, priceFactor, feePercent }) {
  const fee = (Number(feePercent) || 0) / 100;
  return amountIn * priceFactor * (1 - fee);
}

function shortAddr(addr) {
  if (!addr) return '-';
  const s = String(addr);
  return s.length > 10 ? s.slice(0, 6) + '...' + s.slice(-4) : s;
}

function formatNumber(n) {
  if (!Number.isFinite(n)) return '-';
  if (Math.abs(n) >= 1) return n.toLocaleString(undefined, { maximumFractionDigits: 6 });
  return n.toPrecision(6);
}

function mapPoolToRow(pool, { amount, from, to }) {
  const attr = pool.attributes || {};
  const rel = pool.relationships || {};
  const dexId = rel.dex?.data?.id || 'unknown';
  const name = attr.name || '';
  const address = attr.address;

  const baseId = rel.base_token?.data?.id || '';
  const quoteId = rel.quote_token?.data?.id || '';
  const fromLc = from.toLowerCase();
  const toLc = to.toLowerCase();
  const baseAddr = baseId.split('_')[1] || '';
  const quoteAddr = quoteId.split('_')[1] || '';

  let priceFactor = null; // to_token per from_token
  if (baseAddr === fromLc && quoteAddr === toLc) {
    priceFactor = safeNum(attr.base_token_price_quote_token);
  } else if (baseAddr === toLc && quoteAddr === fromLc) {
    priceFactor = safeNum(attr.quote_token_price_base_token);
  } else {
    const p1 = safeNum(attr.base_token_price_quote_token);
    const p2 = safeNum(attr.quote_token_price_base_token);
    priceFactor = Number.isFinite(p1) ? p1 : p2;
  }
  if (!Number.isFinite(priceFactor)) return null;

  const feePercent = safeNum(attr.pool_fee_percentage) ?? parseFeePercentFromName(name);
  const estimatedOutput = estimateOutput({ amountIn: amount, priceFactor, feePercent });
  const priceDisplay = formatNumber(priceFactor) + ' ' + shortAddr(to) + ' / ' + shortAddr(from);

  return {
    dexName: dexId,
    price: priceDisplay,
    liquidityUsd: safeNum(attr.reserve_in_usd),
    feePercent: feePercent,
    address,
    estimatedOutput,
  };
}

function App() {
  const [network, setNetwork] = useState('eth');
  const [from, setFrom] = useState('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2');
  const [to, setTo] = useState('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48');
  const [amount, setAmount] = useState('1');
  const [status, setStatus] = useState('');
  const [networks, setNetworks] = useState([
    { id: 'eth', name: 'Ethereum' },
    { id: 'base', name: 'Base' },
    { id: 'solana', name: 'Solana' },
    { id: 'polygon_pos', name: 'Polygon POS' },
    { id: 'arbitrum', name: 'Arbitrum' },
    { id: 'optimism', name: 'Optimism' },
  ]);
  const [rows, setRows] = useState([]);
  const [fromSearch, setFromSearch] = useState('');
  const [toSearch, setToSearch] = useState('');
  const [fromResults, setFromResults] = useState([]);
  const [toResults, setToResults] = useState([]);
  const [usageCount, setUsageCount] = useState(0);
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [showPaywall, setShowPaywall] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [paywallError, setPaywallError] = useState('');
  const [paywallEnabled, setPaywallEnabled] = useState(true);

  const remainingSearches = (!paywallEnabled || isUnlocked) ? null : Math.max(0, USAGE_LIMIT - usageCount);
  const tokensForNetwork = useMemo(() => TOKEN_DIRECTORY[network] || [], [network]);

  useEffect(() => {
    if (tokensForNetwork.length >= 2) {
      setFrom(tokensForNetwork[0].address);
      setTo(tokensForNetwork[1].address);
    } else {
      setFrom('');
      setTo('');
    }
    setFromSearch(''); setToSearch(''); setFromResults([]); setToResults([]);
  }, [network]);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const syncFromStorage = () => {
      try {
        const storedUsage = window.localStorage.getItem(USAGE_STORAGE_KEY);
        if (storedUsage != null) {
          const parsed = Number(storedUsage);
          if (Number.isFinite(parsed)) setUsageCount(parsed);
        }
        const unlocked = window.localStorage.getItem(PAYWALL_STORAGE_KEY) === 'paid';
        setIsUnlocked(unlocked);
      } catch (_) {}
    };
    syncFromStorage();
    const handler = () => syncFromStorage();
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetch('/api/paywall/status')
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return;
        const active = Boolean(data?.active);
        setPaywallEnabled(active);
        if (!active) {
          setIsUnlocked(true);
        }
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const paywallParam = params.get('paywall');
    if (!paywallParam) return;
    if (paywallParam === 'cancelled') {
      setPaywallError('Checkout was cancelled. You can try again when ready.');
      setStatus('Free search limit reached. Unlock unlimited access to continue.');
      setShowPaywall(true);
    } else if (paywallParam === 'success') {
      setStatus('Payment confirmed. Unlimited searches unlocked.');
      setShowPaywall(false);
    }
    params.delete('paywall');
    const qs = params.toString();
    const nextUrl = qs ? `${window.location.pathname}?${qs}${window.location.hash}` : `${window.location.pathname}${window.location.hash}`;
    window.history.replaceState({}, '', nextUrl);
  }, []);

  useEffect(() => {
    if (isUnlocked) {
      setShowPaywall(false);
      setUsageCount(0);
      try {
        if (typeof window !== 'undefined') {
          window.localStorage.removeItem(USAGE_STORAGE_KEY);
        }
      } catch (_) {}
    }
  }, [isUnlocked]);

  useEffect(() => {
    if (!paywallEnabled || isUnlocked) return;
    if (usageCount >= USAGE_LIMIT) {
      setStatus('Free search limit reached. Unlock unlimited access to continue.');
      setShowPaywall(true);
    }
  }, [paywallEnabled, isUnlocked, usageCount]);

  useEffect(() => {
    const term = fromSearch.trim();
    if (term.length < 2) { setFromResults([]); return; }
    const ctrl = new AbortController();
    const t = setTimeout(async () => {
      try {
        const r = await fetch(`/api/token-search?network=${encodeURIComponent(network)}&q=${encodeURIComponent(term)}&limit=8`, { signal: ctrl.signal });
        const data = await r.json();
        setFromResults(Array.isArray(data?.data) ? data.data : []);
      } catch {}
    }, 250);
    return () => { clearTimeout(t); ctrl.abort(); };
  }, [fromSearch, network]);

  useEffect(() => {
    const term = toSearch.trim();
    if (term.length < 2) { setToResults([]); return; }
    const ctrl = new AbortController();
    const t = setTimeout(async () => {
      try {
        const r = await fetch(`/api/token-search?network=${encodeURIComponent(network)}&q=${encodeURIComponent(term)}&limit=8`, { signal: ctrl.signal });
        const data = await r.json();
        setToResults(Array.isArray(data?.data) ? data.data : []);
      } catch {}
    }, 250);
    return () => { clearTimeout(t); ctrl.abort(); };
  }, [toSearch, network]);

  useEffect(() => {
    fetch('/api/networks')
      .then((r) => r.json())
      .then((data) => {
        const extra = (data?.data || []).map((n) => ({ id: n.id, name: n.attributes?.name || n.id }));
        const setIds = new Set(networks.map((n) => n.id));
        const merged = networks.concat(extra.filter((n) => !setIds.has(n.id)));
        setNetworks(merged);
      })
      .catch(() => {});
  }, []);

  const startCheckout = async () => {
    setCheckoutLoading(true);
    setPaywallError('');
    try {
      const response = await fetch('/api/paywall/create-session', { method: 'POST' });
      let payload = {};
      try {
        payload = await response.json();
      } catch (_) {}
      if (!response.ok) {
        if (response.status === 503) {
          throw new Error('Checkout is not available yet. Please configure Stripe credentials.');
        }
        throw new Error(payload?.error || 'Failed to start checkout.');
      }
      if (payload?.url) {
        window.location.href = payload.url;
        return;
      }
      throw new Error('Checkout URL missing.');
    } catch (err) {
      console.error(err);
      setPaywallError(err?.message || 'Unable to start checkout.');
    } finally {
      setCheckoutLoading(false);
    }
  };

  const onSearch = async () => {
    const amt = parseFloat(String(amount).trim());
    if (!from || !to || !Number.isFinite(amt) || amt <= 0) {
      setStatus('Please enter valid inputs (addresses and amount).');
      return;
    }
    if (paywallEnabled && !isUnlocked && usageCount >= USAGE_LIMIT) {
      setStatus('Free search limit reached. Unlock unlimited access to continue.');
      setShowPaywall(true);
      return;
    }

    if (paywallEnabled && !isUnlocked) {
      setShowPaywall(false);
      setPaywallError('');
      setUsageCount((prev) => {
        const nextCount = prev + 1;
        try {
          if (typeof window !== 'undefined') {
            window.localStorage.setItem(USAGE_STORAGE_KEY, String(nextCount));
          }
        } catch (_) {}
        return nextCount;
      });
    }

    setStatus('Fetching pools...');
    setRows([]);
    try {
      const res = await fetch(`/api/pools?network=${encodeURIComponent(network)}&from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`);
      if (!res.ok) throw new Error('Network error');
      const payload = await res.json();
      const pools = payload?.data || [];
      const mapped = pools
        .map((p) => mapPoolToRow(p, { amount: amt, from, to }))
        .filter(Boolean)
        .sort((a, b) => (b.estimatedOutput ?? 0) - (a.estimatedOutput ?? 0));
      setRows(mapped);
      setStatus(mapped.length ? `Found ${mapped.length} pools. Sorted by best Estimated Output.` : 'No pools found for this pair.');
    } catch (e) {
      console.error(e);
      setStatus('Failed to fetch pools.');
    }
  };

  return (
    <div className="container">
      <h1>DEX Aggregator Dashboard</h1>
      <section className="form-section">
        <div className="field">
          <label htmlFor="network">Network</label>
          <select id="network" value={network} onChange={(e) => setNetwork(e.target.value)}>
            {networks.map((n) => (
              <option key={n.id} value={n.id}>{n.name}</option>
            ))}
          </select>
        </div>

        <div className="field field--wide">
          <label>From Token (contract address)</label>
          <div className="token-row">
            <select value={from || '__custom__'} onChange={(e) => { const v = e.target.value; setFrom(v === '__custom__' ? '' : v); }}>
              {tokensForNetwork.map((t) => (<option key={t.symbol} value={t.address}>{t.symbol}</option>))}
              <option value="__custom__">Custom address...</option>
            </select>
            <input placeholder="Search symbol or name (e.g., USDC)" value={fromSearch} list="fromSuggestions"
              onChange={(e) => setFromSearch(e.target.value)}
              onBlur={(e) => { const picked = fromResults.find(x => x.address.toLowerCase() === e.target.value.toLowerCase()); if (picked) setFrom(picked.address); }} />
            <datalist id="fromSuggestions">
              {fromResults.map((r) => (<option key={r.address} value={r.address} label={`${(r.symbol || '').toUpperCase()} - ${r.name || ''} - ${shortAddr(r.address)}`} />))}
            </datalist>
          </div>
          <input className="token-address" placeholder="0x..." value={from} onChange={(e) => setFrom(e.target.value)} />
        </div>

        <div className="swap-col">
          <button className="swap-btn" title="Swap" onClick={() => { const a = from; setFrom(to); setTo(a); }}>Swap</button>
        </div>

        <div className="field field--wide">
          <label>To Token (contract address)</label>
          <div className="token-row">
            <select value={to || '__custom__'} onChange={(e) => { const v = e.target.value; setTo(v === '__custom__' ? '' : v); }}>
              {tokensForNetwork.map((t) => (<option key={t.symbol} value={t.address}>{t.symbol}</option>))}
              <option value="__custom__">Custom address...</option>
            </select>
            <input placeholder="Search symbol or name (e.g., WETH)" value={toSearch} list="toSuggestions"
              onChange={(e) => setToSearch(e.target.value)}
              onBlur={(e) => { const picked = toResults.find(x => x.address.toLowerCase() === e.target.value.toLowerCase()); if (picked) setTo(picked.address); }} />
            <datalist id="toSuggestions">
              {toResults.map((r) => (<option key={r.address} value={r.address} label={`${(r.symbol || '').toUpperCase()} - ${r.name || ''} - ${shortAddr(r.address)}`} />))}
            </datalist>
          </div>
          <input className="token-address" placeholder="0x..." value={to} onChange={(e) => setTo(e.target.value)} />
        </div>

        <div className="field">
          <label htmlFor="amount">Input Amount</label>
          <input id="amount" type="number" min="0" step="any" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="e.g., 1" />
          <div className="chip-row">
            {['0.1','1','5','10'].map(v => (
              <button key={v} type="button" className="chip" onClick={() => setAmount(v)}>{v}</button>
            ))}
          </div>
        </div>

        <div className="actions">
          <button onClick={onSearch} disabled={checkoutLoading}>Find Pools</button>
          {isUnlocked ? (
            <div className="usage-note usage-note--unlocked">Unlimited searches unlocked</div>
          ) : (
            <div className="usage-note">{remainingSearches > 0 ? `${remainingSearches} free searches left` : 'No free searches left'}</div>
          )}
        </div>
      </section>

      <section className="results-section">
        <h2>Results</h2>
        <div className="status">{status}</div>
        <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>DEX Name</th>
              <th>Price</th>
              <th>Pool Liquidity (USD)</th>
              <th>Pool Fee (%)</th>
              <th>Pool Address</th>
              <th className="prominent">Estimated Output</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.address + i} className={i === 0 ? 'best-row' : ''}>
                <td>{i === 0 ? <span className="badge">Best</span> : null}{r.dexName}</td>
                <td>{r.price}</td>
                <td>${formatNumber(r.liquidityUsd)}</td>
                <td>{r.feePercent != null ? r.feePercent : '-'}</td>
                <td>
                  <span className="addr">{shortAddr(r.address)}</span>
                  <button className="copy-btn" onClick={async () => { try { await navigator.clipboard.writeText(r.address); } catch {} }}>Copy</button>
                </td>
                <td className="prominent">{formatNumber(r.estimatedOutput)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </section>

      {showPaywall && (
        <div className="modal-overlay" role="dialog" aria-modal="true">
          <div className="modal-card">
            <h3>Unlock unlimited searches</h3>
            <p>You have used all {USAGE_LIMIT} free searches. Upgrade to keep exploring the best pools.</p>
            {paywallError ? <div className="modal-error">{paywallError}</div> : null}
            <div className="modal-actions">
              <button onClick={startCheckout} disabled={checkoutLoading}>
                {checkoutLoading ? 'Redirecting...' : 'Unlock with Stripe'}
              </button>
              <button type="button" className="secondary" onClick={() => setShowPaywall(false)} disabled={checkoutLoading}>
                Maybe later
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
