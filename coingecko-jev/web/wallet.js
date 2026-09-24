const { BTN, TONE, esc, compactUsd, price, pct, flags } = Moon;
const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);

const PERSONA = {
  proven_trader: ["Proven trader", "success"], accumulator: ["Accumulator", "primary"], one_hit_winner: ["One-hit winner", "warning"],
  whale: ["Whale", "info"], sniper: ["Sniper", "warning"], market_maker_bot: ["Market maker / bot", "neutral"], flipper: ["Flipper", "neutral"],
  new_wallet: ["New wallet", "neutral"], insider_like: ["Insider-like", "danger"], treasury_allocation: ["Treasury / allocation", "info"],
};
const STYLE = { scalper: "Scalper", swing_trader: "Swing trader", position_holder: "Position holder", arbitrage_bot: "Arbitrage / bot" };
const S = { chains: {}, address: params.get("address"), chain: params.get("chain") || "auto", data: null, tab: "holdings" };

const usdSigned = (v) => (v == null ? "—" : `<span class="${v > 0 ? "gecko-up" : v < 0 ? "gecko-down" : ""}">${v < 0 ? "−" : v > 0 ? "+" : ""}${compactUsd(Math.abs(v))}</span>`);
const addrShow = (a) => (flags.anon ? `Wallet #${(Moon.hash(a || "") % 900) + 100}` : a);
const netName = (n) => S.chains[n] || n;
const netBadge = (n) => Moon.chainBadge(n);
const when = (iso) => { const h = (Date.now() - new Date(iso).getTime()) / 36e5; return isNaN(h) ? "—" : h < 1 ? `${Math.max(1, Math.round(h * 60))}m ago` : h < 48 ? `${Math.round(h)}h ago` : `${Math.round(h / 24)}d ago`; };

async function init() {
  try { S.chains = (await (await fetch("/api/config")).json()).wallet_chains || {}; } catch {}
  await Moon.loadChains();
  const picker = Moon.chainPicker($("chainSel"), ["auto", ...Object.keys(S.chains)], S.chain, (v) => { S.chain = v; });
  $("goBtn").className = `${BTN.base} ${BTN.primary} ${BTN.md}`;
  $("goBtn").innerHTML = `Profile with ${Moon.JEV}`;
  $("addrInput").value = S.address && !flags.anon ? S.address : "";
  $("addrForm").onsubmit = (e) => {
    e.preventDefault();
    const a = $("addrInput").value.trim();
    if (!/^0x[0-9a-fA-F]{40}$/.test(a)) { $("addrInput").focus(); return; }
    const p = new URLSearchParams(location.search); p.set("address", a); p.set("chain", S.chain); p.delete("replay");
    location.search = p.toString();
  };
  const from = params.get("from");
  const backs = { xray: ["Wallet X-ray", params.get("back") || "/xray.html"], radar: ["Smart Money Radar", "/radar.html"], pulse: ["Pump Pulse", "/pulse.html"] };
  if (backs[from]) {
    const [label, href] = backs[from];
    $("backLink").href = href.startsWith("/") ? href : "/" + from + ".html";
    $("backLink").textContent = `← ${label}`;
    $("backLink").classList.remove("tw-hidden");
  }
  renderDevBar();
  if (flags.replay) return load(`/api/wallet/snapshot?name=${encodeURIComponent(flags.replay)}`);
  if (S.address) load(`/api/wallet/profile?address=${encodeURIComponent(S.address)}&chain=${S.chain}`);
  else renderEmpty();
}

