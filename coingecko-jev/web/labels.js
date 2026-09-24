const { BTN, TONE, esc, compactUsd, price, pct, anonName, tokenAvatar, ago, usd6, flags } = Moon;

const S = {
  chain: "solana",
  window: "1h",
  n: 50,
  rows: [],
  results: {},
  prev: null,
  running: false,
  filters: new Set(),
  preset: null,
  sort: "rank",
  lastRun: null,
};

const CHAINS = { solana: "Solana", base: "Base", bsc: "BNB Chain", eth: "Ethereum", robinhood: "Robinhood Chain" };
let WALLET_CHAINS = {};
fetch("/api/config").then((r) => r.json()).then((c) => { WALLET_CHAINS = c.wallet_chains || {}; if (typeof onWalletChains === "function") onWalletChains(); }).catch(() => {});
const WINDOWS = ["5m", "1h", "6h", "24h"];
const SIZES = [20, 50];
const MOMENTUM_TONE = { pumping: "success", climbing: "primary", flat: "neutral", cooling: "warning", dumping: "danger" };
const MOMENTUM_ORDER = { pumping: 0, climbing: 1, flat: 2, cooling: 3, dumping: 4 };
const CHIP_DEFS = [
  ["organic", "Organic demand", "success"],
  ["artificial", "Artificial demand", "danger"],
  ["wash", "Wash-like", "danger"],
  ["whale", "Whale-heavy", "warning"],
  ["rug", "Rug risk", "danger"],
  ["thin", "Thin liquidity", "warning"],
  ["fresh", "Fresh launch", "info"],
  ["sell", "Sell pressure", "danger"],
];
const PRESETS = {
  organic_momentum: {
    label: "Organic momentum",
    test: (r) => ["pumping", "climbing"].includes(r.momentum?.value) && val(r, "demand") >= 67 && val(r, "rug_risk") < 34,
  },
  exit_liquidity: {
    label: "Likely exit liquidity",
    test: (r) => r.momentum?.value === "dumping" && (hasChip(r, "whale") || hasChip(r, "wash")),
  },
  fresh_risky: { label: "Fresh & risky", test: (r) => hasChip(r, "fresh") && val(r, "rug_risk") >= 67 },
};
const QLABEL = {
  momentum: "Momentum", demand: "Organic demand", wash_like: "Wash-like activity", whale_heavy: "Whale-heavy supply",
  rug_risk: "Rug-pull risk", thin_liq: "Thin liquidity", fresh: "Fresh launch", sell_pressure: "Sell pressure",
};

const val = (r, q) => r?.answers?.[q]?.value ?? 0;
const hasChip = (r, id) => (r?.chips || []).some((c) => c.id === id);
const $ = (id) => document.getElementById(id);

function seg(el, options, current, onPick) {
  el.innerHTML = options
    .map(([v, label]) => {
      const on = String(v) === String(current);
      return `<button data-v="${esc(v)}" class="tw-px-3 tw-py-1.5 tw-rounded-md tw-text-xs tw-leading-4 tw-font-semibold tw-transition-colors ${
        on ? "tw-bg-white tw-text-gray-900 tw-shadow-sm dark:tw-bg-moon-600 dark:tw-text-moon-50" : "tw-text-gray-500 hover:tw-text-gray-900 dark:tw-text-moon-200 dark:hover:tw-text-moon-50"
      }">${esc(label)}</button>`;
    })
    .join("");
  el.querySelectorAll("button").forEach((b) => (b.onclick = () => !S.running && onPick(b.dataset.v)));
}

