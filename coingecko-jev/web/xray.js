const { BTN, TONE, esc, compactUsd, price, pct, anonName, tokenAvatar, usd6, flags } = Moon;
const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);

const PERSONA = {
  proven_trader: ["Proven trader", "success", "#32CA5B"],
  accumulator: ["Accumulator", "primary", "#80E038"],
  one_hit_winner: ["One-hit winner", "warning", "#FFE866"],
  whale: ["Whale", "info", "#33C0FF"],
  sniper: ["Sniper", "warning", "#FF9D84"],
  insider_like: ["Insider-like", "danger", "#FF3A33"],
  treasury_allocation: ["Treasury / allocation", "info", "#1971B7"],
  market_maker_bot: ["Market maker / bot", "neutral", "#7D96B5"],
  flipper: ["Flipper", "neutral", "#5D7CA2"],
  new_wallet: ["New wallet", "neutral", "#384A61"],
  protocol: ["Protocol / contract", "neutral", "#212D3B"],
};
const STANCE_TONE = { accumulating: "success", holding: "neutral", distributing: "danger", exited: "neutral" };
const VERDICT_TONE = { smart_money_accumulating: "success", smart_money_distributing: "danger", insider_heavy: "danger", treasury_concentrated: "info", bot_heavy_trading: "warning", bot_driven: "warning", organic_mixed: "info" };
const profileHref = (w) => `/wallet.html?address=${w.address}&chain=${S.chain}&from=xray&back=${encodeURIComponent(location.pathname + location.search)}${flags.anon ? "&anon=1" : ""}`;

const S = {
  chains: {}, chain: params.get("chain") || "base", token: params.get("token"), pool: params.get("pool"),
  ctx: null, wallets: [], agg: null, verdict: null, running: false, filter: null, compBy: "wallets", sort: "default",
};

const walletName = (w) => (flags.anon ? `Wallet #${(Moon.hash(w.address) % 900) + 100}` : w.label || w.short);
const tokenSym = () => (flags.anon ? anonName(S.token || "x") : S.ctx?.symbol || "");

// ---------- header ----------
async function init() {
  try { S.chains = (await (await fetch("/api/config")).json()).wallet_chains || {}; } catch {}
  if (!S.chains[S.chain]) S.chain = Object.keys(S.chains)[0] || "base";
  await Moon.loadChains();
  Moon.chainPicker($("chainSel"), Object.keys(S.chains), S.chain, (v) => { S.chain = v; go(null); }, () => S.running);
  const ref = params.get("from");
  if (ref && /^(labels|pulse)$/.test(ref)) {
    const b = $("backLink");
    b.href = `/${ref}.html${location.search.includes("anon=1") ? "?anon=1" : ""}`;
    b.textContent = `← ${ref === "labels" ? "Jev Labels" : "Pump Pulse"}`;
    b.classList.remove("tw-hidden");
  }
  initSearch();
  renderDevBar();
  if (flags.replay) return startReplay(flags.replay);
  if (S.token) loadToken(); else renderEmpty();
}

function go(token, pool) {
  const p = new URLSearchParams(location.search);
  p.set("chain", S.chain);
  token ? p.set("token", token) : p.delete("token");
  pool ? p.set("pool", pool) : p.delete("pool");
  location.search = p.toString();
}

function renderRun() {
  const b = $("runBtn");
  if (!S.ctx) { b.className = "tw-hidden"; return; }
  const done = S.wallets.length > 0;
  b.className = `${BTN.base} ${BTN.primary} ${BTN.lg} ${S.running ? "tw-opacity-50 tw-pointer-events-none" : ""}`;
  b.innerHTML = S.running ? `${Moon.jevLogo()} Jev is reading wallets…` : done ? `↻ Re-run X-ray with ${Moon.JEV}` : `🔬 X-ray with ${Moon.JEV}`;
  b.onclick = run;
}