function renderEmpty() {
  $("emptyView").innerHTML = `<div class="tw-rounded-xl tw-border tw-border-gray-200 dark:tw-border-moon-700 tw-bg-white dark:tw-bg-moon-800 tw-p-8">
    <div class="tw-text-2xl tw-leading-8 tw-font-bold">Profile any wallet</div>
    <p class="tw-text-sm tw-text-gray-500 dark:tw-text-moon-200 tw-mt-1 tw-max-w-2xl">Paste an address. Jev reads its PnL across every token it has traded on ${Object.keys(S.chains).length} networks, its portfolio, its trading cadence and the kinds of tokens it trades, then labels it: proven trader, whale, sniper, market maker or bot, and more. Tags like memecoin-focused or disciplined exits come with confidence.</p>
    <p class="tw-text-sm tw-text-gray-500 dark:tw-text-moon-200 tw-mt-3">Don't know who to look at? <a href="/radar.html" class="tw-font-semibold tw-text-primary-600 dark:tw-text-primary-400 hover:tw-underline">Start from the Smart Money Radar →</a></p></div>`;
}

async function load(url) {
  $("emptyView").innerHTML = `<div class="tw-relative tw-overflow-hidden tw-rounded-xl tw-border tw-border-gray-200 dark:tw-border-moon-700 tw-bg-white dark:tw-bg-moon-800 tw-p-10 tw-text-center"><div class="jev-sweep"></div>
    <div class="tw-text-base tw-font-semibold tw-inline-flex tw-items-center tw-gap-2">${Moon.jevLogo("tw-w-5 tw-h-5")} Jev is reading this wallet…</div><div class="tw-text-sm tw-text-gray-500 dark:tw-text-moon-200 tw-mt-1">multi-chain PnL · portfolio · recent trades</div></div>`;
  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error();
    S.data = await r.json();
  } catch {
    $("emptyView").innerHTML = `<div class="tw-rounded-xl tw-border tw-border-gray-200 dark:tw-border-moon-700 tw-bg-white dark:tw-bg-moon-800 tw-p-8 tw-text-sm tw-text-gray-500 dark:tw-text-moon-200">Couldn't load data for this wallet. Check the address and try again.</div>`;
    return;
  }
  if (S.data.locked) { $("emptyView").innerHTML = Moon.lockedHtml(S.data); return; }
  $("emptyView").innerHTML = "";
  renderSummary();
  renderTabs();
}

function stat(k, v, sub) {
  return `<div><div class="tw-text-xs tw-text-gray-500 dark:tw-text-moon-300">${k}</div><div class="tw-text-xl tw-leading-7 tw-font-bold tw-tabular-nums">${v}</div>${sub ? `<div class="tw-text-xs tw-text-gray-500 dark:tw-text-moon-300">${sub}</div>` : ""}</div>`;
}