function chainSegHtml(cur) {
  return Object.keys(CHAINS).map((v) => `<button data-v="${v}" class="tw-inline-flex tw-items-center tw-gap-1.5 tw-px-3 tw-py-1.5 tw-rounded-md tw-text-xs tw-leading-4 tw-font-semibold ${v === cur ? "tw-bg-white tw-text-gray-900 tw-shadow-sm dark:tw-bg-moon-600 dark:tw-text-moon-50" : "tw-text-gray-500 hover:tw-text-gray-900 dark:tw-text-moon-200 dark:hover:tw-text-moon-50"}">${Moon.chainLogo(v)}${CHAINS[v]}</button>`).join("");
}
function renderControls() {
  $("chainSeg").innerHTML = chainSegHtml(S.chain);
  $("chainSeg").querySelectorAll("button").forEach((b) => (b.onclick = () => { if (S.running || b.dataset.v === S.chain) return; S.chain = b.dataset.v; renderControls(); loadFeed(); }));
  seg($("windowSeg"), WINDOWS.map((w) => [w, "Trending " + w]), S.window, (v) => { S.window = v; renderControls(); loadFeed(); });
  seg($("sizeSeg"), SIZES.map((n) => [n, n + " tokens"]), S.n, (v) => { S.n = +v; renderControls(); loadFeed(); });
  const labelled = Object.keys(S.results).length > 0;
  const b = $("labelBtn");
  b.className = `${BTN.base} ${BTN.primary} ${BTN.lg} ${S.running ? "tw-opacity-50 tw-pointer-events-none" : ""}`;
  b.innerHTML = S.running ? `${Moon.jevLogo()} Jev is labelling…` : labelled ? `↻ Re-label with ${Moon.JEV}` : `Label with ${Moon.JEV}`;
  b.onclick = () => runLabels();
}

const COLS = [
  ["#", "tw-w-10 tw-text-left tw-pl-4"],
  ["Token", "tw-text-left"],
  ["Price", "tw-text-right"],
  ["5m", "tw-text-right tw-hidden min-[1600px]:tw-table-cell"],
  ["1h", "tw-text-right"],
  ["6h", "tw-text-right tw-hidden min-[1800px]:tw-table-cell"],
  ["24h", "tw-text-right"],
  ["Volume", "tw-text-right tw-hidden xl:tw-table-cell"],
  ["Liquidity", "tw-text-right tw-hidden xl:tw-table-cell"],
  ["FDV", "tw-text-right tw-hidden min-[1800px]:tw-table-cell"],
  ["Txns 24h", "tw-text-right tw-hidden min-[1600px]:tw-table-cell"],
  ["Makers", "tw-text-right tw-hidden min-[1600px]:tw-table-cell"],
  ["Momentum", "tw-text-left tw-pl-6"],
  ["Jev Risk", "tw-text-left"],
  ["Jev labels", "tw-text-left tw-pr-4"],
];

function renderHead() {
  $("thead").innerHTML = COLS.map(([h, c]) => {
    const jev = ["Momentum", "Jev Risk", "Jev labels"].includes(h);
    return `<th class="tw-py-2.5 tw-px-2 tw-whitespace-nowrap ${c} ${jev ? "tw-text-primary-700 dark:tw-text-primary-400" : ""}">${h}</th>`;
  }).join("");
}

const xrayHref = (row) => `/xray.html?chain=${S.chain}&token=${encodeURIComponent(row.token?.address || "")}&pool=${encodeURIComponent(row.id)}&from=labels${flags.anon ? "&anon=1" : ""}`;
function xrayBtn(row) {
  if (!WALLET_CHAINS[S.chain] || !row.token?.address) return "";
  return `<a href="${xrayHref(row)}" onclick="event.stopPropagation()" title="X-ray this token's wallets" class="tw-inline-flex tw-items-center tw-whitespace-nowrap tw-shrink-0 tw-rounded tw-border tw-border-gray-300 dark:tw-border-moon-600 tw-px-1.5 tw-text-[10px] tw-leading-4 tw-font-bold tw-text-gray-600 dark:tw-text-moon-200 hover:tw-border-primary-500 hover:tw-text-primary-600 dark:hover:tw-text-primary-400">🔬<span class="tw-hidden 2xl:tw-inline tw-ml-0.5">X-ray</span></a>`;
}
function onWalletChains() { if (S.rows?.length) renderRows(); }

function tokenCell(row) {
  const t = row.token || {};
  const sym = flags.anon ? anonName(row.id) : t.symbol || "?";
  const pool = flags.anon ? `${anonName(row.id)} / ${(row.pool_name || "").split("/").pop()?.trim() || "—"}` : row.pool_name;
  return `<div class="tw-flex tw-items-center tw-gap-2.5 tw-min-w-[150px]">
    ${tokenAvatar(t.image_url, sym)}
    <div class="tw-min-w-0">
      <div class="tw-flex tw-items-baseline tw-gap-2">
        <span class="tw-font-semibold tw-text-gray-900 dark:tw-text-moon-50 tw-truncate tw-max-w-[140px]">${esc(sym)}</span>
        <span class="tw-text-xs tw-text-gray-500 dark:tw-text-moon-300">${ago(row.age_h)}</span>
      </div>
      <div class="tw-flex tw-items-center tw-gap-1.5 tw-text-xs tw-leading-4 tw-text-gray-500 dark:tw-text-moon-300"><span class="tw-truncate tw-max-w-[110px] 2xl:tw-max-w-[160px]">${esc(pool)}</span>${xrayBtn(row)}</div>
    </div></div>`;
}