// ---------- search / empty ----------
let sTimer = null, sReq = 0;
function initSearch() {
  const input = $("searchInput"), box = $("searchResults");
  if (flags.replay) { $("searchBox").classList.add("tw-hidden"); $("chainSel").classList.add("tw-hidden"); return; }
  input.oninput = () => {
    clearTimeout(sTimer);
    const q = input.value.trim();
    if (q.length < 2) { box.classList.add("tw-hidden"); return; }
    sTimer = setTimeout(async () => {
      const my = ++sReq;
      let rows = [];
      try { const r = await fetch(`/api/xray/search?chain=${S.chain}&q=${encodeURIComponent(q)}`); rows = r.ok ? await r.json() : []; } catch {}
      if (my !== sReq) return;
      box.innerHTML = rows.length ? rows.map((r, i) => `<button data-i="${i}" class="tw-w-full tw-text-left tw-flex tw-items-center tw-gap-3 tw-px-4 tw-py-2.5 hover:tw-bg-gray-50 dark:hover:tw-bg-moon-700 ${i ? "tw-border-t tw-border-gray-100 dark:tw-border-moon-700" : ""}">
          ${tokenAvatar(r.token?.image_url, r.token?.symbol)}<div class="tw-flex-1 tw-min-w-0"><div class="tw-font-semibold tw-truncate">${esc(flags.anon ? anonName(r.token?.address || r.id) : r.pool_name)} <span class="tw-text-xs tw-font-medium tw-text-gray-500 dark:tw-text-moon-300">${esc(r.dex || "")}</span></div>
          <div class="tw-text-xs tw-font-mono tw-text-gray-500 dark:tw-text-moon-300 tw-truncate">${flags.anon ? "••••" : esc(r.token?.address || "")}</div></div>
          <div class="tw-text-right tw-text-xs tw-tabular-nums"><div class="tw-text-sm tw-font-semibold">${price(r.price_usd)}</div><div class="tw-text-gray-500 dark:tw-text-moon-300">Liq ${compactUsd(r.reserve_usd)}</div></div></button>`).join("")
        : `<div class="tw-px-4 tw-py-5 tw-text-sm tw-text-center tw-text-gray-500 dark:tw-text-moon-200">No tokens found for “${esc(q)}”.</div>`;
      box.classList.remove("tw-hidden");
      box.querySelectorAll("[data-i]").forEach((b) => (b.onclick = () => { const r = rows[+b.dataset.i]; go(r.token.address, r.id); }));
    }, 300);
  };
  input.onkeydown = (e) => { if (e.key === "Escape") box.classList.add("tw-hidden"); if (e.key === "Enter") box.querySelector("[data-i]")?.click(); };
  document.addEventListener("click", (e) => { if (!$("searchBox").contains(e.target)) box.classList.add("tw-hidden"); });
}

async function renderEmpty() {
  const el = $("emptyView");
  el.innerHTML = `<div class="tw-rounded-xl tw-border tw-border-gray-200 dark:tw-border-moon-700 tw-bg-white dark:tw-bg-moon-800 tw-p-8">
    <div class="tw-text-2xl tw-leading-8 tw-font-bold">X-ray any token's wallets</div>
    <p class="tw-text-sm tw-text-gray-500 dark:tw-text-moon-200 tw-mt-1 tw-max-w-2xl">Jev reads the top holders and traders of a token (their PnL across every token they've traded, their trading cadence and how they behave on this one) and labels each wallet: proven trader, insider-like, sniper, market maker or bot, and more.</p>
    <div class="tw-text-xs tw-font-semibold tw-text-gray-500 dark:tw-text-moon-300 tw-mt-6 tw-mb-2 tw-flex tw-items-center tw-gap-1.5">Trending on ${Moon.chainBadge(S.chain)}</div>
    <div id="trendGrid" class="tw-grid tw-grid-cols-2 md:tw-grid-cols-5 tw-gap-3"><span class="tw-text-sm tw-text-gray-500">Loading…</span></div></div>`;
  let rows = [];
  try { rows = await (await fetch(`/api/xray/trending?chain=${S.chain}`)).json(); } catch {}
  $("trendGrid").innerHTML = rows.length ? rows.map((r, i) => `<button data-i="${i}" class="tw-text-left tw-rounded-xl tw-border tw-border-gray-200 dark:tw-border-moon-700 hover:tw-border-primary-500 dark:hover:tw-border-primary-400 tw-p-3 tw-flex tw-items-center tw-gap-2.5">
      ${tokenAvatar(r.token?.image_url, r.token?.symbol)}<div class="tw-min-w-0"><div class="tw-font-semibold tw-truncate">${esc(flags.anon ? anonName(r.token.address) : r.token?.symbol)}</div><div class="tw-text-xs tw-tabular-nums">${pct(r.change?.h24)}</div></div></button>`).join("")
    : `<span class="tw-text-sm tw-text-gray-500 dark:tw-text-moon-200">Search for a token above.</span>`;
  $("trendGrid").querySelectorAll("[data-i]").forEach((b) => (b.onclick = () => { const r = rows[+b.dataset.i]; go(r.token.address, r.id); }));
}

