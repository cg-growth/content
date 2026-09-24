const { BTN, esc, compactUsd, price, pct, anonName, tokenAvatar, usd6, flags } = Moon;
const $ = (id) => document.getElementById(id);

const BUCKETS = ["Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"];
const BUCKET_PILL = {
  "Extreme Fear": "tw-bg-danger-500 tw-text-white",
  Fear: "tw-bg-danger-100 tw-text-danger-700",
  Neutral: "tw-bg-gray-100 tw-text-gray-600 tw-ring-1 tw-ring-gray-300",
  Greed: "tw-bg-success-100 tw-text-success-800",
  "Extreme Greed": "tw-bg-primary-500 tw-text-white",
};
const BUCKET_HEX = { "Extreme Fear": "#FF3A33", Fear: "#FF9D84", Neutral: "#94A3B8", Greed: "#00A83E", "Extreme Greed": "#4BCC00" };
const COMP_LABEL = { momentum: "Momentum", volatility: "Volatility", volume: "Volume", range: "Range position", insights: "Coin insights", news: "News mood", holistic: "Jev holistic read" };
const COMP_HELP = {
  insights: "Jev-scored CoinGecko Coin Insights, recency-weighted (weighted above news)",
  momentum: "Price vs its 30d and 90d moving averages",
  volatility: "7d realised volatility vs 90d average (higher = fear)",
  volume: "24h volume vs 30d average, signed by today's direction",
  range: "Where price sits in its 90d high–low range",
  news: "Jev-scored headline sentiment, relevance- and recency-weighted",
  holistic: "Jev's overall read of this coin's data + news",
};

const S = {
  scope: "top", n: 100, stables: false, category: null, categories: null, catQuery: "", basket: [],
  coins: [], results: {}, running: false, bucketFilter: new Set(), preset: null, sort: "rank", weights: null, replayScope: null,
};
try { S.basket = JSON.parse(localStorage.getItem("fng-basket") || "[]").slice(0, 50); } catch {}
const saveBasket = () => { try { localStorage.setItem("fng-basket", JSON.stringify(S.basket)); } catch {} };

const bucketOf = (v) => (v == null ? null : v <= 24 ? BUCKETS[0] : v <= 44 ? BUCKETS[1] : v <= 55 ? BUCKETS[2] : v <= 75 ? BUCKETS[3] : BUCKETS[4]);
const name = (c) => (flags.anon ? anonName(c.id) : c.name);
const symbol = (c) => (flags.anon ? "" : c.symbol);
function sentiment(r) {
  if (!r) return null;
  const w = r.weights_used || {};
  const parts = [["insights", r.insights_score], ["news", r.news_score]].filter(([k, v]) => v != null && w[k]);
  const tot = parts.reduce((a, [k]) => a + w[k], 0);
  return tot ? parts.reduce((a, [k, v]) => a + v * w[k], 0) / tot : null;
}
const divergence = (r) => { const s = sentiment(r); return s != null && r.market_score != null ? s - r.market_score : null; };

function sparkSvg(pts, cls = "tw-w-32 tw-h-10") {
  if (!pts || pts.length < 2) return "";
  const lo = Math.min(...pts), hi = Math.max(...pts), span = hi - lo || 1;
  const d = pts.map((p, i) => `${i ? "L" : "M"}${((i / (pts.length - 1)) * 120).toFixed(1)} ${(36 - ((p - lo) / span) * 34 + 1).toFixed(1)}`).join(" ");
  return `<svg viewBox="0 0 120 38" preserveAspectRatio="none" class="${cls}"><path d="${d}" fill="none" stroke="${pts.at(-1) >= pts[0] ? "#00A83E" : "#FF3A33"}" stroke-width="1.6"/></svg>`;
}

function ago(iso) {
  const h = (Date.now() - new Date(iso).getTime()) / 36e5;
  if (isNaN(h)) return "";
  if (h < 1) return `${Math.max(1, Math.round(h * 60))}m ago`;
  if (h < 48) return `${Math.round(h)}h ago`;
  return `${Math.round(h / 24)}d ago`;
}

const PRESETS = {
  divergence: { label: "Divergence: sentiment vs chart", test: (r) => Math.abs(divergence(r) ?? 0) >= 30 },
  fearful: {
    label: "Most fearful large caps",
    test: (r) => {
      const caps = S.coins.map((c) => c.market_cap || 0).sort((a, b) => b - a);
      return (r.coin.market_cap || 0) >= (caps[Math.min(19, caps.length - 1)] ?? 0);
    },
    sort: "fng_asc",
  },
};

// ---------- scope: top coins / category / my coins ----------
const SEG_ON = "tw-bg-white tw-text-gray-900 tw-shadow-sm";
const SEG_OFF = "tw-text-gray-500 hover:tw-text-gray-900";
const locked = () => S.running || flags.replay;

function scopeLabel() {
  const sc = flags.replay ? S.replayScope : { kind: S.scope };
  if (sc?.kind === "category") return (flags.replay ? sc.label : S.category?.name) || "Category";
  if (sc?.kind === "custom") return "Your coins";
  return `Top ${flags.replay ? sc?.n ?? "" : S.n} coins`;
}

function renderScopeTabs() {
  $("scopeTabs").innerHTML = [["top", "Top coins"], ["category", "Categories"], ["custom", "My coins"]].map(([k, l]) =>
    `<button data-k="${k}" class="tw-px-3 tw-py-1.5 tw-rounded-md tw-text-xs tw-leading-4 tw-font-semibold ${S.scope === k ? SEG_ON : SEG_OFF}">${l}${k === "custom" && S.basket.length ? ` <span class="tw-tabular-nums tw-opacity-70">${S.basket.length}</span>` : ""}</button>`).join("");
  $("scopeTabs").querySelectorAll("button").forEach((b) => (b.onclick = () => {
    if (locked() || S.scope === b.dataset.k) return;
    S.scope = b.dataset.k;
    renderScopeTabs(); renderScopePanel(); loadUniverse();
  }));
  if (flags.replay) $("scopeTabs").classList.add("tw-hidden");
}