function skeleton(w) {
  return `<span class="tw-inline-block tw-h-5 ${w} tw-rounded tw-bg-gray-100 dark:tw-bg-moon-700 ${S.running ? "tw-animate-pulse" : ""}"></span>`;
}

function momentumPill(m) {
  if (!m?.value) return "";
  const tone = TONE[MOMENTUM_TONE[m.value] || "neutral"];
  return `<span class="jev-pop tw-inline-flex tw-items-center tw-gap-1 tw-whitespace-nowrap tw-rounded-full tw-border tw-px-2.5 tw-py-0.5 tw-text-xs tw-leading-4 tw-font-semibold tw-capitalize ${tone} ${m.low_conf ? "chip-lowconf" : ""}" title="confidence ${(m.confidence ?? 0).toFixed(2)}">${Moon.ic("momentum", m.value)} ${esc(m.value)}${m.low_conf ? " ?" : ""}</span>`;
}

function riskCell(risk) {
  const tone = risk >= 67 ? "tw-bg-danger-500" : risk >= 34 ? "tw-bg-warning-500" : "tw-bg-success-500 dark:tw-bg-success-400";
  const pctW = Math.max(4, Math.round(risk));
  return `<div class="jev-pop tw-flex tw-items-center tw-gap-2 tw-min-w-[96px]">
    <span class="tw-font-semibold tw-tabular-nums tw-w-8">${Math.round(risk)}</span>
    <span class="tw-relative tw-h-1.5 tw-w-14 tw-rounded-full tw-bg-gray-200 dark:tw-bg-moon-600 tw-overflow-hidden">
      <span class="tw-absolute tw-inset-y-0 tw-left-0 ${tone} tw-rounded-full" data-w="${pctW}"></span></span></div>`;
}

function chipHtml(c) {
  return `<span class="jev-pop tw-inline-flex tw-items-center tw-rounded-md tw-border tw-px-2 tw-py-0.5 tw-text-xs tw-leading-4 tw-font-semibold tw-whitespace-nowrap ${TONE[c.tone]} ${c.low_conf ? "chip-lowconf" : ""}">${Moon.ic("chip", c.id)} ${esc(c.label)}${c.low_conf ? " ?" : ""}</span>`;
}

function rowHtml(row, i) {
  const r = S.results[row.id];
  const tx = row.txns?.h24 || {};
  const jevCols = r?.error
    ? `<td colspan="3" class="tw-px-2 tw-text-xs tw-text-danger-500">Jev error: ${esc(r.error)}</td>`
    : r
    ? `<td class="tw-px-2 tw-pl-6">${momentumPill(r.momentum)}</td><td class="tw-px-2">${riskCell(r.risk)}</td>
       <td class="tw-px-2 tw-pr-4"><div class="tw-flex tw-flex-wrap tw-gap-1 tw-min-w-[170px]">${(r.chips || []).map(chipHtml).join("") || `<span class="tw-text-xs tw-text-gray-400 dark:tw-text-moon-400">no flags</span>`}</div></td>`
    : `<td class="tw-px-2 tw-pl-6">${S.running ? skeleton("tw-w-20") : ""}</td><td class="tw-px-2">${S.running ? skeleton("tw-w-16") : ""}</td><td class="tw-px-2 tw-pr-4">${S.running ? skeleton("tw-w-40") : ""}</td>`;
  return `<td class="tw-py-2 tw-pl-4 tw-pr-2 tw-text-gray-500 dark:tw-text-moon-300 tw-tabular-nums">${i + 1}</td>
    <td class="tw-py-2 tw-px-2">${tokenCell(row)}</td>
    <td class="tw-px-2 tw-text-right tw-font-semibold tw-tabular-nums tw-whitespace-nowrap">${price(row.price_usd)}</td>
    ${["m5", "h1", "h6", "h24"].map((w) => `<td class="tw-px-2 tw-text-right tw-whitespace-nowrap ${{ m5: "tw-hidden min-[1600px]:tw-table-cell", h6: "tw-hidden min-[1800px]:tw-table-cell" }[w] || ""}">${pct(row.change?.[w])}</td>`).join("")}
    <td class="tw-px-2 tw-text-right tw-tabular-nums tw-hidden xl:tw-table-cell">${compactUsd(row.volume?.h24)}</td>
    <td class="tw-px-2 tw-text-right tw-tabular-nums tw-hidden xl:tw-table-cell">${compactUsd(row.reserve_usd)}</td>
    <td class="tw-px-2 tw-text-right tw-tabular-nums tw-hidden min-[1800px]:tw-table-cell">${compactUsd(row.fdv_usd)}</td>
    <td class="tw-px-2 tw-text-right tw-tabular-nums tw-whitespace-nowrap tw-hidden min-[1600px]:tw-table-cell"><span class="gecko-up">${(tx.buys ?? 0).toLocaleString()}</span><span class="tw-text-gray-400 dark:tw-text-moon-400"> / </span><span class="gecko-down">${(tx.sells ?? 0).toLocaleString()}</span></td>
    <td class="tw-px-2 tw-text-right tw-tabular-nums tw-hidden min-[1600px]:tw-table-cell">${(row.makers_h24 ?? 0).toLocaleString()}</td>
    ${jevCols}`;
}