// ---------- token ----------
async function loadToken() {
  try {
    const r = await fetch(`/api/xray/token?chain=${S.chain}&token=${encodeURIComponent(S.token)}${S.pool ? "&pool=" + encodeURIComponent(S.pool) : ""}`);
    if (!r.ok) throw new Error();
    S.ctx = await r.json();
  } catch {
    $("emptyView").innerHTML = `<div class="tw-rounded-xl tw-border tw-border-gray-200 dark:tw-border-moon-700 tw-bg-white dark:tw-bg-moon-800 tw-p-8 tw-text-sm tw-text-gray-500 dark:tw-text-moon-200">Couldn't load wallet data for this token. Try another token.</div>`;
    return;
  }
  renderTokenCard();
  renderRun();
}

function renderTokenCard() {
  const c = S.ctx, el = $("tokenCard");
  el.classList.remove("tw-hidden");
  el.innerHTML = `<div class="tw-flex tw-flex-wrap tw-items-center tw-gap-x-8 tw-gap-y-3">
    <div class="tw-flex tw-items-center tw-gap-3">${tokenAvatar(c.image_url, c.symbol, "tw-w-11 tw-h-11")}
      <div><div class="tw-text-xl tw-leading-7 tw-font-bold">${esc(tokenSym())} <span class="tw-text-sm tw-font-medium tw-text-gray-500 dark:tw-text-moon-300">${esc(flags.anon ? "" : c.name || "")}</span></div>
      <div class="tw-text-xs tw-text-gray-500 dark:tw-text-moon-300 tw-flex tw-items-center tw-gap-1.5">${Moon.chainBadge(c.chain)}${c.pool_name && !flags.anon ? " · " + esc(c.pool_name) : ""}</div></div></div>
    <div><div class="tw-text-2xl tw-leading-8 tw-font-bold tw-tabular-nums">${price(c.price_usd)}</div><div class="tw-text-xs">${pct(c.change_24h)} <span class="tw-text-gray-500 dark:tw-text-moon-300">24h</span></div></div>
    ${[["Liquidity", compactUsd(c.liquidity_usd)], ["FDV", compactUsd(c.fdv_usd)], ["24h volume", compactUsd(c.volume_24h_usd)], ["Holders", c.holders_count ? c.holders_count.toLocaleString() : "—"]]
      .map(([k, v]) => `<div><div class="tw-text-xs tw-text-gray-500 dark:tw-text-moon-300">${k}</div><div class="tw-font-semibold tw-tabular-nums">${v}</div></div>`).join("")}
  </div>`;
}

// ---------- verdict + composition ----------
function statCard(title, value, sub, tone) {
  return `<div class="tw-rounded-xl tw-border tw-border-gray-200 dark:tw-border-moon-700 tw-bg-white dark:tw-bg-moon-800 tw-p-4 ${tone ? "" : ""}">
    <div class="tw-text-xs tw-font-semibold tw-text-gray-500 dark:tw-text-moon-300">${title}</div>
    <div class="tw-mt-1 ${tone ? `tw-inline-flex tw-rounded-lg tw-border tw-px-2.5 tw-py-1 tw-text-base tw-font-bold ${TONE[tone]}` : "tw-text-2xl tw-leading-8 tw-font-bold tw-tabular-nums"}">${value}</div>
    <div class="tw-text-xs tw-text-gray-500 dark:tw-text-moon-300 tw-mt-1">${sub}</div></div>`;
}

