const { BTN, TONE, esc, compactUsd, tokenAvatar, anonName, usd6, flags } = Moon;
const $ = (id) => document.getElementById(id);

const PERSONA = {
  proven_trader: ["Proven trader", "success"], accumulator: ["Accumulator", "primary"], one_hit_winner: ["One-hit winner", "warning"],
  whale: ["Whale", "info"], sniper: ["Sniper", "warning"], market_maker_bot: ["Market maker / bot", "neutral"], flipper: ["Flipper", "neutral"], new_wallet: ["New wallet", "neutral"],
};
const STYLE = { scalper: "Scalper", swing_trader: "Swing", position_holder: "Holder", arbitrage_bot: "Arb / bot" };
const SOURCES = [["trending_1h", "Trending now"], ["trending_24h", "Trending 24h"], ["new", "New launches"]];
const S = {
  chains: {}, chain: "base", source: "trending_1h", n: 10, batch: null, tokens: [], cands: [], results: {}, selected: new Set(),
  running: false, persona: null, copyOnly: false, hideBots: true, sort: "rank",
};

const addrShow = (c) => (flags.anon ? `Wallet #${(Moon.hash(c.address) % 900) + 100}` : c.label || c.short);
const usdSigned = (v) => (v == null ? "—" : `<span class="${v > 0 ? "gecko-up" : v < 0 ? "gecko-down" : ""}">${v < 0 ? "−" : ""}${compactUsd(Math.abs(v))}</span>`);
const seg = (el, opts, cur, fn) => {
  el.innerHTML = opts.map(([v, l]) => `<button data-v="${v}" class="tw-px-3 tw-py-1.5 tw-rounded-md tw-text-xs tw-font-semibold ${String(v) === String(cur) ? "tw-bg-white tw-text-gray-900 tw-shadow-sm dark:tw-bg-moon-600 dark:tw-text-moon-50" : "tw-text-gray-500 hover:tw-text-gray-900 dark:tw-text-moon-200 dark:hover:tw-text-moon-50"}">${l}</button>`).join("");
  el.querySelectorAll("button").forEach((b) => (b.onclick = () => !S.running && fn(b.dataset.v)));
};

async function init() {
  try { S.chains = (await (await fetch("/api/config")).json()).wallet_chains || {}; } catch {}
  await Moon.loadChains();
  Moon.chainPicker($("chainSel"), Object.keys(S.chains), S.chain, (v) => { S.chain = v; const b = $("introScan"); if (b) b.innerHTML = `📡 Scan ${esc(S.chains[S.chain] || "")} for candidates`; }, () => S.running);
  renderControls();
  renderDevBar();
  if (flags.replay) return startReplay(flags.replay);
  $("intro").innerHTML = `<div class="tw-rounded-xl tw-border tw-border-gray-200 dark:tw-border-moon-700 tw-bg-white dark:tw-bg-moon-800 tw-p-8">
    <div class="tw-text-2xl tw-leading-8 tw-font-bold">Don't know which wallets to follow?</div>
    <p class="tw-text-sm tw-text-gray-500 dark:tw-text-moon-200 tw-mt-1 tw-max-w-3xl">The radar scans the top traders of today's hottest tokens on a network and builds a candidate list. Wallets that show up across several tokens rank first, and ones that look like high-frequency bots sink. Then one click has Jev profile each candidate from its multi-chain PnL, portfolio and trading behaviour, so you can filter for the ones worth following.</p>
    <div class="tw-mt-5"><button id="introScan" class="${BTN.base} ${BTN.primary} ${BTN.lg}">📡 Scan ${esc(S.chains[S.chain] || "")} for candidates</button></div></div>`;
  $("introScan").onclick = scan;
}

function renderControls() {
  seg($("sourceSeg"), SOURCES, S.source, (v) => { S.source = v; renderControls(); });
  seg($("tokensSeg"), [[5, "5 tokens"], [10, "10 tokens"], [20, "20 tokens"]], S.n, (v) => { S.n = +v; renderControls(); });
  $("scanBtn").className = `${BTN.base} ${BTN.secondary} ${BTN.md} ${S.running ? "tw-opacity-50 tw-pointer-events-none" : ""}`;
  $("scanBtn").innerHTML = "📡 Scan";
  $("scanBtn").onclick = scan;
  const b = $("runBtn");
  if (!S.cands.length) { b.className = "tw-hidden"; return; }
  const done = Object.keys(S.results).length;
  b.className = `${BTN.base} ${BTN.primary} ${BTN.lg} ${S.running || !S.selected.size ? "tw-opacity-50 tw-pointer-events-none" : ""}`;
  b.innerHTML = S.running ? `${Moon.jevLogo()} Jev is profiling…` : done ? `↻ Profile ${S.selected.size} again with ${Moon.JEV}` : `Profile ${S.selected.size} wallets with ${Moon.JEV}`;
  b.onclick = run;
}

