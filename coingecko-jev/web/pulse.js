const { BTN, TONE, esc, compactUsd, price, pct, anonName, tokenAvatar, usd6, flags } = Moon;
const $ = (id) => document.getElementById(id);
const CHAINS = { solana: "Solana", base: "Base", bsc: "BNB Chain", eth: "Ethereum", robinhood: "Robinhood Chain" };
let WALLET_CHAINS = {};
fetch("/api/config").then((r) => r.json()).then((c) => { WALLET_CHAINS = c.wallet_chains || {}; if (typeof onWalletChains === "function") onWalletChains(); }).catch(() => {});
const PHASE_TONE = { accumulation: "primary", breakout: "success", distribution: "warning", capitulation: "danger", ranging: "neutral" };
const COLORS = { up: "#32CA5B", down: "#FF3A33", grid: "#212D3B", text: "#9EB0C7", border: "#212D3B" };

const INTERVALS = { "1s": 1, "15s": 15, "1m": 60, "5m": 300, "15m": 900, "1h": 3600 };

const S = {
  interval: "1s",
  ivStore: new Map(),
  ivReq: 0,
  chain: "solana",
  picks: { focus: null, watch: new Set() },
  poolsList: [],
  session: null, // {chain, pools: [...], live}
  roles: {},
  closes: {}, // pid -> [[sec, close]]
  lastSec: {},
  scores: {}, // pid -> last score
  scoreTimes: [],
  tradeTimes: [],
  tokenTimes: [],
  markers: [],
  lastLatency: null,
  ws: null,
  wsStatus: "idle",
  credits: null,
};

const sym = (p) => (flags.anon ? anonName(p.id) : p.symbol || p.name || p.id.slice(0, 6));
const poolName = (p) => (flags.anon ? `${anonName(p.id)} / ${(p.name || "").split("/").pop()?.trim() || ""}` : p.name || "");
const focusPid = () => Object.keys(S.roles).find((k) => S.roles[k] === "focus");
const poolById = (pid) => S.session?.pools.find((p) => p.id === pid);

// ---------- header ----------
function chainSegHtml(cur) {
  return Object.keys(CHAINS).map((v) => `<button data-v="${v}" class="tw-inline-flex tw-items-center tw-gap-1.5 tw-px-3 tw-py-1.5 tw-rounded-md tw-text-xs tw-leading-4 tw-font-semibold ${v === cur ? "tw-bg-white tw-text-gray-900 tw-shadow-sm dark:tw-bg-moon-600 dark:tw-text-moon-50" : "tw-text-gray-500 hover:tw-text-gray-900 dark:tw-text-moon-200 dark:hover:tw-text-moon-50"}">${Moon.chainLogo(v)}${CHAINS[v]}</button>`).join("");
}
function renderChainSeg() {
  $("chainSeg").innerHTML = chainSegHtml(S.chain);
  $("chainSeg").querySelectorAll("button").forEach((b) => (b.onclick = () => { if (S.session?.live) return; S.chain = b.dataset.v; renderChainSeg(); loadPicker(); }));
}

function renderBadge() {
  const now = Date.now();
  const calls = S.scoreTimes.filter((t) => now - t < 10000).length / 10;
  const trades = S.tradeTimes.filter((t) => now - t < 10000).length / 10;
  const tok = S.tokenTimes.filter(([t]) => now - t < 60000).reduce((a, [, k]) => a + k, 0) / 60;
  const costHr = (tok * 3600) / 1e6 * 0.042;
  const dot = { live: "tw-bg-success-500 dark:tw-bg-success-400 tw-animate-pulse", connecting: "tw-bg-warning-500", reconnecting: "tw-bg-warning-500 tw-animate-pulse", replay: "tw-bg-info-500", idle: "tw-bg-gray-400 dark:tw-bg-moon-500" }[S.wsStatus] || "tw-bg-gray-400";
  if (!S.session) { $("badge").innerHTML = ""; return; }
  $("badge").innerHTML = `
    <span class="tw-inline-flex tw-items-center tw-gap-1.5"><span class="tw-w-2 tw-h-2 tw-rounded-full ${dot}"></span>${S.wsStatus === "replay" ? "Replay" : "CoinGecko WebSocket " + S.wsStatus}</span>
    <span class="tw-rounded-md tw-bg-gray-100 dark:tw-bg-moon-800 tw-px-2 tw-py-1">${trades.toFixed(1)} trades/s</span>
    <span class="tw-rounded-md tw-bg-primary-50 tw-text-primary-800 dark:tw-bg-primary-500/15 dark:tw-text-primary-300 tw-px-2 tw-py-1">Jev ${S.lastLatency ?? "—"} ms · ${calls.toFixed(1)} calls/s · $${costHr.toFixed(2)}/hr</span>
    ${S.credits != null ? `<span class="tw-rounded-md tw-bg-gray-100 dark:tw-bg-moon-800 tw-px-2 tw-py-1">${S.credits.toFixed(0)} WS credits</span>` : ""}`;
}
setInterval(renderBadge, 1000);

function renderStop() {
  const b = $("stopBtn");
  if (!S.session?.live) { b.className = "tw-hidden"; return; }
  b.className = `${BTN.base} ${BTN.secondary} ${BTN.md}`;
  b.textContent = "■ Stop";
  b.onclick = () => { send({ cmd: "stop" }); };
}

// ---------- picker ----------
let pickerReq = 0;
async function loadPicker() {
  const req = ++pickerReq;
  $("pickerList").innerHTML = `<div class="tw-px-4 tw-py-10 tw-text-center tw-text-sm tw-text-gray-500 dark:tw-text-moon-200">Loading busiest pools from CoinGecko…</div>`;
  S.picks = { focus: null, watch: new Set() };
  S.poolsList = [];
  try {
    const list = await (await fetch(`/api/pulse/pools?chain=${S.chain}`)).json();
    if (req !== pickerReq) return;
    S.poolsList = list;
  } catch (e) {
    if (req !== pickerReq) return;
    $("pickerList").innerHTML = `<div class="tw-p-4 tw-text-danger-500 tw-text-sm">Failed to load pools: ${esc(e.message)}</div>`;
    return;
  }
  if (S.poolsList.length) {
    S.picks.focus = S.poolsList[0].id;
    S.poolsList.slice(1, 4).forEach((p) => S.picks.watch.add(p.id));
  }
  renderPicker();
}