function renderVerdict() {
  const el = $("verdict"), a = S.agg, v = S.verdict;
  if (!a) { el.classList.add("tw-hidden"); return; }
  el.classList.remove("tw-hidden");
  const net = a.smart_net_flow_24h_usd || 0;
  el.innerHTML =
    statCard("Jev verdict", v ? `${Moon.ic("verdict", v.verdict)} ${esc(v.label)}` : "—", v ? `confidence ${Math.round(v.confidence * 100)}% · holder quality ${Math.round(v.quality)}/100` : "", v ? VERDICT_TONE[v.verdict] : null) +
    statCard("Smart money, net 24h", `<span class="${net > 0 ? "gecko-up" : net < 0 ? "gecko-down" : ""}">${net === 0 ? "$0" : (net > 0 ? "+" : "−") + compactUsd(Math.abs(net))}</span>`, `${a.smart_wallets} proven traders / accumulators`) +
    statCard("Insider-like supply", `${a.insider_like_supply_pct.toFixed(1)}%`, `plus ${(a.treasury_allocation_supply_pct || 0).toFixed(1)}% in treasury / allocation wallets`) +
    statCard("Bot / market maker volume", `${Math.round(a.bot_volume_share * 100)}%`, "of the top wallets' traded volume") +
    statCard("Copy-worthy wallets", `${a.copyable_wallets}`, "proven, skilled, active, not insider-like");
}

function renderComposition() {
  const el = $("composition");
  const scored = S.wallets;
  if (!scored.length) { el.classList.add("tw-hidden"); return; }
  el.classList.remove("tw-hidden");
  const comp = {};
  for (const w of scored) {
    const c = (comp[w.persona] ||= { wallets: 0, volume: 0, supply: 0 });
    c.wallets += 1;
    c.volume += (w.token?.bought_usd || 0) + (w.token?.sold_usd || 0);
    c.supply += w.token?.supply_share_pct || 0;
  }
  const key = { wallets: "wallets", volume: "volume", supply: "supply" }[S.compBy];
  const tot = Object.values(comp).reduce((s, c) => s + c[key], 0) || 1;
  const order = Object.keys(PERSONA).filter((k) => comp[k]);
  el.innerHTML = `<div class="tw-flex tw-flex-wrap tw-items-center tw-gap-3 tw-mb-3">
      <div class="tw-text-base tw-font-semibold">Who's in this token</div>
      <div class="tw-inline-flex tw-rounded-lg tw-bg-gray-100 dark:tw-bg-moon-900 tw-p-1 tw-gap-1 tw-ml-auto">${[["wallets", "By wallets"], ["volume", "By traded volume"], ["supply", "By supply held"]].map(([k, l]) =>
        `<button data-by="${k}" class="tw-px-2.5 tw-py-1 tw-rounded-md tw-text-xs tw-font-semibold ${S.compBy === k ? "tw-bg-white tw-text-gray-900 dark:tw-bg-moon-600 dark:tw-text-moon-50" : "tw-text-gray-500 dark:tw-text-moon-200"}">${l}</button>`).join("")}</div></div>
    <div class="tw-flex tw-h-7 tw-rounded-lg tw-overflow-hidden tw-ring-1 tw-ring-gray-200 dark:tw-ring-moon-700">${order.map((k) => {
      const w = (comp[k][key] / tot) * 100;
      return w > 0.3 ? `<div title="${esc(PERSONA[k][0])} ${w.toFixed(1)}%" class="tw-h-full" data-w="${w.toFixed(2)}" data-c="${PERSONA[k][2]}"></div>` : "";
    }).join("")}</div>
    <div class="tw-flex tw-flex-wrap tw-gap-2 tw-mt-3">${order.map((k) => {
      const on = S.filter === k;
      return `<button data-p="${k}" class="tw-inline-flex tw-items-center tw-gap-1.5 tw-rounded-md tw-border tw-px-2 tw-py-1 tw-text-xs tw-font-semibold ${TONE[PERSONA[k][1]]} ${on ? "tw-ring-2 tw-ring-primary-500 dark:tw-ring-primary-400" : "tw-opacity-85 hover:tw-opacity-100"}">
        <span class="tw-w-2.5 tw-h-2.5 tw-rounded-sm" data-c="${PERSONA[k][2]}"></span>${Moon.ic("persona", k)} ${esc(PERSONA[k][0])} <span class="tw-tabular-nums tw-opacity-70">${((comp[k][key] / tot) * 100).toFixed(0)}% · ${comp[k].wallets}</span></button>`;
    }).join("")}${S.filter ? `<button id="clearFilter" class="tw-text-xs tw-font-semibold tw-text-gray-500 dark:tw-text-moon-200 hover:tw-underline">Show all</button>` : ""}</div>`;
  el.querySelectorAll("[data-w]").forEach((d) => { d.style.width = d.dataset.w + "%"; d.style.background = d.dataset.c; });
  el.querySelectorAll("[data-c]:not([data-w])").forEach((d) => { d.style.background = d.dataset.c; });
  el.querySelectorAll("[data-by]").forEach((b) => (b.onclick = () => { S.compBy = b.dataset.by; renderComposition(); }));
  el.querySelectorAll("[data-p]").forEach((b) => (b.onclick = () => { S.filter = S.filter === b.dataset.p ? null : b.dataset.p; renderComposition(); renderTable(); }));
  const clr = $("clearFilter");
  if (clr) clr.onclick = () => { S.filter = null; renderComposition(); renderTable(); };
}

