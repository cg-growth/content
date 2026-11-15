// Multi-chain crypto wallet: front end.
// The private key is created and kept here, in the browser, and never sent to the server.
const $ = (id) => document.getElementById(id);
const usd = (v) => {
  if (v == null) return "–";
  const n = Number(v);
  // Small prices (memecoins) need significant digits, not 2 decimals
  const opts = Math.abs(n) > 0 && Math.abs(n) < 1 ? { maximumSignificantDigits: 4 } : { maximumFractionDigits: 2 };
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", ...opts });
};
// PnL amounts under half a cent are rounding noise, so show them as $0.00
const pnlUsd = (v) => (v == null ? "–" : usd(Math.abs(Number(v)) < 0.005 ? 0 : v));
const pct = (v) => (v == null ? "–" : `${Number(v) >= 0 ? "+" : ""}${Number(v).toFixed(2)}%`);
const short = (a) => `${a.slice(0, 6)}…${a.slice(-4)}`;

let config = {};
let wallet = null; // ethers.Wallet, in memory only
let chart = null;

async function api(path, options) {
  const res = await fetch(path, options);
  const body = await res.json();
  if (!res.ok) throw Object.assign(new Error(body.error || res.statusText), { upgrade: body.upgrade });
  return body;
}

function showError(el, err) {
  el.innerHTML = err.upgrade
    ? `<p class="note">Wallet data needs an <a href="https://www.coingecko.com/en/api/pricing" target="_blank">Analyst plan API key</a> or above. Wallet creation, send and price charts work on the Demo plan.</p>`
    : `<p class="error">${err.message}</p>`;
}

// ---- Wallet address ------------------------------------------------------
function createWallet() {
  wallet = ethers.Wallet.createRandom();
  $("my-address").textContent = wallet.address;
  $("backup").innerHTML = `Back up this private key now. It isn't stored anywhere:<br><code>${wallet.privateKey}</code>`;
  $("address").value = wallet.address;
  refreshSepolia();
}

function importWallet() {
  try {
    wallet = new ethers.Wallet($("import-key").value.trim());
    $("my-address").textContent = wallet.address;
    $("backup").textContent = "Key imported into this browser tab only.";
    $("import-key").value = "";
    refreshSepolia();
  } catch {
    $("backup").textContent = "That doesn't look like a valid private key.";
  }
}

// ---- Portfolio -----------------------------------------------------------
async function loadPortfolio(address) {
  const el = $("portfolio");
  el.innerHTML = "Loading…";
  try {
    const p = await api(`/api/portfolio/${address}`);
    const byNetwork = p.networks
      .filter((n) => Number(n.value_usd) > 0)
      .map((n) => `<span class="chip">${config.networks[n.network] || n.network} ${usd(n.value_usd)}</span>`)
      .join("");
    const rows = p.balances
      .slice(0, 15) // top 15 by value; the API sorts by value_usd by default
      .map((b) => `
        <tr data-coin="${b.coingecko_coin_id || ""}" data-symbol="${b.symbol}">
          <td>${b.logo ? `<img src="${b.logo}" alt="">` : `<span class="dot">${b.symbol.charAt(0).toUpperCase()}</span>`} ${b.symbol}</td>
          <td>${config.networks[b.network] || b.network}</td>
          <td>${Number(b.balance ?? 0).toLocaleString("en-US", { maximumFractionDigits: 4 })}</td>
          <td>${usd(b.price_usd)}</td>
          <td class="${Number(b.h24_price_change_percentage) >= 0 ? "up" : "down"}">${pct(b.h24_price_change_percentage)}</td>
          <td>${usd(b.value_usd)}</td>
        </tr>`)
      .join("");
    el.innerHTML = `
      <p class="total">${usd(p.total_value_usd)} <small>across ${p.total_holdings} holdings</small></p>
      <div class="chips">${byNetwork}</div>
      <table><thead><tr><th>Token</th><th>Network</th><th>Balance</th><th>Price</th><th>24h</th><th>Value</th></tr></thead>
      <tbody>${rows}</tbody></table>`;
    el.querySelectorAll("tr[data-coin]").forEach((tr) =>
      tr.addEventListener("click", () => loadChart(tr.dataset.coin, tr.dataset.symbol)));
    // Show activity for ?network= if given, otherwise where this wallet holds the most value
    const top = [...p.networks].sort((a, b) => Number(b.value_usd) - Number(a.value_usd))[0];
    const wanted = new URLSearchParams(location.search).get("network");
    if (wanted && config.networks[wanted]) $("activity-network").value = wanted;
    else if (top) $("activity-network").value = top.network;
    loadActivity(address);
  } catch (err) {
    showError(el, err);
  }
}

// ---- Token detail: price chart ------------------------------------------
async function loadChart(coinId, symbol) {
  $("chart-title").textContent = coinId ? `${symbol}: 30-day price` : `${symbol}: no CoinGecko price chart for this token`;
  if (!coinId) return;
  const { prices } = await api(`/api/chart/${coinId}?days=30`);
  if (chart) chart.destroy();
  chart = new Chart($("chart"), {
    type: "line",
    data: {
      labels: prices.map((p) => new Date(p[0]).toLocaleDateString()),
      datasets: [{ data: prices.map((p) => p[1]), borderColor: "#4bcc00", pointRadius: 0, tension: 0.2 }],
    },
    options: { plugins: { legend: { display: false } }, scales: { x: { ticks: { maxTicksLimit: 6 } } } },
  });
}

