#!/usr/bin/env python3
"""Generates the LYRA concept drawing sheets (SVG, English), v3 concept:
free-standing touch mirror plus three camera pillars (two front, one back,
bases bolted to the floor), optional contact research module (vertical
Doppler grips with a solid hydrogel cassette),
face pipeline and system / AI modules.

Default output: docs/drawings/ (resolved relative to this script).
An optional argv[1] overrides the output directory.
PNG exports: run render_png.py (same folder) after this script.
Earlier sheets (v1: handle tape cassette, compact config, Russian set) are in
docs/drawings/archive/v1/.
"""
import math, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.normpath(os.path.join(HERE, ".."))
os.makedirs(OUT, exist_ok=True)
W, H = 1400, 990
NSHEETS = 5


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class S:
    def __init__(self): self.p = []
    def add(self, x): self.p.append(x)
    def line(self, x1, y1, x2, y2, cls="o", extra=""):
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="{cls}" {extra}/>')
    def rect(self, x, y, w, h, cls="o", rx=0, extra=""):
        if "fill=" in extra and cls == "o":
            cls = "nc"  # let the fill attribute win over the .o class
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" class="{cls}" {extra}/>')
    def circle(self, cx, cy, r, cls="o", extra=""):
        if "fill=" in extra and cls == "o":
            cls = "nc"
        self.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" class="{cls}" {extra}/>')
    def ellipse(self, cx, cy, rx, ry, cls="o", extra=""):
        self.add(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" class="{cls}" {extra}/>')
    def poly(self, pts, cls="o", closed=True, extra=""):
        d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        tag = "polygon" if closed else "polyline"
        self.add(f'<{tag} points="{d}" class="{cls}" {extra}/>')
    def path(self, d, cls="o", extra=""):
        self.add(f'<path d="{d}" class="{cls}" {extra}/>')
    def text(self, x, y, s, cls="t", anchor="start", extra=""):
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" text-anchor="{anchor}" {extra}>{esc(s)}</text>')
    def mtext(self, x, y, lines, cls="t", anchor="start", dy=16):
        for i, s in enumerate(lines):
            self.text(x, y + i * dy, s, cls, anchor)
    def dim(self, x1, y1, x2, y2, label, off=0, cls="dl"):
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="dim"/>')
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        if abs(x2 - x1) < 1:
            self.add(f'<text x="{mx-6+off:.1f}" y="{my:.1f}" class="{cls}" text-anchor="middle" transform="rotate(-90 {mx-6+off:.1f} {my:.1f})">{esc(label)}</text>')
        else:
            self.text(mx, my - 6 + off, label, cls, "middle")
    def ext(self, x1, y1, x2, y2):
        self.line(x1, y1, x2, y2, "ex")
    def leader(self, x1, y1, x2, y2, anchor="start", lines=(), cls="s", dy=13):
        self.add(f'<circle cx="{x1:.1f}" cy="{y1:.1f}" r="2.2" fill="#222"/>')
        self.line(x1, y1, x2, y2, "ld")
        tx = x2 + (4 if anchor == "start" else -4 if anchor == "end" else 0)
        self.mtext(tx, y2 + 4, list(lines), cls, anchor, dy)
    def arrow(self, x1, y1, x2, y2, cls="fl"):
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="{cls}" marker-end="url(#fa)"/>')
    def parrow(self, d, cls="fl"):
        self.add(f'<path d="{d}" class="{cls}" marker-end="url(#fa)"/>')
    def box(self, x, y, w, h, title, lines=(), cls="blk", tcls="b", lcls="s", dy=14, rx=4, center=True):
        self.rect(x, y, w, h, cls, rx=rx)
        if center:
            self.text(x + w / 2, y + 18, title, tcls, "middle")
            self.mtext(x + w / 2, y + 18 + dy + 2, list(lines), lcls, "middle", dy)
        else:
            self.text(x + 8, y + 18, title, tcls)
            self.mtext(x + 8, y + 18 + dy + 2, list(lines), lcls, "start", dy)
    def out(self): return "\n".join(self.p)


# provenance tags (sheet 5)
TAGS = {
    "TEAM": ("TEAM RECORDING", "#1f5fa8"),
    "OPEN": ("OPEN DATASET", "#1a7a4a"),
    "NASA": ("NASA MATERIAL", "#b35900"),
    "SIM": ("SIMULATION", "#6a3d9a"),
}


def tag(s, x, y, key, anchor="start"):
    label, col = TAGS[key]
    w = len(label) * 6.4 + 12
    if anchor == "end":
        x -= w
    s.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="15" rx="7" fill="{col}"/>')
    s.add(f'<text x="{x + w/2:.1f}" y="{y + 11:.1f}" text-anchor="middle" class="tg">{esc(label)}</text>')
    return w


STYLE = """
<defs>
  <marker id="da" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,1.5 L10,5 L0,8.5 z" fill="#222"/></marker>
  <marker id="fa" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#222"/></marker>
  <marker id="fr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#c0392b"/></marker>
  <marker id="fb" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#1f5fa8"/></marker>
  <pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="#555" stroke-width="1"/></pattern>
  <pattern id="hatch2" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)"><line x1="0" y1="0" x2="0" y2="5" stroke="#777" stroke-width="0.8"/></pattern>
  <style>
    text{font-family:Arial,Helvetica,sans-serif}
    .t{font-size:13px;fill:#111}
    .s{font-size:11px;fill:#333}
    .xs{font-size:10px;fill:#444}
    .b{font-size:13px;fill:#111;font-weight:bold}
    .bs{font-size:11px;fill:#111;font-weight:bold}
    .h{font-size:20px;fill:#111;font-weight:bold}
    .vh{font-size:15px;fill:#111;font-weight:bold}
    .dl{font-size:12px;fill:#111}
    .ai{font-size:12px;fill:#b00020;font-weight:bold}
    .tg{font-size:9.5px;fill:#fff;font-weight:bold;letter-spacing:0.2px}
    .rt{font-size:11px;fill:#c0392b}
    .bt{font-size:11px;fill:#1f5fa8}
    .gt{font-size:11px;fill:#1a7a4a}
    .o{stroke:#1a1a1a;stroke-width:1.6;fill:none}
    .of{stroke:#1a1a1a;stroke-width:1.6;fill:#f2f2f2}
    .ofd{stroke:#1a1a1a;stroke-width:1.6;fill:#d9d9d9}
    .mir{stroke:#1a1a1a;stroke-width:1.8;fill:#e8eef4}
    .thick{stroke:#1a1a1a;stroke-width:3;fill:none}
    .post{stroke:#1a1a1a;stroke-width:1.4;fill:#bdbdbd}
    .thin{stroke:#333;stroke-width:1;fill:none}
    .hid{stroke:#444;stroke-width:1.1;fill:none;stroke-dasharray:6 4}
    .ctr{stroke:#666;stroke-width:0.9;fill:none;stroke-dasharray:14 3 3 3}
    .ex{stroke:#555;stroke-width:0.8;fill:none}
    .dim{stroke:#222;stroke-width:0.9;fill:none;marker-start:url(#da);marker-end:url(#da)}
    .ld{stroke:#333;stroke-width:0.9;fill:none}
    .fl{stroke:#222;stroke-width:1.5;fill:none}
    .fld{stroke:#222;stroke-width:1.5;fill:none;stroke-dasharray:7 4}
    .sl{fill:#c0392b;fill-opacity:0.12;stroke:#c0392b;stroke-width:1;stroke-dasharray:5 3}
    .tof{fill:#1f5fa8;fill-opacity:0.09;stroke:#1f5fa8;stroke-width:1;stroke-dasharray:5 3}
    .hum{stroke:#777;stroke-width:1.2;fill:none;stroke-dasharray:3 3}
    .cont{stroke:#1f5fa8;stroke-width:1.6;fill:none;stroke-dasharray:5 3}
    .palm{stroke:#1f5fa8;stroke-width:1.6;fill:#1f5fa8;fill-opacity:0.10}
    .gel{stroke:#1a7a4a;stroke-width:1.4;fill:#1a7a4a;fill-opacity:0.22}
    .rim{stroke:#1a1a1a;stroke-width:1.2;fill:#9e9e9e}
    .mem{stroke:#6a3d9a;stroke-width:2.2;fill:none}
    .skin{stroke:#8a5a44;stroke-width:1.4;fill:#f3d9c9}
    .ac{stroke:#c0392b;stroke-width:1.6;fill:none;marker-end:url(#fr)}
    .acd{stroke:#1f5fa8;stroke-width:1.4;fill:none;stroke-dasharray:5 3;marker-end:url(#fb)}
    .frame{stroke:#111;stroke-width:2;fill:none}
    .blk{stroke:#1a1a1a;stroke-width:1.5;fill:#fafafa}
    .blkg{stroke:#1a1a1a;stroke-width:1.5;fill:#eef3ee}
    .blkb{stroke:#1a1a1a;stroke-width:1.5;fill:#eaf0f8}
    .blkd{stroke:#555;stroke-width:1.4;fill:#fafafa;stroke-dasharray:6 4}
    .note{stroke:#b35900;stroke-width:1.5;fill:#fff8ef}
    .grp{stroke:#555;stroke-width:1;fill:none;stroke-dasharray:6 4}
  </style>
</defs>
"""


def sheet(num, title, body):
    s = S()
    s.add(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fff"/>')
    s.rect(15, 15, W - 30, H - 30, "frame")
    s.rect(25, 25, W - 50, H - 50, "thin")
    s.text(45, 60, f"Sheet {num}. {title}", "h")
    s.text(45, 82, "LYRA concept (v3: touch mirror + three camera pillars). "
                   "Concept, not a manufacturing drawing; dimensions approximate, in mm.", "s")
    # title block
    x0, y0, x1, y1 = 985, 838, W - 25, H - 25
    s.add(f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="#fff" stroke="#111" stroke-width="1.6"/>')
    for dy in (34, 60, 86, 107):
        s.line(x0, y0 + dy, x1, y0 + dy, "thin")
    s.line(x0 + 100, y0, x0 + 100, y0 + 34, "thin")
    s.line(x0 + 250, y0 + 60, x0 + 250, y0 + 86, "thin")
    s.text(x0 + 50, y0 + 25, "LYRA", "h", "middle")
    s.text(x0 + 110, y0 + 22, title, "b")
    s.text(x0 + 10, y0 + 52, "Concept, NASA Space Apps 2026", "t")
    s.text(x1 - 10, y0 + 52, "AI (SI) assisted drawing", "ai", "end")
    s.text(x0 + 10, y0 + 78, "Scale: NTS   Units: mm", "t")
    s.text(x0 + 260, y0 + 78, f"Sheet {num}/{NSHEETS}", "b")
    s.text(x0 + 10, y0 + 101, "Concept, not a manufacturing drawing; dimensions approximate", "s")
    s.text(x0 + 10, y1 - 6, "Screening aid, not a diagnosis. No medical claims.", "s")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">\n'
            f'<title>LYRA sheet {num}: {esc(title)}</title>\n{STYLE}\n{s.out()}\n{body}\n</svg>\n')


# ------------------------------------------------------------------ geometry (mm)
# x: lateral (crew right = +x), d: depth from mirror plane (crew stands at d ~ 600,
# facing the mirror, i.e. toward -d), z: height above floor.
# v3 layout: free-standing touch mirror on its own stand + three camera pillars
# (two front pillars at +/-60 deg from the facing direction, one back pillar),
# each on a base plate bolted to the floor. No ceiling attachment.
MIR_X = 350          # mirror half width (approx. 700 wide)
MIR_Z = (100, 1900)  # mirror bottom / top
MS_X = 390           # mirror stand legs at x = +/-390, d = -20
MS_TOP = 2000        # mirror stand height
CREW_D = 600
PIL_R = 750          # pillar distance from the crew member
PILLARS = [          # (name, x, d)
    ("FL", -650, 225),
    ("FR", 650, 225),
    ("B", 0, CREW_D + PIL_R),
]
PIL_TOP = 2000       # pillar height (free-standing)
PIL_W = 80           # pillar cross-section
CAM_Z = ((1650, "H"), (1150, "T"), (500, "L"))
FOOT = 200           # base foot length (tripod)
AREA = (-400, 400, 350, 850)  # marked area x0, x1, d0, d1
GRIP_Z = (950, 1250)


def base_feet(px, d):
    """Tripod base: three feet, one pointing away from the crew member."""
    a0 = math.atan2(d - CREW_D, px)
    return [(px + FOOT * math.cos(a0 + i * 2 * math.pi / 3),
             d + FOOT * math.sin(a0 + i * 2 * math.pi / 3)) for i in range(3)]


# ------------------------------------------------------------------ sheet 1
def sheet1():
    s = S()
    # ---------- plan
    s.text(50, 120, "Top view (plan)", "vh")
    k = 0.2
    cx, y0 = 235, 225
    X = lambda mm: cx + mm * k
    Y = lambda d: y0 + d * k
    # FOV wedges from every pillar toward the crew member
    for _, px, d in PILLARS:
        ang = math.atan2(CREW_D - d, -px)
        far = PIL_R + 320
        hw = math.radians(28)
        p1 = (px + far * math.cos(ang - hw), d + far * math.sin(ang - hw))
        p2 = (px + far * math.cos(ang + hw), d + far * math.sin(ang + hw))
        s.poly([(X(px), Y(d)), (X(p1[0]), Y(p1[1])), (X(p2[0]), Y(p2[1]))], "tof")
    # face channel (mirror face module)
    s.poly([(X(0), Y(10)), (X(-110), Y(CREW_D - 40)), (X(110), Y(CREW_D - 40))], "sl")
    # marked area + feet
    s.rect(X(AREA[0]), Y(AREA[2]), (AREA[1] - AREA[0]) * k, (AREA[3] - AREA[2]) * k, "hid")
    for fx in (-110, 110):
        s.rect(X(fx) - 10, Y(CREW_D) - 22, 20, 44, "thin", rx=8)
    # crew (top: shoulders + head)
    s.ellipse(X(0), Y(CREW_D + 20), 225 * k, 115 * k, "hum")
    s.circle(X(0), Y(CREW_D - 10), 85 * k, "hum")
    # mirror stand + mirror
    for sg in (-1, 1):
        s.rect(X(sg * (MS_X + 60)) - 8, Y(-20) - 14, 16, 28, "thin", rx=3)   # base plate
        s.rect(X(sg * MS_X) - 4, Y(-20) - 4, 8, 8, "post")
    s.rect(X(-MIR_X), Y(-10), 2 * MIR_X * k, 30 * k, "mir")
    # vertical grips on the mirror stand legs
    for sg in (-1, 1):
        s.line(X(sg * MS_X), Y(-20), X(sg * 400), Y(70), "thin")
        s.circle(X(sg * 400), Y(70), 4.5, "ofd")
    # pillars with tripod bases
    for _, px, d in PILLARS:
        for fx, fd in base_feet(px, d):
            s.line(X(px), Y(d), X(fx), Y(fd), "o")
            s.circle(X(fx), Y(fd), 4, "of")
        s.rect(X(px) - PIL_W * k / 2, Y(d) - PIL_W * k / 2, PIL_W * k, PIL_W * k, "post")
    # radius circle (pillars on one circle around the crew member)
    s.circle(X(0), Y(CREW_D), PIL_R * k, "ctr")
    # dims
    xl, xr = PILLARS[0][1], PILLARS[1][1]
    yb = Y(PILLARS[2][2] + FOOT) + 22
    s.ext(X(xl), Y(225) + 8, X(xl), yb + 8); s.ext(X(xr), Y(225) + 8, X(xr), yb + 8)
    s.dim(X(xl), yb, X(xr), yb, "approx. 1300")
    xd = X(xl - FOOT) - 22
    s.ext(X(-MIR_X) - 4, Y(0), xd - 8, Y(0)); s.ext(X(-200), Y(PILLARS[2][2]), xd - 8, Y(PILLARS[2][2]))
    s.dim(xd, Y(0), xd, Y(PILLARS[2][2]), "approx. 1350", off=-2)
    s.ext(X(-200), Y(CREW_D), xd + 26 - 8, Y(CREW_D))
    s.dim(xd + 26, Y(0), xd + 26, Y(CREW_D), "approx. 600", off=-2)
    s.ext(X(-MIR_X), Y(-12), X(-MIR_X), Y(-75)); s.ext(X(MIR_X), Y(-12), X(MIR_X), Y(-75))
    s.dim(X(-MIR_X), Y(-65), X(MIR_X), Y(-65), "mirror approx. 700")
    # radius label
    s.leader(X(PIL_R * math.cos(math.radians(-20))), Y(CREW_D + PIL_R * math.sin(math.radians(-20))),
             X(780), Y(520), "start", ["pillars on R approx. 750,", "120 deg apart"])
    # leaders (plan)
    s.leader(X(250), Y(5), X(800), Y(-110), "start", ["touch mirror"])
    s.leader(X(MS_X), Y(-20), X(800), Y(-40), "start", ["mirror stand"])
    s.leader(X(400), Y(70), X(800), Y(60), "start", ["vertical Doppler grip", "(optional, research)"])
    s.leader(X(650), Y(225), X(800), Y(250), "start", ["front pillar R"])
    s.leader(X(0) + 6, Y(PILLARS[2][2]), X(780), Y(1300), "start", ["back pillar"])
    s.leader(X(110), Y(CREW_D + 20), X(780), Y(1000), "start", ["foot restraints"])
    # notes under plan
    ny = 610
    s.mtext(50, ny, [
        "The crew member (dashed) steps into the marked area (dashed rectangle,",
        "approx. 800 x 500) and faces the touch mirror.",
        "Three free-standing camera pillars stand on one circle around the crew",
        "member: two in front at +/-60 deg, one behind. Blue wedges = camera views;",
        "red wedge = face channel of the mirror face module.",
        "Each pillar base plate bolts to the floor (e.g. seat-track rails): in",
        "microgravity a weighted base holds nothing. No ceiling attachment.",
        "Cameras check pose and frame quality before any capture.",
        "Optional contact research module: vertical grips on the mirror stand legs",
        "(see sheets 2 and 3). Not part of the contactless core.",
    ], "s", "start", 15)

    # ---------- mirror face elevation
    s.text(520, 120, "Touch mirror, face view", "vh")
    km = 0.25
    mx0, mfloor = 530, 720
    MX = lambda x: mx0 + (x + MIR_X) * km
    MZ = lambda z: mfloor - z * km
    s.line(MX(-MIR_X) - 15, MZ(0), MX(MIR_X) + 15, MZ(0), "thick")
    s.rect(MX(-MIR_X) - 15, MZ(0), 2 * MIR_X * km + 30, 8, extra='fill="url(#hatch)" stroke="none"')
    s.rect(MX(-MIR_X), MZ(MIR_Z[1]), 2 * MIR_X * km, (MIR_Z[1] - MIR_Z[0]) * km, "mir")
    # status strip
    s.rect(MX(-260), MZ(1860), 520 * km, 70 * km, "thin")
    s.text(MX(0), MZ(1860) + 14, "prompts / status", "xs", "middle")
    # face module in the top bezel
    s.rect(MX(-90), MZ(1960), 180 * km, 50 * km, "ofd")
    # head guide
    s.ellipse(MX(0), MZ(1640), 90 * km, 115 * km, "cont")
    # torso contour
    s.path(f"M{MX(-210)},{MZ(1460)} Q{MX(0)},{MZ(1520)} {MX(210)},{MZ(1460)} "
           f"L{MX(170)},{MZ(1000)} L{MX(190)},{MZ(880)} L{MX(-190)},{MZ(880)} L{MX(-170)},{MZ(1000)} Z", "cont")
    # palm zones
    for sg in (-1, 1):
        px, pz = sg * 275, 1150
        s.ellipse(MX(px), MZ(pz), 55 * km, 85 * km, "palm")
        for f in range(4):
            fx = px + sg * (-30 + f * 20)
            s.line(MX(fx), MZ(pz + 70), MX(fx), MZ(pz + 125), "cont")
    # foot contours
    for fx in (-110, 110):
        s.path(f"M{MX(fx-45)},{MZ(150)} Q{MX(fx-50)},{MZ(400)} {MX(fx)},{MZ(420)} "
               f"Q{MX(fx+50)},{MZ(400)} {MX(fx+45)},{MZ(150)} Z", "cont")
    # NFC reader on the mirror frame (right edge)
    s.rect(MX(MIR_X) - 64, MZ(800), 74, 24, "ofd", rx=3)
    s.text(MX(MIR_X) - 27, MZ(800) + 16, "NFC reader", "bs", "middle")
    s.ext(MX(-MIR_X), MZ(MIR_Z[0]) + 2, MX(-MIR_X), MZ(0) + 30); s.ext(MX(MIR_X), MZ(MIR_Z[0]) + 2, MX(MIR_X), MZ(0) + 30)
    s.dim(MX(-MIR_X), MZ(0) + 26, MX(MIR_X), MZ(0) + 26, "approx. 700", off=16)
    s.ext(MX(MIR_X) + 3, MZ(MIR_Z[1]), MX(MIR_X) + 22, MZ(MIR_Z[1]))
    s.ext(MX(MIR_X) + 3, MZ(MIR_Z[0]), MX(MIR_X) + 22, MZ(MIR_Z[0]))
    s.dim(MX(MIR_X) + 16, MZ(MIR_Z[1]), MX(MIR_X) + 16, MZ(MIR_Z[0]), "approx. 1800", off=16)
    ly = 790
    s.mtext(520, ly, [
        "Blue dashed: contours shown on the mirror",
        "(head guide, torso, feet). Shaded ovals:",
        "palm zones. They standardize the pose,",
        "they are not a medical sensor.",
        "Grey bar in top bezel: face module.",
        "NFC: NFC reader on the mirror frame",
        "(station, fallback ID when 3D face ID",
        "is not confident; card kept at station).",
    ], "s", "start", 14)

    # ---------- isometric
    s.text(730, 120, "Isometric view (from behind-left)", "vh")
    k2 = 0.165
    ox, oy = 935, 590
    c30 = math.cos(math.radians(30))
    def P(x, d, z):
        return (ox + (x + d) * c30 * k2, oy + (d - x) * 0.5 * k2 - z * k2)
    def L(a, b, cls="o", extra=""):
        s.line(*P(*a), *P(*b), cls, extra)
    def post(x, d, z0=0, z1=PIL_TOP, w=6, col="#1a1a1a"):
        a, b = P(x, d, z0), P(x, d, z1)
        s.add(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{col}" stroke-width="{w}"/>')
    def cam(x, d, z):
        m = P(x, d, z)
        s.rect(m[0] - 5, m[1] - 7, 10, 14, "of")
        s.circle(m[0], m[1] - 2, 1.8, "o", extra='fill="#111" stroke="none"')
    def pillar(px, d):
        for fx, fd in base_feet(px, d):
            L((px, d, 0), (fx, fd, 0), "thick")
            c = P(fx, fd, 0)
            s.ellipse(c[0], c[1], 5, 3, "of")
        post(px, d)
        top = P(px, d, PIL_TOP)
        s.rect(top[0] - 4, top[1] - 3, 8, 3, "ofd")
        for z, _ in CAM_Z:
            cam(px, d, z)
    # floor outline
    s.poly([P(-850, -250, 0), P(850, -250, 0), P(850, 1550, 0), P(-850, 1550, 0)], "thin", extra='stroke-dasharray="1 4"')
    s.poly([P(AREA[0], AREA[2], 0), P(AREA[1], AREA[2], 0), P(AREA[1], AREA[3], 0), P(AREA[0], AREA[3], 0)], "hid")
    # cables along the floor to the compute unit (behind the mirror)
    for _, px, d in PILLARS:
        s.path("M{:.1f},{:.1f} Q{:.1f},{:.1f} {:.1f},{:.1f}".format(
            *P(px, d, 0), *P(px * 0.5 + 100, (d - 150) * 0.5, 0), *P(150, -150, 0)),
            "thin", extra='stroke="#777"')
    cu = P(150, -150, 0)
    s.rect(cu[0] - 9, cu[1] - 14, 18, 14, "ofd", rx=2)
    # front pillars first (farther from the viewer)
    pillar(650, 225)
    # mirror stand + mirror
    for sg in (-1, 1):
        L((sg * MS_X - 120, -20, 0), (sg * MS_X + 120, -20, 0), "thick")
        post(sg * MS_X, -20, 0, MS_TOP, w=4)
    s.poly([P(-MIR_X, 0, MIR_Z[0]), P(MIR_X, 0, MIR_Z[0]), P(MIR_X, 0, MIR_Z[1]), P(-MIR_X, 0, MIR_Z[1])], "mir")
    s.poly([P(-90, 0, 1910), P(90, 0, 1910), P(90, 0, 1960), P(-90, 0, 1960)], "ofd")
    # grips (vertical) on the mirror stand legs
    for sg in (-1, 1):
        a, b = P(sg * 400, 70, GRIP_Z[0]), P(sg * 400, 70, GRIP_Z[1])
        s.add(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#555" stroke-width="7" stroke-linecap="round"/>')
        L((sg * MS_X, -20, GRIP_Z[0] + 20), (sg * 400, 70, GRIP_Z[0] + 20), "thin")
        L((sg * MS_X, -20, GRIP_Z[1] - 20), (sg * 400, 70, GRIP_Z[1] - 20), "thin")
    pillar(-650, 225)
    # crew (dashed figure)
    hd = CREW_D
    L((0, hd, 900), (0, hd, 1450), "hum")
    L((-200, hd, 1430), (200, hd, 1430), "hum")
    L((-200, hd, 1430), (-300, hd, 1050), "hum")
    L((200, hd, 1430), (300, hd, 1050), "hum")
    L((-100, hd, 950), (-110, hd, 60), "hum")
    L((100, hd, 950), (110, hd, 60), "hum")
    L((-110, hd, 950), (110, hd, 950), "hum")
    hcx, hcy = P(0, hd, 1620)
    s.circle(hcx, hcy, 95 * k2, "hum")
    for fx in (-110, 110):
        s.poly([P(fx - 50, hd - 110, 0), P(fx + 50, hd - 110, 0), P(fx + 50, hd + 110, 0), P(fx - 50, hd + 110, 0)], "thin")
    # back pillar (nearest to the viewer)
    pillar(0, PILLARS[2][2])
    # labels (iso)
    def lab(pt3, tx, ty, lines, anchor="start"):
        x, y = P(*pt3)
        s.leader(x, y, tx, ty, anchor, lines)
    LX, RX = 836, 1262
    lab((-90, 0, 1935), LX, 190, ["face module", "(RGB + IR camera", "+ IR projector)"], "end")
    lab((-MIR_X, 0, 1500), LX, 265, ["touch mirror"], "end")
    lab((-650, 225, 1650), LX, 330, ["front pillar L", "camera module H"], "end")
    lab((-400, 70, 1100), LX, 420, ["vertical Doppler", "grip (optional,", "research)"], "end")
    lab((-MS_X - 100, -20, 0), LX, 520, ["mirror stand base"], "end")
    lab((AREA[0], AREA[2], 0), LX, 600, ["marked area"], "end")
    lab((-110, hd - 60, 0), LX, 660, ["foot restraints"], "end")
    lab((650, 225, 1150), RX, 200, ["front pillar R", "camera module T"], "start")
    lab((0, PILLARS[2][2], 1650), RX, 300, ["back pillar", "(H / T / L modules)"], "start")
    lab((0, hd, 1300), RX, 420, ["crew member"], "start")
    fx, fd = base_feet(0, PILLARS[2][2])[0]
    lab((fx, fd, 0), RX, 640, ["pillar base, bolted", "to the floor"], "start")
    s.text(730, 815, "Pillars approx. 2000 high, no ceiling mount; camera modules at head, torso, leg height; cables run to the compute unit.", "s")
    return sheet(1, "General view", s.out())


# ------------------------------------------------------------------ sheet 2
def sheet2():
    s = S()
    k = 0.28
    floor = 790
    Z = lambda z: floor - z * k

    def slab(xa, xb):
        s.line(xa, Z(0), xb, Z(0), "thick")
        s.rect(xa, Z(0), xb - xa, 8, extra='fill="url(#hatch)" stroke="none"')

    def pillar_el(xc, cls="post", labels=True, hidden=False):
        """Pillar in elevation: post, camera modules, base with bolts."""
        w = PIL_W * k
        if hidden:
            s.rect(xc - w / 2, Z(PIL_TOP), w, PIL_TOP * k, "hid")
        else:
            s.rect(xc - w / 2, Z(PIL_TOP), w, PIL_TOP * k, cls)
            s.rect(xc - FOOT * k, Z(0) - 6, 2 * FOOT * k, 6, "ofd")
            for bx in (xc - FOOT * k + 5, xc + FOOT * k - 5):
                s.line(bx, Z(0) - 9, bx, Z(0) + 3, "o")
        if labels:
            for z, nm in CAM_Z:
                s.rect(xc - 10, Z(z) - 13, 20, 26, "hid" if hidden else "of")
                s.text(xc, Z(z) + 4, nm, "xs", "middle")

    # ---------------- front elevation (looking at the mirror face from behind the crew)
    cx = 340
    X = lambda x: cx + x * k
    s.text(50, 120, "Front elevation (looking at the mirror face)", "vh")
    slab(X(-850), X(850))
    s.text(X(-850), Z(0) + 22, "floor", "s")
    # FOV from the two front pillars toward the crew member
    for sg in (-1, 1):
        for z, za, zb in ((1650, 1880, 1350), (1150, 1500, 800), (500, 1000, 0)):
            s.poly([(X(sg * 650), Z(z)), (X(sg * 170), Z(za)), (X(sg * 170), Z(zb))], "tof")
    # mirror stand + mirror
    for sg in (-1, 1):
        s.rect(X(sg * MS_X) - 25 * k, Z(MS_TOP), 50 * k, MS_TOP * k, "post")
        s.rect(X(sg * MS_X) - 120 * k, Z(0) - 6, 240 * k, 6, "ofd")
    s.rect(X(-MIR_X), Z(MIR_Z[1]), 2 * MIR_X * k, (MIR_Z[1] - MIR_Z[0]) * k, "mir")
    s.rect(X(-90), Z(1960), 180 * k, 50 * k, "ofd")
    # vertical grips on the mirror stand legs
    for sg in (-1, 1):
        gx = X(sg * 420)
        s.line(X(sg * MS_X), Z(GRIP_Z[0] + 20), gx, Z(GRIP_Z[0] + 20), "thin")
        s.line(X(sg * MS_X), Z(GRIP_Z[1] - 20), gx, Z(GRIP_Z[1] - 20), "thin")
        s.rect(gx - 6, Z(GRIP_Z[1]), 12, (GRIP_Z[1] - GRIP_Z[0]) * k, "ofd", rx=5)
    # front pillars
    for sg in (-1, 1):
        pillar_el(X(sg * 650))
    # back pillar (between viewer and crew member): hidden outline
    pillar_el(X(0), hidden=True)
    # crew (dashed, in front of mirror)
    s.circle(X(0), Z(1630), 95 * k, "hum")
    s.path(f"M{X(-200)},{Z(1440)} L{X(200)},{Z(1440)} L{X(150)},{Z(950)} L{X(-150)},{Z(950)} Z", "hum")
    s.path(f"M{X(-110)},{Z(950)} L{X(-120)},{Z(60)} M{X(110)},{Z(950)} L{X(120)},{Z(60)}", "hum")
    s.path(f"M{X(-200)},{Z(1440)} L{X(-330)},{Z(1150)} M{X(200)},{Z(1440)} L{X(330)},{Z(1150)}", "hum")
    for fx in (-120, 120):
        s.rect(X(fx) - 12, Z(70), 24, 70 * k, "thin")
    # dims front
    s.ext(X(-650), Z(0) + 10, X(-650), Z(0) + 38); s.ext(X(650), Z(0) + 10, X(650), Z(0) + 38)
    s.dim(X(-650), Z(0) + 32, X(650), Z(0) + 32, "approx. 1300 between front pillars")
    s.ext(X(650) + 14, Z(PIL_TOP), X(650) + 60, Z(PIL_TOP))
    s.dim(X(650) + 50, Z(PIL_TOP), X(650) + 50, Z(0), "approx. 2000", off=16)
    s.ext(X(-420) - 8, Z(GRIP_Z[0]), X(-420) - 40, Z(GRIP_Z[0]))
    s.dim(X(-420) - 32, Z(GRIP_Z[0]), X(-420) - 32, Z(0), "approx. 950", off=-2)
    # labels front (left margin)
    s.leader(X(-90), Z(1940), 120, 205, "end", ["face module:", "RGB + IR camera", "+ IR projector"])
    s.leader(X(-650) - 8, Z(1650), 120, 290, "end", ["front pillar L:", "camera module H", "(RGB + IR depth)"])
    s.leader(X(-420), Z(1150), 120, 420, "end", ["VERTICAL grip", "(Doppler)"])
    s.text(30, 462, "Optional research", "bs"); s.text(30, 475, "module (contact)", "bs")
    s.leader(X(-MIR_X) + 4, Z(700), 120, 560, "end", ["touch mirror"])
    s.leader(X(-650) - 50, Z(0) - 3, 120, 700, "end", ["pillar base,", "bolted to floor"])
    s.leader(X(-120), Z(30), 120, 760, "end", ["foot restraints"])
    s.leader(X(0) + 12, Z(1950), X(130), 165, "start", ["back pillar (behind the", "viewer, dashed)"])

    # ---------------- side elevation (from +x, mirror on the left)
    x0 = 820
    D = lambda d: x0 + d * k
    s.text(760, 120, "Side elevation: camera fields of view", "vh")
    BD = PILLARS[2][2]
    slab(D(-180), D(1580))
    # FOV cones (under objects)
    s.poly([(D(20), Z(1935)), (D(CREW_D - 60), Z(1820)), (D(CREW_D - 60), Z(1480))], "sl")
    for z, za, zb in ((1650, 1850, 1400), (1150, 1500, 800), (500, 900, 0)):
        s.poly([(D(225), Z(z)), (D(CREW_D - 40), Z(za)), (D(CREW_D - 40), Z(zb))], "tof")
        s.poly([(D(BD), Z(z)), (D(CREW_D + 70), Z(za + 50)), (D(CREW_D + 70), Z(max(zb - 50, 0)))], "tof")
    # mirror stand + mirror
    s.rect(D(-20) - 25 * k, Z(MS_TOP), 50 * k, MS_TOP * k, "post")
    s.rect(D(-20) - 120 * k, Z(0) - 6, 240 * k, 6, "ofd")
    s.rect(D(0), Z(MIR_Z[1]), 30 * k, (MIR_Z[1] - MIR_Z[0]) * k, "mir")
    s.rect(D(0), Z(1960), 45 * k, 50 * k, "ofd")
    # grip (vertical, near the stand leg)
    s.line(D(-20), Z(GRIP_Z[0] + 20), D(70), Z(GRIP_Z[0] + 20), "thin")
    s.line(D(-20), Z(GRIP_Z[1] - 20), D(70), Z(GRIP_Z[1] - 20), "thin")
    s.rect(D(70) - 6, Z(GRIP_Z[1]), 12, (GRIP_Z[1] - GRIP_Z[0]) * k, "ofd", rx=5)
    s.line(D(70), Z(GRIP_Z[1]) - 14, D(70), Z(GRIP_Z[0]) + 14, "ctr")
    # front pillar R (nearest to the viewer; L is behind it) and back pillar
    pillar_el(D(225))
    pillar_el(D(BD))
    # crew facing mirror (left)
    s.circle(D(CREW_D), Z(1630), 95 * k, "hum")
    s.path(f"M{D(CREW_D-40)},{Z(1450)} L{D(CREW_D-20)},{Z(950)} M{D(CREW_D+50)},{Z(1450)} L{D(CREW_D+50)},{Z(950)}", "hum")
    s.path(f"M{D(CREW_D-20)},{Z(950)} L{D(CREW_D-30)},{Z(60)} M{D(CREW_D+50)},{Z(950)} L{D(CREW_D+30)},{Z(60)}", "hum")
    s.path(f"M{D(CREW_D-20)},{Z(1430)} L{D(CREW_D-40)},{Z(1050)}", "hum")
    s.rect(D(CREW_D - 70), Z(70), 140 * k, 70 * k, "thin")
    # dims side
    for dd in (0, 225, CREW_D, BD):
        s.ext(D(dd), Z(0) + 10, D(dd), Z(0) + 38)
    s.dim(D(0), Z(0) + 32, D(225), Z(0) + 32, "225", off=-2)
    s.dim(D(225), Z(0) + 32, D(CREW_D), Z(0) + 32, "375")
    s.dim(D(CREW_D), Z(0) + 32, D(BD), Z(0) + 32, "approx. 750")
    s.ext(D(BD) + 14, Z(PIL_TOP), D(BD) + 60, Z(PIL_TOP))
    s.dim(D(BD) + 50, Z(PIL_TOP), D(BD) + 50, Z(0), "approx. 2000", off=16)
    # labels side
    s.leader(D(300), Z(1800), 1250, 150, "start", ["face: RGB + IR", "camera, IR pattern"])
    s.leader(D(BD) + 10, Z(1650), 1250, 230, "start", ["back pillar H"])
    s.leader(D(BD) + 10, Z(1150), 1250, 350, "start", ["back pillar T", "(scapulae, spine)"])
    s.leader(D(BD) + 10, Z(500), 1250, 600, "start", ["back pillar L", "(pelvis, legs)"])
    s.leader(D(225) + 10, Z(1650), D(225) + 40, 170, "start", ["front pillar R", "(L hidden behind)"])
    s.leader(D(70) + 6, Z(1050), D(225) + 22, 560, "start", ["vertical grip,", "axis vertical", "(dash-dot)"])
    # legend
    ly = 870
    s.poly([(50, ly - 10), (78, ly - 2), (50, ly + 6)], "sl")
    s.text(86, ly, "Face channel: IR projector pattern + IR camera + RGB camera (mirror top bezel, head height)", "s")
    s.poly([(50, ly + 10), (78, ly + 18), (50, ly + 26)], "tof")
    s.text(86, ly + 20, "Body cameras: RGB + IR depth modules on 3 synced pillars; skeleton keypoints merged in one", "s")
    s.text(86, ly + 34, "coordinate system (sensor choice to verify on a prototype).", "s")
    s.text(50, ly + 56, "H / T / L = camera module at head / torso / leg height. Grips: optional research module (contact), "
                        "not part of the contactless core.", "s")
    s.text(50, ly + 72, "Front pillars: face, chest, arms, shoulder and pelvis symmetry, head and trunk tilt. Back pillar: scapulae, spine.", "s")
    return sheet(2, "Front and side views", s.out())

# ------------------------------------------------------------------ sheet 3
def sheet3():
    s = S()
    s.text(50, 120, "Section A-A through the vertical grip (scale enlarged, schematic)", "vh")
    # --- post and grip body
    s.rect(70, 150, 40, 640, extra='fill="url(#hatch)" stroke="#1a1a1a" stroke-width="1.4"')
    s.text(90, 808, "mirror stand", "s", "middle")
    s.text(90, 822, "leg", "s", "middle")
    # brackets
    s.rect(110, 200, 70, 22, "post"); s.rect(110, 718, 70, 22, "post")
    # grip shell (vertical)
    gx0, gx1, gy0, gy1 = 180, 300, 170, 770
    s.rect(gx0, gy0, gx1 - gx0, gy1 - gy0, "of", rx=40)
    s.line((gx0 + gx1) / 2, gy0 - 25, (gx0 + gx1) / 2, gy1 + 25, "ctr")
    s.text((gx0 + gx1) / 2, gy0 - 30, "grip axis (vertical)", "s", "middle")
    # transducer
    tx0, tx1, ty0, ty1 = 232, 300, 360, 580
    s.rect(tx0, ty0, tx1 - tx0, ty1 - ty0, "ofd")
    s.rect(tx0 + 10, ty0 + 20, 30, ty1 - ty0 - 40, extra='fill="url(#hatch2)" stroke="#1a1a1a" stroke-width="1"')
    s.line(tx1, ty0 + 10, tx1, ty1 - 10, "thick")  # active face
    # cable
    s.path(f"M{tx0+40},{ty1} L{tx0+40},{gy1-25}", "thin")
    # (1) holder: C-clip fixed on transducer body
    hx = tx1
    s.path(f"M{tx0+30},{ty0-12} L{hx+14},{ty0-12} L{hx+14},{ty0+12} L{hx+4},{ty0+12} "
           f"L{hx+4},{ty1-12} L{hx+14},{ty1-12} L{hx+14},{ty1+12} L{tx0+30},{ty1+12}", "o",
           extra='fill="#c8c8c8" fill-opacity="0.6"')
    # (2) thin hydrogel pad
    px0, px1 = hx + 4, hx + 30
    s.rect(px0, ty0 + 14, px1 - px0, ty1 - ty0 - 28, "gel")
    # (3) soft rim
    s.rect(hx + 14, ty0 - 4, 20, 16, "rim", rx=4)
    s.rect(hx + 14, ty1 - 12, 20, 16, "rim", rx=4)
    # (4) membrane
    s.path(f"M{px1+3},{ty0-6} L{px1+3},{ty1+6}", "mem")
    # skin / palm
    sx = px1 + 5
    s.path(f"M{sx},{ty0-60} L{sx},{ty1+60} Q{sx+60},{ty1+150} {sx+150},{ty1+120} "
           f"L{sx+170},{ty0-90} Q{sx+80},{ty0-140} {sx},{ty0-60} Z", "skin")
    s.text(sx + 95, ty0 + 200, "palm (hand wraps", "s", "middle")
    s.text(sx + 95, ty0 + 214, "the grip)", "s", "middle")
    # acoustic path
    for yy in (430, 470, 510):
        s.line(tx1 + 2, yy, sx + 70, yy, "ac")
    for yy in (450, 490):
        s.line(sx + 66, yy, tx1 + 4, yy, "acd")
    s.text(sx + 95, 618, "pulses out (red)", "rt", "middle")
    s.text(sx + 95, 632, "echo back (blue)", "bt", "middle")
    # no air gap callout
    s.rect(330, 665, 175, 40, "note", rx=4)
    s.text(417, 682, "NO AIR GAP in the", "bs", "middle")
    s.text(417, 697, "acoustic path", "bs", "middle")
    s.line(345, 665, px1 - 6, ty1 - 30, "ld")
    # numbered leaders 1-4
    def num(x, y, n):
        s.circle(x, y, 9, "blk")
        s.text(x, y + 4, str(n), "bs", "middle")
    s.leader(tx0 + 40, ty0 - 12, 330, 205, "start", [])
    num(345, 205, 1)
    s.leader(px0 + 12, ty0 + 40, 480, 290, "start", []); num(495, 290, 2)
    s.leader(hx + 30, ty0 - 2, 420, 245, "start", []); num(435, 245, 3)
    s.leader(px1 + 3, ty0 + 20, 540, 330, "start", []); num(555, 330, 4)
    s.leader(tx0 + 20, ty1 - 10, 318, 738, "start", ["transducer (face toward the palm)"])
    s.leader(tx1 - 1, ty1 - 30, 318, 762, "start", ["active face (vertical, toward the palm)"])
    s.mtext(510, 160, ["1 holder, fixed on transducer body",
                       "2 thin replaceable hydrogel pad",
                       "   (thickness TBD by ground test)",
                       "3 soft protective rim (limits gel",
                       "   displacement)",
                       "4 thin membrane (contamination",
                       "   barrier, keeps skin contact)"], "s", "start", 14)
    s.text(50, 862, "Solid hydrogel cassette = parts 1 to 4. Pad thickness and press force: to be determined experimentally on a ground mock-up.", "s")
    s.text(50, 878, "Earlier tape-cassette / liquid-gel handle idea: archived (docs/drawings/archive/v1).", "s")

    # --- right column: workflow, versions, note
    rx = 790
    s.rect(rx, 140, 580, 330, "blk", rx=4)
    s.text(rx + 12, 162, "Workflow (8 steps)", "b")
    steps = [
        "Insert the hydrogel pad into the holder on the transducer face.",
        "Check the pad for bubbles or damage.",
        "Place the palm on the marked zone of the grip.",
        "The cassette is gently pressed to the skin (it is not a standalone sensor).",
        "The transducer sends pulses through the hydrogel.",
        "The receiver registers the echo.",
        "Software checks contact quality and signal stability.",
        "If quality is poor: ask to reposition the hand or repeat.",
    ]
    for i, st in enumerate(steps):
        yy = 192 + i * 34
        s.circle(rx + 24, yy - 4, 10, "blk")
        s.text(rx + 24, yy, str(i + 1), "bs", "middle")
        s.text(rx + 44, yy, st, "t")
    # versions
    s.rect(rx, 490, 283, 170, "blkb", rx=4)
    s.text(rx + 12, 512, "DEMO version (hackathon)", "b")
    s.mtext(rx + 12, 534, ["Mock cassette on the grip.",
                           "On-screen diagram of the",
                           "signal path (no real",
                           "ultrasound measurement)."], "t", "start", 18)
    s.rect(rx + 297, 490, 283, 170, "blkg", rx=4)
    s.text(rx + 309, 512, "EXTENDED version", "b")
    s.mtext(rx + 309, 534, ["Real transducer only after a",
                            "phantom / ground test-bench",
                            "check of coupling and signal",
                            "stability."], "t", "start", 18)
    # honest note
    s.rect(rx, 678, 580, 140, "note", rx=4)
    s.text(rx + 12, 700, "Honest scope", "b")
    s.mtext(rx + 12, 722, [
        "Research module, not part of the contactless core.",
        "The acoustic coupling principle is published; efficiency for this",
        "transducer and palm contact must be verified on a phantom /",
        "ground test bench.",
        "Does not assess heart, veins or cardiovascular risk.",
    ], "t", "start", 18)
    return sheet(3, "Doppler grip and hydrogel cassette", s.out())


# ------------------------------------------------------------------ sheet 4
def sheet4():
    s = S()
    s.text(50, 120, "IR / depth channel (face)", "vh")
    bw, bh, gap, y0 = 168, 222, 22, 136
    xs = [50 + i * (bw + gap) for i in range(7)]
    titles = [("IR projector", ["invisible dot /", "stripe pattern"]),
              ("IR camera", ["pattern deformed", "by the face"]),
              ("Correspondence", ["projector pattern", "vs image"]),
              ("Triangulation", ["calibrated", "camera + projector"]),
              ("Depth map", ["distance per", "pixel"]),
              ("Point cloud", ["3D points"]),
              ("Mesh", ["surface reconstruction:", "neighbours joined", "into triangles"])]
    for i, (t, ls) in enumerate(titles):
        x = xs[i]
        s.rect(x, y0, bw, bh, "blk", rx=4)
        s.text(x + bw / 2, y0 + 150, t, "b", "middle")
        s.mtext(x + bw / 2, y0 + 168, ls, "s", "middle", 14)
        if i < 6:
            s.arrow(x + bw + 2, y0 + 65, x + bw + gap - 2, y0 + 65)
    ic = lambda i: (xs[i] + bw / 2, y0 + 62)
    # 0 projector
    cx, cy = ic(0)
    s.rect(cx - 50, cy - 16, 36, 32, "ofd", rx=3)
    s.circle(cx - 14, cy, 6, "of")
    for a in (-0.5, -0.25, 0, 0.25, 0.5):
        s.line(cx - 8, cy, cx + 60, cy + 68 * math.tan(a), "thin", extra='stroke="#c0392b" stroke-dasharray="2 2"')
    for j in range(5):
        for q in range(3):
            s.circle(cx + 50 + q * 6, cy - 34 + j * 17, 1.4, "o", extra='fill="#c0392b" stroke="none"')
    # 1 IR camera: dots on a face outline, deformed
    cx, cy = ic(1)
    s.ellipse(cx, cy, 42, 54, "thin")
    for j in range(-4, 5):
        for q in range(-3, 4):
            px = cx + q * 11 + (3 * math.sin(j * 0.7) if abs(q) < 3 else 0)
            py = cy + j * 11 + 4 * math.exp(-(q * q) / 3) * (1 if j > 0 else -1) * 0.5
            if ((px - cx) / 42) ** 2 + ((py - cy) / 54) ** 2 < 1:
                s.circle(px, py, 1.6, "o", extra='fill="#c0392b" stroke="none"')
    # 2 correspondence
    cx, cy = ic(2)
    s.rect(cx - 70, cy - 40, 55, 80, "thin"); s.rect(cx + 15, cy - 40, 55, 80, "thin")
    s.text(cx - 42, cy + 54, "pattern", "xs", "middle"); s.text(cx + 42, cy + 54, "image", "xs", "middle")
    for (a, b) in ((-20, -24), (0, 4), (20, 22)):
        s.circle(cx - 42, cy + a, 2.5, "o", extra='fill="#c0392b" stroke="none"')
        s.circle(cx + 46, cy + b, 2.5, "o", extra='fill="#c0392b" stroke="none"')
        s.line(cx - 39, cy + a, cx + 43, cy + b, "thin", extra='stroke-dasharray="3 2"')
    # 3 triangulation
    cx, cy = ic(3)
    p1, p2, pt = (cx - 60, cy + 40), (cx + 60, cy + 40), (cx + 5, cy - 40)
    s.rect(p1[0] - 8, p1[1] - 6, 16, 12, "ofd"); s.rect(p2[0] - 8, p2[1] - 6, 16, 12, "ofd")
    s.line(*p1, *pt, "thin"); s.line(*p2, *pt, "thin"); s.line(p1[0], p1[1], p2[0], p2[1], "hid")
    s.circle(*pt, 3.5, "o", extra='fill="#111"')
    s.text(cx, cy + 58, "baseline", "xs", "middle")
    s.text(p1[0], p1[1] + 18, "proj.", "xs", "middle"); s.text(p2[0], p2[1] + 18, "cam.", "xs", "middle")
    # 4 depth map (grey levels)
    cx, cy = ic(4)
    for j in range(8):
        for q in range(8):
            dd = math.hypot((q - 3.5) / 3.5, (j - 3.5) / 4.2)
            g = int(70 + min(dd, 1.0) * 170)
            s.add(f'<rect x="{cx-48+q*12:.1f}" y="{cy-48+j*12:.1f}" width="12" height="12" fill="rgb({g},{g},{g})"/>')
    s.rect(cx - 48, cy - 48, 96, 96, "thin")
    s.text(cx, cy + 62, "dark = near", "xs", "middle")
    # 5 point cloud
    cx, cy = ic(5)
    import random
    rnd = random.Random(7)
    for _ in range(140):
        a = rnd.uniform(0, 2 * math.pi); r = math.sqrt(rnd.uniform(0, 1))
        px, py = cx + 40 * r * math.cos(a), cy + 52 * r * math.sin(a)
        s.circle(px, py, 1.3, "o", extra='fill="#1f5fa8" stroke="none"')
    # 6 mesh
    cx, cy = ic(6)
    pts = {}
    for j in range(-3, 4):
        for q in range(-3, 4):
            px, py = cx + q * 13 + (j % 2) * 6, cy + j * 15
            if ((px - cx) / 46) ** 2 + ((py - cy) / 56) ** 2 < 1:
                pts[(j, q)] = (px, py)
    for (j, q), p in pts.items():
        for nb in ((j, q + 1), (j + 1, q), (j + 1, q + (1 if j % 2 else -1))):
            if nb in pts:
                s.line(*p, *pts[nb], "thin", extra='stroke="#1f5fa8"')
    # library tags under boxes
    ly = y0 + bh + 26
    s.rect(xs[1], ly - 16, xs[4] + bw - xs[1], 26, "blkb", rx=4)
    s.text((xs[1] + xs[4] + bw) / 2, ly + 2, "OpenCV: calibration, pattern decoding, depth", "bs", "middle")
    s.rect(xs[5], ly - 16, xs[6] + bw - xs[5], 26, "blkg", rx=4)
    s.text((xs[5] + xs[6] + bw) / 2, ly + 2, "Open3D or PCL: point cloud, mesh", "bs", "middle")
    s.rect(xs[0], ly - 16, bw, 42, "note", rx=4)
    s.text(xs[0] + bw / 2, ly + 1, "Projector does not", "bs", "middle")
    s.text(xs[0] + bw / 2, ly + 16, "build the mesh", "bs", "middle")

    # ---- RGB channel
    ry = 470
    s.text(50, ry - 12, "RGB channel (separate camera)", "vh")
    s.rect(50, ry, 168, 110, "blk", rx=4)
    s.rect(50 + 50, ry + 22, 48, 32, "ofd", rx=3); s.circle(50 + 74, ry + 38, 10, "of")
    s.text(134, ry + 80, "RGB camera", "b", "middle")
    s.text(134, ry + 96, "colour video", "s", "middle")
    feats = [("Expression", "face regions over time"), ("Skin colour", "colour features"),
             ("Head pose", "position and tilt"), ("rPPG pulse", "with quality flags")]
    fx0 = 250
    for i, (t, d) in enumerate(feats):
        yy = ry - 4 + i * 30
        s.rect(fx0, yy, 200, 26, "blkb", rx=4)
        s.text(fx0 + 10, yy + 17, t, "bs")
        s.text(fx0 + 92, yy + 17, d, "xs")
        s.line(218, ry + 55, fx0, yy + 13, "thin")
    # ---- fusion block
    fxb, fyb = 520, 470
    s.rect(fxb, fyb, 300, 150, "blk", rx=6)
    s.text(fxb + 150, fyb + 22, "Fusion: RGB + IR + depth", "b", "middle")
    s.mtext(fxb + 14, fyb + 46, ["mesh aligned to the RGB image",
                                 "(shared calibration, synced frames)",
                                 "colour features + depth geometry",
                                 "features + temporal features",
                                 "output: per-region features, quality"], "s", "start", 16)
    s.arrow(450, ry + 50, fxb - 2, fyb + 60)
    # mesh -> fusion (route down from mesh box)
    mx = xs[6] + bw / 2
    s.parrow(f"M{xs[6] + 30},{y0 + bh + 48} L{xs[6] + 30},{y0 + bh + 70} L{fxb + 230},{y0 + bh + 70} L{fxb + 230},{fyb - 2}")
    s.text(fxb + 240, y0 + bh + 64, "mesh + depth", "s")
    s.arrow(fxb + 150, fyb + 150, fxb + 150, fyb + 195)
    s.rect(fxb, fyb + 197, 300, 40, "blkd", rx=4)
    s.text(fxb + 150, fyb + 215, "to AI modules 1 to 3 (sheet 5)", "bs", "middle")
    s.text(fxb + 150, fyb + 230, "screening, not a diagnosis", "xs", "middle")

    # ---- key regions panel
    kx, ky = 880, 450
    s.text(kx, ky + 8, "Mesh: key regions tracked", "vh")
    fcx, fcy = kx + 120, ky + 175
    s.ellipse(fcx, fcy, 85, 120, "o")
    reg = dict(
        brows=[(fcx - 50, fcy - 52, fcx - 18, fcy - 58), (fcx + 18, fcy - 58, fcx + 50, fcy - 52)],
    )
    for (a, b, c, d) in reg["brows"]:
        s.line(a, b, c, d, "thick", extra='stroke="#1f5fa8"')
    for sg in (-1, 1):
        s.ellipse(fcx + sg * 34, fcy - 30, 15, 7, "palm")
        s.ellipse(fcx + sg * 50, fcy + 20, 18, 22, "cont")
    s.path(f"M{fcx},{fcy-25} L{fcx-12},{fcy+22} L{fcx+12},{fcy+22} Z", "palm")
    s.ellipse(fcx, fcy + 55, 26, 10, "palm")
    s.ellipse(fcx, fcy + 100, 22, 12, "cont")
    labs = [("brows", (fcx + 50, fcy - 52), -70), ("eyes", (fcx + 49, fcy - 30), -40),
            ("nose", (fcx + 12, fcy + 15), -10), ("cheeks", (fcx + 68, fcy + 20), 20),
            ("lips", (fcx + 26, fcy + 55), 55), ("chin", (fcx + 22, fcy + 100), 95)]
    for name, (px, py), ty in labs:
        s.leader(px, py, kx + 260, fcy + ty, "start", [name])
    s.mtext(kx, ky + 320, ["A few key regions are enough;",
                           "no need for a 30,000-polygon model."], "s", "start", 14)
    s.text(50, 680, "IR channel works with the room light dimmed; RGB gives colour and rPPG.", "s")
    s.text(50, 696, "Every block is checkable on its own (inputs, outputs, quality).", "s")
    return sheet(4, "Face pipeline (IR, depth, mesh, RGB)", s.out())


# ------------------------------------------------------------------ sheet 5
def sheet5():
    s = S()
    s.text(50, 120, "Data flow: sensors, quality gate, AI modules, comparison, status, report", "vh")
    # onboard compute group
    s.rect(300, 140, 790, 520, "grp", rx=8)
    s.text(310, 156, "Onboard compute (station / module)", "s")

    # --- sensors column
    sx, sw = 45, 225
    s.text(sx, 152, "Sensors", "b")
    s.box(sx, 165, sw, 95, "Mirror face module", ["RGB camera + IR camera", "+ IR projector (face),", "illumination"], center=False)
    tag(s, sx + 8, 240, "TEAM")
    s.box(sx, 272, sw, 64, "Front pillars L / R", ["RGB + IR depth modules H/T/L"], center=False)
    tag(s, sx + 8, 316, "TEAM")
    s.box(sx, 348, sw, 64, "Back pillar", ["H/T/L modules (scapulae, spine)"], center=False)
    tag(s, sx + 8, 392, "TEAM")
    s.box(sx, 424, sw, 78, "Touch mirror", ["foot / torso / palm contours,", "touch input, display"], center=False)
    s.rect(sx + 6, 478, sw - 12, 19, "blkd", rx=3)
    s.text(sx + 12, 491, "NFC reader (station, fallback ID)", "s")
    s.rect(sx, 520, sw, 82, "blkd", rx=4)
    s.text(sx + 8, 538, "Doppler grips (optional)", "b")
    s.mtext(sx + 8, 556, ["research module, contact;", "demo: mock cassette +", "signal path diagram"], "s", "start", 14)
    s.box(sx, 618, sw, 50, "Simulated crew data", ["demo app input"], center=False)
    tag(s, sx + sw - 8, 624, "SIM", "end")

    # --- quality gate
    qx, qw = 320, 160
    s.rect(qx, 260, qw, 230, "blk", rx=4)
    s.text(qx + qw / 2, 282, "Quality gate", "b", "middle")
    s.mtext(qx + 10, 306, ["pose inside contours", "all 3 pillar views", "light level", "motion", "sync between views",
                           "Doppler: contact quality", "fail: prompt to adjust", "and repeat capture"], "s", "start", 16)
    for yy in (212, 304, 380, 463):
        s.arrow(sx + sw + 2, yy, qx - 2, min(max(yy, 270), 480))
    s.parrow(f"M{sx + sw + 2},{560} L{qx - 30},{560} L{qx - 30},{470} L{qx - 2},{470}", "fld")
    s.parrow(f"M{sx + sw + 2},{643} L{qx - 16},{643} L{qx - 16},{480} L{qx - 2},{480}", "fl")

    # --- AI modules
    ax, aw = 510, 290
    mods = [("1 Camera / IR processing", "face detection, segmentation, IR dots, outliers, temporal refine", None),
            ("2 RGB + IR fusion", "colour, depth geometry and temporal features", None),
            ("3 rPPG with quality outputs", "signal quality, usable duration, motion, light, reject reason", "OPEN"),
            ("4 Body / posture (3 views)", "skeleton keypoints merged in one coordinate system", "NASA"),
            ("5 Change classifier", "compares features with the personal baseline", None)]
    for i, (t, d, tg) in enumerate(mods):
        yy = 170 + i * 92
        s.rect(ax, yy, aw, 80, "blkb" if i < 4 else "blkg", rx=4)
        s.text(ax + 10, yy + 20, t, "b")
        words = d.split(" "); l1, l2 = "", ""
        for w_ in words:
            if len(l1) + len(w_) < 44 and not l2: l1 += (" " if l1 else "") + w_
            else: l2 += (" " if l2 else "") + w_
        s.text(ax + 10, yy + 40, l1, "s"); s.text(ax + 10, yy + 55, l2, "s")
        if tg:
            tag(s, ax + aw - 8, yy + 60, tg, "end")
    s.text(ax + 10, 166 + 5 * 92 + 6, "", "s")
    s.mtext(ax, 638, ["3: shows 'measurement not confirmed'", "instead of a fake value."], "xs", "start", 12)
    for yy in (210, 302, 394, 486):
        s.arrow(qx + qw + 2, min(max(yy, 270), 480), ax - 2, yy)
    # internal arrows modules -> classifier
    s.parrow(f"M{ax + aw + 2},{210} L{ax + aw + 14},{210} L{ax + aw + 14},{578} L{ax + aw + 2},{578}")
    for yy in (302, 394, 486):
        s.line(ax + aw, yy, ax + aw + 14, yy, "fl")

    # --- comparison
    cx_, cw = 840, 230
    s.rect(cx_, 380, cw, 230, "blk", rx=4)
    s.text(cx_ + cw / 2, 402, "Comparison", "b", "middle")
    s.mtext(cx_ + 10, 426, ["personal baseline (own", "earlier sessions)", "environment mode:",
                            "Earth / microgravity /", "rover / module"], "s", "start", 15)
    tag(s, cx_ + 10, 508, "NASA")
    s.mtext(cx_ + 10, 540, ["posture norms: NASA-STD-3001,", "HIDH; spaceflight change", "context: OSDR (Inspiration4)"], "xs", "start", 13)
    s.arrow(ax + aw + 14, 578, cx_ - 2, 578)
    s.parrow(f"M{cx_ + cw / 2},{378} L{cx_ + cw / 2},{350}")
    # statuses
    stx, stw = 1110, 260
    s.text(stx, 152, "Status (with explanation)", "b")
    sts = [("Within baseline", "#1a7a4a", ["no relevant change"]),
           ("Repeat measurement", "#b35900", ["low quality or unclear", "change: capture again"]),
           ("Refer to specialist", "#c0392b", ["change confirmed: medical", "team reviews"])]
    for i, (t, col, ls) in enumerate(sts):
        yy = 165 + i * 82
        s.add(f'<rect x="{stx}" y="{yy}" width="{stw}" height="70" rx="4" fill="#fff" stroke="{col}" stroke-width="2.2"/>')
        s.add(f'<text x="{stx + 10}" y="{yy + 20}" class="b" fill="{col}" style="fill:{col}">{esc(t)}</text>')
        s.mtext(stx + 10, yy + 38, ls, "s", "start", 14)
    s.parrow(f"M{cx_ + cw / 2},{350} L{cx_ + cw / 2},{282} L{stx - 16},{282}")
    s.line(stx - 14, 200, stx - 14, 668, "fl")
    for yy in (200, 282, 364):
        s.arrow(stx - 14, yy, stx - 2, yy)
    s.text(cx_ + cw / 2 + 6, 274, "result + reliability", "xs")
    s.mtext(stx, 420, ["Report states: which indicator", "changed, how reliable, what", "action. Screening, not a diagnosis."], "s", "start", 14)

    # outputs
    oy = 690
    s.box(320, oy, 260, 70, "Mirror display / voice", ["status, prompts, 'repeat' requests"], center=False)
    s.box(620, oy, 300, 70, "Store-and-forward report queue", ["onboard, survives link outages"], center=False)
    s.box(960, oy, 410, 70, "Medical team on Earth (comm delay)", ["a human makes the medical decision"], center=False)
    s.parrow(f"M{1240},{462} L{1240},{680} L{790},{680} L{790},{oy - 2}")
    s.text(1246, 600, "report", "s")
    s.parrow(f"M{qx + 80},{490} L{qx + 80},{oy - 2}", "fld")
    s.text(qx + 86, 600, "prompts", "s")
    s.arrow(580 + 2, oy + 35, 620 - 2, oy + 35)
    s.arrow(920 + 2, oy + 35, 960 - 2, oy + 35)
    s.parrow(f"M{stx - 14},{668} L{450},{668} L{450},{oy - 2}")
    s.text(456, 684, "status to crew", "xs")

    # provenance legend
    ly = 790
    s.text(50, ly, "Data provenance", "b")
    rows = [("TEAM", "own mirror-demo recordings (camera views, pose, quality tests)"),
            ("OPEN", "CameraVitals: RGB video synced with cardiac and respiratory signals (rPPG validation)"),
            ("NASA", "Life Sciences Data Archive / Life Sciences Portal, NASA Open Data Portal, OSDR incl. Inspiration4,"),
            ("SIM", "the demo app runs on simulated crew data")]
    for i, (k_, d) in enumerate(rows):
        yy = ly + 12 + i * 33
        tag(s, 50, yy, k_)
        s.text(180, yy + 11, d, "s")
    s.text(180, ly + 12 + 2 * 33 + 24, "NASA-STD-3001 / Human Integration Design Handbook (neutral body posture, anthropometry)", "s")
    return sheet(5, "System and AI modules", s.out())


files = {
    "01_general_view.svg": sheet1(),
    "02_front_side_views.svg": sheet2(),
    "03_doppler_cassette.svg": sheet3(),
    "04_face_pipeline.svg": sheet4(),
    "05_system_ai.svg": sheet5(),
}
for n, c in files.items():
    with open(os.path.join(OUT, n), "w", encoding="utf-8") as f:
        f.write(c)
    print("wrote", n)