// ---------- table ----------
const COLS = ["#", "Wallet", "Jev label", "Skill", "Insider-like", "Copy-worthy", "Now", "Supply", "PnL on token", "Lifetime PnL", "Win rate", "Tokens", "Trades/day"];
const XHIDE = { "Win rate": "tw-hidden xl:tw-table-cell", "Tokens": "tw-hidden xl:tw-table-cell", "Trades/day": "tw-hidden xl:tw-table-cell", "Lifetime PnL": "tw-hidden 2lg:tw-table-cell" };
function renderHead() {
  $("thead").innerHTML = COLS.map((h, i) => `<th class="tw-py-2.5 tw-px-2 tw-whitespace-nowrap ${XHIDE[h] || ""} ${i === 0 ? "tw-pl-4 tw-text-left" : i < 3 ? "tw-text-left" : "tw-text-right"} ${["Jev label", "Skill", "Insider-like", "Copy-worthy", "Now"].includes(h) ? "tw-text-primary-700 dark:tw-text-primary-400" : ""}">${h}</th>`).join("");
}

const hasTrades = (w) => !!(w.lifetime?.available && w.lifetime.tokens_traded > 0) || (w.token?.buy_count || 0) + (w.token?.sell_count || 0) > 0;
const usdSigned = (v) => (v == null ? "—" : `<span class="${v > 0 ? "gecko-up" : v < 0 ? "gecko-down" : ""}">${v < 0 ? "−" : ""}${compactUsd(Math.abs(v))}</span>`);