function renderPicker() {
  const head = `<div class="tw-grid tw-grid-cols-[80px_80px_1fr_110px_110px_110px_110px] tw-gap-2 tw-px-4 tw-py-2 tw-text-xs tw-font-semibold tw-text-gray-500 dark:tw-text-moon-300"><span>Focus</span><span>Watch</span><span>Pool</span><span class="tw-text-right">Price</span><span class="tw-text-right">5m</span><span class="tw-text-right">5m txns</span><span class="tw-text-right">Liquidity</span></div>`;
  $("pickerList").innerHTML = head + S.poolsList.map((r) => {
    const m5 = r.txns?.m5 || {};
    const p = { id: r.id, symbol: r.token?.symbol, name: r.pool_name };
    const isF = S.picks.focus === r.id;
    const isW = S.picks.watch.has(r.id);
    return `<div class="tw-grid tw-grid-cols-[80px_80px_1fr_110px_110px_110px_110px] tw-gap-2 tw-items-center tw-px-4 tw-py-2 tw-text-sm hover:tw-bg-gray-50 dark:hover:tw-bg-moon-700">
      <label class="tw-flex"><input type="radio" name="focus" value="${r.id}" ${isF ? "checked" : ""} class="tw-h-4 tw-w-4 tw-text-primary-500 tw-border-gray-300 dark:tw-border-moon-600 dark:tw-bg-transparent focus:tw-ring-primary-600"></label>
      <label class="tw-flex"><input type="checkbox" value="${r.id}" ${isW ? "checked" : ""} ${isF ? "disabled" : ""} class="tw-h-4 tw-w-4 tw-rounded tw-text-primary-500 tw-border-gray-300 dark:tw-border-moon-600 dark:tw-bg-transparent focus:tw-ring-primary-600"></label>
      <div class="tw-flex tw-items-center tw-gap-2.5 tw-min-w-0">${tokenAvatar(r.token?.image_url, sym(p))}<div class="tw-min-w-0"><div class="tw-font-semibold tw-truncate">${esc(sym(p))}</div><div class="tw-text-xs tw-text-gray-500 dark:tw-text-moon-300 tw-truncate">${esc(poolName(p))}</div></div></div>
      <span class="tw-text-right tw-font-semibold tw-tabular-nums">${price(r.price_usd)}</span>
      <span class="tw-text-right">${pct(r.change?.m5)}</span>
      <span class="tw-text-right tw-tabular-nums"><span class="gecko-up">${m5.buys ?? 0}</span> / <span class="gecko-down">${m5.sells ?? 0}</span></span>
      <span class="tw-text-right tw-tabular-nums">${compactUsd(r.reserve_usd)}</span></div>`;
  }).join("");
  $("pickerList").querySelectorAll("input[type=radio]").forEach((i) => (i.onchange = () => { S.picks.focus = i.value; S.picks.watch.delete(i.value); renderPicker(); }));
  $("pickerList").querySelectorAll("input[type=checkbox]").forEach((i) => (i.onchange = () => {
    if (i.checked) { if (S.picks.watch.size >= 3) { i.checked = false; return; } S.picks.watch.add(i.value); } else S.picks.watch.delete(i.value);
  }));
  const b = $("startBtn");
  if (S.locked) {
    b.className = `${BTN.base} ${BTN.primary}`;
    b.innerHTML = "🔒 Requires Analyst plan or higher — Upgrade";
    b.onclick = () => window.open(S.lockedInfo?.upgrade_url || "https://www.coingecko.com/en/api/pricing", "_blank", "noopener");
    return;
  }
  b.className = `${BTN.base} ${BTN.primary} ${BTN.lg}`;
  b.innerHTML = `Start live scoring with ${Moon.JEV}`;
  b.onclick = () => {
    if (!S.picks.focus) return;
    b.innerHTML = "Seeding history…";
    b.classList.add("tw-opacity-50", "tw-pointer-events-none");
    send({ cmd: "start", chain: S.chain, focus: S.picks.focus, watch: [...S.picks.watch] });
  };
}

// ---------- search ----------
let searchTimer = null, searchReq = 0, searchRows = [];
function initSearch() {
  const input = $("searchInput"), box = $("searchResults");
  if (flags.replay) { $("searchBox").classList.add("tw-hidden"); return; }
  const close = () => box.classList.add("tw-hidden");
  input.addEventListener("input", () => {
    clearTimeout(searchTimer);
    const q = input.value.trim();
    if (q.length < 2) { close(); $("searchSpin").classList.add("tw-hidden"); return; }
    $("searchSpin").classList.remove("tw-hidden");
    searchTimer = setTimeout(() => runSearch(q), 300);
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { close(); input.blur(); }
    if (e.key === "Enter" && searchRows.length) { e.preventDefault(); streamPool(searchRows[0]); }
  });
  input.addEventListener("focus", () => { if (searchRows.length && input.value.trim().length >= 2) box.classList.remove("tw-hidden"); });
  document.addEventListener("click", (e) => { if (!$("searchBox").contains(e.target)) close(); });
}