function renderSummary() {
  const d = S.data, p = d.profile, L = p.lifetime || {}, P = p.portfolio || {}, R = p.recent_activity || {};
  const per = PERSONA[p.persona] || [p.persona_label, "neutral"];
  const a = p.answers || {};
  const probs = a.persona?.probabilities ? Object.entries(a.persona.probabilities).sort((x, y) => y[1] - x[1]).slice(0, 4) : [];
  const tagRows = Object.entries(a).filter(([k]) => k.startsWith("tag_")).map(([k, v]) => [k.slice(4), v.value]);
  const TAGN = { memecoin_focus: "Memecoin-focused", bluechip_focus: "Blue-chip focused", early_buyer: "Early buyer", risk_manager: "Disciplined exits" };
  $("summary").classList.remove("tw-hidden");
  $("summary").innerHTML = `<div class="tw-grid tw-grid-cols-1 2lg:tw-grid-cols-[1fr_380px] tw-gap-4">
    <div class="tw-rounded-xl tw-border tw-border-gray-200 dark:tw-border-moon-700 tw-bg-white dark:tw-bg-moon-800 tw-p-5">
      <div class="tw-flex tw-flex-wrap tw-items-center tw-gap-3">
        <span class="tw-font-mono tw-text-base tw-font-semibold tw-break-all">${esc(addrShow(p.address))}</span>
        <span class="tw-rounded-md tw-bg-gray-100 dark:tw-bg-moon-700 tw-px-2 tw-py-0.5 tw-text-xs tw-font-semibold">Wallet</span>
        <span class="tw-text-xs tw-text-gray-500 dark:tw-text-moon-300 tw-inline-flex tw-items-center tw-gap-1.5">trades read on ${Moon.chainBadge(d.chain)} · PnL & balances across all networks</span>
      </div>
      <div class="tw-flex tw-flex-wrap tw-items-center tw-gap-2 tw-mt-3">
        <span class="jev-pop tw-inline-flex tw-items-center tw-gap-1.5 tw-rounded-lg tw-border tw-px-3 tw-py-1 tw-text-base tw-font-bold ${TONE[per[1]]}">${Moon.ic("persona", p.persona)} ${esc(per[0])}</span>
        <span class="tw-inline-flex tw-items-center tw-gap-1.5 tw-rounded-lg tw-border tw-px-3 tw-py-1 tw-text-sm tw-font-semibold ${TONE.neutral}">${Moon.ic("style", p.style)} ${esc(STYLE[p.style] || p.style)}</span>
        ${p.copy_worthy ? `<span class="tw-inline-flex tw-rounded-lg tw-px-3 tw-py-1 tw-text-sm tw-font-bold tw-bg-success-500/15 tw-text-success-400">✓ Copy-worthy</span>` : ""}
        ${(p.tags || []).map((t) => `<span class="jev-pop tw-inline-flex tw-items-center tw-gap-1 tw-rounded-md tw-border tw-px-2 tw-py-0.5 tw-text-xs tw-font-semibold ${TONE.info}">${Moon.ic("tag", t)} ${esc(t)}</span>`).join("")}
      </div>
      <div class="tw-grid tw-grid-cols-2 md:tw-grid-cols-4 2lg:tw-grid-cols-4 tw-gap-x-6 tw-gap-y-4 tw-mt-5">
        ${stat("Portfolio value", P.available ? compactUsd(P.portfolio_value_usd) : "—", P.holdings ? `${P.holdings} holdings` : "")}
        ${stat("Realized PnL", L.available ? usdSigned(L.lifetime_realized_pnl_usd) : "—", "lifetime, all networks")}
        ${stat("Unrealized PnL", L.available ? usdSigned(L.lifetime_unrealized_pnl_usd) : "—", "")}
        ${stat("Win rate", L.win_rate_tokens != null ? Math.round(L.win_rate_tokens * 100) + "%" : "—", "of most-traded tokens sold")}
        ${stat("Tokens traded", L.tokens_traded != null ? L.tokens_traded.toLocaleString() : "—", "")}
        ${stat("Trades", L.total_buys != null ? (L.total_buys + L.total_sells).toLocaleString() : "—", L.total_buys != null ? `${L.total_buys.toLocaleString()} buys · ${L.total_sells.toLocaleString()} sells` : "")}
        ${stat("Active on", (L.active_networks || []).length ? `<div class="tw-flex tw-flex-wrap tw-gap-x-3 tw-gap-y-1 tw-text-sm tw-font-semibold tw-mt-1">${(L.active_networks || []).map((n) => Moon.chainBadge(n, "tw-w-5 tw-h-5")).join("")}</div>` : "—", "")}
        ${stat("Last trade", R.days_since_last_trade != null ? (R.days_since_last_trade < 1 ? "today" : Math.round(R.days_since_last_trade) + "d ago") : "—", R.recent_trades_per_day ? `${R.recent_trades_per_day} trades/day recently` : "")}
      </div>
    </div>
    <div class="tw-rounded-xl tw-border tw-border-gray-200 dark:tw-border-moon-700 tw-bg-white dark:tw-bg-moon-800 tw-p-5">
      <div class="tw-text-sm tw-font-semibold">Jev's read <span class="tw-text-xs tw-font-medium tw-text-gray-500 dark:tw-text-moon-300">· ${p.latency_ms} ms · ${p.input_tokens} tokens</span></div>
      <div class="tw-mt-2 tw-space-y-1.5">${probs.map(([k, v]) => `<div class="tw-flex tw-items-center tw-gap-2 tw-text-xs"><span class="tw-w-36 tw-truncate">${Moon.ic("persona", k)} ${esc((PERSONA[k] || [k])[0])}</span><span class="tw-flex-1 tw-h-1.5 tw-rounded-full tw-bg-gray-200 dark:tw-bg-moon-600 tw-overflow-hidden"><span class="tw-block tw-h-full tw-bg-primary-500 dark:tw-bg-primary-400 tw-rounded-full" data-w="${Math.round(v * 100)}"></span></span><span class="tw-tabular-nums tw-w-9 tw-text-right">${Math.round(v * 100)}%</span></div>`).join("")}</div>
      <div class="tw-divide-y tw-divide-gray-200 dark:tw-divide-moon-700 tw-mt-3 tw-text-sm">
        <div class="tw-flex tw-justify-between tw-py-1.5"><span>Skill (repeatable, not luck)</span><b class="tw-tabular-nums">${Math.round(p.skill)}/100</b></div>
        <div class="tw-flex tw-justify-between tw-py-1.5"><span>Worth copying</span><b class="tw-tabular-nums">${Math.round(p.copyable * 100)}%</b></div>
        ${tagRows.map(([k, v]) => `<div class="tw-flex tw-justify-between tw-py-1.5"><span>${Moon.ic("tag", TAGN[k])} ${esc(TAGN[k] || k)}</span><b class="tw-tabular-nums ${v >= 0.6 ? "tw-text-info-400" : "tw-text-gray-500 dark:tw-text-moon-300"}">${Math.round(v * 100)}%</b></div>`).join("")}
      </div>
      <p class="tw-text-xs tw-text-gray-500 dark:tw-text-moon-300 tw-mt-2">Tags at 60%+ are shown on the profile. "Copy-worthy" = proven trader, skill ≥ 70, traded in the last 30 days.</p>
    </div></div>`;
  $("summary").querySelectorAll("[data-w]").forEach((e) => (e.style.width = e.dataset.w + "%"));
}