function renderScopePanel() {
  const el = $("scopePanel");
  if (flags.replay) { el.innerHTML = ""; return; }
  if (S.scope === "top") {
    el.innerHTML = `<div class="tw-flex tw-flex-wrap tw-items-center tw-gap-4">
      <div id="sizeSeg" class="tw-inline-flex tw-rounded-lg tw-bg-gray-100 tw-p-1 tw-gap-1">${[50, 100, 250].map((n) => `<button data-v="${n}" class="tw-px-3 tw-py-1.5 tw-rounded-md tw-text-xs tw-leading-4 tw-font-semibold ${n === S.n ? SEG_ON : SEG_OFF}">Top ${n}</button>`).join("")}</div>
      <label class="tw-flex tw-items-center tw-text-sm tw-font-medium tw-text-gray-900"><input id="stablesChk" type="checkbox" ${S.stables ? "checked" : ""} class="tw-h-4 tw-w-4 tw-mr-2 tw-rounded tw-border tw-border-gray-300 tw-text-primary-500 focus:tw-ring-primary-600">Include stablecoins &amp; wrapped</label></div>`;
    el.querySelectorAll("#sizeSeg button").forEach((b) => (b.onclick = () => { if (locked()) return; S.n = +b.dataset.v; renderScopePanel(); loadUniverse(); }));
    $("stablesChk").onchange = (e) => { if (locked()) { e.target.checked = S.stables; return; } S.stables = e.target.checked; loadUniverse(); };
  } else if (S.scope === "category") renderCategoryPanel();
  else renderCustomPanel();
}

const INPUT_GROUP = "tw-overflow-hidden tw-flex tw-items-center tw-w-full tw-bg-white tw-gap-x-1 tw-rounded-lg tw-ring-2 tw-ring-gray-200 focus-within:tw-ring-primary-500";
const INPUT = "tw-flex-1 tw-bg-transparent tw-border-0 tw-p-0 tw-pl-1 tw-pr-2 tw-text-gray-900 tw-text-sm tw-w-full tw-h-11 placeholder:tw-text-gray-400 focus:tw-ring-0 focus-visible:tw-outline-none";

async function ensureCategories() {
  if (S.categories) return S.categories;
  try { S.categories = await (await fetch("/api/fng/categories")).json(); } catch { S.categories = []; }
  return S.categories;
}

function categoryCard(c) {
  const up = (c.change_24h ?? 0) >= 0;
  const on = S.category?.id === c.id;
  return `<button data-cat="${esc(c.id)}" class="tw-text-left tw-rounded-xl tw-border ${on ? "tw-border-primary-500 tw-ring-2 tw-ring-primary-500" : "tw-border-gray-200 hover:tw-border-gray-300"} tw-bg-white tw-p-3">
    <div class="tw-flex tw-items-start tw-justify-between tw-gap-2"><span class="tw-text-sm tw-font-semibold tw-text-gray-900 tw-leading-5">${esc(c.name)}</span>
      <span class="tw-flex -tw-space-x-1.5 tw-shrink-0">${(c.top_3_coins || []).slice(0, 3).map((u) => `<img src="${esc(u)}" alt="" class="tw-w-5 tw-h-5 tw-rounded-full tw-ring-2 tw-ring-white tw-bg-gray-100">`).join("")}</span></div>
    <div class="tw-flex tw-items-baseline tw-gap-2 tw-mt-1.5 tw-text-xs tw-tabular-nums">${c.market_cap != null ? `<span class="tw-font-semibold tw-text-gray-700">${compactUsd(c.market_cap)}</span><span class="${up ? "gecko-up" : "gecko-down"} tw-font-semibold">${up ? "▴" : "▾"} ${Math.abs(c.change_24h ?? 0).toFixed(1)}%</span>` : `<span class="tw-text-gray-400">no market data</span>`}</div></button>`;
}

async function renderCategoryPanel() {
  const el = $("scopePanel");
  if (S.category && !S.catBrowsing) {
    const c = S.category;
    el.innerHTML = `<div class="tw-flex tw-flex-wrap tw-items-center tw-gap-4 tw-rounded-xl tw-border tw-border-gray-200 tw-bg-gray-50 tw-px-4 tw-py-3">
      <span class="tw-text-xs tw-font-semibold tw-text-gray-500">Category</span>
      <span class="tw-text-base tw-font-bold tw-text-gray-900">${esc(c.name)}</span>
      ${c.market_cap != null ? `<span class="tw-text-sm tw-tabular-nums tw-text-gray-700">Market cap <b>${compactUsd(c.market_cap)}</b></span><span class="tw-text-sm">${pct(c.change_24h)} <span class="tw-text-xs tw-text-gray-500">24h</span></span>` : ""}
      ${c.volume_24h ? `<span class="tw-text-sm tw-tabular-nums tw-text-gray-700">Volume <b>${compactUsd(c.volume_24h)}</b></span>` : ""}
      <div class="tw-ml-auto tw-flex tw-items-center tw-gap-3"><div id="sizeSeg" class="tw-inline-flex tw-rounded-lg tw-bg-white tw-p-1 tw-gap-1 tw-ring-1 tw-ring-gray-200">${[50, 100].map((n) => `<button data-v="${n}" class="tw-px-3 tw-py-1 tw-rounded-md tw-text-xs tw-font-semibold ${n === Math.min(S.n, 100) ? SEG_ON : SEG_OFF}">Top ${n}</button>`).join("")}</div>
      <button id="changeCat" class="${BTN.base} ${BTN.secondary} ${BTN.sm}">Change category</button></div></div>`;
    el.querySelectorAll("#sizeSeg button").forEach((b) => (b.onclick = () => { if (locked()) return; S.n = +b.dataset.v; renderScopePanel(); loadUniverse(); }));
    $("changeCat").onclick = () => { if (locked()) return; S.catBrowsing = true; renderCategoryPanel(); };
    return;
  }
  el.innerHTML = `<div class="tw-rounded-xl tw-border tw-border-gray-200 tw-bg-white tw-p-4">
    <div class="tw-flex tw-flex-wrap tw-items-center tw-gap-3 tw-mb-3"><div class="tw-text-base tw-font-semibold">Pick a category</div>
      <span class="tw-text-xs tw-text-gray-500">Largest by market cap first, or search all ${S.categories ? S.categories.length.toLocaleString() : "1,000+"} CoinGecko categories, including niche ones</span></div>
    <div class="${INPUT_GROUP} tw-mb-3"><span class="tw-pl-3 tw-text-gray-400">⌕</span><input id="catSearch" type="search" autocomplete="off" placeholder="Search categories, e.g. AI Agents, Restaking, Solana Meme" value="${esc(S.catQuery)}" class="${INPUT}"></div>
    <div id="catGrid" class="tw-grid tw-grid-cols-2 md:tw-grid-cols-4 2lg:tw-grid-cols-6 tw-gap-3"><div class="tw-col-span-full tw-text-sm tw-text-gray-500">Loading categories…</div></div></div>`;
  const input = $("catSearch");
  input.oninput = () => { S.catQuery = input.value; paintCatGrid(); };
  await ensureCategories();
  paintCatGrid();
  if (!S.category) input.focus();
}