function paintBars(scope) {
  scope.querySelectorAll("[data-w]").forEach((el) => el.classList.add(`tw-w-[${el.dataset.w}%]`));
}

function renderRows() {
  const tbody = $("tbody");
  tbody.innerHTML = "";
  S.rows.forEach((row, i) => {
    const tr = document.createElement("tr");
    tr.id = "row-" + row.id;
    tr.className = "tw-cursor-pointer hover:tw-bg-gray-50 dark:hover:tw-bg-moon-700";
    tr.dataset.rank = i;
    tr.innerHTML = rowHtml(row, i);
    tr.onclick = () => openDrawer(row.id);
    tbody.appendChild(tr);
  });
  paintBars(tbody);
  $("emptyState").classList.toggle("tw-hidden", S.rows.length > 0);
  applyFilters();
}

function updateRow(id, flash) {
  const tr = document.getElementById("row-" + id);
  if (!tr) return;
  const i = +tr.dataset.rank;
  tr.innerHTML = rowHtml(S.rows[i], i);
  paintBars(tr);
  if (flash) {
    tr.classList.remove("jev-flash");
    void tr.offsetWidth;
    tr.classList.add("jev-flash");
  }
}

function renderFilterBar() {
  const bar = $("filterBar");
  const results = Object.values(S.results).filter((r) => !r.error);
  if (!results.length) { bar.classList.add("tw-hidden"); return; }
  bar.classList.remove("tw-hidden");
  const count = (id) => results.filter((r) => hasChip(r, id)).length;
  const presetBtns = Object.entries(PRESETS).map(([k, p]) => {
    const n = results.filter(p.test).length;
    const on = S.preset === k;
    return `<button data-preset="${k}" class="tw-inline-flex tw-items-center tw-gap-1.5 tw-rounded-lg tw-px-3 tw-py-1.5 tw-text-xs tw-leading-4 tw-font-semibold ${
      on ? "tw-bg-primary-500 tw-text-white dark:tw-bg-primary-400 dark:tw-text-primary-900" : "tw-bg-gray-100 tw-text-gray-900 dark:tw-bg-moon-700 dark:tw-text-moon-50 hover:tw-bg-gray-200 dark:hover:tw-bg-moon-600"
    }">★ ${esc(p.label)} <span class="tw-tabular-nums tw-opacity-70">${n}</span></button>`;
  }).join("");
  const chipBtns = CHIP_DEFS.map(([id, label, tone]) => {
    const on = S.filters.has(id);
    return `<button data-chip="${id}" class="tw-inline-flex tw-items-center tw-gap-1.5 tw-rounded-md tw-border tw-px-2 tw-py-1 tw-text-xs tw-leading-4 tw-font-semibold ${TONE[tone]} ${
      on ? "tw-ring-2 tw-ring-primary-500 dark:tw-ring-primary-400" : "tw-opacity-80 hover:tw-opacity-100"
    }">${Moon.ic("chip", id)} ${esc(label)} <span class="tw-tabular-nums tw-opacity-70">${count(id)}</span></button>`;
  }).join("");
  const sorts = [["rank", "Trending rank"], ["risk_desc", "Jev Risk ↓"], ["risk_asc", "Jev Risk ↑"], ["demand_desc", "Organic demand ↓"], ["momentum", "Momentum"]];
  const sortSel = `<label class="tw-ml-auto tw-flex tw-items-center tw-gap-2 tw-text-xs tw-font-semibold tw-text-gray-500 dark:tw-text-moon-200">Sort
    <select id="sortSel" class="tw-rounded-lg tw-border-0 tw-ring-2 tw-ring-gray-200 dark:tw-ring-moon-600 tw-bg-white dark:tw-bg-moon-900 tw-text-gray-900 dark:tw-text-moon-50 tw-text-xs tw-py-1.5 tw-pl-2 tw-pr-8 focus:tw-ring-primary-500">${sorts
      .map(([v, l]) => `<option value="${v}" ${S.sort === v ? "selected" : ""}>${l}</option>`).join("")}</select></label>`;
  const clear = S.filters.size || S.preset ? `<button id="clearF" class="tw-text-xs tw-font-semibold tw-text-gray-500 dark:tw-text-moon-200 hover:tw-underline">Clear</button>` : "";
  bar.innerHTML = presetBtns + `<span class="tw-w-px tw-h-5 tw-bg-gray-200 dark:tw-bg-moon-700 tw-mx-1"></span>` + chipBtns + clear + sortSel;
  bar.querySelectorAll("[data-preset]").forEach((b) => (b.onclick = () => { S.preset = S.preset === b.dataset.preset ? null : b.dataset.preset; renderFilterBar(); applyFilters(); }));
  bar.querySelectorAll("[data-chip]").forEach((b) => (b.onclick = () => { const id = b.dataset.chip; S.filters.has(id) ? S.filters.delete(id) : S.filters.add(id); renderFilterBar(); applyFilters(); }));
  const c = $("clearF");
  if (c) c.onclick = () => { S.filters.clear(); S.preset = null; renderFilterBar(); applyFilters(); };
  $("sortSel").onchange = (e) => { S.sort = e.target.value; applyFilters(); };
}