function tokenIcon(img, sym, net) {
  return `<span class="tw-relative tw-inline-flex tw-shrink-0">${Moon.tokenAvatar(img, sym, "tw-w-7 tw-h-7")}<span class="tw-absolute -tw-bottom-1 -tw-right-1 tw-rounded-full tw-ring-2 tw-ring-white dark:tw-ring-moon-800">${Moon.chainLogo(net, "tw-w-3.5 tw-h-3.5")}</span></span>`;
}

const TABS = [["holdings", "Holdings"], ["performance", "Performance"], ["trades", "Recent trades"], ["transfers", "Transfers"], ["chains", "By chain"]];
function renderTabs() {
  $("tabs").classList.remove("tw-hidden");
  const n = { holdings: (S.data.holdings || []).length, performance: S.data.performance.length, trades: S.data.trades.length, transfers: (S.data.transfers || []).length, chains: (S.data.networks || []).length };
  $("tabBar").innerHTML = TABS.map(([k, l]) => `<button data-t="${k}" class="tw-py-3 tw-text-sm tw-font-semibold tw-border-b-2 ${S.tab === k ? "tw-border-primary-500 tw-text-gray-900 dark:tw-border-primary-400 dark:tw-text-moon-50" : "tw-border-transparent tw-text-gray-500 dark:tw-text-moon-300 hover:tw-text-gray-900 dark:hover:tw-text-moon-50"}">${l} <span class="tw-text-xs tw-opacity-70">${n[k]}</span></button>`).join("");
  $("tabBar").querySelectorAll("[data-t]").forEach((b) => (b.onclick = () => { S.tab = b.dataset.t; renderTabs(); }));
  $("tabBody").innerHTML = { holdings: holdingsHtml, performance: perfHtml, trades: tradesHtml, transfers: transfersHtml, chains: chainsHtml }[S.tab]();
  $("tabBody").querySelectorAll("[data-w]").forEach((e) => (e.style.width = e.dataset.w + "%"));
}