function paintCatGrid() {
  const grid = $("catGrid");
  if (!grid) return;
  const q = S.catQuery.trim().toLowerCase();
  const list = (S.categories || []).filter((c) => !q || c.name.toLowerCase().includes(q) || c.id.includes(q)).slice(0, q ? 36 : 18);
  grid.innerHTML = list.length ? list.map(categoryCard).join("") : `<div class="tw-col-span-full tw-text-sm tw-text-gray-500">No categories match “${esc(S.catQuery)}”.</div>`;
  grid.querySelectorAll("[data-cat]").forEach((b) => (b.onclick = () => {
    if (locked()) return;
    S.category = S.categories.find((c) => c.id === b.dataset.cat);
    S.catBrowsing = false;
    renderCategoryPanel(); loadUniverse();
  }));
}

function renderCustomPanel() {
  const el = $("scopePanel");
  el.innerHTML = `<div class="tw-rounded-xl tw-border tw-border-gray-200 tw-bg-white tw-p-4">
    <div class="tw-flex tw-flex-wrap tw-items-center tw-gap-3 tw-mb-3"><div class="tw-text-base tw-font-semibold">Pick the coins to score</div>
      <span class="tw-text-xs tw-text-gray-500">Search any coin on CoinGecko by name or ticker · up to 50</span></div>
    <div class="tw-relative">
      <div class="${INPUT_GROUP}"><span class="tw-pl-3 tw-text-gray-400">⌕</span><input id="coinSearch" type="search" autocomplete="off" placeholder="Search coins, e.g. Bitcoin, HYPE, Pudgy Penguins" class="${INPUT}"><span id="coinSpin" class="tw-hidden tw-pr-3 tw-text-xs tw-text-gray-500">searching…</span></div>
      <div id="coinResults" class="tw-hidden tw-absolute tw-left-0 tw-w-[min(620px,calc(100vw-2rem))] tw-top-14 tw-z-40 tw-max-h-[60vh] tw-overflow-y-auto tw-rounded-xl tw-border tw-border-gray-200 tw-bg-white tw-shadow-2xl"></div>
    </div>
    <div id="basket" class="tw-flex tw-flex-wrap tw-gap-2 tw-mt-3"></div></div>`;
  paintBasket();
  let timer = null, req = 0;
  const input = $("coinSearch"), box = $("coinResults");
  input.oninput = () => {
    clearTimeout(timer);
    const q = input.value.trim();
    if (q.length < 2) { box.classList.add("tw-hidden"); return; }
    $("coinSpin").classList.remove("tw-hidden");
    timer = setTimeout(async () => {
      const my = ++req;
      let d = { coins: [], categories: [] };
      try { d = await (await fetch(`/api/fng/search?q=${encodeURIComponent(q)}`)).json(); } catch {}
      if (my !== req) return;
      $("coinSpin").classList.add("tw-hidden");
      const inBasket = new Set(S.basket.map((c) => c.id));
      box.innerHTML = (d.coins.length ? d.coins.map((c) => `<button data-coin="${esc(c.id)}" class="tw-w-full tw-flex tw-items-center tw-gap-3 tw-px-4 tw-py-2.5 hover:tw-bg-gray-50 tw-text-left">
          ${tokenAvatar(c.image, c.symbol, "tw-w-7 tw-h-7")}<div class="tw-flex-1 tw-min-w-0"><span class="tw-font-semibold">${esc(c.name)}</span> <span class="tw-text-xs tw-text-gray-500">${esc(c.symbol || "")}</span></div>
          <span class="tw-text-xs tw-text-gray-500 tw-tabular-nums">${c.rank ? "#" + c.rank : ""}</span><span class="tw-text-xs tw-font-semibold ${inBasket.has(c.id) ? "tw-text-gray-400" : "tw-text-primary-600"}">${inBasket.has(c.id) ? "Added" : "+ Add"}</span></button>`).join("")
        : `<div class="tw-px-4 tw-py-4 tw-text-sm tw-text-gray-500">No coins found for “${esc(q)}”.</div>`) +
        (d.categories.length ? `<div class="tw-px-4 tw-pt-2 tw-pb-1 tw-text-xs tw-font-semibold tw-text-gray-500 tw-border-t tw-border-gray-100">Categories</div>` + d.categories.map((c) => `<button data-opencat="${esc(c.id)}" data-name="${esc(c.name)}" class="tw-w-full tw-text-left tw-px-4 tw-py-2 tw-text-sm hover:tw-bg-gray-50">Open category: <b>${esc(c.name)}</b></button>`).join("") : "");
      box.classList.remove("tw-hidden");
      box.querySelectorAll("[data-coin]").forEach((b) => (b.onclick = () => {
        const c = d.coins.find((x) => x.id === b.dataset.coin);
        if (c && !S.basket.some((x) => x.id === c.id) && S.basket.length < 50) { S.basket.push({ id: c.id, name: c.name, symbol: c.symbol, image: c.image }); saveBasket(); paintBasket(); renderScopeTabs(); loadUniverse(); }
        box.classList.add("tw-hidden"); input.value = ""; input.focus();
      }));
      box.querySelectorAll("[data-opencat]").forEach((b) => (b.onclick = async () => {
        await ensureCategories();
        S.category = S.categories.find((c) => c.id === b.dataset.opencat) || { id: b.dataset.opencat, name: b.dataset.name };
        S.scope = "category"; S.catBrowsing = false;
        renderScopeTabs(); renderScopePanel(); loadUniverse();
      }));
    }, 300);
  };
  input.onkeydown = (e) => { if (e.key === "Escape") box.classList.add("tw-hidden"); if (e.key === "Enter") box.querySelector("[data-coin]")?.click(); };
  document.addEventListener("click", (e) => { if (!el.contains(e.target)) box.classList.add("tw-hidden"); });
}