async function scan() {
  if (S.running) return;
  S.running = true; S.results = {}; S.persona = null; S.copyOnly = false;
  renderControls();
  $("intro").innerHTML = `<div class="tw-relative tw-overflow-hidden tw-rounded-xl tw-border tw-border-gray-200 dark:tw-border-moon-700 tw-bg-white dark:tw-bg-moon-800 tw-p-8 tw-text-center"><div class="jev-sweep"></div><div class="tw-font-semibold">Scanning the top traders of ${S.n} ${SOURCES.find((s) => s[0] === S.source)[1].toLowerCase()} tokens on ${esc(S.chains[S.chain])}…</div></div>`;
  try {
    const r = await fetch(`/api/radar/candidates?chain=${S.chain}&source=${S.source}&tokens=${S.n}`);
    if (!r.ok) throw new Error();
    const d = await r.json();
    if (d.locked) { $("intro").innerHTML = Moon.lockedHtml(d); S.running = false; renderControls(); return; }
    S.batch = d.batch; S.tokens = d.tokens; S.cands = d.candidates;
  } catch {
    $("intro").innerHTML = `<div class="tw-rounded-xl tw-border tw-border-gray-200 dark:tw-border-moon-700 tw-bg-white dark:tw-bg-moon-800 tw-p-8 tw-text-sm tw-text-gray-500 dark:tw-text-moon-200">Couldn't build a candidate list right now. Try another source or network.</div>`;
    S.running = false; renderControls(); return;
  }
  S.running = false;
  S.selected = new Set(S.cands.filter((c) => !c.likely_bot).slice(0, 40).map((c) => c.address));
  $("intro").innerHTML = "";
  $("counter").innerHTML = `${S.cands.length} candidates from ${S.tokens.length} tokens · ${S.cands.filter((c) => c.likely_bot).length} look like bots`;
  renderAll();
}

function renderAll() { renderControls(); renderStrip(); renderFilters(); renderTable(); }

function renderStrip() {
  const el = $("sourceStrip");
  el.classList.remove("tw-hidden");
  el.innerHTML = `<div class="tw-flex tw-flex-wrap tw-items-center tw-gap-2"><span class="tw-text-xs tw-font-semibold tw-text-gray-500 dark:tw-text-moon-300">Scanned</span>${S.tokens.map((t) => `<a href="/xray.html?chain=${S.chain}&token=${encodeURIComponent(t.address)}&from=radar${flags.anon ? "&anon=1" : ""}" class="tw-inline-flex tw-items-center tw-gap-1.5 tw-rounded-full tw-bg-gray-100 dark:tw-bg-moon-800 tw-pl-1 tw-pr-2.5 tw-py-1 tw-text-xs tw-font-semibold hover:tw-ring-1 hover:tw-ring-primary-500">${tokenAvatar(t.image_url, t.symbol, "tw-w-5 tw-h-5")}${esc(flags.anon ? anonName(t.address) : t.symbol)}</a>`).join("")}</div>`;
}

function visible() {
  let list = S.cands.filter((c) => !(S.hideBots && c.likely_bot));
  if (S.persona) list = list.filter((c) => S.results[c.address]?.persona === S.persona);
  if (S.copyOnly) list = list.filter((c) => S.results[c.address]?.copy_worthy);
  const R = (c) => S.results[c.address];
  const key = {
    rank: () => 0,
    skill: (c) => -(R(c)?.skill ?? -1),
    pnl: (c) => -(R(c)?.lifetime?.lifetime_realized_pnl_usd ?? -1e15),
    winrate: (c) => -(R(c)?.lifetime?.win_rate_tokens ?? -1),
    portfolio: (c) => -(R(c)?.portfolio?.portfolio_value_usd ?? -1),
    seen: (c) => -c.seen_in.length,
  }[S.sort];
  return list.map((c, i) => [c, i]).sort((a, b) => key(a[0]) - key(b[0]) || a[1] - b[1]).map(([c]) => c);
}