function applyFilters() {
  const tbody = $("tbody");
  const trs = [...tbody.children];
  const active = S.filters.size > 0 || S.preset;
  let shown = 0;
  trs.forEach((tr) => {
    const id = tr.id.slice(4);
    const r = S.results[id];
    let ok = true;
    if (active) {
      ok = !!r && !r.error && [...S.filters].every((f) => hasChip(r, f)) && (!S.preset || PRESETS[S.preset].test(r));
    }
    tr.classList.toggle("tw-hidden", !ok);
    if (ok) shown++;
  });
  const key = {
    rank: (tr) => +tr.dataset.rank,
    risk_desc: (tr) => -(S.results[tr.id.slice(4)]?.risk ?? -1),
    risk_asc: (tr) => S.results[tr.id.slice(4)]?.risk ?? 999,
    demand_desc: (tr) => -val(S.results[tr.id.slice(4)], "demand"),
    momentum: (tr) => MOMENTUM_ORDER[S.results[tr.id.slice(4)]?.momentum?.value] ?? 9,
  }[S.sort];
  trs.sort((a, b) => key(a) - key(b) || +a.dataset.rank - +b.dataset.rank).forEach((tr) => tbody.appendChild(tr));
  const empty = $("emptyState");
  if (S.rows.length && !shown) { empty.textContent = "No tokens match these labels right now."; empty.classList.remove("tw-hidden"); }
  else if (S.rows.length) empty.classList.add("tw-hidden");
}

function setCounter(p) {
  if (!p) { $("counter").innerHTML = ""; return; }
  const done = p.done != null ? `labelled <b class="tw-text-gray-900 dark:tw-text-moon-50">${p.done}/${p.total}</b> · ` : "";
  $("counter").innerHTML = `${done}${(p.elapsed_ms / 1000).toFixed(1)} s · ${p.calls} Jev calls · ${usd6(p.cost_usd)}${p.p50_ms ? ` · p50 ${p.p50_ms} ms` : ""}`;
}