function paintBasket() {
  const el = $("basket");
  if (!el) return;
  el.innerHTML = S.basket.length
    ? S.basket.map((c) => `<span class="tw-inline-flex tw-items-center tw-gap-1.5 tw-rounded-full tw-bg-gray-100 tw-pl-1 tw-pr-2 tw-py-1 tw-text-xs tw-font-semibold">${tokenAvatar(c.image, c.symbol, "tw-w-5 tw-h-5")}${esc(c.symbol || c.name)}<button data-rm="${esc(c.id)}" class="tw-text-gray-400 hover:tw-text-danger-600" aria-label="Remove">×</button></span>`).join("") +
      `<button id="clearBasket" class="tw-text-xs tw-font-semibold tw-text-gray-500 hover:tw-underline">Clear all</button>`
    : `<span class="tw-text-sm tw-text-gray-500">No coins yet. Search above and add a few.</span>`;
  el.querySelectorAll("[data-rm]").forEach((b) => (b.onclick = () => { if (locked()) return; S.basket = S.basket.filter((c) => c.id !== b.dataset.rm); saveBasket(); paintBasket(); renderScopeTabs(); loadUniverse(); }));
  const clr = $("clearBasket");
  if (clr) clr.onclick = () => { if (locked()) return; S.basket = []; saveBasket(); paintBasket(); renderScopeTabs(); loadUniverse(); };
}

function scopeQuery() {
  if (S.scope === "category" && S.category) return `category=${encodeURIComponent(S.category.id)}&n=${Math.min(S.n, 100)}&label=${encodeURIComponent(S.category.name)}`;
  if (S.scope === "custom") return `ids=${encodeURIComponent(S.basket.map((c) => c.id).join(","))}&n=${Math.max(5, S.basket.length)}&label=Your%20coins`;
  return `n=${S.n}&stables=${S.stables}`;
}

function renderControls() {
  const b = $("runBtn");
  const scored = Object.keys(S.results).length > 0;
  b.className = `${BTN.base} ${BTN.primary} ${BTN.lg} ${S.running ? "tw-opacity-50 tw-pointer-events-none" : ""}`;
  b.innerHTML = S.running ? `${Moon.jevLogo()} Jev is scoring…` : scored ? `↻ Recompute with ${Moon.JEV}` : `Compute Fear &amp; Greed with ${Moon.JEV}`;
  b.onclick = run;
}

// ---------- gauge ----------
function gauge(v, size = "tw-w-36") {
  const segs = [[0, 24], [25, 44], [45, 55], [56, 75], [76, 100]];
  const arc = (a0, a1) => {
    const r = 80, cx = 100, cy = 100;
    const t0 = Math.PI * (1 - a0 / 100), t1 = Math.PI * (1 - a1 / 100);
    return `M${cx + r * Math.cos(t0)} ${cy - r * Math.sin(t0)} A${r} ${r} 0 0 1 ${cx + r * Math.cos(t1)} ${cy - r * Math.sin(t1)}`;
  };
  const paths = segs.map(([a, b], i) => `<path d="${arc(a + 0.8, b - 0.8)}" fill="none" stroke="${BUCKET_HEX[BUCKETS[i]]}" stroke-width="14" stroke-linecap="butt" opacity="${v == null || bucketOf(v) === BUCKETS[i] ? 1 : 0.28}"/>`).join("");
  const ang = v == null ? -90 : -90 + (v / 100) * 180;
  return `<svg viewBox="0 0 200 112" class="${size}">${paths}
    <g class="gauge-needle" transform="rotate(${ang})"><line x1="100" y1="100" x2="100" y2="36" stroke="#0F172A" stroke-width="3.5" stroke-linecap="round"/></g>
    <circle cx="100" cy="100" r="6" fill="#0F172A"/></svg>`;
}

function renderAggregate() {
  const rows = Object.values(S.results).filter((r) => r.fng != null && r.coin.market_cap);
  const el = $("aggregate");
  if (!rows.length) {
    el.innerHTML = `${gauge(null, "tw-w-24")}<div><div class="tw-text-xs tw-font-semibold tw-text-gray-500">${esc(scopeLabel())} · cap-weighted</div><div class="tw-text-sm tw-text-gray-500">Compute to see it</div></div>`;
    return;
  }
  const tot = rows.reduce((a, r) => a + r.coin.market_cap, 0);
  const v = rows.reduce((a, r) => a + r.fng * r.coin.market_cap, 0) / tot;
  const b = bucketOf(v);
  el.innerHTML = `${gauge(v, "tw-w-24")}<div><div class="tw-text-xs tw-font-semibold tw-text-gray-500">${esc(scopeLabel())} · cap-weighted, ${rows.length} coins</div>
    <div class="tw-flex tw-items-baseline tw-gap-2"><span class="tw-text-3xl tw-leading-9 tw-font-bold tw-tabular-nums">${Math.round(v)}</span><span class="tw-rounded-full tw-px-2.5 tw-py-0.5 tw-text-xs tw-font-semibold ${BUCKET_PILL[b]}">${Moon.ic("fng", b)} ${b}</span></div></div>`;
}

// ---------- table ----------
const COLS = [
  ["#", "tw-text-left tw-pl-4 tw-w-12"], ["Coin", "tw-text-left"], ["Price", "tw-text-right"], ["24h", "tw-text-right"], ["7d", "tw-text-right"],
  ["30d", "tw-text-right"], ["Market Cap", "tw-text-right"], ["24h Volume", "tw-text-right"], ["Fear & Greed", "tw-text-left tw-pl-6"],
  ["Sentiment", "tw-text-right"], ["Latest insight", "tw-text-left tw-pr-4"],
];

function renderHead() {
  $("thead").innerHTML = COLS.map(([h, c]) => `<th class="tw-py-3 tw-px-2 tw-whitespace-nowrap ${c} ${["Fear & Greed", "Sentiment", "Latest insight"].includes(h) ? "tw-text-primary-700" : ""}">${h}</th>`).join("");
}