function renderFilters() {
  const el = $("filterBar");
  el.classList.remove("tw-hidden");
  const res = Object.values(S.results).filter((r) => !r.error);
  const counts = {};
  res.forEach((r) => (counts[r.persona] = (counts[r.persona] || 0) + 1));
  el.innerHTML = `<label class="tw-flex tw-items-center tw-text-xs tw-font-semibold tw-text-gray-600 dark:tw-text-moon-200 tw-mr-2"><input id="hideBots" type="checkbox" ${S.hideBots ? "checked" : ""} class="tw-h-4 tw-w-4 tw-mr-2 tw-rounded tw-text-primary-500 tw-border-gray-300 dark:tw-border-moon-600 dark:tw-bg-transparent">Hide likely bots</label>
    ${res.length ? `<button id="copyOnly" class="tw-inline-flex tw-items-center tw-gap-1 tw-rounded-lg tw-px-3 tw-py-1.5 tw-text-xs tw-font-bold ${S.copyOnly ? "tw-bg-success-500 tw-text-white" : "tw-bg-success-500/15 tw-text-success-400"}">✓ Copy-worthy <span class="tw-opacity-70">${res.filter((r) => r.copy_worthy).length}</span></button>` : ""}
    ${Object.keys(PERSONA).filter((k) => counts[k]).map((k) => `<button data-p="${k}" class="tw-inline-flex tw-items-center tw-gap-1.5 tw-rounded-md tw-border tw-px-2 tw-py-1 tw-text-xs tw-font-semibold ${TONE[PERSONA[k][1]]} ${S.persona === k ? "tw-ring-2 tw-ring-primary-500 dark:tw-ring-primary-400" : "tw-opacity-85 hover:tw-opacity-100"}">${Moon.ic("persona", k)} ${PERSONA[k][0]} <span class="tw-opacity-70">${counts[k]}</span></button>`).join("")}
    <label class="tw-ml-auto tw-flex tw-items-center tw-gap-2 tw-text-xs tw-font-semibold tw-text-gray-500 dark:tw-text-moon-200">Sort <select id="sortSel" class="tw-rounded-lg tw-border-0 tw-ring-2 tw-ring-gray-200 dark:tw-ring-moon-600 tw-bg-white dark:tw-bg-moon-900 tw-text-gray-900 dark:tw-text-moon-50 tw-text-xs tw-py-1.5 tw-pl-2 tw-pr-8">${[["rank", "Radar rank"], ["skill", "Jev skill"], ["pnl", "Lifetime PnL"], ["winrate", "Win rate"], ["portfolio", "Portfolio"], ["seen", "Seen in most tokens"]].map(([v, l]) => `<option value="${v}" ${S.sort === v ? "selected" : ""}>${l}</option>`).join("")}</select></label>`;
  $("hideBots").onchange = (e) => { S.hideBots = e.target.checked; renderTable(); };
  const co = $("copyOnly"); if (co) co.onclick = () => { S.copyOnly = !S.copyOnly; renderFilters(); renderTable(); };
  el.querySelectorAll("[data-p]").forEach((b) => (b.onclick = () => { S.persona = S.persona === b.dataset.p ? null : b.dataset.p; renderFilters(); renderTable(); }));
  $("sortSel").onchange = (e) => { S.sort = e.target.value; renderTable(); };
}

