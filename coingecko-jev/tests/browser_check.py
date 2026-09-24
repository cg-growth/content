"""Headless UI checks: python tests/browser_check.py labels [chain]  (server must be running)."""
import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(Path(__file__).resolve().parent.parent / ".browsers"))
from playwright.async_api import async_playwright  # noqa: E402

BASE = "http://127.0.0.1:8787"
SHOTS = Path(__file__).resolve().parent.parent / "fixtures" / "screens"


async def labels(page, chain, query=""):
    await page.goto(f"{BASE}/labels.html{query}")
    await page.wait_for_selector("#tbody tr", timeout=30000)
    if chain != "solana":
        await page.click(f"#chainSeg button[data-v='{chain}']")
        await page.wait_for_timeout(500)
        await page.wait_for_selector("#tbody tr", timeout=30000)
    rows = await page.locator("#tbody tr").count()
    print(f"  feed rows: {rows}")
    await page.screenshot(path=SHOTS / f"labels-{chain}-feed.png")
    await page.click("#labelBtn")
    await page.wait_for_timeout(1200)
    await page.screenshot(path=SHOTS / f"labels-{chain}-running.png")
    await page.wait_for_function("() => !document.getElementById('labelBtn').textContent.includes('labelling')", timeout=120000)
    print("  counter:", (await page.inner_text("#counter")).replace("\n", " "))
    await page.wait_for_timeout(1500)
    labelled = await page.locator("#tbody tr .jev-pop").count()
    print(f"  jev elements rendered: {labelled}")
    await page.screenshot(path=SHOTS / f"labels-{chain}-labelled.png")
    chip = page.locator("#filterBar [data-chip='thin']")
    if await chip.count():
        await chip.click()
        vis = await page.locator("#tbody tr:not(.tw-hidden)").count()
        print(f"  filter 'thin' → visible rows {vis}")
        await chip.click()
    await page.select_option("#sortSel", "risk_desc")
    await page.locator("#tbody tr").first.click()
    await page.wait_for_timeout(400)
    await page.screenshot(path=SHOTS / f"labels-{chain}-drawer.png")
    print("  drawer title:", await page.inner_text("#drawerTitle"))


async def stats(page):
    return await (await page.request.get(f"{BASE}/api/stats")).json()


async def labels_replay(page, chain, query=""):
    names = [f["name"] for f in await (await page.request.get(f"{BASE}/api/fixtures?demo=labels")).json()]
    name = next(n for n in names if f"-{chain}-" in n)
    before = await stats(page)
    await page.goto(f"{BASE}/labels.html?replay={name}&speed=4&anon=1&record=1")
    await page.wait_for_selector("#tbody tr", timeout=30000)
    await page.click("#labelBtn")
    await page.wait_for_function("() => !document.getElementById('labelBtn').textContent.includes('labelling')", timeout=120000)
    await page.wait_for_timeout(1500)
    after = await stats(page)
    print(f"  replay {name}: rows {await page.locator('#tbody tr').count()}, labelled {await page.locator('#tbody tr .jev-pop').count()} elements")
    print(f"  network during replay: CG calls +{after['cg_calls'] - before['cg_calls']}, Jev calls +{after['jev']['calls'] - before['jev']['calls']}")
    dev_visible = await page.locator("#devBar:not(.tw-hidden)").count()
    print(f"  record mode hides dev bar: {dev_visible == 0}; anon first token: {await page.inner_text('#tbody tr:first-child td:nth-child(2) span')}")
    await page.screenshot(path=SHOTS / f"labels-{chain}-replay-anon.png")