function rowHtml(w, i) {
  const t = w.token || {}, L = w.lifetime || {}, R = w.recent_activity || {};
  const p = PERSONA[w.persona] || [w.persona_label, "neutral"];
  const role = (w.source || "").replace("holder + trader", "holder · trader");
  const tokPnl = (t.realized_pnl_usd || 0) + (t.unrealized_pnl_usd || 0);
  const scored = w.scored && hasTrades(w);
  const noTrades = w.scored && !hasTrades(w);
  return `<td class="tw-py-2 tw-pl-4 tw-pr-2 tw-text-gray-500 dark:tw-text-moon-300 tw-tabular-nums">${i + 1}</td>
    <td class="tw-py-2 tw-px-2"><div class="tw-flex tw-flex-col"><span class="tw-font-semibold tw-font-mono tw-text-xs tw-truncate tw-max-w-[190px]">${esc(walletName(w))}</span>
      <span class="tw-text-[11px] tw-text-gray-500 dark:tw-text-moon-300">${esc(role)}${noTrades ? " · no trade history" : ""}${w.persona !== "protocol" && /^0x[0-9a-fA-F]{40}$/.test(w.address) ? ` · <a href="${profileHref(w)}" class="tw-text-primary-600 dark:tw-text-primary-400 hover:tw-underline" onclick="event.stopPropagation()">profile →</a>` : ""}</span></div></td>
    <td class="tw-px-2"><span class="jev-pop tw-inline-flex tw-whitespace-nowrap tw-rounded-md tw-border tw-px-2 tw-py-0.5 tw-text-xs tw-font-semibold ${TONE[p[1]]} ${w.persona_confidence != null && w.persona_confidence < 0.5 ? "chip-lowconf" : ""}">${Moon.ic("persona", w.persona)} ${esc(p[0])}${w.persona_confidence != null && w.persona_confidence < 0.5 ? " ?" : ""}</span></td>
    <td class="tw-px-2 tw-text-right">${scored && !["market_maker_bot", "protocol"].includes(w.persona) ? `<div class="tw-inline-flex tw-items-center tw-gap-2"><span class="tw-tabular-nums tw-font-semibold tw-w-7">${Math.round(w.skill)}</span><span class="tw-relative tw-h-1.5 tw-w-12 tw-rounded-full tw-bg-gray-200 dark:tw-bg-moon-600 tw-overflow-hidden"><span class="tw-absolute tw-inset-y-0 tw-left-0 tw-rounded-full ${w.skill >= 67 ? "tw-bg-success-500 dark:tw-bg-success-400" : w.skill >= 34 ? "tw-bg-warning-500" : "tw-bg-gray-400 dark:tw-bg-moon-400"}" data-w="${Math.max(3, Math.round(w.skill))}"></span></span></div>` : `<span class="tw-text-gray-400 dark:tw-text-moon-500">—</span>`}</td>
    <td class="tw-px-2 tw-text-right tw-tabular-nums ${w.scored && w.insider >= 0.6 ? "gecko-down tw-font-semibold" : ""}">${w.scored ? Math.round(w.insider * 100) + "%" : "—"}</td>
    <td class="tw-px-2 tw-text-right">${w.copy_worthy ? `<span class="tw-inline-flex tw-rounded-full tw-px-2 tw-py-0.5 tw-text-xs tw-font-bold tw-bg-success-500/15 tw-text-success-400">✓ copy</span>` : ""}</td>
    <td class="tw-px-2 tw-text-right">${w.scored ? `<span class="tw-inline-flex tw-rounded-md tw-border tw-px-2 tw-py-0.5 tw-text-xs tw-font-semibold tw-capitalize ${TONE[STANCE_TONE[w.stance] || "neutral"]}">${Moon.ic("stance", w.stance)} ${esc(w.stance)}</span>` : ""}</td>
    <td class="tw-px-2 tw-text-right tw-tabular-nums">${t.supply_share_pct ? t.supply_share_pct.toFixed(2) + "%" : "—"}</td>
    <td class="tw-px-2 tw-text-right tw-tabular-nums">${scored ? usdSigned(tokPnl) : "—"}</td>
    <td class="tw-px-2 tw-text-right tw-tabular-nums tw-hidden 2lg:tw-table-cell">${scored && L.available ? usdSigned(L.lifetime_realized_pnl_usd) : "—"}</td>
    <td class="tw-px-2 tw-text-right tw-tabular-nums tw-hidden xl:tw-table-cell">${L.win_rate_tokens != null ? Math.round(L.win_rate_tokens * 100) + "%" : "—"}</td>
    <td class="tw-px-2 tw-text-right tw-tabular-nums tw-hidden xl:tw-table-cell">${L.tokens_traded ?? "—"}</td>
    <td class="tw-px-2 tw-pr-4 tw-text-right tw-tabular-nums tw-hidden xl:tw-table-cell">${R.recent_trades_per_day ?? "—"}</td>`;
}

function renderTable() {
  const card = $("tableCard");
  card.classList.remove("tw-hidden");
  const list = S.wallets.filter((w) => !S.filter || w.persona === S.filter);
  const tbody = $("tbody");
  tbody.innerHTML = "";
  list.forEach((w, i) => {
    const tr = document.createElement("tr");
    tr.className = "tw-cursor-pointer hover:tw-bg-gray-50 dark:hover:tw-bg-moon-700";
    tr.innerHTML = rowHtml(w, i);
    tr.onclick = () => openDrawer(w);
    tbody.appendChild(tr);
  });
  tbody.querySelectorAll("[data-w]").forEach((el) => (el.style.width = el.dataset.w + "%"));
  const msg = $("tableMsg");
  msg.classList.toggle("tw-hidden", list.length > 0 || S.running);
  if (!list.length && !S.running) msg.textContent = "No wallets yet.";
}

function sortWallets() {
  const rank = (w) => (w.persona === "protocol" ? 1 : 0);
  S.wallets.sort((a, b) => rank(a) - rank(b) || (b.token?.supply_share_pct || 0) - (a.token?.supply_share_pct || 0) || ((b.token?.bought_usd || 0) + (b.token?.sold_usd || 0)) - ((a.token?.bought_usd || 0) + (a.token?.sold_usd || 0)));
}