const RHIDE = { "Win rate": "tw-hidden xl:tw-table-cell", "Chains": "tw-hidden xl:tw-table-cell", "Last trade": "tw-hidden xl:tw-table-cell", "PnL in those tokens": "tw-hidden 2lg:tw-table-cell" };
const COLS = ["", "Wallet", "Seen in", "PnL in those tokens", "Jev label", "Skill", "Style", "Tags", "Lifetime PnL", "Win rate", "Portfolio", "Chains", "Last trade"];
function renderTable() {
  $("tableCard").classList.remove("tw-hidden");
  $("thead").innerHTML = COLS.map((h, i) => `<th class="tw-py-2.5 tw-px-2 tw-whitespace-nowrap ${RHIDE[h] || ""} ${i < 3 || i === 4 || i === 6 || i === 7 ? "tw-text-left" : "tw-text-right"} ${i === 0 ? "tw-pl-4 tw-w-8" : ""} ${["Jev label", "Skill", "Style", "Tags"].includes(h) ? "tw-text-primary-700 dark:tw-text-primary-400" : ""}">${h}</th>`).join("");
  const tbody = $("tbody");
  tbody.innerHTML = "";
  for (const c of visible()) {
    const r = S.results[c.address];
    const L = r?.lifetime || {}, P = r?.portfolio || {}, R = r?.recent_activity || {};
    const per = r && !r.error ? PERSONA[r.persona] || [r.persona_label, "neutral"] : null;
    const tr = document.createElement("tr");
    tr.className = "tw-cursor-pointer hover:tw-bg-gray-50 dark:hover:tw-bg-moon-700";
    tr.innerHTML = `<td class="tw-py-2 tw-pl-4 tw-pr-2"><input type="checkbox" data-sel="${c.address}" ${S.selected.has(c.address) ? "checked" : ""} class="tw-h-4 tw-w-4 tw-rounded tw-text-primary-500 tw-border-gray-300 dark:tw-border-moon-600 dark:tw-bg-transparent"></td>
      <td class="tw-py-2 tw-px-2"><div class="tw-font-mono tw-text-xs tw-font-semibold">${esc(addrShow(c))}</div>${c.likely_bot ? `<div class="tw-text-[10px] tw-text-gray-500 dark:tw-text-moon-300">very high trade count</div>` : ""}</td>
      <td class="tw-px-2"><div class="tw-flex tw-items-center tw-gap-1"><span class="tw-font-semibold tw-tabular-nums tw-mr-1">${c.seen_in.length}</span>${c.seen_in.slice(0, 5).map((s) => tokenAvatar(s.image_url, s.symbol, "tw-w-5 tw-h-5")).join("")}</div></td>
      <td class="tw-px-2 tw-text-right tw-tabular-nums tw-hidden 2lg:tw-table-cell">${usdSigned(c.realized_seen_usd)}</td>
      <td class="tw-px-2">${per ? `<span class="jev-pop tw-inline-flex tw-whitespace-nowrap tw-rounded-md tw-border tw-px-2 tw-py-0.5 tw-text-xs tw-font-semibold ${TONE[per[1]]} ${r.persona_confidence < 0.5 ? "chip-lowconf" : ""}">${Moon.ic("persona", r.persona)} ${esc(per[0])}</span>${r.copy_worthy ? ` <span class="tw-text-xs tw-font-bold tw-text-success-400">✓</span>` : ""}` : S.running && S.selected.has(c.address) ? `<span class="tw-inline-block tw-h-5 tw-w-24 tw-rounded tw-bg-gray-100 dark:tw-bg-moon-700 tw-animate-pulse"></span>` : ""}</td>
      <td class="tw-px-2 tw-text-right tw-tabular-nums">${per ? Math.round(r.skill) : ""}</td>
      <td class="tw-px-2 tw-text-xs tw-whitespace-nowrap">${per ? `${Moon.ic("style", r.style)} ${esc(STYLE[r.style] || r.style)}` : ""}</td>
      <td class="tw-px-2"><div class="tw-flex tw-flex-wrap tw-gap-1 tw-max-w-[260px]">${per ? (r.tags || []).slice(0, 3).map((t) => `<span class="tw-rounded tw-border tw-px-1.5 tw-text-[10px] tw-font-semibold tw-whitespace-nowrap ${TONE.info}">${Moon.ic("tag", t)} ${esc(t)}</span>`).join("") : ""}</div></td>
      <td class="tw-px-2 tw-text-right tw-tabular-nums">${per && L.available ? usdSigned(L.lifetime_realized_pnl_usd) : ""}</td>
      <td class="tw-px-2 tw-text-right tw-tabular-nums tw-hidden xl:tw-table-cell">${per && L.win_rate_tokens != null ? Math.round(L.win_rate_tokens * 100) + "%" : ""}</td>
      <td class="tw-px-2 tw-text-right tw-tabular-nums">${per && P.available ? compactUsd(P.portfolio_value_usd) : ""}</td>
      <td class="tw-px-2 tw-text-right tw-hidden xl:tw-table-cell"><div class="tw-inline-flex -tw-space-x-1">${per ? (L.active_networks || []).map((n) => `<span title="${esc(Moon.chainLabel(n))}" class="tw-rounded-full tw-ring-2 tw-ring-white dark:tw-ring-moon-800">${Moon.chainLogo(n, "tw-w-5 tw-h-5")}</span>`).join("") : ""}</div></td>
      <td class="tw-px-2 tw-pr-4 tw-text-right tw-text-xs tw-text-gray-500 dark:tw-text-moon-300 tw-hidden xl:tw-table-cell">${per ? (R.days_since_last_trade == null ? "—" : R.days_since_last_trade < 1 ? "today" : Math.round(R.days_since_last_trade) + "d") : ""}</td>`;
    tr.onclick = (e) => {
      if (e.target.matches("input[type=checkbox]")) return;
      location.href = `/wallet.html?address=${c.address}&chain=${S.chain}&from=radar${flags.anon ? "&anon=1" : ""}`;
    };
    tbody.appendChild(tr);
  }
  tbody.querySelectorAll("[data-sel]").forEach((cb) => (cb.onchange = () => { cb.checked ? S.selected.add(cb.dataset.sel) : S.selected.delete(cb.dataset.sel); renderControls(); }));
}