async def pulse(page, chain, query="", seconds=180):
    await page.goto(f"{BASE}/pulse.html{query}")
    if chain != "solana":
        await page.click(f"#chainSeg button[data-v='{chain}']")
    await page.wait_for_selector("#pickerList input[type=radio]", timeout=30000)
    print("  picker rows:", await page.locator("#pickerList input[type=radio]").count())
    await page.screenshot(path=SHOTS / f"pulse-{chain}-picker.png")
    await page.click("#startBtn")
    await page.wait_for_selector("#live:not(.tw-hidden)", timeout=60000)
    await page.wait_for_function("() => Object.keys(S.scores).length > 0", timeout=60000)
    t0 = await page.evaluate("Date.now()")
    half = seconds // 2
    await page.wait_for_timeout(half * 1000)
    await page.screenshot(path=SHOTS / f"pulse-{chain}-live.png")
    before = await page.evaluate("focusPid()")
    if await page.locator("#watch [data-pid]").count():
        await page.locator("#watch [data-pid]").first.click()
        await page.wait_for_function(f"() => focusPid() !== '{before}'", timeout=10000)
        print("  focus switched:", before[:8], "->", (await page.evaluate("focusPid()"))[:8])
    await page.wait_for_timeout((seconds - half) * 1000)
    await page.screenshot(path=SHOTS / f"pulse-{chain}-live-2.png")
    r = await page.evaluate("""() => ({
        scores: S.scoreTimes.length, trades: S.tradeTimes.length, markers: S.markers.length,
        focusCandles: candles.data().length, ribbon: pumpLine.data().length, ws: S.wsStatus, credits: S.credits,
        latency: S.lastLatency, gauge: document.querySelector('#gaugePump .tw-text-3xl')?.textContent })""")
    print(f"  after {seconds}s: {r}")
    await page.click("#stopBtn")
    await page.wait_for_timeout(1500)
    print("  after stop:", (await page.inner_text("#liveBadge")).replace("\n", " "))


async def pulse_search(page, chain, query=""):
    """Search by ticker, stream the first hit, switch through every interval, then search by contract address."""
    await page.goto(f"{BASE}/pulse.html{query}")
    await page.wait_for_selector("#pickerList input[type=radio]", timeout=30000)
    term = "bonk" if chain == "solana" else "pons"
    await page.fill("#searchInput", term)
    await page.wait_for_selector("#searchResults [data-i]", timeout=20000)
    n = await page.locator("#searchResults [data-i]").count()
    first = await page.evaluate("searchRows[0]")
    print(f"  search '{term}': {n} results, first {first['pool_name']} ({first['id'][:10]}…)")
    await page.screenshot(path=SHOTS / f"pulse-{chain}-search.png")
    await page.locator("#searchResults [data-i]").first.click()
    await page.wait_for_function("() => S.session && S.session.live && focusPid()", timeout=60000)
    print("  streaming:", (await page.evaluate("focusPid()"))[:10], "== first hit:", await page.evaluate("focusPid()") == first["id"])
    await page.wait_for_timeout(15000)
    for iv in ["15s", "1m", "5m", "15m", "1h", "1s"]:
        await page.click(f"#intervalSeg button[data-iv='{iv}']")
        sec = {"1s": 1, "15s": 15, "1m": 60, "5m": 300, "15m": 900, "1h": 3600}[iv]
        await page.wait_for_function(
            f"() => {{ const d = candles.data(); return S.interval === '{iv}' && d.length > 10 && d.slice(-20).every(x => x.time % {sec} === 0) && (d[d.length-1].time - d[0].time) >= {sec} * 10; }}",
            timeout=30000,
        )
        info = await page.evaluate("() => { const d = candles.data(); return {bars: d.length, span_s: d.length ? d[d.length-1].time - d[0].time : 0, step: d.length > 1 ? d[d.length-1].time - d[d.length-2].time : null}; }")
        print(f"  interval {iv:>3}: {info}")
        if iv in ("1m", "1s"):
            await page.screenshot(path=SHOTS / f"pulse-{chain}-interval-{iv}.png")
    await page.fill("#searchInput", first["id"])
    await page.wait_for_selector("#searchResults [data-i]", timeout=20000)
    hit = await page.evaluate("searchRows[0].id")
    print("  contract-address search returns that pool first:", hit == first["id"])
    await page.keyboard.press("Escape")
    await page.click("#stopBtn")
    await page.wait_for_timeout(1000)