const TH = (cols) => `<thead class="tw-text-xs tw-font-semibold tw-text-gray-500 dark:tw-text-moon-300 tw-border-b tw-border-gray-200 dark:tw-border-moon-700"><tr>${cols.map(([h, r], i) => `<th class="tw-py-2.5 tw-px-3 ${i === 0 ? "tw-pl-5" : ""} ${r ? "tw-text-right" : "tw-text-left"} tw-whitespace-nowrap">${h}</th>`).join("")}</tr></thead>`;
const tableWrap = (head, rows, empty) => rows.length ? `<table class="tw-w-full tw-text-sm">${head}<tbody class="tw-divide-y tw-divide-gray-200 dark:tw-divide-moon-700">${rows.join("")}</tbody></table>` : `<div class="tw-py-10 tw-text-center tw-text-sm tw-text-gray-500 dark:tw-text-moon-200">${empty}</div>`;
const xrayLink = (net, addr, label) => S.chains[net] && addr && !/^0xe{40}$/i.test(addr) ? `<a class="hover:tw-underline" href="/xray.html?chain=${net}&token=${encodeURIComponent(addr)}&from=wallet${flags.anon ? "&anon=1" : ""}">${esc(label)}</a>` : esc(label);

const NOT_ON_CHAIN = (what) => `<div class="tw-py-10 tw-text-center tw-text-sm tw-text-gray-500 dark:tw-text-moon-200">🔒 ${esc(what)} isn't available on ${esc(S.data.chain_label)} yet.</div>`;

function holdingsHtml() {
  if (S.data.holdings === null) return NOT_ON_CHAIN("Holdings");
  const tot = S.data.holdings.reduce((s, h) => s + (h.value || 0), 0) || 1;
  return tableWrap(TH([["Token"], ["Chain"], ["Balance", 1], ["Price", 1], ["24h", 1], ["Value", 1], ["Share", 1]]), S.data.holdings.map((h) => `<tr class="hover:tw-bg-gray-50 dark:hover:tw-bg-moon-700">
    <td class="tw-py-2.5 tw-px-3 tw-pl-5 tw-font-semibold"><div class="tw-flex tw-items-center tw-gap-2.5">${tokenIcon(h.image, h.symbol, h.network)}${xrayLink(h.network, h.address, h.symbol || "?")}${h.native ? ` <span class="tw-text-[10px] tw-font-medium tw-text-gray-500 dark:tw-text-moon-300">native</span>` : ""}</div></td>
    <td class="tw-px-3 tw-text-gray-600 dark:tw-text-moon-200 tw-text-xs">${netBadge(h.network)}</td>
    <td class="tw-px-3 tw-text-right tw-tabular-nums">${h.balance != null ? h.balance.toLocaleString("en-US", { maximumFractionDigits: 4 }) : "—"}</td>
    <td class="tw-px-3 tw-text-right tw-tabular-nums">${price(h.price)}</td><td class="tw-px-3 tw-text-right">${pct(h.change_24h)}</td>
    <td class="tw-px-3 tw-text-right tw-tabular-nums tw-font-semibold">${compactUsd(h.value)}</td>
    <td class="tw-px-3 tw-pr-5 tw-text-right"><div class="tw-inline-flex tw-items-center tw-gap-2"><span class="tw-tabular-nums tw-w-12">${(((h.value || 0) / tot) * 100).toFixed(1)}%</span><span class="tw-h-1.5 tw-w-24 tw-rounded-full tw-bg-gray-200 dark:tw-bg-moon-600 tw-overflow-hidden"><span class="tw-block tw-h-full tw-bg-info-500 tw-rounded-full" data-w="${Math.max(2, ((h.value || 0) / tot) * 100)}"></span></span></div></td></tr>`), "No balances above $1 on the supported networks.");
}

