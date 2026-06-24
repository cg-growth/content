require('dotenv').config();
const express = require('express');
const axios = require('axios');
const path = require('path');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3000;

const Stripe = process.env.STRIPE_SECRET_KEY ? require('stripe') : null;
const stripe = Stripe ? new Stripe(process.env.STRIPE_SECRET_KEY, { apiVersion: '2024-06-20' }) : null;
const STRIPE_PRICE_ID = process.env.STRIPE_PRICE_ID;
const STRIPE_PRODUCT_ID = process.env.STRIPE_PRODUCT_ID;
const PUBLIC_BASE_URL = process.env.PUBLIC_BASE_URL || (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : null);
const PAYWALL_SUCCESS_PATH = '/paywall-success.html';
function resolveBaseUrl() {
  if (PUBLIC_BASE_URL) return PUBLIC_BASE_URL.replace(/\/$/, '');
  const localPort = process.env.PORT || 3000;
  return `http://localhost:${localPort}`;
}
const PAYWALL_BASE_URL = resolveBaseUrl();

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Basic request logging for the app server
app.use((req, _res, next) => {
  const ts = new Date().toISOString();
  console.log(`[APP] ${ts} ${req.method} ${req.originalUrl}`);
  if (Object.keys(req.query || {}).length) {
    console.log(`[APP] query`, req.query);
  }
  next();
});

const DEMO_KEY = process.env.CG_DEMO_API_KEY;
const PRO_KEY = process.env.CG_PRO_API_KEY;

// Per docs, the endpoints we use are available on Demo; use Demo only (no runtime fallback).
const BASE = 'https://api.coingecko.com/api/v3/onchain';
const PRO_BASE = 'https://pro-api.coingecko.com/api/v3';

async function cgFetch(pathname, params = {}) {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== null)).toString();
  const fullUrl = `${BASE}${pathname}${qs ? `?${qs}` : ''}`;
  const headers = DEMO_KEY ? { 'x-cg-demo-api-key': DEMO_KEY } : undefined;
  const ts = Date.now();
  console.log(`[CG] GET ${fullUrl}`);
  console.log(`[CG] headers:`, headers ? Object.keys(headers) : 'none');
  try {
    const r = await axios.get(`${BASE}${pathname}`, {
      params,
      headers,
      timeout: 15000,
      validateStatus: () => true,
    });
    const ms = Date.now() - ts;
    let bodyStr;
    try { bodyStr = JSON.stringify(r.data); } catch { bodyStr = undefined; }
    const len = bodyStr ? bodyStr.length : undefined;
    console.log(`[CG] -> status ${r.status} in ${ms}ms${len ? `, bytes~${len}` : ''}`);
    if (bodyStr) {
      const cap = 10000; // print response (truncated if large)
      const preview = bodyStr.length > cap ? bodyStr.slice(0, cap) + '... (truncated)' : bodyStr;
      console.log(`[CG] body: ${preview}`);
    }
    if (r.status >= 200 && r.status < 300) return r.data;
    const err = new Error(`CG request failed with status ${r.status}`);
    err.response = r;
    throw err;
  } catch (e) {
    const status = e?.response?.status || '';
    let errBody;
    try { errBody = JSON.stringify(e?.response?.data); } catch { errBody = undefined; }
    console.error(`[CG][ERR] ${fullUrl} ${status} ${e.message}`);
    if (errBody) console.error(`[CG][ERR] body: ${errBody}`);
    throw e;
  }
}

// PRO fetcher (used only for endpoints that are Pro-only, e.g., /search and /coins/{id})
async function cgProFetch(pathname, params = {}) {
  if (!PRO_KEY) throw new Error('Missing CG_PRO_API_KEY for Pro endpoint');
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== null)).toString();
  const fullUrl = `${PRO_BASE}${pathname}${qs ? `?${qs}` : ''}`;
  const headers = { 'x-cg-pro-api-key': PRO_KEY };
  const ts = Date.now();
  console.log(`[CG-PRO] GET ${fullUrl}`);
  console.log(`[CG-PRO] headers:`, Object.keys(headers));
  try {
    const r = await axios.get(`${PRO_BASE}${pathname}`, {
      params,
      headers,
      timeout: 15000,
      validateStatus: () => true,
    });
    const ms = Date.now() - ts;
    let bodyStr;
    try { bodyStr = JSON.stringify(r.data); } catch { bodyStr = undefined; }
    const len = bodyStr ? bodyStr.length : undefined;
    console.log(`[CG-PRO] -> status ${r.status} in ${ms}ms${len ? `, bytes~${len}` : ''}`);
    if (bodyStr) {
      const cap = 10000;
      const preview = bodyStr.length > cap ? bodyStr.slice(0, cap) + '... (truncated)' : bodyStr;
      console.log(`[CG-PRO] body: ${preview}`);
    }
    if (r.status >= 200 && r.status < 300) return r.data;
    const err = new Error(`CG-PRO request failed with status ${r.status}`);
    err.response = r;
    throw err;
  } catch (e) {
    const status = e?.response?.status || '';
    let errBody;
    try { errBody = JSON.stringify(e?.response?.data); } catch { errBody = undefined; }
    console.error(`[CG-PRO][ERR] ${fullUrl} ${status} ${e.message}`);
    if (errBody) console.error(`[CG-PRO][ERR] body: ${errBody}`);
    throw e;
  }
}

