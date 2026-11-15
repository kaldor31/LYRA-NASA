#!/usr/bin/env python3
"""Slide 5 chart as a static image (renders the same in PowerPoint, Keynote and PDF exports).

NASA OSDR OSD-575 (Inspiration4), file LSDS-8_Comprehensive_Metabolic_Panel_CMP.upload_SUBMITTED.csv:
serum SODIUM, mmol/L. Baseline = mean of L-92, L-44, L-3; R+1 = first day after return. Lab range 135 to 146.
Dumbbell per crew member (no truncated bars). Palette validated with the dataviz validator (light mode).
Output: docs/presentation/charts/osd575_sodium.png  (needs Google Chrome for the SVG -> PNG step)
"""
import os
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "charts", "osd575_sodium.png"))
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

CREW = ["C001", "C002", "C003", "C004"]
BASE = [140.7, 142.0, 138.7, 139.7]
R1 = [138, 137, 137, 140]
LAB = (135, 146)
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK2, MUTED, GRID, BAND = "#0B1D33", "#33475B", "#6B7A88", "#E1E7ED", "#EEF3F7"

W, H = 1180, 640
X0, X1 = 150, 1030           # plot area; the change column sits right of it
XC = 1150
Y0, ROW = 200, 105           # first row centre, row step
LO, HI = 132, 148
X = lambda v: X0 + (v - LO) / (HI - LO) * (X1 - X0)


def svg():
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
         f'font-family="Calibri, Helvetica, Arial, sans-serif">', f'<rect width="{W}" height="{H}" fill="#fff"/>']
    o.append(f'<text x="20" y="40" font-size="26" font-weight="700" fill="{INK}">NASA OSDR OSD-575 (Inspiration4): serum sodium, mmol/L</text>')
    # legend
    lx = 20
    for col, lab in ((BLUE, "Pre-flight baseline (mean of 3)"), (ORANGE, "Day after return (R+1)")):
        o.append(f'<circle cx="{lx + 9}" cy="78" r="9" fill="{col}"/>')
        o.append(f'<text x="{lx + 26}" y="85" font-size="20" fill="{INK2}">{lab}</text>')
        lx += 26 + len(lab) * 10 + 40
    yb, ye = Y0 - 60, Y0 + ROW * (len(CREW) - 1) + 60
    # lab range band
    o.append(f'<rect x="{X(LAB[0]):.1f}" y="{yb}" width="{X(LAB[1]) - X(LAB[0]):.1f}" height="{ye - yb}" fill="{BAND}"/>')
    o.append(f'<text x="{(X(LAB[0]) + X(LAB[1])) / 2:.1f}" y="{yb - 10}" font-size="17" fill="{MUTED}" text-anchor="middle">lab reference range 135 to 146</text>')
    # grid + axis
    for v in range(LO, HI + 1, 2):
        o.append(f'<line x1="{X(v):.1f}" y1="{yb}" x2="{X(v):.1f}" y2="{ye}" stroke="{GRID}" stroke-width="1"/>')
        o.append(f'<text x="{X(v):.1f}" y="{ye + 28}" font-size="17" fill="{MUTED}" text-anchor="middle">{v}</text>')
    # rows
    for i, (c, b, r) in enumerate(zip(CREW, BASE, R1)):
        y = Y0 + i * ROW
        o.append(f'<text x="{X0 - 24}" y="{y + 7}" font-size="22" font-weight="700" fill="{INK}" text-anchor="end">{c}</text>')
        o.append(f'<line x1="{X(b):.1f}" y1="{y}" x2="{X(r):.1f}" y2="{y}" stroke="#9AA7B4" stroke-width="3" stroke-linecap="round"/>')
        for v, col in ((b, BLUE), (r, ORANGE)):
            o.append(f'<circle cx="{X(v):.1f}" cy="{y}" r="11" fill="{col}" stroke="#fff" stroke-width="3"/>')
        lo, hi = (r, b) if r <= b else (b, r)
        # baseline is a mean (1 decimal); R+1 is the lab value as reported
        lab_lo, lab_hi = (f"{r:g}", f"{b:.1f}") if r <= b else (f"{b:.1f}", f"{r:g}")
        o.append(f'<text x="{X(lo) - 18:.1f}" y="{y + 7}" font-size="19" fill="{INK2}" text-anchor="end">{lab_lo}</text>')
        o.append(f'<text x="{X(hi) + 18:.1f}" y="{y + 7}" font-size="19" fill="{INK2}" text-anchor="start">{lab_hi}</text>')
        d = r - b
        o.append(f'<text x="{XC}" y="{y + 7}" font-size="19" font-weight="700" fill="{INK}" text-anchor="end">{d:+.1f}</text>')
    o.append(f'<text x="{XC}" y="{Y0 - 40}" font-size="16" fill="{MUTED}" text-anchor="end">change</text>')
    o.append('</svg>')
    return "\n".join(o)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(f'<!doctype html><html><body style="margin:0">{svg()}</body></html>')
        tmp = f.name
    prof = tempfile.mkdtemp(prefix="lyra-chrome-")
    try:
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={prof}",
                        "--hide-scrollbars", "--force-device-scale-factor=2", f"--window-size={W},{H}",
                        f"--screenshot={OUT}", "file://" + tmp],
                       check=True, timeout=90, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        os.unlink(tmp)
    print("written", os.path.relpath(OUT, os.getcwd()))


if __name__ == "__main__":
    main()
