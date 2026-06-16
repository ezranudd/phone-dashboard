import os, socket, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright

# Every chart div, grouped by the tab it lives in.
CHARTS_BY_TAB = {
    "overview": ["chart-yearly-trends"],
    "distribution": ["chart-brand-pie", "chart-os-pie", "chart-battery-type-pie",
                     "chart-histograms", "chart-tiers-scatter", "chart-tiers-summary"],
    "brand-value": ["chart-value-ranking", "chart-avg-price-by-brand",
                    "chart-battery-efficiency", "chart-specs-by-brand", "chart-price-by-os"],
    "advanced": ["chart-price-drivers", "chart-pred-actual",
                 "chart-video-formats", "chart-correlation"],
}
TOTAL = sum(len(ids) for ids in CHARTS_BY_TAB.values())

def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port

# Run on a dedicated ephemeral port so we never accidentally test a stale server
# that may already be running on :5000.
PORT = _free_port()
BASE = "http://127.0.0.1:%d" % PORT

proc = subprocess.Popen([sys.executable, "main.py"], env={**os.environ, "PORT": str(PORT)})
failures = []
try:
    ready = False
    for _ in range(30):
        if proc.poll() is not None:
            sys.exit("FAIL: main.py exited before serving (exit code %s)" % proc.returncode)
        try:
            urllib.request.urlopen(BASE + "/"); ready = True; break
        except Exception:
            time.sleep(0.5)
    if not ready:
        sys.exit("FAIL: server did not become ready at %s" % BASE)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Fail loudly on any uncaught JS error or Plotly console error. Ignore
        # unrelated resource-load errors (e.g. the browser's automatic favicon 404).
        js_errors = []
        page.on("pageerror", lambda e: js_errors.append(str(e)))
        page.on("console", lambda m: js_errors.append(m.text)
                if m.type == "error" and "Failed to load resource" not in m.text else None)

        page.goto(BASE + "/")

        for tab, ids in CHARTS_BY_TAB.items():
            page.click('button[data-tab="%s"]' % tab)
            # Open every <details> so charts in collapsed sections become visible.
            page.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
            page.wait_for_timeout(200)
            for cid in ids:
                # .plot-container exists for every Plotly trace type (incl. table,
                # which has no .main-svg); its width catches zero-width renders.
                try:
                    page.wait_for_selector("#%s .plot-container" % cid, timeout=5000)
                    box = page.query_selector("#%s .plot-container" % cid).bounding_box()
                    if box and box["width"] > 100:
                        print("OK  %-26s width=%.0fpx" % (cid, box["width"]))
                    else:
                        failures.append("%s did not size: %s" % (cid, box))
                except Exception as e:
                    failures.append("%s never rendered: %s" % (cid, e))

        # Resize-gotcha regression: collapse + reopen brand pie's <details>.
        page.click('button[data-tab="distribution"]')
        page.click("#chart-brand-pie >> xpath=ancestor::details/summary")
        page.click("#chart-brand-pie >> xpath=ancestor::details/summary")
        page.wait_for_timeout(300)
        box = page.query_selector("#chart-brand-pie .plot-container").bounding_box()
        if box and box["width"] > 100:
            print("OK  %-26s width=%.0fpx (after details toggle)" % ("chart-brand-pie", box["width"]))
        else:
            failures.append("brand pie collapsed after toggle: %s" % box)

        if js_errors:
            failures.append("JS errors: %s" % js_errors)

        browser.close()
finally:
    proc.terminate()

if failures:
    print("\nFAIL")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("\nPASS (%d/%d charts rendered)" % (TOTAL, TOTAL))