const PAYWALL_ACTIVE = Boolean(stripe && (STRIPE_PRICE_ID || STRIPE_PRODUCT_ID));

let cachedStripePriceId = null;
async function resolveStripePriceId() {
  if (!stripe) return null;
  if (STRIPE_PRICE_ID) return STRIPE_PRICE_ID;
  if (cachedStripePriceId) return cachedStripePriceId;
  if (!STRIPE_PRODUCT_ID) return null;
  try {
    const prices = await stripe.prices.list({ product: STRIPE_PRODUCT_ID, active: true, limit: 1 });
    const price = Array.isArray(prices?.data) ? prices.data[0] : null;
    if (!price?.id) {
      throw new Error('No active price found for product ' + STRIPE_PRODUCT_ID);
    }
    cachedStripePriceId = price.id;
    return cachedStripePriceId;
  } catch (err) {
    console.error('[PAYWALL][ERR] resolve price', err?.message || err);
    throw err;
  }
}

app.post('/api/paywall/create-session', async (_req, res) => {
  if (!stripe || (!STRIPE_PRICE_ID && !STRIPE_PRODUCT_ID)) {
    return res.status(503).json({ error: 'Paywall not configured' });
  }
  try {
    const priceId = await resolveStripePriceId();
    if (!priceId) {
      return res.status(503).json({ error: 'Paywall not configured' });
    }
    const session = await stripe.checkout.sessions.create({
      line_items: [{ price: priceId, quantity: 1 }],
      mode: 'payment',
      allow_promotion_codes: true,
      success_url: `${PAYWALL_BASE_URL}${PAYWALL_SUCCESS_PATH}?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${PAYWALL_BASE_URL}/?paywall=cancelled`,
    });
    res.json({ url: session.url });
  } catch (err) {
    console.error('[PAYWALL][ERR] create-session', err?.message || err);
    res.status(500).json({ error: 'Failed to start checkout', details: err?.message || 'Unknown error' });
  }
});
app.get('/api/paywall/checkout-session/:id', async (req, res) => {
  if (!stripe) {
    return res.status(503).json({ error: 'Paywall not configured' });
  }
  const { id } = req.params;
  if (!id) return res.status(400).json({ error: 'Missing session id' });
  try {
    const session = await stripe.checkout.sessions.retrieve(id);
    res.json({
      id: session.id,
      payment_status: session.payment_status,
      amount_total: session.amount_total,
      currency: session.currency,
    });
  } catch (err) {
    console.error('[PAYWALL][ERR] checkout-session', err?.message || err);
    res.status(500).json({ error: 'Failed to verify checkout session', details: err?.message || 'Unknown error' });
  }
});

app.get('/api/paywall/status', (_req, res) => {
  res.json({ active: PAYWALL_ACTIVE });
});

// Cache coingecko asset platform id per onchain network id
const platformIdCache = new Map();
async function getPlatformIdForNetwork(networkId) {
  if (platformIdCache.has(networkId)) return platformIdCache.get(networkId);
  const resp = await cgFetch('/networks');
  const arr = Array.isArray(resp?.data) ? resp.data : [];
  for (const n of arr) {
    const id = n?.id; const pid = n?.attributes?.coingecko_asset_platform_id;
    if (id && pid) platformIdCache.set(id, pid);
  }
  return platformIdCache.get(networkId);
}