function fngCell(r) {
  if (!r) return S.running ? `<span class="tw-inline-block tw-h-6 tw-w-40 tw-rounded tw-bg-gray-100 tw-animate-pulse"></span>` : "";
  if (r.error) return `<span class="tw-text-xs tw-text-danger-600">Jev error</span>`;
  const b = r.bucket || bucketOf(r.fng);
  return `<div class="jev-pop tw-flex tw-items-center tw-gap-2 tw-min-w-[210px] tw-whitespace-nowrap">
    <span class="tw-inline-flex tw-items-center tw-justify-center tw-w-10 tw-h-7 tw-rounded-md tw-font-bold tw-tabular-nums ${BUCKET_PILL[b]}">${Math.round(r.fng)}</span>
    <span class="tw-text-xs tw-font-semibold tw-text-gray-700">${Moon.ic("fng", b)} ${b}</span>
    ${r.insights_score != null ? `<span class="tw-text-warning-500 tw-text-xs" title="Includes CoinGecko Coin Insights">✦</span>` : r.thin_news ? `<span class="tw-rounded tw-bg-gray-100 tw-text-gray-500 tw-px-1.5 tw-py-0.5 tw-text-[10px] tw-font-semibold">light news</span>` : ""}</div>`;
}

function latestCell(r) {
  if (!r || r.error) return "";
  const ins = (r.insights || []).find((it) => (Date.now() - new Date(it.posted_at).getTime()) / 36e5 <= 7 * 24);
  if (ins) return `<div class="jev-pop tw-text-xs tw-leading-4 tw-text-gray-700 tw-max-w-[360px] tw-truncate"><span class="tw-text-warning-600">✦</span> <span class="tw-font-semibold">${esc(ins.title)}</span> <span class="tw-text-gray-400">· ${ago(ins.posted_at)}</span></div>`;
  const th = r.top_headline;
  return th ? `<div class="jev-pop tw-text-xs tw-leading-4 tw-text-gray-600 tw-max-w-[360px] tw-truncate">${esc(th.title)} <span class="tw-text-gray-400">· ${esc(th.source || "")}</span></div>` : "";
}

function rowHtml(c, i) {
  const r = S.results[c.id];
  const sent = sentiment(r);
  return `<td class="tw-py-3 tw-pl-4 tw-pr-2 tw-text-gray-500 tw-tabular-nums">${c.rank ?? i + 1}</td>
    <td class="tw-py-3 tw-px-2"><div class="tw-flex tw-items-center tw-gap-2.5 tw-min-w-[170px]">${tokenAvatar(c.image, c.symbol, "tw-w-6 tw-h-6")}
      <span class="tw-font-semibold tw-text-gray-900 tw-truncate tw-max-w-[130px]">${esc(name(c))}</span><span class="tw-text-xs tw-text-gray-500">${esc(symbol(c))}</span></div></td>
    <td class="tw-px-2 tw-text-right tw-font-semibold tw-tabular-nums">${price(c.price)}</td>
    <td class="tw-px-2 tw-text-right tw-whitespace-nowrap">${pct(c.change?.["24h"])}</td>
    <td class="tw-px-2 tw-text-right tw-whitespace-nowrap">${pct(c.change?.["7d"])}</td>
    <td class="tw-px-2 tw-text-right tw-whitespace-nowrap">${pct(c.change?.["30d"])}</td>
    <td class="tw-px-2 tw-text-right tw-tabular-nums">${compactUsd(c.market_cap)}</td>
    <td class="tw-px-2 tw-text-right tw-tabular-nums">${compactUsd(c.volume)}</td>
    <td class="tw-px-2 tw-pl-6">${fngCell(r)}</td>
    <td class="tw-px-2 tw-text-right tw-tabular-nums">${r && !r.error ? (sent != null ? `<span class="jev-pop tw-font-semibold ${sent <= 44 ? "gecko-down" : sent >= 56 ? "gecko-up" : ""}">${Math.round(sent)}</span>` : `<span class="tw-text-gray-400">—</span>`) : ""}</td>
    <td class="tw-px-2 tw-pr-4">${latestCell(r)}</td>`;
}

function renderRows() {
  const tbody = $("tbody");
  tbody.innerHTML = "";
  S.coins.forEach((c, i) => {
    const tr = document.createElement("tr");
    tr.id = "row-" + c.id;
    tr.dataset.rank = i;
    tr.className = "tw-cursor-pointer hover:tw-bg-gray-50";
    tr.innerHTML = rowHtml(c, i);
    tr.onclick = () => openDrawer(c.id);
    tbody.appendChild(tr);
  });
  $("emptyState").classList.toggle("tw-hidden", S.coins.length > 0);
  applyFilters();
}

function updateRow(id) {
  const tr = document.getElementById("row-" + id);
  if (!tr) return;
  const i = +tr.dataset.rank;
  tr.innerHTML = rowHtml(S.coins[i], i);
}