async function runSearch(q) {
  const req = ++searchReq;
  const box = $("searchResults");
  let rows = [];
  try {
    const r = await fetch(`/api/pulse/search?chain=${S.session?.live ? S.session.chain : S.chain}&q=${encodeURIComponent(q)}`);
    rows = r.ok ? await r.json() : [];
  } catch {}
  if (req !== searchReq) return;
  $("searchSpin").classList.add("tw-hidden");
  searchRows = rows;
  const chainLabel = CHAINS[S.session?.live ? S.session.chain : S.chain];
  box.innerHTML = rows.length
    ? `<div class="tw-px-4 tw-py-2 tw-text-xs tw-font-semibold tw-text-gray-500 dark:tw-text-moon-300 tw-border-b tw-border-gray-200 dark:tw-border-moon-700">${rows.length} pools on ${esc(chainLabel)} · click to stream live</div>` +
      rows.map((r, i) => {
        const p = { id: r.id, symbol: r.token?.symbol, name: r.pool_name };
        const m5 = r.txns?.m5 || {};
        return `<button data-i="${i}" class="tw-w-full tw-text-left tw-grid tw-grid-cols-[1fr_auto] tw-gap-3 tw-items-center tw-px-4 tw-py-2.5 hover:tw-bg-gray-50 dark:hover:tw-bg-moon-700 ${i ? "tw-border-t tw-border-gray-100 dark:tw-border-moon-700" : ""}">
          <div class="tw-flex tw-items-center tw-gap-2.5 tw-min-w-0">${tokenAvatar(r.token?.image_url, sym(p))}
            <div class="tw-min-w-0"><div class="tw-flex tw-items-baseline tw-gap-2"><span class="tw-font-semibold tw-truncate">${esc(poolName(p))}</span><span class="tw-text-xs tw-text-gray-500 dark:tw-text-moon-300 tw-truncate">${esc(r.dex || "")}</span></div>
            <div class="tw-text-xs tw-text-gray-500 dark:tw-text-moon-300 tw-font-mono tw-truncate">${flags.anon ? "••••" : esc(r.id)}</div></div></div>
          <div class="tw-text-right tw-text-xs tw-tabular-nums"><div class="tw-text-sm tw-font-semibold">${price(r.price_usd)} ${pct(r.change?.h24)}</div>
            <div class="tw-text-gray-500 dark:tw-text-moon-300">Vol ${compactUsd(r.volume?.h24)} · Liq ${compactUsd(r.reserve_usd)} · 5m txns ${(m5.buys ?? 0) + (m5.sells ?? 0)}</div></div></button>`;
      }).join("")
    : `<div class="tw-px-4 tw-py-6 tw-text-sm tw-text-center tw-text-gray-500 dark:tw-text-moon-200">No pools found on ${esc(chainLabel)} for “${esc(q)}”.</div>`;
  box.classList.remove("tw-hidden");
  box.querySelectorAll("[data-i]").forEach((b) => (b.onclick = () => streamPool(rows[+b.dataset.i])));
}

function streamPool(row) {
  $("searchResults").classList.add("tw-hidden");
  $("searchInput").value = "";
  $("searchInput").blur();
  searchRows = [];
  const chain = S.session?.live ? S.session.chain : S.chain;
  S.chain = chain;
  showStarting(row.pool_name);
  send({ cmd: "start", chain, focus: row.id, watch: [] });
}

function showStarting(label) {
  $("liveBadge").className = "tw-inline-flex tw-items-center tw-gap-2 tw-text-xs tw-font-semibold";
  $("liveBadge").innerHTML = `<span class="tw-rounded-md tw-bg-warning-500 tw-text-gray-900 tw-px-2 tw-py-0.5 tw-animate-pulse">Starting · seeding history${label && !flags.anon ? " for " + esc(label) : ""}…</span>`;
}

// ---------- charts ----------
let chart, candles, volume, ribbon, pumpLine, dumpLine;
function initCharts() {
  const LC = LightweightCharts;
  const base = {
    layout: { background: { color: "transparent" }, textColor: COLORS.text, fontFamily: "Inter, sans-serif" },
    grid: { vertLines: { color: COLORS.grid }, horzLines: { color: COLORS.grid } },
    rightPriceScale: { borderColor: COLORS.border },
    timeScale: { borderColor: COLORS.border, timeVisible: true, secondsVisible: true, rightOffset: 4, barSpacing: 7 },
    crosshair: { mode: 0 },
    autoSize: true,
  };
  chart = LC.createChart($("chart"), base);
  candles = chart.addCandlestickSeries({ upColor: COLORS.up, downColor: COLORS.down, wickUpColor: COLORS.up, wickDownColor: COLORS.down, borderVisible: false, priceFormat: { type: "custom", formatter: (v) => price(v), minMove: 1e-12 } });
  volume = chart.addHistogramSeries({ priceScaleId: "vol", priceFormat: { type: "volume" } });
  chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
  candles.priceScale().applyOptions({ scaleMargins: { top: 0.08, bottom: 0.22 } });
  ribbon = LC.createChart($("ribbon"), { ...base, rightPriceScale: { borderColor: COLORS.border, scaleMargins: { top: 0.08, bottom: 0.08 } }, timeScale: { ...base.timeScale, visible: false } });
  pumpLine = ribbon.addLineSeries({ color: COLORS.up, lineWidth: 2, priceLineVisible: false, lastValueVisible: true, autoscaleInfoProvider: () => ({ priceRange: { minValue: 0, maxValue: 100 } }) });
  dumpLine = ribbon.addLineSeries({ color: COLORS.down, lineWidth: 2, priceLineVisible: false, lastValueVisible: true, autoscaleInfoProvider: () => ({ priceRange: { minValue: 0, maxValue: 100 } }) });
  chart.timeScale().subscribeVisibleLogicalRangeChange(() => {
    if (ivSec() > 60) { ribbon.timeScale().fitContent(); return; }
    const r = chart.timeScale().getVisibleRange();
    if (r) try { ribbon.timeScale().setVisibleRange(r); } catch {}
  });
}

const ivSec = () => INTERVALS[S.interval];
const bucketOf = (sec) => Math.floor(sec / ivSec()) * ivSec();
const volColor = (o, c) => (c >= o ? "rgba(50,202,91,.45)" : "rgba(255,58,51,.45)");

function aggregate(rows1s, iv) {
  const out = new Map();
  for (const [t, o, h, l, c, v] of rows1s) {
    const b = Math.floor(t / iv) * iv;
    const cur = out.get(b);
    if (!cur) out.set(b, [b, o, h, l, c, v]);
    else { cur[2] = Math.max(cur[2], h); cur[3] = Math.min(cur[3], l); cur[4] = c; cur[5] += v; }
  }
  return out;
}