async function loadFeed() {
  S.results = {};
  S.filters.clear();
  S.preset = null;
  setCounter(null);
  renderControls();
  renderFilterBar();
  $("tbody").innerHTML = "";
  const empty = $("emptyState");
  empty.textContent = "Loading trending pools from CoinGecko…";
  empty.classList.remove("tw-hidden");
  try {
    const r = await fetch(`/api/labels/feed?chain=${S.chain}&window=${S.window}&n=${S.n}`);
    if (!r.ok) throw new Error(await r.text());
    S.rows = await r.json();
    renderRows();
  } catch (e) {
    empty.textContent = "Could not load the feed: " + e.message;
  }
}

function sweep(on) {
  const wrap = $("tableWrap");
  wrap.querySelector(".jev-sweep")?.remove();
  if (on) wrap.insertAdjacentHTML("afterbegin", `<div class="jev-sweep"></div>`);
}

function consume(url) {
  S.prev = Object.keys(S.results).length ? JSON.parse(JSON.stringify(S.results)) : null;
  S.running = true;
  renderControls();
  S.rows.forEach((r) => { if (!S.prev) updateRow(r.id); });
  sweep(true);
  const es = new EventSource(url);
  es.addEventListener("row", (e) => {
    const d = JSON.parse(e.data);
    const before = S.prev?.[d.id];
    S.results[d.id] = d;
    const changed = !!before && (before.momentum?.value !== d.momentum?.value || (before.chips || []).map((c) => c.id).join() !== (d.chips || []).map((c) => c.id).join());
    updateRow(d.id, changed);
    if (S.filters.size || S.preset) applyFilters();
  });
  es.addEventListener("progress", (e) => setCounter(JSON.parse(e.data)));
  const finish = () => {
    es.close();
    S.running = false;
    sweep(false);
    renderControls();
    renderFilterBar();
    applyFilters();
  };
  es.addEventListener("done", (e) => { const d = JSON.parse(e.data); setCounter({ ...d, done: Object.keys(S.results).length, total: S.rows.length }); finish(); });
  es.addEventListener("fail", (e) => { $("counter").textContent = "Run failed: " + JSON.parse(e.data).error; finish(); });
  es.onerror = () => { if (S.running) finish(); };
}

function runLabels() {
  if (S.running || !S.rows.length) return;
  if (flags.replay) {
    S.results = {};
    renderRows();
    consume(`/api/labels/replay?name=${encodeURIComponent(flags.replay)}&speed=${flags.speed}`);
    return;
  }
  consume(`/api/labels/run?chain=${S.chain}&ids=${S.rows.map((r) => r.id).join(",")}`);
}