function renderFilterBar() {
  const bar = $("filterBar");
  const rs = Object.values(S.results).filter((r) => !r.error && r.fng != null);
  if (!rs.length) { bar.classList.add("tw-hidden"); return; }
  bar.classList.remove("tw-hidden");
  const presets = Object.entries(PRESETS).map(([k, p]) => {
    const on = S.preset === k;
    return `<button data-preset="${k}" class="tw-inline-flex tw-items-center tw-gap-1.5 tw-rounded-lg tw-px-3 tw-py-1.5 tw-text-xs tw-font-semibold ${on ? "tw-bg-primary-500 tw-text-white" : "tw-bg-gray-100 tw-text-gray-900 hover:tw-bg-gray-200"}">★ ${esc(p.label)} <span class="tw-opacity-70 tw-tabular-nums">${rs.filter(p.test).length}</span></button>`;
  }).join("");
  const chips = BUCKETS.map((b) => {
    const on = S.bucketFilter.has(b);
    const n = rs.filter((r) => r.bucket === b).length;
    return `<button data-bucket="${b}" class="tw-inline-flex tw-items-center tw-gap-1.5 tw-rounded-full tw-px-3 tw-py-1 tw-text-xs tw-font-semibold ${BUCKET_PILL[b]} ${on ? "tw-ring-2 tw-ring-offset-1 tw-ring-gray-900" : "tw-opacity-85 hover:tw-opacity-100"}">${Moon.ic("fng", b)} ${b} <span class="tw-tabular-nums tw-opacity-80">${n}</span></button>`;
  }).join("");
  const sorts = [["rank", "Market cap rank"], ["fng_desc", "Fear & Greed ↓ (greediest)"], ["fng_asc", "Fear & Greed ↑ (most fearful)"], ["news_desc", "Sentiment ↓"], ["div", "Biggest divergence"]];
  const clear = S.bucketFilter.size || S.preset ? `<button id="clearF" class="tw-text-xs tw-font-semibold tw-text-gray-500 hover:tw-underline">Clear</button>` : "";
  bar.innerHTML = presets + `<span class="tw-w-px tw-h-5 tw-bg-gray-200 tw-mx-1"></span>` + chips + clear +
    `<label class="tw-ml-auto tw-flex tw-items-center tw-gap-2 tw-text-xs tw-font-semibold tw-text-gray-500">Sort <select id="sortSel" class="tw-rounded-lg tw-border-0 tw-ring-2 tw-ring-gray-200 tw-bg-white tw-text-gray-900 tw-text-xs tw-py-1.5 tw-pl-2 tw-pr-8 focus:tw-ring-primary-500">${sorts.map(([v, l]) => `<option value="${v}" ${S.sort === v ? "selected" : ""}>${l}</option>`).join("")}</select></label>`;
  bar.querySelectorAll("[data-preset]").forEach((b) => (b.onclick = () => {
    S.preset = S.preset === b.dataset.preset ? null : b.dataset.preset;
    if (S.preset && PRESETS[S.preset].sort) S.sort = PRESETS[S.preset].sort;
    if (S.preset === "divergence") S.sort = "div";
    renderFilterBar(); applyFilters();
  }));
  bar.querySelectorAll("[data-bucket]").forEach((b) => (b.onclick = () => { const k = b.dataset.bucket; S.bucketFilter.has(k) ? S.bucketFilter.delete(k) : S.bucketFilter.add(k); renderFilterBar(); applyFilters(); }));
  const c = $("clearF");
  if (c) c.onclick = () => { S.bucketFilter.clear(); S.preset = null; S.sort = "rank"; renderFilterBar(); applyFilters(); };
  $("sortSel").onchange = (e) => { S.sort = e.target.value; applyFilters(); };
}

function applyFilters() {
  const tbody = $("tbody");
  const trs = [...tbody.children];
  const active = S.bucketFilter.size || S.preset;
  let shown = 0;
  trs.forEach((tr) => {
    const r = S.results[tr.id.slice(4)];
    let ok = true;
    if (active) ok = !!r && !r.error && r.fng != null && (!S.bucketFilter.size || S.bucketFilter.has(r.bucket)) && (!S.preset || PRESETS[S.preset].test(r));
    tr.classList.toggle("tw-hidden", !ok);
    if (ok) shown++;
  });
  const R = (tr) => S.results[tr.id.slice(4)];
  const key = {
    rank: (tr) => +tr.dataset.rank,
    fng_desc: (tr) => -(R(tr)?.fng ?? -1),
    fng_asc: (tr) => R(tr)?.fng ?? 999,
    news_desc: (tr) => -(sentiment(R(tr)) ?? -1),
    div: (tr) => -Math.abs(divergence(R(tr)) ?? 0),
  }[S.sort];
  trs.sort((a, b) => key(a) - key(b) || +a.dataset.rank - +b.dataset.rank).forEach((tr) => tbody.appendChild(tr));
  const empty = $("emptyState");
  if (S.coins.length && !shown) { empty.textContent = "No coins match these filters."; empty.classList.remove("tw-hidden"); }
  else if (S.coins.length) empty.classList.add("tw-hidden");
}

function setCounter(p) {
  if (!p) { $("counter").innerHTML = ""; return; }
  const done = p.done != null ? `scored <b class="tw-text-gray-900">${p.done}/${p.total}</b> · ` : "";
  $("counter").innerHTML = `${done}${(p.elapsed_ms / 1000).toFixed(1)} s · ${p.calls} Jev calls · ${usd6(p.cost_usd)}`;
}

// ---------- data ----------
async function loadUniverse() {
  S.results = {};
  S.bucketFilter.clear();
  S.preset = null;
  setCounter(null);
  renderControls();
  renderFilterBar();
  renderAggregate();
  $("tbody").innerHTML = "";
  const empty = $("emptyState");
  empty.textContent = "Loading coins from CoinGecko…";
  empty.classList.remove("tw-hidden");
  try {
    $("pageTitle").textContent = `Fear & Greed · ${scopeLabel()}`;
    if (S.scope === "category" && !S.category) { S.coins = []; $("tbody").innerHTML = ""; empty.textContent = "Pick a category above to load its market feed."; return; }
    if (S.scope === "custom" && !S.basket.length) { S.coins = []; $("tbody").innerHTML = ""; empty.textContent = "Add coins with the search above to score them."; return; }
    const r = await fetch(`/api/fng/universe?${scopeQuery()}`);
    if (!r.ok) throw new Error(await r.text());
    S.coins = await r.json();
    renderRows();
  } catch (e) {
    empty.textContent = "Could not load coins: " + e.message;
  }
}

function sweep(on) {
  const wrap = $("tableWrap");
  wrap.querySelector(".jev-sweep")?.remove();
  if (on) wrap.insertAdjacentHTML("afterbegin", `<div class="jev-sweep"></div>`);
}

function consume(url) {
  S.running = true;
  S.results = {};
  renderControls();
  renderRows();
  sweep(true);
  const es = new EventSource(url);
  es.addEventListener("start", (e) => { const d = JSON.parse(e.data); S.weights = d.weights; });
  es.addEventListener("row", (e) => {
    const d = JSON.parse(e.data);
    S.results[d.coin.id] = d;
    updateRow(d.coin.id);
    renderAggregate();
  });
  es.addEventListener("progress", (e) => setCounter(JSON.parse(e.data)));
  const finish = () => { es.close(); S.running = false; sweep(false); renderControls(); renderFilterBar(); applyFilters(); renderAggregate(); };
  es.addEventListener("done", (e) => { const d = JSON.parse(e.data); setCounter({ ...d, done: Object.keys(S.results).length, total: S.coins.length }); finish(); });
  es.addEventListener("fail", (e) => { $("counter").textContent = "Run failed: " + JSON.parse(e.data).error; finish(); });
  es.onerror = () => { if (S.running) finish(); };
}