function consume(url) {
  S.running = true; S.results = {};
  renderAll();
  const card = $("tableCard");
  card.insertAdjacentHTML("afterbegin", `<div class="jev-sweep"></div>`);
  const es = new EventSource(url);
  let t = null;
  const repaint = () => { if (t) return; t = setTimeout(() => { t = null; renderFilters(); renderTable(); }, 300); };
  es.addEventListener("wallet", (e) => { const d = JSON.parse(e.data); S.results[d.address] = d; repaint(); });
  es.addEventListener("progress", (e) => { const p = JSON.parse(e.data); $("counter").innerHTML = `profiled <b class="tw-text-gray-900 dark:tw-text-moon-50">${p.done}/${p.total}</b> · ${(p.elapsed_ms / 1000).toFixed(1)} s · ${p.calls} Jev calls · ${usd6(p.cost_usd)}`; });
  const finish = () => { es.close(); S.running = false; card.querySelector(".jev-sweep")?.remove(); renderAll(); };
  es.addEventListener("done", finish);
  es.addEventListener("fail", (e) => { $("counter").textContent = JSON.parse(e.data).error; finish(); });
  es.onerror = () => { if (S.running) finish(); };
}

function run() {
  if (S.running || !S.selected.size) return;
  if (flags.replay) consume(`/api/radar/replay?name=${encodeURIComponent(flags.replay)}&speed=${flags.speed}`);
  else consume(`/api/radar/run?batch=${S.batch}&ids=${[...S.selected].join(",")}`);
}

async function startReplay(name) {
  const r = await fetch(`/api/radar/snapshot?name=${encodeURIComponent(name)}`);
  if (!r.ok) return;
  const d = await r.json();
  S.chain = d.chain; S.cands = d.candidates; S.tokens = [];
  const seen = {};
  d.candidates.forEach((c) => c.seen_in.forEach((s) => (seen[s.address] = { address: s.address, symbol: s.symbol, image_url: s.image_url })));
  S.tokens = Object.values(seen).slice(0, 20);
  S.selected = new Set(d.candidates.map((c) => c.address));
  ["chainSel", "sourceSeg", "tokensSeg", "scanBtn"].forEach((id) => $(id).classList.add("tw-hidden"));
  renderAll();
}

async function renderDevBar() {
  let items = [];
  try { items = await (await fetch("/api/fixtures?demo=radar")).json(); } catch {}
  $("devBar").innerHTML = `<span>Snapshots</span><select id="snapSel" class="tw-rounded-md tw-border-0 tw-ring-1 tw-ring-gray-200 dark:tw-ring-moon-600 tw-bg-white dark:tw-bg-moon-900 tw-text-xs tw-py-1 tw-pl-2 tw-pr-7"><option value="">— live —</option>${items.map((f) => `<option>${esc(f.name)}</option>`).join("")}</select><button id="replayBtn" class="${BTN.base} ${BTN.soft} ${BTN.sm}">Replay</button>`;
  $("replayBtn").onclick = () => { const n = $("snapSel").value; const p = new URLSearchParams(location.search); n ? p.set("replay", n) : p.delete("replay"); location.search = p.toString(); };
  Moon.applyDevVisibility();
}

init();