function renderIntervalSeg() {
  $("intervalSeg").innerHTML = Object.keys(INTERVALS).map((k) => {
    const on = k === S.interval;
    return `<button data-iv="${k}" class="tw-px-2.5 tw-py-1 tw-rounded-md tw-text-xs tw-leading-4 tw-font-semibold tw-tabular-nums ${on ? "tw-bg-white tw-text-gray-900 tw-shadow-sm dark:tw-bg-moon-600 dark:tw-text-moon-50" : "tw-text-gray-500 hover:tw-text-gray-900 dark:tw-text-moon-200 dark:hover:tw-text-moon-50"}">${k}</button>`;
  }).join("");
  $("intervalSeg").querySelectorAll("button").forEach((b) => (b.onclick = () => { if (b.dataset.iv === S.interval) return; S.interval = b.dataset.iv; renderIntervalSeg(); loadFocusChart(); }));
  $("intervalNote").textContent = S.interval === "1s"
    ? "1s candles built live from CoinGecko WebSocket trades"
    : S.session?.live ? `History from CoinGecko OHLCV (${S.interval}) · live bar updated from WebSocket trades` : `${S.interval} candles aggregated from the recorded 1s stream`;
}

async function loadFocusChart() {
  const pid = focusPid();
  const store = S.candleStore?.[pid];
  if (!pid || !store) return;
  const req = ++S.ivReq;
  const iv = ivSec();
  const rows1s = [...store.values()].sort((a, b) => a[0] - b[0]);
  let rows;
  if (iv === 1) rows = rows1s.slice(-1200);
  else {
    let hist = [];
    if (S.session?.live) {
      try { hist = await (await fetch(`/api/pulse/ohlcv?chain=${S.session.chain}&pool=${encodeURIComponent(pid)}&interval=${S.interval}`)).json(); } catch {}
      if (req !== S.ivReq) return;
    }
    const m = aggregate((Array.isArray(hist) ? hist : []).slice().sort((a, b) => a[0] - b[0]), iv);
    const lastHist = m.size ? Math.max(...m.keys()) : -Infinity;
    for (const [b, c] of aggregate(rows1s, iv)) if (b > lastHist || !m.has(b)) m.set(b, c);
    rows = [...m.values()].sort((a, b) => a[0] - b[0]).slice(-1000);
  }
  S.ivStore = new Map(rows.map((r) => [r[0], [...r]]));
  candles.setData(rows.map(([t, o, h, l, c]) => ({ time: t, open: o, high: h, low: l, close: c })));
  volume.setData(rows.map(([t, o, , , c, v]) => ({ time: t, value: v, color: volColor(o, c) })));
  S.lastSec[pid] = rows.length ? rows[rows.length - 1][0] : 0;
  chart.applyOptions({ timeScale: { secondsVisible: iv < 60, barSpacing: iv === 1 ? 7 : 9 } });
  const hist = S.scoreHist[pid] || [];
  pumpLine.setData(hist.map((s) => ({ time: s.time, value: s.pump })));
  dumpLine.setData(hist.map((s) => ({ time: s.time, value: s.dump })));
  refreshMarkers(pid);
  const n = rows.length;
  if (n) chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, n - 240), to: n + 4 });
  renderIntervalSeg();
}

function refreshMarkers(pid) {
  const seen = new Map();
  S.markers.filter((m) => m.p === pid).map(markerObj).forEach((mk) => seen.set(mk.time + mk.shape, mk));
  candles.setMarkers([...seen.values()].sort((a, b) => a.time - b.time));
}

function markerObj(m) {
  const t = bucketOf(Math.floor(m.t / 1000));
  return m.side === "dump"
    ? { time: t, position: "aboveBar", color: COLORS.down, shape: "arrowDown", text: `Jev: dump ${Math.round(m.value)}%` }
    : { time: t, position: "belowBar", color: COLORS.up, shape: "arrowUp", text: `Jev: pump ${Math.round(m.value)}%` };
}

// ---------- gauges ----------
function gaugeSvg(value, raw, label, tone, conf) {
  const v = Math.max(0, Math.min(100, value || 0));
  const len = Math.PI * 80;
  const off = len * (1 - v / 100);
  const stroke = tone === "up" ? COLORS.up : COLORS.down;
  const angle = -90 + (v / 100) * 180;
  const lowc = conf != null && conf < 0.5;
  return `<div class="tw-text-center" title="raw ${raw ?? "—"} · confidence ${conf != null ? (conf * 100).toFixed(0) + "%" : "—"}">
    <svg viewBox="0 0 200 120" class="tw-w-full">
      <path d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke="#212D3B" stroke-width="16" stroke-linecap="round"/>
      <path class="gauge-arc" d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke="${stroke}" stroke-width="16" stroke-linecap="round" stroke-dasharray="${len}" stroke-dashoffset="${off}"/>
      <g class="gauge-needle" transform="rotate(${angle})"><line x1="100" y1="100" x2="100" y2="34" stroke="#DFE5EC" stroke-width="3" stroke-linecap="round"/></g>
      <circle cx="100" cy="100" r="6" fill="#DFE5EC"/>
    </svg>
    <div class="tw-text-3xl tw-leading-9 tw-font-bold tw-tabular-nums -tw-mt-3 ${tone === "up" ? "gecko-up" : "gecko-down"}">${Math.round(v)}</div>
    <div class="tw-text-sm tw-font-semibold tw-text-gray-700 dark:tw-text-moon-100">${label}${lowc ? ` <span class="tw-text-xs tw-text-warning-700 dark:tw-text-warning-400">· low confidence</span>` : ""}</div></div>`;
}