function run() {
  if (S.running || !S.coins.length) return;
  if (flags.replay) consume(`/api/fng/replay?name=${encodeURIComponent(flags.replay)}&speed=${flags.speed}`);
  else consume(`/api/fng/run?${scopeQuery()}`);
}

// ---------- drawer ----------
function historySvg(r) {
  const back = (r.backfill || []).map((p) => [p.t, p.market]);
  const hist = (r.history || []).map((p) => [p.t, p.index]).filter((p) => p[1] != null);
  const all = [...back, ...hist];
  if (all.length < 2) return `<p class="tw-text-xs tw-text-gray-500">Not enough history yet.</p>`;
  const W = 580, H = 150, P = 8;
  const t0 = Math.min(...all.map((p) => p[0])), t1 = Math.max(...all.map((p) => p[0]));
  const x = (t) => P + ((t - t0) / (t1 - t0 || 1)) * (W - 2 * P);
  const y = (v) => H - P - (v / 100) * (H - 2 * P);
  const line = (pts) => pts.map((p, i) => `${i ? "L" : "M"}${x(p[0]).toFixed(1)} ${y(p[1]).toFixed(1)}`).join(" ");
  const bands = [[0, 24], [25, 44], [45, 55], [56, 75], [76, 100]].map(([a, b], i) => `<rect x="${P}" y="${y(b)}" width="${W - 2 * P}" height="${y(a) - y(b)}" fill="${BUCKET_HEX[BUCKETS[i]]}" opacity="0.06"/>`).join("");
  const dots = hist.map((p) => `<circle cx="${x(p[0])}" cy="${y(p[1])}" r="3.5" fill="${BUCKET_HEX[bucketOf(p[1])]}"/>`).join("");
  return `<svg viewBox="0 0 ${W} ${H}" class="tw-w-full">${bands}
    <path d="${line(back)}" fill="none" stroke="#64748b" stroke-width="1.5" stroke-dasharray="4 3"/>
    ${hist.length > 1 ? `<path d="${line(hist)}" fill="none" stroke="#0F172A" stroke-width="2"/>` : ""}${dots}</svg>
    <div class="tw-flex tw-gap-4 tw-text-xs tw-text-gray-500 tw-mt-1"><span>┄ market-only index, backfilled 90 days from price history</span><span>● full index (market + news), recorded since launch</span></div>`;
}