async def pulse_replay(page, chain, query=""):
    names = [f["name"] for f in await (await page.request.get(f"{BASE}/api/fixtures?demo=pulse")).json()]
    name = next(n for n in names if f"-{chain}-" in n)
    before = await stats(page)
    for speed in (1, 4):
        await page.goto(f"{BASE}/pulse.html?replay={name}&speed={speed}&anon=1&record=1")
        await page.wait_for_function("() => S.session && Object.keys(S.scores).length > 0", timeout=60000)
        await page.wait_for_timeout(20000)
        r = await page.evaluate("() => ({scores: S.scoreTimes.length, trades: S.tradeTimes.length, candles: candles.data().length, badge: document.getElementById('liveBadge').innerText})")
        print(f"  replay {name} @{speed}x after 20s: {r}")
        await page.screenshot(path=SHOTS / f"pulse-{chain}-replay-{speed}x.png")
    after = await stats(page)
    print(f"  network during replay: CG calls +{after['cg_calls'] - before['cg_calls']}, Jev calls +{after['jev']['calls'] - before['jev']['calls']}")


async def fng(page, _chain="", query=""):
    await page.goto(f"{BASE}/fng.html{query}")
    await page.wait_for_selector("#tbody tr", timeout=30000)
    print("  universe rows:", await page.locator("#tbody tr").count())
    theme_dark = await page.evaluate("document.documentElement.classList.contains('tw-dark')")
    bg = await page.evaluate("getComputedStyle(document.body).backgroundColor")
    print(f"  light theme: {not theme_dark} (body bg {bg})")
    await page.screenshot(path=SHOTS / "fng-universe.png")
    await page.click("#runBtn")
    await page.wait_for_timeout(4000)
    await page.screenshot(path=SHOTS / "fng-running.png")
    await page.wait_for_function("() => !document.getElementById('runBtn').textContent.includes('scoring')", timeout=300000)
    await page.wait_for_timeout(1500)
    print("  counter:", (await page.inner_text("#counter")).replace("\n", " "))
    print("  aggregate:", (await page.inner_text("#aggregate")).replace("\n", " "))
    await page.screenshot(path=SHOTS / "fng-scored.png")
    for k in ("divergence", "fearful"):
        await page.click(f"[data-preset='{k}']")
        vis = await page.locator("#tbody tr:not(.tw-hidden)").count()
        print(f"  preset {k}: {vis} rows")
        await page.screenshot(path=SHOTS / f"fng-preset-{k}.png")
        await page.click(f"[data-preset='{k}']")
    await page.select_option("#sortSel", "rank")
    await page.locator("#row-bitcoin").click()
    await page.wait_for_timeout(500)
    heads = await page.locator("#drawerBody li").count()
    struck = await page.locator("#drawerBody .tw-line-through").count()
    ins_cards = await page.locator("#drawerBody .tw-rounded-2xl").count()
    print(f"  bitcoin drawer: {heads} headlines (struck-through: {struck}), {ins_cards} insight cards, gauge value {await page.inner_text('#drawerBody .tw-text-5xl')}")
    with_ins = await page.evaluate("Object.values(S.results).filter(r => (r.insights||[]).length).length")
    print(f"  coins with insights: {with_ins}")
    await page.screenshot(path=SHOTS / "fng-drawer-bitcoin.png")