function openDrawer(id) {
  const r = S.results[id];
  const row = S.rows.find((x) => x.id === id);
  const sym = flags.anon ? anonName(id) : row?.token?.symbol;
  $("drawerTitle").innerHTML = `Why Jev labelled <span class="tw-text-primary-600 dark:tw-text-primary-400">${esc(sym)}</span> this way ${row ? xrayBtn(row) : ""}`;
  const body = $("drawerBody");
  if (!r) {
    body.innerHTML = `<p class="tw-text-sm tw-text-gray-500 dark:tw-text-moon-200">Not labelled yet. Click “Label with Jev”.</p>`;
  } else if (r.error) {
    body.innerHTML = `<p class="tw-text-sm tw-text-danger-500">${esc(r.error)}</p>`;
  } else {
    const ans = Object.entries(r.answers).map(([q, a]) => {
      let v = "";
      if (a.type === "choice") {
        const probs = Object.entries(a.probabilities || {}).sort((x, y) => y[1] - x[1]).map(([k, p]) => `<span class="tw-tabular-nums">${esc(k)} ${(p * 100).toFixed(0)}%</span>`).join(" · ");
        v = `<div class="tw-font-semibold tw-capitalize">${esc(a.choice)}</div><div class="tw-text-xs tw-text-gray-500 dark:tw-text-moon-300">${probs}</div>`;
      } else if (a.type === "score") {
        v = `<div class="tw-font-semibold tw-tabular-nums">${a.value.toFixed(0)} / 100</div>`;
      } else {
        v = `<div class="tw-font-semibold tw-tabular-nums">${(a.value * 100).toFixed(0)}% likely</div>`;
      }
      const conf = a.confidence != null ? `<div class="tw-text-xs tw-tabular-nums ${a.confidence < 0.5 ? "tw-text-warning-700 dark:tw-text-warning-400" : "tw-text-gray-500 dark:tw-text-moon-300"}">confidence ${(a.confidence * 100).toFixed(0)}%${a.confidence < 0.5 ? " · needs review" : ""}</div>` : `<div class="tw-text-xs tw-text-gray-400 dark:tw-text-moon-400">yes/no probability</div>`;
      return `<div class="tw-flex tw-justify-between tw-gap-4 tw-py-2.5"><div><div class="tw-text-sm tw-font-semibold">${esc(QLABEL[q] || q)}</div><div class="tw-text-xs tw-text-gray-500 dark:tw-text-moon-300">${a.type}</div></div><div class="tw-text-right tw-text-sm">${v}${conf}</div></div>`;
    }).join("");
    let stateJson = JSON.stringify(r.state, null, 2);
    if (flags.anon) stateJson = stateJson.replace(/"token": ".*?"/, `"token": "${sym}"`);
    body.innerHTML = `
      <div class="tw-flex tw-flex-wrap tw-gap-1">${momentumPill(r.momentum)}${(r.chips || []).map(chipHtml).join("")}</div>
      <section><div class="tw-text-sm tw-font-semibold tw-mb-1">1 · CoinGecko data sent to Jev (state)</div>
        <pre class="tw-text-xs tw-leading-4 tw-font-mono tw-bg-gray-50 dark:tw-bg-moon-900 tw-rounded-lg tw-p-3 tw-overflow-x-auto tw-max-h-80 tw-border tw-border-gray-200 dark:tw-border-moon-700">${esc(stateJson)}</pre></section>
      <section><div class="tw-text-sm tw-font-semibold tw-mb-1">2 · Jev's typed answers <span class="tw-text-xs tw-font-medium tw-text-gray-500 dark:tw-text-moon-300">· ${r.latency_ms} ms · ${r.input_tokens} input tokens</span></div>
        <div class="tw-divide-y tw-divide-gray-200 dark:tw-divide-moon-700">${ans}</div></section>
      <section><div class="tw-text-sm tw-font-semibold tw-mb-1">3 · Jev Risk = ${r.risk.toFixed(1)}</div>
        <div class="tw-text-xs tw-font-mono tw-text-gray-500 dark:tw-text-moon-200">${esc(S.lastRun?.formula || "0.35·rug_risk + 0.20·(100 − demand) + 0.15·wash·100 + 0.15·whale·100 + 0.15·thin·100")}</div>
        <p class="tw-text-xs tw-text-gray-500 dark:tw-text-moon-300 tw-mt-1">Labels and the composite are mapped from Jev's answers by fixed thresholds in code, so every label is explainable.</p></section>`;
  }
  $("drawer").classList.remove("tw-translate-x-full");
  $("scrim").classList.remove("tw-hidden");
}

function closeDrawer() {
  $("drawer").classList.add("tw-translate-x-full");
  $("scrim").classList.add("tw-hidden");
}
$("drawerClose").onclick = closeDrawer;
$("scrim").onclick = closeDrawer;
document.addEventListener("keydown", (e) => e.key === "Escape" && closeDrawer());

async function renderDevBar() {
  const bar = $("devBar");
  let items = [];
  try { items = await (await fetch("/api/fixtures?demo=labels")).json(); } catch {}
  bar.innerHTML = `<span>Snapshots</span>
    <select id="snapSel" class="tw-rounded-md tw-border-0 tw-ring-1 tw-ring-gray-200 dark:tw-ring-moon-600 tw-bg-white dark:tw-bg-moon-900 tw-text-xs tw-py-1 tw-pl-2 tw-pr-7">
      <option value="">— live —</option>${items.map((f) => `<option>${esc(f.name)}</option>`).join("")}</select>
    <button id="replayBtn" class="${BTN.base} ${BTN.soft} ${BTN.sm}">Replay</button>`;
  $("replayBtn").onclick = () => {
    const name = $("snapSel").value;
    if (name) location.search = new URLSearchParams({ ...Object.fromEntries(new URLSearchParams(location.search)), replay: name }).toString();
  };
  Moon.applyDevVisibility();
}

async function startReplay(name) {
  const r = await fetch(`/api/labels/snapshot?name=${encodeURIComponent(name)}`);
  S.rows = await r.json();
  S.chain = name.split("-")[1] || S.chain;
  renderControls();
  renderRows();
}

renderHead();
renderControls();
Moon.loadChains().then(renderControls);
renderDevBar();
if (flags.replay) startReplay(flags.replay);
else loadFeed();
