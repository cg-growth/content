// Moon Design System 1.2 Tailwind config (copied from design-system-v1.html) + shared helpers.
tailwind.config = {
  prefix: "tw-",
  darkMode: "class",
  theme: {
    screens: { sm: "640px", md: "768px", lg: "1024px", "2lg": "1200px", xl: "1280px", "2xl": "1536px" },
    extend: {
      colors: {
        current: "currentColor",
        black: { DEFAULT: "#000000" },
        white: { DEFAULT: "#FFF", 12: "#FFFFFF1F", 38: "#FFFFFF61", 60: "#FFFFFF99", 87: "#FFFFFFDE" },
        primary: { 50: "#F3FCE5", 100: "#E8FCC9", 200: "#CDF995", 300: "#A6EF5F", 400: "#80E038", 500: "#4BCC00", 600: "#35AF00", 700: "#239200", 800: "#157600", 900: "#0B6100" },
        gray: { 50: "#F8FAFC", 100: "#F1F5F9", 200: "#EFF2F5", 300: "#CBD5E1", 400: "#94A3B8", 500: "#64748b", 600: "#475569", 700: "#334155", 800: "#1E293B", 900: "#0F172A" },
        success: { 50: "#E4FAE3", 100: "#C9FAC8", 200: "#93F69A", 300: "#5BE473", 400: "#32CA5B", 500: "#00A83E", 600: "#009043", 700: "#007844", 800: "#006140", 900: "#00503D" },
        warning: { 50: "#FFFDE8", 100: "#FFFBD6", 200: "#FFF5AD", 300: "#FFEE84", 400: "#FFE866", 500: "#FFDD33", 600: "#DBB925", 700: "#B79719", 800: "#937710", 900: "#7A5F09" },
        danger: { DEFAULT: "#FF3A33", 50: "#FFF0E8", 100: "#FFE5D6", 200: "#FFC4AD", 300: "#FF9D84", 400: "#FF7866", 500: "#FF3A33", 600: "#D8252E", 700: "#B7192F", 800: "#93102D", 900: "#7A092C" },
        info: { 50: "#E8FEFF", 100: "#D6FDFF", 200: "#ADF6FF", 300: "#84E9FF", 400: "#66D9FF", 500: "#33C0FF", 600: "#2597DB", 700: "#1971B7", 800: "#105193", 900: "#09397A" },
        moon: { 50: "#DFE5EC", 100: "#BECBDA", 200: "#9EB0C7", 300: "#7D96B5", 400: "#5D7CA2", 500: "#4A6382", 600: "#384A61", 700: "#212D3B", 800: "#1B232D", 900: "#0D1217" },
      },
      boxShadow: {
        primaryShadow: "0 4px 0 0 #35AF00",
        primaryHover: "0 4px 0 0 #239200",
        primaryActive: "0 0 0 0 #239200",
        secondaryShadow: "0 4px 0 0 #CBD5E1",
        secondaryShadowDark: "0 4px 0 0 #4A6382",
      },
    },
    fontFamily: {
      "gecko-body": ["InterVariable", "Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "Helvetica", "Arial", "sans-serif"],
      mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"],
    },
  },
};

const Moon = (() => {
  const params = new URLSearchParams(location.search);
  const flags = {
    record: params.get("record") === "1",
    anon: params.get("anon") === "1",
    replay: params.get("replay") || null,
    speed: parseFloat(params.get("speed") || "1"),
  };
  if (flags.record) document.documentElement.classList.add("record-mode");

  const BTN = {
    base: "tw-inline-flex tw-items-center tw-justify-center tw-gap-2 tw-font-semibold tw-rounded-lg tw-select-none tw-transition-all tw-duration-150 focus:tw-outline-none",
    primary: "tw-bg-primary-500 dark:tw-bg-primary-400 tw-text-white dark:tw-text-primary-900 tw-shadow-primaryShadow hover:tw-bg-primary-600 hover:tw-shadow-primaryHover active:tw-translate-y-1 active:tw-shadow-primaryActive tw-mb-1",
    secondary: "tw-bg-white dark:tw-bg-moon-800 tw-text-gray-900 dark:tw-text-moon-50 tw-border-t-2 tw-border-x-2 tw-border-gray-300 dark:tw-border-moon-500 tw-shadow-secondaryShadow dark:tw-shadow-secondaryShadowDark hover:tw-bg-gray-100 dark:hover:tw-bg-moon-700 active:tw-translate-y-1 tw-mb-1",
    soft: "tw-bg-gray-200 dark:tw-bg-moon-700 tw-text-gray-900 dark:tw-text-moon-50 hover:tw-bg-gray-300 dark:hover:tw-bg-moon-600",
    md: "tw-px-4 tw-py-2 tw-text-sm",
    sm: "tw-px-2.5 tw-py-1.5 tw-text-xs",
    lg: "tw-px-4 tw-py-2.5 tw-text-sm",
  };

  const TONE = {
    success: "tw-bg-success-50 tw-text-success-700 tw-border-success-200 dark:tw-bg-success-500/15 dark:tw-text-success-400 dark:tw-border-success-500/40",
    danger: "tw-bg-danger-50 tw-text-danger-600 tw-border-danger-200 dark:tw-bg-danger-500/15 dark:tw-text-danger-400 dark:tw-border-danger-500/40",
    warning: "tw-bg-warning-50 tw-text-warning-800 tw-border-warning-300 dark:tw-bg-warning-500/15 dark:tw-text-warning-400 dark:tw-border-warning-500/40",
    info: "tw-bg-info-50 tw-text-info-700 tw-border-info-200 dark:tw-bg-info-500/15 dark:tw-text-info-400 dark:tw-border-info-500/40",
    neutral: "tw-bg-gray-100 tw-text-gray-700 tw-border-gray-300 dark:tw-bg-moon-700 dark:tw-text-moon-100 dark:tw-border-moon-600",
    primary: "tw-bg-primary-50 tw-text-primary-800 tw-border-primary-200 dark:tw-bg-primary-500/15 dark:tw-text-primary-300 dark:tw-border-primary-500/40",
  };

  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

  function compactUsd(v) {
    if (v == null || isNaN(v)) return "—";
    const a = Math.abs(v);
    if (a >= 1e12) return "$" + (v / 1e12).toFixed(2) + "T";
    if (a >= 1e9) return "$" + (v / 1e9).toFixed(1) + "B";
    if (a >= 1e6) return "$" + (v / 1e6).toFixed(2) + "M";
    if (a >= 1e3) return "$" + Math.round(v).toLocaleString("en-US");
    return "$" + v.toFixed(2);
  }

  const SUB = "₀₁₂₃₄₅₆₇₈₉";
  function price(v) {
    if (v == null || isNaN(v)) return "—";
    if (v >= 1000) return "$" + v.toLocaleString("en-US", { maximumFractionDigits: 2 });
    if (v >= 1) return "$" + v.toFixed(v >= 100 ? 2 : 4).replace(/0+$/, "").replace(/\.$/, ".00");
    if (v >= 0.01) return "$" + v.toFixed(4);
    if (v >= 0.000001) return "$" + v.toFixed(6);
    const s = v.toFixed(20).split(".")[1];
    const zeros = s.match(/^0*/)[0].length;
    const sig = s.slice(zeros, zeros + 4).replace(/0+$/, "");
    return "$0.0" + String(zeros).split("").map((d) => SUB[+d]).join("") + sig;
  }

  function pct(v, withArrow = true) {
    if (v == null || isNaN(v)) return `<span class="tw-text-gray-400 dark:tw-text-moon-400">—</span>`;
    const cls = v > 0 ? "gecko-up" : v < 0 ? "gecko-down" : "tw-text-gray-500 dark:tw-text-moon-200";
    const arrow = !withArrow ? "" : v > 0 ? "▴ " : v < 0 ? "▾ " : "— ";
    return `<span class="${cls} tw-tabular-nums">${arrow}${Math.abs(v).toFixed(2)}%</span>`;
  }

  function hash(s) {
    let h = 2166136261;
    for (const c of String(s)) h = Math.imul(h ^ c.charCodeAt(0), 16777619);
    return h >>> 0;
  }
  const anonName = (id) => "TOKEN-" + String.fromCharCode(65 + (hash(id) % 26)) + (hash(id + "x") % 90 + 10);

  function tokenAvatar(url, label, size = "tw-w-7 tw-h-7") {
    const blur = flags.anon ? " tw-blur-sm" : "";
    if (url && !flags.anon) return `<img src="${esc(url)}" alt="" class="${size} tw-rounded-full tw-shrink-0 tw-bg-gray-100 dark:tw-bg-moon-700${blur}" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'${size} tw-rounded-full tw-shrink-0 tw-bg-gray-200 dark:tw-bg-moon-600'}))">`;
    return `<span class="${size} tw-rounded-full tw-shrink-0 tw-inline-flex tw-items-center tw-justify-center tw-text-[10px] tw-font-bold tw-bg-gray-200 tw-text-gray-600 dark:tw-bg-moon-600 dark:tw-text-moon-100${blur}">${esc((label || "?").slice(0, 2).toUpperCase())}</span>`;
  }

  function ago(hours) {
    if (hours == null) return "—";
    if (hours < 1) return Math.max(1, Math.round(hours * 60)) + "m";
    if (hours < 48) return Math.round(hours) + "h";
    if (hours < 24 * 60) return Math.round(hours / 24) + "d";
    return Math.round(hours / 24 / 30) + "mo";
  }

  const usd6 = (v) => "$" + (v || 0).toFixed(v < 0.01 ? 4 : 3);

  function applyDevVisibility() {
    if (flags.record) document.querySelectorAll("[data-dev]").forEach((el) => el.classList.add("tw-hidden"));
  }

  // ---------- visual vocabulary for Jev outputs ----------
  const ICON = {
    persona: {
      proven_trader: "🎯", accumulator: "🧺", one_hit_winner: "🎰", whale: "🐋", sniper: "⚡", insider_like: "🕵️", treasury_allocation: "🏦",
      market_maker_bot: "🤖", flipper: "🔁", new_wallet: "🌱", protocol: "🏛️",
    },
    tag: {
      "Memecoin-focused": "🐸", "Blue-chip focused": "💎", "Early buyer": "🚀", "Disciplined exits": "🛡️", "High-frequency": "⏱️",
      "Multi-chain": "🌐", "Whale-sized": "🐋", "Stablecoin-heavy": "💵", "Dormant": "💤",
    },
    style: { scalper: "⏱️", swing_trader: "🌊", position_holder: "⚓", arbitrage_bot: "🤖" },
    verdict: {
      smart_money_accumulating: "📈", smart_money_distributing: "📉", insider_heavy: "🕵️", treasury_concentrated: "🏦",
      bot_heavy_trading: "🤖", bot_driven: "🤖", organic_mixed: "🌿",
    },
    stance: { accumulating: "🟢", holding: "⚪", distributing: "🔴", exited: "🚪" },
    momentum: { pumping: "🚀", climbing: "📈", flat: "➖", cooling: "🧊", dumping: "📉" },
    phase: { accumulation: "🧺", breakout: "🚀", distribution: "📤", capitulation: "🩸", ranging: "↔️" },
    chip: { organic: "🌱", artificial: "⚠️", wash: "🧼", whale: "🐋", rug: "🚩", thin: "💧", fresh: "🆕", sell: "📉" },
    fng: { "Extreme Fear": "😱", Fear: "😟", Neutral: "😐", Greed: "🙂", "Extreme Greed": "🤑" },
  };
  const ic = (group, key) => (ICON[group] && ICON[group][key]) || "";

  // ---------- chains ----------
  let CHAIN_META = {};
  let chainsPromise = null;
  function loadChains() {
    if (!chainsPromise) chainsPromise = fetch("/api/chains").then((r) => r.json()).then((m) => (CHAIN_META = m || {})).catch(() => ({}));
    return chainsPromise;
  }
  function chainLogo(id, size = "tw-w-4 tw-h-4") {
    if (id === "auto") return `<span class="${size} tw-inline-flex tw-items-center tw-justify-center tw-shrink-0 tw-text-[12px]">🌐</span>`;
    const m = CHAIN_META[id];
    return m?.image
      ? `<img src="${esc(m.image)}" alt="" class="${size} tw-rounded-full tw-shrink-0 tw-bg-white">`
      : `<span class="${size} tw-rounded-full tw-shrink-0 tw-inline-block tw-bg-gray-300 dark:tw-bg-moon-600"></span>`;
  }
  const chainLabel = (id) => (id === "auto" ? "Auto-detect chain" : CHAIN_META[id]?.label || id);
  const chainBadge = (id, size) => `<span class="tw-inline-flex tw-items-center tw-gap-1.5 tw-whitespace-nowrap">${chainLogo(id, size)}<span>${esc(chainLabel(id))}</span></span>`;

  function chainPicker(el, ids, current, onChange, locked = () => false) {
    const render = () => {
      el.innerHTML = `<div class="tw-relative">
        <button type="button" data-open class="tw-inline-flex tw-items-center tw-gap-2 tw-rounded-lg tw-ring-2 tw-ring-gray-200 dark:tw-ring-moon-600 tw-bg-white dark:tw-bg-moon-900 tw-px-3 tw-h-10 tw-text-sm tw-font-semibold tw-text-gray-900 dark:tw-text-moon-50 hover:tw-ring-primary-500">
          ${chainLogo(current, "tw-w-5 tw-h-5")}<span>${esc(chainLabel(current))}</span><span class="tw-text-gray-400 dark:tw-text-moon-400 tw-text-xs">▾</span></button>
        <div data-menu class="tw-hidden tw-absolute tw-left-0 tw-top-12 tw-z-50 tw-min-w-[220px] tw-rounded-xl tw-border tw-border-gray-200 dark:tw-border-moon-600 tw-bg-white dark:tw-bg-moon-800 tw-shadow-2xl tw-py-1">
          ${ids.map((id) => `<button type="button" data-id="${esc(id)}" class="tw-w-full tw-flex tw-items-center tw-gap-2.5 tw-px-3 tw-py-2 tw-text-sm tw-font-semibold hover:tw-bg-gray-50 dark:hover:tw-bg-moon-700 ${id === current ? "tw-text-primary-600 dark:tw-text-primary-400" : "tw-text-gray-900 dark:tw-text-moon-50"}">${chainLogo(id, "tw-w-5 tw-h-5")}${esc(chainLabel(id))}${id === current ? `<span class="tw-ml-auto">✓</span>` : ""}</button>`).join("")}
        </div></div>`;
      const menu = el.querySelector("[data-menu]");
      el.querySelector("[data-open]").onclick = (e) => { e.stopPropagation(); if (!locked()) menu.classList.toggle("tw-hidden"); };
      el.querySelectorAll("[data-id]").forEach((b) => (b.onclick = () => { menu.classList.add("tw-hidden"); if (b.dataset.id !== current) { current = b.dataset.id; render(); onChange(current); } }));
    };
    document.addEventListener("click", () => el.querySelector("[data-menu]")?.classList.add("tw-hidden"));
    render();
    return { set: (id) => { current = id; render(); } };
  }

  // ---------- disclaimer (every page) ----------
  const DISCLAIMER =
    "Demo only, not financial advice. Labels, scores and verdicts are AI outputs from Jev and may be inaccurate or incomplete; they haven't been audited for accuracy. " +
    "This showcases what's possible when structured CoinGecko API data meets AI models like Jev. Do your own research before relying on any of it.";
  function injectDisclaimer() {
    const footer = document.querySelector("footer");
    if (!footer || footer.querySelector("[data-disclaimer]")) return;
    const dark = document.documentElement.classList.contains("tw-dark");
    const div = document.createElement("div");
    div.setAttribute("data-disclaimer", "");
    div.className = `tw-border-b ${dark ? "tw-border-moon-700 tw-bg-moon-800/60 tw-text-moon-200" : "tw-border-gray-200 tw-bg-gray-50 tw-text-gray-600"}`;
    div.innerHTML = `<div class="tw-max-w-[1880px] tw-mx-auto tw-px-4 tw-py-2.5 tw-flex tw-items-start tw-gap-2 tw-text-xs tw-leading-5"><span aria-hidden="true">ⓘ</span><span><b class="${dark ? "tw-text-moon-50" : "tw-text-gray-900"}">Disclaimer.</b> ${esc(DISCLAIMER)}</span></div>`;
    footer.prepend(div);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", injectDisclaimer);
  else injectDisclaimer();

  const jevLogo = (size = "tw-w-4 tw-h-4") => `<img src="/typesafe-logo.png?v=${"20260924d"}" alt="TypeSafe" class="${size} tw-rounded-full tw-shrink-0 tw-inline-block">`;
  const JEV = `<span class="tw-inline-flex tw-items-center tw-gap-1 tw-align-middle">${jevLogo()}<span>Jev</span></span>`;

  // ---------- plan-gating (shared lock card for Analyst/Basic-only features) ----------
  async function capabilities() {
    if (window.__caps) return window.__caps;
    try { window.__caps = await (await fetch("/api/capabilities")).json(); } catch { window.__caps = { analyst: true, websocket: true }; }
    return window.__caps;
  }
  function lockedHtml(d) {
    const msg = (d && d.message) || "This feature needs a CoinGecko API Analyst plan or higher.";
    const url = (d && d.upgrade_url) || "https://www.coingecko.com/en/api/pricing";
    return `<div class="tw-rounded-xl tw-border tw-border-warning-300 dark:tw-border-warning-600/60 tw-bg-warning-50 dark:tw-bg-moon-800 tw-p-10 tw-text-center">
      <div class="tw-text-3xl">🔒</div>
      <div class="tw-text-base tw-font-semibold tw-mt-3 tw-text-gray-900 dark:tw-text-moon-50 tw-max-w-md tw-mx-auto">${esc(msg)}</div>
      <a href="${esc(url)}" target="_blank" rel="noopener" class="${BTN.base} ${BTN.primary} tw-inline-flex tw-mt-4">Upgrade to Analyst →</a>
    </div>`;
  }

  return {
    jevLogo, JEV,
    flags, BTN, TONE, esc, compactUsd, price, pct, anonName, tokenAvatar, ago, usd6, hash, applyDevVisibility,
    ICON, ic, loadChains, chainLogo, chainLabel, chainBadge, chainPicker, chains: () => CHAIN_META, DISCLAIMER,
    capabilities, lockedHtml,
  };
})();