function openDrawer(id) {
  const r = S.results[id];
  const c = S.coins.find((x) => x.id === id);
  $("drawerTitle").innerHTML = `${tokenAvatar(c?.image, c?.symbol, "tw-w-7 tw-h-7")}<span>${esc(name(c))}</span><span class="tw-text-sm tw-font-medium tw-text-gray-500">${esc(symbol(c))}</span>`;
  const body = $("drawerBody");
  if (!r) body.innerHTML = `<p class="tw-text-sm tw-text-gray-500">Not scored yet. Click “Compute Fear &amp; Greed with Jev”.</p>`;
  else if (r.error) body.innerHTML = `<p class="tw-text-sm tw-text-danger-600">${esc(r.error)}</p>`;
  else {
    const w = r.weights_used || {};
    const comps = Object.keys(COMP_LABEL).map((k) => {
      const v = r.components[k];
      const used = w[k] != null;
      return `<div class="tw-py-2">
        <div class="tw-flex tw-justify-between tw-text-sm"><span class="tw-font-semibold">${COMP_LABEL[k]} <span class="tw-text-xs tw-font-medium tw-text-gray-500">${used ? `weight ${(w[k] * 100).toFixed(0)}%` : "not used"}</span></span>
          <span class="tw-font-semibold tw-tabular-nums">${v != null ? Math.round(v) : "—"}</span></div>
        <div class="tw-text-xs tw-text-gray-500">${COMP_HELP[k]}</div>
        <div class="tw-h-2 tw-mt-1.5 tw-rounded-full tw-bg-gray-100 tw-overflow-hidden"><div class="tw-h-full tw-rounded-full tw-w-[${Math.round(v ?? 0)}%] ${v == null ? "" : v <= 44 ? "tw-bg-danger-500" : v <= 55 ? "tw-bg-gray-400" : "tw-bg-success-500"} ${used ? "" : "tw-opacity-40"}"></div></div></div>`;
    }).join("");
    const formula = Object.entries(w).map(([k, x]) => `${(x * 100).toFixed(0)}%·${COMP_LABEL[k].toLowerCase()}`).join(" + ");
    const moodTag = (m) => m == null ? "" : `<span class="tw-inline-flex tw-rounded-full tw-px-2 tw-py-0.5 tw-text-[11px] tw-font-semibold ${BUCKET_PILL[bucketOf(m)]}">Jev mood ${Math.round(m)} · ${bucketOf(m)}</span>`;
    const relevant = r.headlines.filter((h) => h.relevant);
    const heads = relevant.map((h) => `<li class="tw-py-2.5">
        <a href="${/^https?:\/\//i.test(h.url || "") ? esc(h.url) : "#"}" target="_blank" rel="noopener noreferrer" class="tw-text-sm tw-font-semibold tw-text-gray-900 hover:tw-underline">${esc(h.title)}</a>
        <div class="tw-flex tw-flex-wrap tw-items-center tw-gap-x-3 tw-gap-y-1 tw-text-xs tw-text-gray-500 tw-mt-1"><span>${esc(h.source || "")}</span><span>${ago(h.posted_at)}</span>${moodTag(h.mood)}</div></li>`).join("");
    const ins = r.insights || [];
    const up = (c?.change?.["24h"] ?? 0) >= 0;
    const coinHead = `<div class="tw-flex tw-items-center tw-gap-3">
        ${tokenAvatar(c?.image, c?.symbol, "tw-w-12 tw-h-12")}
        <div class="tw-flex-1 tw-min-w-0"><div class="tw-text-base tw-font-semibold tw-text-gray-700">${esc(name(c))}</div>
          <div class="tw-flex tw-items-baseline tw-gap-2"><span class="tw-text-lg tw-font-bold tw-tabular-nums">${price(c?.price)}</span>
          <span class="tw-text-sm tw-font-semibold tw-tabular-nums ${up ? "gecko-up" : "gecko-down"}">${up ? "▴" : "▾"} ${Math.abs(c?.change?.["24h"] ?? 0).toFixed(1)}%</span></div></div>
        ${sparkSvg(c?.sparkline_7d, "tw-w-36 tw-h-12")}</div>`;
    const insightsHtml = ins.length ? `
      <section>
        <div class="tw-flex tw-items-center tw-gap-3 tw-mb-3"><span class="tw-text-sm tw-font-medium tw-text-gray-500">Coin insights</span><span class="tw-flex-1 tw-h-px tw-bg-gray-200"></span>
          <span class="tw-text-xs tw-text-gray-500">${r.insights_score != null ? `Jev insight mood <b class="tw-text-gray-900 tw-tabular-nums">${Math.round(r.insights_score)}</b>` : ""}</span></div>
        <div class="tw-rounded-2xl tw-border tw-border-gray-200 tw-p-5 tw-space-y-4">
          ${coinHead}
          <div><div class="tw-text-lg tw-leading-6 tw-font-bold tw-text-gray-900"><span class="tw-text-warning-500">✦</span> ${esc(ins[0].title)}</div>
            <p class="tw-text-base tw-leading-6 tw-text-gray-500 tw-mt-2">${esc(ins[0].description || "")}</p>
            <div class="tw-flex tw-items-center tw-gap-3 tw-mt-3 tw-text-xs tw-text-gray-500"><span>${ago(ins[0].posted_at)}</span>${moodTag(ins[0].mood)}</div></div>
        </div>
        ${ins.slice(1).map((it) => `<div class="tw-rounded-2xl tw-border tw-border-gray-200 tw-p-4 tw-mt-3">
          <div class="tw-text-base tw-leading-6 tw-font-bold tw-text-gray-900"><span class="tw-text-warning-500">✦</span> ${esc(it.title)}</div>
          <p class="tw-text-sm tw-leading-5 tw-text-gray-500 tw-mt-1.5">${esc(it.description || "")}</p>
          <div class="tw-flex tw-items-center tw-gap-3 tw-mt-2 tw-text-xs tw-text-gray-500"><span>${ago(it.posted_at)}</span>${moodTag(it.mood)}</div></div>`).join("")}
      </section>` : "";
    body.innerHTML = `
      <section class="tw-flex tw-items-center tw-gap-5">
        ${gauge(r.fng, "tw-w-44")}
        <div><div class="tw-text-5xl tw-font-bold tw-tabular-nums">${Math.round(r.fng)}</div>
          <span class="tw-inline-block tw-mt-1 tw-rounded-full tw-px-3 tw-py-1 tw-text-sm tw-font-semibold ${BUCKET_PILL[r.bucket]}">${Moon.ic("fng", r.bucket)} ${r.bucket}</span>
          ${r.thin_news ? `<div class="tw-mt-2 tw-text-xs tw-font-semibold tw-text-gray-500">Light news coverage in the last 4 days, so the index leans on ${ins.length ? "coin insights and " : ""}market data.</div>` : ""}</div>
      </section>
      ${insightsHtml}
      <section><div class="tw-text-base tw-font-semibold">What drives it</div><div class="tw-divide-y tw-divide-gray-100">${comps}</div>
        <div class="tw-text-xs tw-font-mono tw-text-gray-500 tw-mt-2">index = ${esc(formula)}</div></section>
      <section><div class="tw-text-base tw-font-semibold tw-mb-1">History</div>${historySvg(r)}</section>
      <section><div class="tw-text-base tw-font-semibold">Recent headlines <span class="tw-text-xs tw-font-medium tw-text-gray-500">· ${relevant.length} about ${esc(name(c))} · scored with the insights in one Jev call, ${r.latency_ms} ms</span></div>
        <ul class="tw-divide-y tw-divide-gray-100">${heads || `<li class="tw-py-2 tw-text-sm tw-text-gray-500">No recent headlines about this coin.</li>`}</ul></section>`;
  }
  $("drawer").classList.remove("tw-translate-x-full");
  $("scrim").classList.remove("tw-hidden");
}
function closeDrawer() { $("drawer").classList.add("tw-translate-x-full"); $("scrim").classList.add("tw-hidden"); }
$("drawerClose").onclick = closeDrawer;
$("scrim").onclick = closeDrawer;
document.addEventListener("keydown", (e) => e.key === "Escape" && closeDrawer());

async function renderDevBar() {
  let items = [];
  try { items = await (await fetch("/api/fixtures?demo=fng")).json(); } catch {}
  $("devBar").innerHTML = `<span>Snapshots</span>
    <select id="snapSel" class="tw-rounded-md tw-border-0 tw-ring-1 tw-ring-gray-200 tw-bg-white tw-text-xs tw-py-1 tw-pl-2 tw-pr-7"><option value="">— live —</option>${items.map((f) => `<option>${esc(f.name)}</option>`).join("")}</select>
    <button id="replayBtn" class="${BTN.base} ${BTN.soft} ${BTN.sm}">Replay</button>`;
  $("replayBtn").onclick = () => {
    const nm = $("snapSel").value;
    const params = new URLSearchParams(location.search);
    if (nm) params.set("replay", nm); else params.delete("replay");
    location.search = params.toString();
  };
  Moon.applyDevVisibility();
}

async function startReplay(nm) {
  const snap = await (await fetch(`/api/fng/snapshot?name=${encodeURIComponent(nm)}`)).json();
  S.coins = Array.isArray(snap) ? snap : snap.coins;
  S.replayScope = Array.isArray(snap) ? { kind: "top" } : snap.scope;
  $("pageTitle").textContent = `Fear & Greed · ${scopeLabel()}`;
  renderAggregate();
  renderRows();
}

renderHead();
renderScopeTabs();
renderScopePanel();
renderControls();
renderAggregate();
renderDevBar();
if (flags.replay) startReplay(flags.replay);
else loadUniverse();