function updateGauges(s) {
  const gp = $("gaugePump"), gd = $("gaugeDump");
  if (!gp.querySelector("svg") || !s) {
    gp.innerHTML = gaugeSvg(s?.pump, s?.pump_raw, "Pump", "up", s?.pump_conf);
    gd.innerHTML = gaugeSvg(s?.dump, s?.dump_raw, "Dump", "down", s?.dump_conf);
  } else {
    for (const [el, v, raw, conf, label, tone] of [[gp, s.pump, s.pump_raw, s.pump_conf, "Pump", "up"], [gd, s.dump, s.dump_raw, s.dump_conf, "Dump", "down"]]) {
      const len = Math.PI * 80;
      const vv = Math.max(0, Math.min(100, v));
      el.querySelector(".gauge-arc").setAttribute("stroke-dashoffset", len * (1 - vv / 100));
      el.querySelector(".gauge-needle").setAttribute("transform", `rotate(${-90 + (vv / 100) * 180})`);
      el.querySelector(".tw-text-3xl").textContent = Math.round(vv);
      el.firstElementChild.title = `raw ${raw} · confidence ${(conf * 100).toFixed(0)}%`;
      el.querySelector(".tw-text-sm").innerHTML = `${label}${conf < 0.5 ? ` <span class="tw-text-xs tw-text-warning-700 dark:tw-text-warning-400">· low confidence</span>` : ""}`;
    }
  }
  $("gaugeMeta").innerHTML = s
    ? `<span>Exhaustion <b class="tw-tabular-nums tw-text-gray-900 dark:tw-text-moon-50">${Math.round(s.exhaustion * 100)}%</b></span><span>smoothed (EMA) · raw ${Math.round(s.pump_raw)} / ${Math.round(s.dump_raw)}</span>`
    : `<span>Waiting for the first Jev score…</span>`;
}

// ---------- focus header / watch ----------
function renderFocusHead() {
  const pid = focusPid();
  const p = poolById(pid);
  if (!p) return;
  const s = S.scores[pid];
  const lastClose = S.closes[pid]?.at(-1)?.[1] ?? p.price_usd;
  const phase = s?.phase ? `<span class="tw-inline-flex tw-rounded-full tw-border tw-px-3 tw-py-1 tw-text-sm tw-font-semibold tw-capitalize ${TONE[PHASE_TONE[s.phase] || "neutral"]} ${s.phase_conf < 0.5 ? "chip-lowconf" : ""}">${Moon.ic("phase", s.phase)} Phase: ${esc(s.phase)}</span>` : "";
  $("focusHead").innerHTML = `${tokenAvatar(p.image_url, sym(p), "tw-w-10 tw-h-10")}
    <div><div class="tw-text-xl tw-leading-7 tw-font-bold">${esc(sym(p))}</div><div class="tw-text-xs tw-text-gray-500 dark:tw-text-moon-300 tw-flex tw-items-center tw-gap-1.5">${esc(poolName(p))} · ${Moon.chainBadge(S.session.chain)}</div></div>
    <div class="tw-text-2xl tw-leading-8 tw-font-bold tw-tabular-nums" id="focusPrice">${price(lastClose)}</div>
    <div class="tw-text-xs tw-text-gray-500 dark:tw-text-moon-200">Liquidity <b class="tw-text-gray-900 dark:tw-text-moon-50 tw-tabular-nums">${compactUsd(p.liquidity_usd)}</b></div>
    <div class="tw-ml-auto tw-flex tw-items-center tw-gap-3">${xrayLink(p)}${phase}</div>`;
}

function xrayLink(p) {
  if (!WALLET_CHAINS[S.session?.chain] || !p.token_address) return "";
  const href = `/xray.html?chain=${S.session.chain}&token=${encodeURIComponent(p.token_address)}&pool=${encodeURIComponent(p.id)}&from=pulse${flags.anon ? "&anon=1" : ""}`;
  return `<a href="${href}" target="_blank" rel="noopener" class="tw-inline-flex tw-items-center tw-gap-1 tw-rounded-lg tw-border tw-border-gray-300 dark:tw-border-moon-600 tw-px-3 tw-py-1 tw-text-sm tw-font-semibold tw-text-gray-700 dark:tw-text-moon-100 hover:tw-border-primary-500 dark:hover:tw-border-primary-400">🔬 X-ray wallets</a>`;
}