// ---------- drawer ----------
function openDrawer(w) {
  $("drawerTitle").innerHTML = `${esc(walletName(w))} ${w.persona !== "protocol" ? `<a href="${profileHref(w)}" class="tw-ml-2 tw-text-sm tw-font-semibold tw-text-primary-600 dark:tw-text-primary-400 hover:tw-underline">Full wallet profile →</a>` : ""}`;
  const p = PERSONA[w.persona] || [w.persona_label, "neutral"];
  const ans = w.answers || {};
  const rowA = (k, v, conf) => `<div class="tw-flex tw-justify-between tw-gap-4 tw-py-2"><span class="tw-text-sm tw-font-semibold">${k}</span><span class="tw-text-sm tw-text-right">${v}${conf != null ? `<div class="tw-text-xs tw-text-gray-500 dark:tw-text-moon-300">confidence ${Math.round(conf * 100)}%</div>` : ""}</span></div>`;
  const probs = ans.persona?.probabilities ? Object.entries(ans.persona.probabilities).sort((a, b) => b[1] - a[1]).slice(0, 4).map(([k, v]) => `${esc((PERSONA[k] || [k])[0])} ${Math.round(v * 100)}%`).join(" · ") : "";
  const clean = (o) => JSON.stringify(o, (k, v) => (flags.anon && ["api_label"].includes(k) ? undefined : v), 2);
  $("drawerBody").innerHTML = w.scored ? `
    <div class="tw-flex tw-flex-wrap tw-gap-2"><span class="tw-inline-flex tw-rounded-md tw-border tw-px-2.5 tw-py-1 tw-text-sm tw-font-bold ${TONE[p[1]]}">${Moon.ic("persona", w.persona)} ${esc(p[0])}</span>${w.copy_worthy ? `<span class="tw-inline-flex tw-rounded-md tw-px-2.5 tw-py-1 tw-text-sm tw-font-bold tw-bg-success-500/15 tw-text-success-400">✓ Copy-worthy</span>` : ""}</div>
    <section><div class="tw-text-sm tw-font-semibold tw-mb-1">Jev's typed answers <span class="tw-text-xs tw-font-medium tw-text-gray-500 dark:tw-text-moon-300">· ${w.latency_ms} ms · ${w.input_tokens} input tokens</span></div>
      <div class="tw-divide-y tw-divide-gray-200 dark:tw-divide-moon-700">
        ${rowA("Behaviour", `<b>${esc(p[0])}</b><div class="tw-text-xs tw-text-gray-500 dark:tw-text-moon-300">${probs}</div>`, w.persona_confidence)}
        ${rowA("Skill (repeatable, not luck)", `<b class="tw-tabular-nums">${Math.round(w.skill)}/100</b>`, w.skill_confidence)}
        ${rowA("Looks like an insider on this token", `<b class="tw-tabular-nums">${Math.round(w.insider * 100)}%</b>`)}
        ${rowA("Worth copying", `<b class="tw-tabular-nums">${Math.round(w.copyable * 100)}%</b>`)}
        ${rowA("What it's doing now", `<b class="tw-capitalize">${esc(w.stance)}</b>`)}
      </div>
      <p class="tw-text-xs tw-text-gray-500 dark:tw-text-moon-300 tw-mt-2">"Copy-worthy" = proven trader, skill ≥ 70, insider-like below 50%, traded in the last 30 days.</p></section>
    <section><div class="tw-text-sm tw-font-semibold tw-mb-1">Wallet data Jev read</div>
      <pre class="tw-text-xs tw-leading-4 tw-font-mono tw-bg-gray-50 dark:tw-bg-moon-900 tw-rounded-lg tw-p-3 tw-overflow-x-auto tw-max-h-96 tw-border tw-border-gray-200 dark:tw-border-moon-700">${esc(clean({ on_this_token: w.token, lifetime: w.lifetime, recent_activity: w.recent_activity }))}</pre></section>`
    : `<p class="tw-text-sm tw-text-gray-500 dark:tw-text-moon-200">${esc(w.label || "This address")} is a protocol, pool, exchange or treasury contract. It holds ${w.token?.supply_share_pct?.toFixed(2) ?? "?"}% of supply and isn't scored as a trader.</p>`;
  $("drawer").classList.remove("tw-translate-x-full");
  $("scrim").classList.remove("tw-hidden");
}
const closeDrawer = () => { $("drawer").classList.add("tw-translate-x-full"); $("scrim").classList.add("tw-hidden"); };
$("drawerClose").onclick = closeDrawer;
$("scrim").onclick = closeDrawer;
document.addEventListener("keydown", (e) => e.key === "Escape" && closeDrawer());

