"""Render daily_report_v3.html to daily_report.pdf using system Chrome via Playwright.

The inputs panel is hidden by print CSS; the PDF is the printable report for the
period passed on the command line (default: the month of the latest data date).

Run:  python render_pdf.py [END] [START] [SHIFT]
      python render_pdf.py 2026-08-25               end date, start = its month
      python render_pdf.py 2026-08-25 2026-08-01    explicit range
      python render_pdf.py 2026-08-25 2026-08-01 DS day shift only
"""
import os
import pathlib
import sys

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = pathlib.Path(os.path.join(HERE, "daily_report_v3.html")).resolve().as_uri()
OUT = os.path.join(HERE, "daily_report.pdf")


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else None
    start = sys.argv[2] if len(sys.argv) > 2 else None
    shift = sys.argv[3] if len(sys.argv) > 3 else None
    with sync_playwright() as p:
        for channel in ("chrome", "msedge"):
            try:
                browser = p.chromium.launch(channel=channel, headless=True)
                print(f"using {channel}")
                break
            except Exception:
                browser = None
        if browser is None:
            browser = p.chromium.launch(headless=True)

        page = browser.new_page(viewport={"width": 1340, "height": 1600})
        page.goto(SRC, wait_until="load")
        # the page boots asynchronously (live cube fetch, then snapshot fallback);
        # the date options do not exist until that finishes
        page.wait_for_function("!document.getElementById('loadOverlay')", timeout=240000)
        if date:
            page.select_option("#dateSel", date)
        if start:
            page.select_option("#startSel", start)
        if shift is not None:
            page.select_option("#shiftSel", shift)
        if date or start or shift is not None:
            page.wait_for_timeout(900)
        page.evaluate("document.fonts.ready")
        # engineering notes load their photographs from IndexedDB
        page.evaluate("window.__notesReady || Promise.resolve()")
        page.emulate_media(media="print")
        page.pdf(path=OUT, format="A4", landscape=False, print_background=True,
                 scale=0.62,
                 margin={"top": "8mm", "bottom": "8mm", "left": "6mm", "right": "6mm"})
        browser.close()
    print(f"wrote {OUT}  ({os.path.getsize(OUT)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
