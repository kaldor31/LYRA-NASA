#!/usr/bin/env python3
"""Renders docs/drawings/*.svg to vector PDFs with headless Google Chrome:
  docs/drawings/pdf/<sheet>.pdf   one page per sheet
  docs/drawings/LYRA_drawings.pdf all sheets, one per page

Set CHROME=/path/to/chrome to override the default macOS location.
Usage (from the repo root, after gen_drawings.py):
    python3 docs/drawings/_src/render_pdf.py
"""
import glob, os, shutil, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(SRC, "pdf")
ALL = os.path.join(SRC, "LYRA_drawings.pdf")
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
W, H = 1400, 990  # sheet size in CSS px (landscape)

PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
@page {{ size: {w}px {h}px; margin: 0; }}
html, body {{ margin: 0; padding: 0; background: #fff; }}
.p {{ width: {w}px; height: {h}px; overflow: hidden; break-after: page; }}
.p:last-child {{ break-after: auto; }}
.p svg {{ display: block; width: {w}px; height: {h}px; }}
</style></head><body>{body}</body></html>"""


def svg_body(path):
    with open(path, encoding="utf-8") as f:
        txt = f.read()
    return f'<div class="p">{txt[txt.index("<svg"):]}</div>'


def print_pdf(html, pdf):
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        tmp = f.name
    # own throwaway profile: with the default profile Chrome can hang while a
    # normal Chrome window is open
    prof = tempfile.mkdtemp(prefix="lyra-chrome-")
    try:
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
                        f"--user-data-dir={prof}", "--no-pdf-header-footer",
                        f"--print-to-pdf={pdf}", "file://" + tmp],
                       check=True, timeout=90, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        os.unlink(tmp)
        shutil.rmtree(prof, ignore_errors=True)


os.makedirs(OUT, exist_ok=True)
svgs = sorted(glob.glob(os.path.join(SRC, "*.svg")))
for svg in svgs:
    pdf = os.path.join(OUT, os.path.basename(svg)[:-4] + ".pdf")
    print_pdf(PAGE.format(w=W, h=H, body=svg_body(svg)), pdf)
    print("rendered", os.path.relpath(pdf, SRC))
print_pdf(PAGE.format(w=W, h=H, body="".join(svg_body(s) for s in svgs)), ALL)
print("rendered", os.path.relpath(ALL, SRC), f"({len(svgs)} pages)")