const PERSONA_TONE = { treasury_allocation: "info", proven_trader: "success", accumulator: "primary", one_hit_winner: "warning", whale: "info", sniper: "warning", insider_like: "danger", market_maker_bot: "neutral", flipper: "neutral", new_wallet: "neutral", protocol: "neutral" };
function onWallets(d) {
  if (d.p !== focusPid()) return;
  $("walletCard").classList.remove("tw-hidden");
  $("tapeCard").classList.replace("tw-h-[420px]", "tw-h-[260px]");
  const f = d.flow;
  const net = f.smart_net_usd || 0;
  const mag = Math.min(50, (Math.abs(net) / Math.max(1000, Math.abs(net) + (f.insider_sell_usd || 0))) * 50);
  $("walletFlow").innerHTML = `<div class="tw-flex tw-items-baseline tw-justify-between"><span class="tw-text-xs tw-text-gray-500 dark:tw-text-moon-300">Proven traders & accumulators, net</span>
      <span class="tw-text-lg tw-font-bold tw-tabular-nums ${net > 0 ? "gecko-up" : net < 0 ? "gecko-down" : ""}">${net === 0 ? "$0" : (net > 0 ? "+" : "−") + compactUsd(Math.abs(net))}</span></div>
    <div class="tw-relative tw-h-2 tw-rounded-full tw-bg-gray-200 dark:tw-bg-moon-600 tw-mt-1.5 tw-overflow-hidden"><span class="tw-absolute tw-top-0 tw-bottom-0 tw-left-1/2 tw-w-px tw-bg-gray-400 dark:tw-bg-moon-400"></span>
      <span id="flowBar" class="tw-absolute tw-top-0 tw-bottom-0 tw-rounded-full ${net >= 0 ? "tw-bg-success-500 dark:tw-bg-success-400" : "tw-bg-danger-500"}"></span></div>
    <div class="tw-grid tw-grid-cols-3 tw-gap-2 tw-mt-3 tw-text-xs"><div><div class="tw-text-gray-500 dark:tw-text-moon-300">Insider-like sells</div><div class="tw-font-semibold tw-tabular-nums ${f.insider_sell_usd ? "gecko-down" : ""}">${f.insider_sell_usd ? compactUsd(f.insider_sell_usd) : "$0"}</div></div>
      <div><div class="tw-text-gray-500 dark:tw-text-moon-300">Bot share</div><div class="tw-font-semibold tw-tabular-nums">${Math.round((f.bot_share || 0) * 100)}%</div></div>
      <div><div class="tw-text-gray-500 dark:tw-text-moon-300">Wallets read</div><div class="tw-font-semibold tw-tabular-nums">${f.wallets_profiled}</div></div></div>`;
  const bar = $("flowBar");
  if (bar) { bar.style.width = mag + "%"; bar.style.left = net >= 0 ? "50%" : 50 - mag + "%"; }
  $("walletList").innerHTML = d.trades.length ? d.trades.map((t) => {
    const buy = t.s === "b";
    const who = flags.anon ? `Wallet #${(Moon.hash(t.w) % 900) + 100}` : t.short;
    const chip = t.persona ? `<span class="tw-inline-flex tw-whitespace-nowrap tw-rounded tw-border tw-px-1.5 tw-text-[10px] tw-font-semibold ${TONE[PERSONA_TONE[t.persona] || "neutral"]}">${Moon.ic("persona", t.persona)} ${esc(t.persona_label)}</span>` : `<span class="tw-text-[10px] tw-text-gray-400 dark:tw-text-moon-500">reading…</span>`;
    return `<a href="/wallet.html?address=${encodeURIComponent(t.w)}&chain=${S.session.chain}&from=pulse${flags.anon ? "&anon=1" : ""}" target="_blank" rel="noopener" title="Open wallet profile" class="tw-group tw-grid tw-grid-cols-[38px_64px_1fr_auto_12px] tw-items-center tw-gap-2 tw-py-1.5 tw-px-1 -tw-mx-1 tw-rounded tw-border-b tw-border-gray-100 dark:tw-border-moon-700 hover:tw-bg-gray-50 dark:hover:tw-bg-moon-700">
      <span class="${buy ? "gecko-up" : "gecko-down"} tw-font-semibold">${buy ? "Buy" : "Sell"}</span><span class="tw-tabular-nums tw-text-right ${buy ? "gecko-up" : "gecko-down"}">${compactUsd(t.u)}</span>
      <span class="tw-font-mono tw-truncate tw-text-gray-700 dark:tw-text-moon-100 group-hover:tw-underline">${esc(who)}</span><span class="tw-flex tw-items-center tw-gap-1">${chip}${t.copy_worthy ? `<span class="tw-text-[10px] tw-font-bold tw-text-success-400">✓</span>` : ""}</span>
      <span class="tw-text-gray-400 dark:tw-text-moon-400 group-hover:tw-text-primary-400">↗</span></a>`;
  }).join("") : `<div class="tw-py-3 tw-text-gray-500 dark:tw-text-moon-300">No trades above $250 in the last few minutes.</div>`;
  $("walletUpdated").textContent = "updated every 30s · click a wallet to profile it";
}

function sparkPath(pts, w = 220, h = 44) {
  if (pts.length < 2) return "";
  const ys = pts.map((p) => p[1]);
  const lo = Math.min(...ys), hi = Math.max(...ys), span = hi - lo || 1;
  return pts.map((p, i) => `${i ? "L" : "M"}${((i / (pts.length - 1)) * w).toFixed(1)} ${(h - ((p[1] - lo) / span) * h).toFixed(1)}`).join(" ");
}

function renderWatch() {
  const wrap = $("watch");
  const pids = Object.keys(S.roles).filter((k) => S.roles[k] === "watch");
  wrap.innerHTML = pids.map((pid) => {
    const p = poolById(pid);
    const s = S.scores[pid];
    const pts = (S.closes[pid] || []).slice(-180);
    const up = pts.length > 1 && pts.at(-1)[1] >= pts[0][1];
    return `<button data-pid="${pid}" class="tw-text-left tw-rounded-xl tw-border tw-border-gray-200 dark:tw-border-moon-700 tw-bg-white dark:tw-bg-moon-800 tw-p-4 hover:tw-border-primary-500 dark:hover:tw-border-primary-400">
      <div class="tw-flex tw-items-center tw-gap-2.5">${tokenAvatar(p.image_url, sym(p))}<div class="tw-min-w-0 tw-flex-1"><div class="tw-font-semibold tw-truncate">${esc(sym(p))}</div><div class="tw-text-xs tw-text-gray-500 dark:tw-text-moon-300 tw-truncate">${esc(poolName(p))}</div></div>
      <div class="tw-text-right"><div class="tw-font-semibold tw-tabular-nums">${price(pts.at(-1)?.[1] ?? p.price_usd)}</div><div class="tw-text-xs tw-capitalize tw-text-gray-500 dark:tw-text-moon-200">${s?.phase ? Moon.ic("phase", s.phase) + " " + esc(s.phase) : "…"}</div></div></div>
      <svg viewBox="0 0 220 44" class="tw-w-full tw-h-11 tw-mt-2" preserveAspectRatio="none"><path d="${sparkPath(pts)}" fill="none" stroke="${up ? COLORS.up : COLORS.down}" stroke-width="1.5"/></svg>
      <div class="tw-grid tw-grid-cols-2 tw-gap-3 tw-mt-2 tw-text-xs tw-font-semibold">
        ${[["Pump", s?.pump, "tw-bg-success-500 dark:tw-bg-success-400"], ["Dump", s?.dump, "tw-bg-danger-500"]].map(([l, v, c]) => `<div><div class="tw-flex tw-justify-between"><span class="tw-text-gray-500 dark:tw-text-moon-200">${l}</span><span class="tw-tabular-nums">${v != null ? Math.round(v) : "—"}</span></div>
          <div class="tw-h-1.5 tw-rounded-full tw-bg-gray-200 dark:tw-bg-moon-600 tw-mt-1 tw-overflow-hidden"><div class="tw-h-full ${c} tw-rounded-full tw-w-[${Math.round(v || 0)}%] tw-transition-all"></div></div></div>`).join("")}
      </div></button>`;
  }).join("");
  wrap.querySelectorAll("[data-pid]").forEach((b) => (b.onclick = () => {
    if (S.session?.live) send({ cmd: "focus", pool: b.dataset.pid });
    else setRoles(Object.fromEntries(Object.keys(S.roles).map((k) => [k, k === b.dataset.pid ? "focus" : "watch"])));
  }));
}
let watchTimer = null;
const scheduleWatch = () => { if (!watchTimer) watchTimer = setTimeout(() => { watchTimer = null; renderWatch(); }, 400); };