function perfHtml() {
  return `<div class="tw-px-5 tw-pt-3 tw-text-xs tw-text-gray-500 dark:tw-text-moon-300">Most-traded tokens by buy volume · click a token to X-ray its holders and traders</div>` + tableWrap(TH([["Token"], ["Chain"], ["Realized", 1], ["Unrealized", 1], ["Bought", 1], ["Sold", 1], ["Buys / sells", 1], ["Avg buy → sell", 1]]), S.data.performance.slice(0, 150).map((t) => `<tr class="hover:tw-bg-gray-50 dark:hover:tw-bg-moon-700">
    <td class="tw-py-2.5 tw-px-3 tw-pl-5 tw-font-semibold"><div class="tw-flex tw-items-center tw-gap-2.5">${tokenIcon(t.image, t.symbol, t.network)}<span>${xrayLink(t.network, t.address, t.symbol || "?")} <span class="tw-text-xs tw-font-medium tw-text-gray-500 dark:tw-text-moon-300">${esc((t.name || "").slice(0, 24))}</span></span></div></td>
    <td class="tw-px-3 tw-text-gray-600 dark:tw-text-moon-200 tw-text-xs">${netBadge(t.network)}</td>
    <td class="tw-px-3 tw-text-right tw-tabular-nums">${usdSigned(t.realized)}</td><td class="tw-px-3 tw-text-right tw-tabular-nums">${usdSigned(t.unrealized)}</td>
    <td class="tw-px-3 tw-text-right tw-tabular-nums">${compactUsd(t.bought_usd)}</td><td class="tw-px-3 tw-text-right tw-tabular-nums">${compactUsd(t.sold_usd)}</td>
    <td class="tw-px-3 tw-text-right tw-tabular-nums"><span class="gecko-up">${t.buys ?? 0}</span> / <span class="gecko-down">${t.sells ?? 0}</span></td>
    <td class="tw-px-3 tw-pr-5 tw-text-right tw-tabular-nums tw-text-gray-600 dark:tw-text-moon-200">${price(t.avg_buy)} → ${price(t.avg_sell)}</td></tr>`), "No trading history on the supported networks.");
}

function tradesHtml() {
  return `<div class="tw-px-5 tw-pt-3 tw-text-xs tw-text-gray-500 dark:tw-text-moon-300">Latest trades on ${esc(S.data.chain_label)}</div>` + tableWrap(TH([["Time"], ["Side"], ["Swap"], ["Value", 1], ["DEX", 1]]), S.data.trades.map((t) => `<tr class="hover:tw-bg-gray-50 dark:hover:tw-bg-moon-700">
    <td class="tw-py-2 tw-px-3 tw-pl-5 tw-text-gray-500 dark:tw-text-moon-300 tw-whitespace-nowrap">${when(t.t)}</td>
    <td class="tw-px-3 tw-font-semibold ${t.kind === "buy" ? "gecko-up" : "gecko-down"} tw-capitalize">${esc(t.kind)}</td>
    <td class="tw-px-3"><div class="tw-flex tw-items-center tw-gap-1.5">${Moon.tokenAvatar(t.from_image, t.from_symbol, "tw-w-5 tw-h-5")}<span>${esc(t.from_symbol)}</span><span class="tw-text-gray-400 dark:tw-text-moon-500 tw-mx-1">→</span>${Moon.tokenAvatar(t.to_image, t.to_symbol, "tw-w-5 tw-h-5")}<span>${esc(t.to_symbol)}</span></div></td>
    <td class="tw-px-3 tw-text-right tw-tabular-nums">${compactUsd(t.usd)}</td><td class="tw-px-3 tw-pr-5 tw-text-right tw-text-gray-500 dark:tw-text-moon-300">${esc(t.dex || "")}</td></tr>`), "No recent trades on this network.");
}

