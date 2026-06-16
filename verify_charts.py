import subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright

# Every chart div, grouped by the tab it lives in.
CHARTS_BY_TAB = {
    "overview": ["chart-yearly-trends"],
    "distribution": ["chart-brand-pie", "chart-os-pie", "chart-battery-type-pie", "chart-histograms"],
    "brand-value": ["chart-avg-price-by-brand", "chart-battery-efficiency",
                    "chart-specs-by-brand", "chart-price-by-os"],
    "advanced": ["chart-video-formats", "chart-correlation"],
}

proc = subprocess.Popen([sys.executable, "main.py"])
failures = []
try:
    for _ in range(30):
        try:
            urllib.request.urlopen("http://127.0.0.1:5000/"); break
        except Exception:
            time.sleep(0.5)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Fail loudly on any uncaught JS error or console error (e.g. a bad Plotly spec).
        js_errors = []
        page.on("pageerror", lambda e: js_errors.append(str(e)))
        page.on("console", lambda m: js_errors.append(m.text) if m.type == "error" else None)

        page.goto("http://127.0.0.1:5000/")

        for tab, ids in CHARTS_BY_TAB.items():
            page.click('button[data-tab="%s"]' % tab)
            # Open every <details> so charts in collapsed sections become visible.
            page.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
            page.wait_for_timeout(200)
            for cid in ids:
                try:
                    page.wait_for_selector("#%s .main-svg" % cid, timeout=5000)
                    box = page.query_selector("#%s .main-svg" % cid).bounding_box()
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
        box = page.query_selector("#chart-brand-pie .main-svg").bounding_box()
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
print("\nPASS (11/11 charts rendered)")
