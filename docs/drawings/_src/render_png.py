#!/usr/bin/env python3
"""Renders docs/drawings/*.svg to docs/drawings/png/*.png (1400x990).

Uses cairosvg if importable, otherwise headless Google Chrome
(set CHROME=/path/to/chrome to override the default macOS location).
Usage (from the repo root):
    python3 docs/drawings/_src/gen_drawings.py
    python3 docs/drawings/_src/render_png.py
"""
import glob, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(SRC, "png")
os.makedirs(OUT, exist_ok=True)
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

try:
    import cairosvg  # type: ignore
except Exception:
    cairosvg = None

for svg in sorted(glob.glob(os.path.join(SRC, "*.svg"))):
    png = os.path.join(OUT, os.path.basename(svg)[:-4] + ".png")
    if cairosvg:
        cairosvg.svg2png(url=svg, write_to=png, output_width=1400, output_height=990)
    else:
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=1", "--window-size=1400,990",
                        f"--screenshot={png}", "file://" + svg],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("rendered", os.path.relpath(png, SRC))
sys.exit(0)