// ---------- tape ----------
function pushTape(d) {
  const tape = $("tape");
  const buy = d.s === "b";
  const big = d.u >= 1000;
  const row = document.createElement("div");
  row.className = `jev-pop tw-grid tw-grid-cols-[56px_1fr_1fr] tw-gap-2 tw-py-1 ${big ? "tw-font-bold" : ""}`;
  row.innerHTML = `<span class="${buy ? "gecko-up" : "gecko-down"} tw-font-semibold">${buy ? "Buy" : "Sell"}</span><span class="tw-text-right ${buy ? "gecko-up" : "gecko-down"}">${compactUsd(d.u)}</span><span class="tw-text-right tw-text-gray-700 dark:tw-text-moon-100">${price(d.pr)}</span>`;
  tape.prepend(row);
  while (tape.children.length > 40) tape.lastChild.remove();
}

// ---------- toasts ----------
function toast(m) {
  const p = poolById(m.p);
  const dump = m.side === "dump";
  const el = document.createElement("div");
  el.className = `jev-marker-in tw-rounded-xl tw-border tw-px-4 tw-py-3 tw-shadow-xl tw-w-80 ${dump ? TONE.danger : TONE.success} tw-bg-white dark:tw-bg-moon-800`;
  el.innerHTML = `<div class="tw-text-sm tw-font-bold">${dump ? "▾ Jev flagged dump risk" : "▴ Jev flagged a pump"} · ${Math.round(m.value)}%</div>
    <div class="tw-text-xs tw-mt-0.5">${esc(p ? sym(p) : "")} · confidence ${Math.round(m.confidence * 100)}% · ${new Date(m.t).toLocaleTimeString()}</div>`;
  $("toasts").prepend(el);
  setTimeout(() => el.remove(), 6000);
}

// ---------- session ----------
function resetWalletCard() {
  $("walletCard").classList.add("tw-hidden");
  $("tapeCard").classList.replace("tw-h-[260px]", "tw-h-[420px]");
}

function setRoles(roles) {
  S.roles = roles;
  resetWalletCard();
  S.session.pools.forEach((p) => (p.role = roles[p.id]));
  loadFocusChart();
  renderFocusHead();
  updateGauges(S.scores[focusPid()]);
  renderWatch();
  $("tape").innerHTML = "";
  (S.seeds?.[focusPid()]?.trades || []).slice(-25).forEach(([t, s, u, pr]) => pushTape({ t, s, u, pr }));
}

function onSession(d) {
  S.session = d;
  S.seeds = d.seeds;
  S.chain = d.chain;
  S.scores = {};
  S.markers = [];
  S.scoreHist = {};
  S.closes = {};
  S.candleStore = {};
  for (const [pid, seed] of Object.entries(d.seeds)) {
    S.closes[pid] = seed.candles.map(([t, , , , c]) => [t, c]);
    S.candleStore[pid] = new Map(seed.candles.map((c) => [c[0], c]));
  }
  S.wsStatus = d.live ? S.wsStatus : "replay";
  $("picker").classList.add("tw-hidden");
  $("live").classList.remove("tw-hidden");
  if (!chart) initCharts();
  renderChainSeg();
  setRoles(Object.fromEntries(d.pools.map((p) => [p.id, p.role])));
  renderStop();
  $("liveBadge").className = "tw-inline-flex tw-items-center tw-gap-2 tw-text-xs tw-font-semibold";
  $("liveBadge").innerHTML = d.live
    ? `<span class="tw-rounded-md tw-bg-danger-500 tw-text-white tw-px-2 tw-py-0.5">● LIVE</span>`
    : `<span class="tw-rounded-md tw-bg-info-500 tw-text-white tw-px-2 tw-py-0.5">REPLAY</span>`;
}

function onTrade(d) {
  S.tradeTimes.push(Date.now());
  if (S.tradeTimes.length > 3000) S.tradeTimes.splice(0, 1000);
  const [sec, o, h, l, c, v] = d.c;
  const store = (S.candleStore[d.p] ||= new Map());
  store.set(sec, d.c);
  if (store.size > 2400) [...store.keys()].sort((a, b) => a - b).slice(0, 600).forEach((k) => store.delete(k));
  const arr = (S.closes[d.p] ||= []);
  if (arr.length && arr.at(-1)[0] === sec) arr.at(-1)[1] = c;
  else if (!arr.length || sec > arr.at(-1)[0]) arr.push([sec, c]);
  if (arr.length > 1200) arr.splice(0, 200);
  if (d.p === focusPid()) {
    let bar = null;
    if (ivSec() === 1) bar = [sec, o, h, l, c, v];
    else {
      const b = bucketOf(sec);
      const cur = S.ivStore.get(b);
      if (!cur) { const prev = S.ivStore.get(S.lastSec[d.p]); bar = [b, prev ? prev[4] : d.pr, Math.max(d.pr, prev ? prev[4] : d.pr), Math.min(d.pr, prev ? prev[4] : d.pr), d.pr, d.u]; }
      else { cur[2] = Math.max(cur[2], d.pr); cur[3] = Math.min(cur[3], d.pr); cur[4] = d.pr; cur[5] += d.u; bar = cur; }
      S.ivStore.set(b, bar);
    }
    if (bar[0] >= (S.lastSec[d.p] || 0)) {
      candles.update({ time: bar[0], open: bar[1], high: bar[2], low: bar[3], close: bar[4] });
      volume.update({ time: bar[0], value: bar[5], color: volColor(bar[1], bar[4]) });
      S.lastSec[d.p] = bar[0];
    }
    pushTape(d);
    const fp = $("focusPrice");
    if (fp) fp.textContent = price(c);
    $("tapeRate").textContent = `${(S.tradeTimes.filter((t) => Date.now() - t < 10000).length / 10).toFixed(1)} trades/s`;
  } else scheduleWatch();
}