// Networks list pass-through (used to populate dropdown)
app.get('/api/networks', async (req, res) => {
  try {
    const data = await cgFetch('/networks');
    res.json(data);
  } catch (e) {
    res.status(500).json({ error: 'Failed to fetch networks', details: e?.response?.data || e.message });
  }
});

// Pools search: requires network id and token addresses
// Discover pools for a token, then fetch detailed data for pools that include the other token.
app.get('/api/pools', async (req, res) => {
  const { network = 'eth', from, to } = req.query;
  if (!from || !to) return res.status(400).json({ error: 'Missing query params: from, to' });
  try {
    console.log(`[APP] Discovering pools for from=${from} on network=${network}`);
    // 1) Discover pools involving the 'from' token
    const discovered = await cgFetch(`/networks/${encodeURIComponent(network)}/tokens/${encodeURIComponent(from)}/pools`);
    const pools = Array.isArray(discovered?.data) ? discovered.data : [];
    console.log(`[APP] Discovered ${pools.length} pools involving from token.`);

    const toLc = String(to).toLowerCase();
    // 2) Filter to pools that pair with the 'to' token
    const matched = pools.filter((p) => {
      const baseId = p?.relationships?.base_token?.data?.id || '';
      const quoteId = p?.relationships?.quote_token?.data?.id || '';
      const baseAddr = baseId.split('_')[1] || '';
      const quoteAddr = quoteId.split('_')[1] || '';
      return baseAddr.toLowerCase() === toLc || quoteAddr.toLowerCase() === toLc;
    });
    console.log(`[APP] Matched ${matched.length} pools that pair with to=${to}.`);

    // 3) Fetch detailed info in batches via multi endpoint
    const addresses = matched.map((p) => p?.attributes?.address).filter(Boolean);
    const chunkSize = 50;
    const results = [];
    for (let i = 0; i < addresses.length; i += chunkSize) {
      const chunk = addresses.slice(i, i + chunkSize);
      console.log(`[APP] Fetching details for chunk ${i / chunkSize + 1} (${chunk.length} pools)`);
      const detail = await cgFetch(`/networks/${encodeURIComponent(network)}/pools/multi/${chunk.join(',')}`);
      if (Array.isArray(detail?.data)) results.push(...detail.data);
    }
    console.log(`[APP] Returning ${results.length} detailed pools.`);

    res.json({ data: results });
  } catch (e) {
    console.error('[APP][ERR] /api/pools', e?.response?.status || '', e?.response?.data || e.message);
    res.status(500).json({ error: 'Failed to fetch pools', details: e?.response?.data || e.message });
  }
});

// Token search (Pro-only): search coins, then resolve platform-specific contract addresses
app.get('/api/token-search', async (req, res) => {
  const { network = 'eth', q = '', limit = '8' } = req.query;
  const query = String(q || '').trim();
  if (!query) return res.json({ data: [] });
  try {
    const platformId = await getPlatformIdForNetwork(network);
    if (!platformId) return res.status(400).json({ error: `Unknown platform for network ${network}` });

    const search = await cgProFetch('/search', { query });
    const coins = Array.isArray(search?.coins) ? search.coins : [];
    const max = Math.max(1, Math.min(20, Number(limit) || 8));
    const shortlist = coins.slice(0, max * 2); // overfetch a bit, filter later

    const details = [];
    for (const c of shortlist) {
      try {
        const d = await cgProFetch(`/coins/${encodeURIComponent(c.id)}`, {
          localization: 'false',
          tickers: 'false',
          market_data: 'false',
          community_data: 'false',
          developer_data: 'false',
          sparkline: 'false',
        });
        details.push({ coin: c, detail: d });
        if (details.length >= max * 3) break; // safety
      } catch (_) {}
    }

    const results = [];
    for (const { coin, detail } of details) {
      const dp = detail?.detail_platforms?.[platformId];
      const addr = dp?.contract_address || detail?.platforms?.[platformId];
      if (addr) {
        results.push({
          coin_id: coin.id,
          symbol: coin.symbol || detail?.symbol,
          name: coin.name || detail?.name,
          address: addr,
          platform_id: platformId,
          decimals: dp?.decimal_place ?? null,
          thumb: coin.thumb || detail?.image?.thumb,
        });
      }
      if (results.length >= max) break;
    }
    res.json({ data: results });
  } catch (e) {
    console.error('[APP][ERR] /api/token-search', e?.response?.status || '', e?.response?.data || e.message);
    res.status(500).json({ error: 'Failed token search', details: e?.response?.data || e.message });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