function transfersHtml() {
  if (S.data.transfers === null) return NOT_ON_CHAIN("Transfers");
  return tableWrap(TH([["Time"], ["Direction"], ["Token"], ["Amount", 1], ["Counterparty", 1]]), S.data.transfers.map((t) => `<tr class="hover:tw-bg-gray-50 dark:hover:tw-bg-moon-700">
    <td class="tw-py-2 tw-px-3 tw-pl-5 tw-text-gray-500 dark:tw-text-moon-300 tw-whitespace-nowrap">${when(t.t)}</td>
    <td class="tw-px-3 tw-font-semibold ${t.direction === "in" ? "gecko-up" : "gecko-down"}">${t.direction === "in" ? "In" : "Out"}</td>
    <td class="tw-px-3">${esc(t.symbol || "?")}</td><td class="tw-px-3 tw-text-right tw-tabular-nums">${t.amount != null ? t.amount.toLocaleString("en-US", { maximumFractionDigits: 4 }) : "—"}</td>
    <td class="tw-px-3 tw-pr-5 tw-text-right tw-font-mono tw-text-xs">${t.counterparty && /^0x[0-9a-fA-F]{40}$/.test(t.counterparty) ? `<a class="hover:tw-underline" href="/wallet.html?address=${t.counterparty}&chain=${S.data.chain}${flags.anon ? "&anon=1" : ""}">${esc(flags.anon ? addrShow(t.counterparty) : t.counterparty.slice(0, 8) + "…" + t.counterparty.slice(-4))}</a>` : "—"}</td></tr>`), "No recent transfers on this network.");
}

function chainsHtml() {
  const bal = {};
  for (const h of S.data.holdings || []) bal[h.network] = (bal[h.network] || 0) + (h.value || 0);
  return tableWrap(TH([["Network"], ["Tokens traded", 1], ["Realized PnL", 1], ["Unrealized PnL", 1], ["Balance", 1]]), (S.data.networks || []).filter((n) => n.tokens > 0).map((n) => `<tr>
    <td class="tw-py-2.5 tw-px-3 tw-pl-5 tw-font-semibold">${Moon.chainBadge(n.network, "tw-w-5 tw-h-5")}</td><td class="tw-px-3 tw-text-right tw-tabular-nums">${(n.tokens || 0).toLocaleString()}</td>
    <td class="tw-px-3 tw-text-right tw-tabular-nums">${usdSigned(parseFloat(n.realized_pnl_usd))}</td><td class="tw-px-3 tw-text-right tw-tabular-nums">${usdSigned(parseFloat(n.unrealized_pnl_usd))}</td>
    <td class="tw-px-3 tw-pr-5 tw-text-right tw-tabular-nums">${compactUsd(bal[n.network] || 0)}</td></tr>`), "No activity on the supported networks.");
}

async function renderDevBar() {
  let items = [];
  try { items = await (await fetch("/api/fixtures?demo=wallet")).json(); } catch {}
  $("devBar").innerHTML = `<span>Snapshots</span><select id="snapSel" class="tw-rounded-md tw-border-0 tw-ring-1 tw-ring-gray-200 dark:tw-ring-moon-600 tw-bg-white dark:tw-bg-moon-900 tw-text-xs tw-py-1 tw-pl-2 tw-pr-7"><option value="">— live —</option>${items.map((f) => `<option>${esc(f.name)}</option>`).join("")}</select><button id="replayBtn" class="${BTN.base} ${BTN.soft} ${BTN.sm}">Replay</button>`;
  $("replayBtn").onclick = () => { const n = $("snapSel").value; const p = new URLSearchParams(location.search); n ? p.set("replay", n) : p.delete("replay"); location.search = p.toString(); };
  Moon.applyDevVisibility();
}

init();