function onScore(d) {
  S.scores[d.p] = d;
  S.scoreTimes.push(Date.now());
  S.tokenTimes.push([Date.now(), d.tokens || 0]);
  if (S.scoreTimes.length > 500) S.scoreTimes.splice(0, 200);
  if (S.tokenTimes.length > 500) S.tokenTimes.splice(0, 200);
  const time = Math.floor(d.t / 1000);
  const hist = (S.scoreHist[d.p] ||= []);
  if (!hist.length || time > hist.at(-1).time) hist.push({ time, pump: d.pump, dump: d.dump });
  if (d.p === focusPid()) {
    S.lastLatency = d.latency_ms;
    if (hist.at(-1).time === time) {
      pumpLine.update({ time, value: d.pump });
      dumpLine.update({ time, value: d.dump });
    }
    updateGauges(d);
    renderFocusHead();
  } else scheduleWatch();
}

function onMarker(d) {
  S.markers.push(d);
  if (d.p === focusPid()) refreshMarkers(d.p);
  toast(d);
}

function send(o) { if (S.ws?.readyState === 1) S.ws.send(JSON.stringify(o)); }

function connect() {
  const q = flags.replay ? `?replay=${encodeURIComponent(flags.replay)}&speed=${flags.speed}` : "";
  const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/pulse/ws${q}`);
  S.ws = ws;
  ws.onmessage = (e) => {
    const { ev, data } = JSON.parse(e.data);
    if (ev === "session") onSession(data);
    else if (ev === "trade") onTrade(data);
    else if (ev === "score") onScore(data);
    else if (ev === "marker") onMarker(data);
    else if (ev === "roles") setRoles(data);
    else if (ev === "starting") showStarting("");
    else if (ev === "wallets") onWallets(data);
    else if (ev === "status") { S.wsStatus = data.ws; S.credits = data.cg_ws_credits; }
    else if (ev === "stopped") onStopped(data);
    else if (ev === "replay_done") { S.wsStatus = "replay"; $("liveBadge").innerHTML = `<span class="tw-rounded-md tw-bg-info-500 tw-text-white tw-px-2 tw-py-0.5">REPLAY · ended</span>`; }
    else if (ev === "locked") { S.wsStatus = "locked"; S.locked = true; $("liveBadge").innerHTML = `<a href="${data.upgrade_url}" target="_blank" rel="noopener" class="tw-rounded-md tw-bg-warning-500 tw-text-white tw-px-2 tw-py-0.5">🔒 ${esc(data.message)} Upgrade →</a>`; }
  };
  ws.onclose = () => { if (!flags.replay && !S.locked) setTimeout(connect, 1500); };
}

function onStopped(d) {
  if (!S.session?.live || d.reason === "restarted") return;
  S.session.live = false;
  S.wsStatus = "idle";
  renderStop();
  $("liveBadge").innerHTML = `<span class="tw-rounded-md tw-bg-gray-500 tw-text-white tw-px-2 tw-py-0.5">STOPPED · ${esc(d.reason)}</span>
    <button id="backBtn" class="${BTN.base} ${BTN.soft} ${BTN.sm}">Pick pools</button>`;
  $("backBtn").onclick = () => { $("live").classList.add("tw-hidden"); $("picker").classList.remove("tw-hidden"); S.session = null; $("liveBadge").className = "tw-hidden"; renderBadge(); loadPicker(); };
}

async function renderDevBar() {
  let items = [];
  try { items = await (await fetch("/api/fixtures?demo=pulse")).json(); } catch {}
  $("devBar").innerHTML = `<span>Recordings</span>
    <select id="recSel" class="tw-rounded-md tw-border-0 tw-ring-1 tw-ring-gray-200 dark:tw-ring-moon-600 tw-bg-white dark:tw-bg-moon-900 tw-text-xs tw-py-1 tw-pl-2 tw-pr-7"><option value="">— live —</option>${items.map((f) => `<option>${esc(f.name)}</option>`).join("")}</select>
    <select id="speedSel" class="tw-rounded-md tw-border-0 tw-ring-1 tw-ring-gray-200 dark:tw-ring-moon-600 tw-bg-white dark:tw-bg-moon-900 tw-text-xs tw-py-1 tw-pl-2 tw-pr-7"><option>1</option><option>2</option><option>4</option></select>
    <button id="replayBtn" class="${BTN.base} ${BTN.soft} ${BTN.sm}">Replay</button>`;
  $("replayBtn").onclick = () => {
    const name = $("recSel").value;
    const params = new URLSearchParams(location.search);
    if (name) { params.set("replay", name); params.set("speed", $("speedSel").value); } else params.delete("replay");
    location.search = params.toString();
  };
  Moon.applyDevVisibility();
}

renderChainSeg();
Moon.loadChains().then(renderChainSeg);
updateGauges(null);
renderDevBar();
initSearch();

async function boot() {
  if (flags.replay) {
    connect();
    $("picker").classList.add("tw-hidden");
    return;
  }
  const caps = await Moon.capabilities();
  if (!caps.websocket) {
    S.locked = true;
    S.lockedInfo = caps;
  } else {
    connect();
  }
  loadPicker();
}
boot();