// ---------- run / replay ----------
function sweep(on) {
  const card = $("tableCard");
  card.querySelector(".jev-sweep")?.remove();
  if (on) card.insertAdjacentHTML("afterbegin", `<div class="jev-sweep"></div>`);
}

function consume(url) {
  S.running = true; S.wallets = []; S.agg = null; S.verdict = null; S.filter = null;
  renderRun(); renderVerdict(); renderHead(); renderTable(); renderComposition();
  $("tableMsg").textContent = "Jev is reading wallets…"; $("tableMsg").classList.remove("tw-hidden");
  sweep(true);
  const es = new EventSource(url);
  let t = null;
  const repaint = () => { if (t) return; t = setTimeout(() => { t = null; sortWallets(); renderTable(); renderComposition(); }, 250); };
  es.addEventListener("start", (e) => { const d = JSON.parse(e.data); if (!S.ctx) { S.ctx = d.token; renderTokenCard(); } });
  es.addEventListener("wallet", (e) => { const d = JSON.parse(e.data); if (!d.error) { S.wallets.push(d); repaint(); } });
  es.addEventListener("progress", (e) => { const p = JSON.parse(e.data); $("counter").innerHTML = `read <b class="tw-text-gray-900 dark:tw-text-moon-50">${p.done}/${p.total}</b> wallets · ${(p.elapsed_ms / 1000).toFixed(1)} s · ${p.calls} Jev calls · ${usd6(p.cost_usd)}`; });
  es.addEventListener("verdict", (e) => { const d = JSON.parse(e.data); S.agg = d.aggregate; S.verdict = d.verdict; renderVerdict(); });
  const finish = () => { es.close(); S.running = false; sweep(false); sortWallets(); renderRun(); renderTable(); renderComposition(); };
  es.addEventListener("done", finish);
  es.addEventListener("fail", (e) => { $("counter").textContent = JSON.parse(e.data).error; finish(); });
  es.onerror = () => { if (S.running) finish(); };
}

function run() {
  if (S.running || !S.ctx) return;
  if (flags.replay) consume(`/api/xray/replay?name=${encodeURIComponent(flags.replay)}&speed=${flags.speed}`);
  else consume(`/api/xray/run?chain=${S.chain}&token=${encodeURIComponent(S.token)}${S.pool ? "&pool=" + encodeURIComponent(S.pool) : ""}`);
}

async function startReplay(name) {
  const r = await fetch(`/api/xray/snapshot?name=${encodeURIComponent(name)}`);
  if (!r.ok) return;
  const d = await r.json();
  S.ctx = d.token; S.token = d.token.address; S.chain = d.token.chain;
  renderTokenCard(); renderRun();
}

async function renderDevBar() {
  let items = [];
  try { items = await (await fetch("/api/fixtures?demo=xray")).json(); } catch {}
  $("devBar").innerHTML = `<span>Snapshots</span><select id="snapSel" class="tw-rounded-md tw-border-0 tw-ring-1 tw-ring-gray-200 dark:tw-ring-moon-600 tw-bg-white dark:tw-bg-moon-900 tw-text-xs tw-py-1 tw-pl-2 tw-pr-7"><option value="">— live —</option>${items.map((f) => `<option>${esc(f.name)}</option>`).join("")}</select><button id="replayBtn" class="${BTN.base} ${BTN.soft} ${BTN.sm}">Replay</button>`;
  $("replayBtn").onclick = () => { const n = $("snapSel").value; const p = new URLSearchParams(location.search); n ? p.set("replay", n) : p.delete("replay"); location.search = p.toString(); };
  Moon.applyDevVisibility();
}

renderHead();
init();