async def fng_scopes(page, _chain="", query=""):
    await page.goto(f"{BASE}/fng.html{query}")
    await page.evaluate("localStorage.removeItem('fng-basket')")
    await page.reload()
    await page.wait_for_selector("#tbody tr", timeout=30000)
    # Category
    await page.click("#scopeTabs button[data-k='category']")
    await page.wait_for_selector("#catGrid [data-cat]", timeout=30000)
    print("  category grid cards:", await page.locator("#catGrid [data-cat]").count())
    await page.screenshot(path=SHOTS / "fng-category-picker.png")
    await page.fill("#catSearch", "ai agents")
    await page.wait_for_timeout(300)
    names = await page.locator("#catGrid [data-cat] span.tw-font-semibold").all_inner_texts()
    print("  search 'ai agents' →", names[:5])
    await page.locator("#catGrid [data-cat='ai-agents']").click()
    await page.wait_for_function("() => S.coins.length > 5 && document.querySelectorAll('#tbody tr').length === S.coins.length", timeout=30000)
    print("  AI Agents feed rows:", await page.locator("#tbody tr").count(), "| title:", await page.inner_text("#pageTitle"))
    await page.click("#scopePanel #sizeSeg button[data-v='50']")
    await page.wait_for_timeout(1500)
    await page.click("#runBtn")
    await page.wait_for_function("() => !document.getElementById('runBtn').textContent.includes('scoring')", timeout=300000)
    await page.wait_for_timeout(1000)
    print("  category run:", (await page.inner_text("#counter")).replace("\n", " "), "|", (await page.inner_text("#aggregate")).replace("\n", " "))
    await page.screenshot(path=SHOTS / "fng-category-scored.png")
    # Niche category via search
    await page.click("#changeCat")
    await page.fill("#catSearch", "pudgy")
    await page.wait_for_timeout(300)
    print("  niche search 'pudgy' →", (await page.locator("#catGrid [data-cat] span.tw-font-semibold").all_inner_texts())[:4])
    # My coins
    await page.click("#scopeTabs button[data-k='custom']")
    for q, cid in (("hyperliquid", "hyperliquid"), ("zcash", "zcash"), ("bonk", "bonk")):
        await page.fill("#coinSearch", q)
        await page.wait_for_selector(f"#coinResults [data-coin='{cid}']", timeout=20000)
        await page.click(f"#coinResults [data-coin='{cid}']")
        await page.wait_for_timeout(300)
    await page.wait_for_function("() => S.coins.length === 3", timeout=30000)
    print("  basket:", await page.evaluate("S.basket.map(c => c.id)"), "| feed rows:", await page.locator("#tbody tr").count())
    await page.screenshot(path=SHOTS / "fng-mycoins-basket.png")
    await page.click("#runBtn")
    await page.wait_for_function("() => !document.getElementById('runBtn').textContent.includes('scoring')", timeout=200000)
    await page.wait_for_timeout(800)
    print("  my coins run:", (await page.inner_text("#counter")).replace("\n", " "), "| scored:", await page.evaluate("Object.values(S.results).map(r => r.coin.symbol + ' ' + Math.round(r.fng))"))
    await page.screenshot(path=SHOTS / "fng-mycoins-scored.png")


async def fng_replay(page, _chain="", query=""):
    names = [f["name"] for f in await (await page.request.get(f"{BASE}/api/fixtures?demo=fng")).json()]
    before = await stats(page)
    await page.goto(f"{BASE}/fng.html?replay={names[0]}&speed=4&record=1")
    await page.wait_for_selector("#tbody tr", timeout=30000)
    await page.click("#runBtn")
    await page.wait_for_function("() => !document.getElementById('runBtn').textContent.includes('scoring')", timeout=120000)
    await page.wait_for_timeout(1000)
    after = await stats(page)
    scored = await page.evaluate("Object.keys(S.results).length")
    print(f"  replay {names[0]}: {scored} coins scored; CG calls +{after['cg_calls'] - before['cg_calls']}, Jev calls +{after['jev']['calls'] - before['jev']['calls']}")


async def main(demo, chain="solana", query=""):
    SHOTS.mkdir(parents=True, exist_ok=True)
    errors = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        page = await b.new_page(viewport={"width": 1920, "height": 1080})
        page.on("console", lambda m: m.type == "error" and errors.append(m.text))
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        fn = {"labels": labels, "labels-replay": labels_replay, "pulse": pulse, "pulse-replay": pulse_replay, "pulse-search": pulse_search, "fng": fng, "fng-replay": fng_replay, "fng-scopes": fng_scopes}[demo]
        await fn(page, chain, query)
        await b.close()
    real = [e for e in errors if "cdn.tailwindcss.com should not be used in production" not in e]
    print(f"  console errors: {len(real)}")
    for e in real[:10]:
        print("   -", e[:200])


if __name__ == "__main__":
    a = sys.argv[1:]
    asyncio.run(main(a[0], a[1] if len(a) > 1 else "solana", a[2] if len(a) > 2 else ""))