// ---- Activity feed ------------------------------------------------------
async function loadActivity(address) {
  const el = $("activity");
  el.innerHTML = "Loading…";
  try {
    const a = await api(`/api/activity/${address}?network=${$("activity-network").value}`);
    if (!a.items.length) return (el.innerHTML = "<p>No trades or transfers in the last 7 days on this network.</p>");
    el.innerHTML = `<table><tbody>${a.items.slice(0, 25).map((i) => `
      <tr><td><span class="tag ${i.type}">${i.type}</span></td>
      <td>${i.symbol ? `${Number(i.amount ?? 0).toLocaleString("en-US", { maximumFractionDigits: 4 })} ${i.symbol}` : `${usd(i.usd)} on ${i.dex}`}</td>
      <td>${new Date(i.time).toLocaleString()}</td>
      <td><code>${short(i.tx_hash)}</code></td></tr>`).join("")}</tbody></table>`;
  } catch (err) {
    showError(el, err);
  }
}

// ---- PnL ----------------------------------------------------------------
async function loadPnl(address) {
  const el = $("pnl");
  el.innerHTML = "Loading…";
  try {
    const p = await api(`/api/pnl/${address}`);
    const cls = (v) => (v == null || Math.abs(Number(v)) < 0.005 ? "" : Number(v) > 0 ? "up" : "down");
    el.innerHTML = `
      <p class="total">Realized <span class="${cls(p.total_realized_pnl_usd)}">${pnlUsd(p.total_realized_pnl_usd)}</span>
        · Unrealized <span class="${cls(p.total_unrealized_pnl_usd)}">${pnlUsd(p.total_unrealized_pnl_usd)}</span></p>
      <div class="chips">${p.networks.map((n) => `<span class="chip">${config.networks[n.network] || n.network}: ${pnlUsd(n.realized_pnl_usd)} realized</span>`).join("")}</div>
      <table><thead><tr><th>Token</th><th>Realized</th><th>Unrealized</th><th>Avg buy</th><th>Avg sell</th><th>Buys / sells</th></tr></thead>
      <tbody>${p.token_stats.filter((t) => t.total_buy_count > 0).slice(0, 15).map((t) => `
        <tr><td>${t.symbol} <small>${config.networks[t.network] || t.network}</small></td>
        <td class="${cls(t.realized_pnl_usd)}">${pnlUsd(t.realized_pnl_usd)}</td>
        <td class="${cls(t.unrealized_pnl_usd)}">${pnlUsd(t.unrealized_pnl_usd)}</td>
        <td>${usd(t.average_buy_price_usd)}</td><td>${usd(t.average_sell_price_usd)}</td>
        <td>${t.total_buy_count} / ${t.total_sell_count}</td></tr>`).join("")}</tbody></table>`;
  } catch (err) {
    showError(el, err);
  }
}

// ---- Send and receive on Sepolia -----------------------------------------
async function refreshSepolia() {
  if (!wallet) return;
  try {
    const s = await api(`/api/sepolia/${wallet.address}`);
    $("sepolia-balance").textContent = `${s.balance_eth} Sepolia ETH`;
  } catch (err) {
    $("sepolia-balance").textContent = err.message;
  }
}

async function sendEth() {
  const out = $("send-result");
  if (!wallet) return (out.textContent = "Create or import a wallet first.");
  try {
    const to = ethers.getAddress($("send-to").value.trim()); // validates and checksums
    const s = await api(`/api/sepolia/${wallet.address}`);
    const tx = {
      to,
      value: ethers.parseEther($("send-amount").value),
      nonce: s.nonce,
      chainId: s.chain_id,
      gasLimit: 21000n, // a plain ETH transfer
      maxPriorityFeePerGas: BigInt(s.max_priority_fee_per_gas),
      maxFeePerGas: BigInt(s.max_fee_per_gas),
      type: 2,
    };
    const rawTx = await wallet.signTransaction(tx); // signed here, in the browser
    const { tx_hash } = await api("/api/sepolia/send", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ raw_tx: rawTx }),
    });
    out.innerHTML = `Sent: <a href="https://sepolia.etherscan.io/tx/${tx_hash}" target="_blank">${short(tx_hash)}</a>`;
  } catch (err) {
    out.textContent = err.message;
  }
}

// ---- Start -----------------------------------------------------------------
function loadAll() {
  const address = $("address").value.trim();
  if (!ethers.isAddress(address)) return alert("Enter a valid address.");
  $("activity-network").value = "eth";
  loadPortfolio(address); // also loads activity for the top network
  loadPnl(address);
}

document.addEventListener("DOMContentLoaded", async () => {
  config = await api("/api/config");
  // Optional deep link: /?address=0x...&network=robinhood
  $("address").value = new URLSearchParams(location.search).get("address") || config.sample_address;
  $("activity-network").innerHTML = Object.entries(config.networks)
    .map(([id, name]) => `<option value="${id}">${name}</option>`).join("");
  $("load").addEventListener("click", loadAll);
  $("activity-network").addEventListener("change", () => loadActivity($("address").value.trim()));
  $("create").addEventListener("click", createWallet);
  $("import").addEventListener("click", importWallet);
  $("send").addEventListener("click", sendEth);
  loadAll();
  loadChart("ethereum", "ETH");
});
