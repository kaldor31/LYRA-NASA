#!/usr/bin/env python3
"""Generates the English LYRA concept drawing sheets (SVG).

Default output: docs/drawings/ (resolved relative to this script).
An optional argv[1] overrides the output directory.
PNG copies of the English sheets live in docs/drawings/png/ (rendered separately).
"""
import math, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.normpath(os.path.join(HERE, ".."))
os.makedirs(OUT, exist_ok=True)
W, H = 1400, 990

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

class S:
    def __init__(self): self.p = []
    def add(self, x): self.p.append(x)
    def line(self, x1, y1, x2, y2, cls="o", extra=""):
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="{cls}" {extra}/>')
    def rect(self, x, y, w, h, cls="o", rx=0, extra=""):
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" class="{cls}" {extra}/>')
    def circle(self, cx, cy, r, cls="o", extra=""):
        self.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" class="{cls}" {extra}/>')
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
        """dimension line between two points with arrows; label centered, offset perpendicular"""
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="dim"/>')
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        if abs(x2 - x1) < 1:  # vertical
            self.add(f'<text x="{mx-6+off:.1f}" y="{my:.1f}" class="{cls}" text-anchor="middle" transform="rotate(-90 {mx-6+off:.1f} {my:.1f})">{esc(label)}</text>')
        else:
            self.text(mx, my - 6 + off, label, cls, "middle")
    def ext(self, x1, y1, x2, y2):
        self.line(x1, y1, x2, y2, "ex")
    def leader(self, x1, y1, x2, y2, label, anchor="start", cls="t", lines=None):
        self.add(f'<circle cx="{x1:.1f}" cy="{y1:.1f}" r="2.2" fill="#222"/>')
        self.line(x1, y1, x2, y2, "ld")
        tx = x2 + (4 if anchor == "start" else -4 if anchor == "end" else 0)
        if lines:
            self.mtext(tx, y2 + 4, lines, cls, anchor, 14)
        else:
            self.text(tx, y2 + 4, label, cls, anchor)
    def arrow(self, x1, y1, x2, y2, cls="fl"):
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="{cls}" marker-end="url(#fa)"/>')
    def out(self): return "\n".join(self.p)

STYLE = """
<defs>
  <marker id="da" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,1.5 L10,5 L0,8.5 z" fill="#222"/></marker>
  <marker id="fa" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#222"/></marker>
  <pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="#555" stroke-width="1"/></pattern>
  <style>
    text{font-family:Arial,Helvetica,sans-serif}
    .t{font-size:13px;fill:#111}
    .s{font-size:11px;fill:#333}
    .b{font-size:13px;fill:#111;font-weight:bold}
    .h{font-size:20px;fill:#111;font-weight:bold}
    .vh{font-size:15px;fill:#111;font-weight:bold}
    .dl{font-size:12px;fill:#111}
    .o{stroke:#1a1a1a;stroke-width:1.6;fill:none}
    .of{stroke:#1a1a1a;stroke-width:1.6;fill:#f2f2f2}
    .ofd{stroke:#1a1a1a;stroke-width:1.6;fill:#d9d9d9}
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
    .sl{fill:#c0392b;fill-opacity:0.13;stroke:#c0392b;stroke-width:1;stroke-dasharray:5 3}
    .tof{fill:#1f5fa8;fill-opacity:0.10;stroke:#1f5fa8;stroke-width:1;stroke-dasharray:5 3}
    .hum{stroke:#777;stroke-width:1.2;fill:none;stroke-dasharray:3 3}
    .gel{stroke:#1a7a4a;stroke-width:3;fill:none}
    .frame{stroke:#111;stroke-width:2;fill:none}
    .blk{stroke:#1a1a1a;stroke-width:1.5;fill:#fafafa}
    .grp{stroke:#555;stroke-width:1;fill:none;stroke-dasharray:6 4}
  </style>
</defs>
"""

def sheet(num, title, body, note_extra=None):
    s = S()
    s.add(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fff"/>')
    s.rect(15, 15, W - 30, H - 30, "frame")
    s.rect(25, 25, W - 50, H - 50, "thin")
    s.text(45, 60, f"Sheet {num}. {title}", "h")
    s.text(45, 82, "LYRA concept. Dimensions in mm, approximate (not a manufacturing drawing).", "s")
    # stamp
    x0, y0, x1, y1 = 985, 845, W - 25, H - 25
    s.add(f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="#fff" stroke="#111" stroke-width="1.6"/>')
    for dy in (36, 66, 94):
        s.line(x0, y0 + dy, x1, y0 + dy, "thin")
    s.line(x0 + 110, y0, x0 + 110, y0 + 36, "thin")
    s.line(x0 + 250, y0 + 66, x0 + 250, y1, "thin")
    s.text(x0 + 55, y0 + 26, "LYRA", "h", "middle")
    s.text(x0 + 120, y0 + 23, title, "b")
    s.text(x0 + 10, y0 + 56, "Concept, NASA Space Apps 2026", "t")
    s.text(x0 + 10, y0 + 85, "Scale: NTS", "t")
    s.text(x0 + 260, y0 + 85, f"Sheet {num}/5", "b")
    s.text(x0 + 10, y1 - 9, "Dimensions in mm, approximate", "s")
    s.text(x0 + 260, y1 - 9, "Format: landscape", "s")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">\n'
            f'<title>LYRA sheet {num}: {esc(title)}</title>\n{STYLE}\n{s.out()}\n{body}\n</svg>\n')

# ---------------------------------------------------------------- sheet 1
def sheet1():
    s = S()
    # ---- plan view
    s.text(60, 125, "Top view (plan), deployed", "vh")
    k = 0.25
    cx, y0 = 330, 300  # center x, panel (depth 0) y
    X = lambda mm: cx + mm * k
    Y = lambda d: y0 + d * k
    # module wall
    s.line(X(-760), Y(-30), X(760), Y(-30), "thick")
    s.rect(X(-760), Y(-60), X(760) - X(-760), 30 * k, extra='fill="url(#hatch)" stroke="none"')
    s.text(X(760), Y(-60) - 6, "module wall", "s", "end")
    # zone
    s.rect(X(-600), Y(0), 1200 * k, 1200 * k, "hid")
    # panel
    s.rect(X(-250), Y(0), 500 * k, 40 * k, "ofd")
    # front posts (depth 100), rear post (depth 1150)
    for px in (-550, 550):
        s.rect(X(px) - 5, Y(100) - 5, 10, 10, "post")
    s.rect(X(0) - 5, Y(1150) - 5, 10, 10, "post")
    # handle brackets from posts to grips
    for sg in (-1, 1):
        s.line(X(sg * 545), Y(100), X(sg * 330), Y(260), "thick")
        s.rect(X(sg * 330) - 6, Y(260) - 9, 12, 18, "ofd", rx=3)
    # person (shoulders ellipse + head)
    s.add(f'<ellipse cx="{X(0)}" cy="{Y(560)}" rx="{225*k}" ry="{120*k}" class="hum"/>')
    s.circle(X(0), Y(520), 80 * k, "hum")
    # foot restraints
    for fx in (-110, 110):
        s.rect(X(fx) - 12, Y(520) - 14, 24, 40, "thin", rx=3, extra='stroke-dasharray="2 2"')
    # folded positions
    s.rect(X(-430) - 5, Y(-25), 10, 10, "hid")
    s.rect(X(430) - 5, Y(-25), 10, 10, "hid")
    s.rect(X(330) - 5, Y(-25), 10, 10, "hid")
    s.path(f"M{X(-550)},{Y(100)} A {130*k} {130*k} 0 0 1 {X(-430)},{Y(-20)}", "hid")
    s.path(f"M{X(550)},{Y(100)} A {130*k} {130*k} 0 0 0 {X(430)},{Y(-20)}", "hid")
    # dimensions
    s.ext(X(-600), Y(1200), X(-600), Y(1290)); s.ext(X(600), Y(1200), X(600), Y(1290))
    s.dim(X(-600), Y(1270), X(600), Y(1270), "1200")
    s.ext(X(600), Y(0), X(700), Y(0)); s.ext(X(600), Y(1200), X(700), Y(1200))
    s.dim(X(680), Y(0), X(680), Y(1200), "1200", off=-2)
    s.ext(X(-250), Y(0), X(-250), Y(-215)); s.ext(X(250), Y(0), X(250), Y(-215))
    s.dim(X(-250), Y(-200), X(250), Y(-200), "500")
    s.ext(X(-600), Y(500), X(-760), Y(500))
    s.ext(X(-600), Y(0), X(-760), Y(0))
    s.dim(X(-740), Y(0), X(-740), Y(500), "≈500 to face", off=-2)
    # leaders
    s.leader(X(-200), Y(20), 60, 205, "", "start", lines=["mirror panel", "≈500×900 with display"])
    s.leader(X(-555), Y(105), 135, 460, "", "end", lines=["front", "post 40×40"])
    s.leader(X(5), Y(1150), X(150), Y(1100), "rear post 40×40", "start")
    s.leader(X(330), Y(260), X(470), Y(380), "", "start", lines=["right handle", "(on bracket)"])
    s.leader(X(110), Y(530), X(470), Y(720), "", "start", lines=["foot restraints"])
    s.leader(X(0), Y(600), X(-300), Y(860), "", "end", lines=["astronaut"])
    s.leader(X(430), Y(-20), 540, 225, "", "start", lines=["stowed: posts", "hinged to the wall"])
    s.text(60, 760, "Work zone 1200×1200 (dashed). 360° coverage: two front posts + one rear post.", "t")
    s.text(60, 778, "Posts attach to module floor and ceiling (on ISS: standard attachment rails), no legs.", "t")
    s.text(60, 796, "Dashed at the wall: stowed position (depth ≈100).", "t")

    # ---- isometric view
    s.text(700, 125, "Isometric view (rear-right)", "vh")
    k2 = 0.2
    ox, oy = 1080, 650
    c30, s30 = math.cos(math.radians(30)), 0.5
    def P(x, d, z):
        return (ox + (x - d) * c30 * k2, oy + (x + d) * s30 * k2 - z * k2)
    def L(a, b, cls="o"):
        s.line(*P(*a), *P(*b), cls)
    # floor zone and ceiling
    fz = [P(-600, 0, 0), P(600, 0, 0), P(600, 1200, 0), P(-600, 1200, 0)]
    s.poly(fz, "hid")
    cz = [P(-600, 0, 2000), P(600, 0, 2000), P(600, 1200, 2000), P(-600, 1200, 2000)]
    s.poly(cz, "hid")
    # wall plane hint
    s.poly([P(-760, -30, 0), P(760, -30, 0), P(760, -30, 2000), P(-760, -30, 2000)], "thin", extra='stroke-dasharray="1 4"')
    # person (simple dashed figure) at depth 500
    hx, hd = 0, 520
    s.line(*P(hx, hd, 80), *P(hx, hd, 1450), "hum")
    s.line(*P(-200, hd, 1430), *P(200, hd, 1430), "hum")
    s.line(*P(-200, hd, 1430), *P(-280, hd - 200, 1100), "hum")
    s.line(*P(200, hd, 1430), *P(280, hd - 200, 1100), "hum")
    s.line(*P(-100, hd, 950), *P(-110, hd, 80), "hum")
    s.line(*P(100, hd, 950), *P(110, hd, 80), "hum")
    hcx, hcy = P(0, hd, 1630)
    s.circle(hcx, hcy, 100 * k2, "hum")
    # foot restraints
    for fx in (-110, 110):
        s.poly([P(fx - 60, hd - 90, 0), P(fx + 60, hd - 90, 0), P(fx + 60, hd + 90, 0), P(fx - 60, hd + 90, 0)], "thin")
        s.line(*P(fx - 60, hd, 0), *P(fx - 60, hd, 60), "thin")
        s.line(*P(fx + 60, hd, 0), *P(fx + 60, hd, 60), "thin")
        s.line(*P(fx - 60, hd, 60), *P(fx + 60, hd, 60), "thin")
    # panel (behind person, depth 0)
    pp = [P(-250, 0, 900), P(250, 0, 900), P(250, 0, 1800), P(-250, 0, 1800)]
    s.poly(pp, "ofd", extra='fill-opacity="0.85"')
    s.poly([P(-220, 0, 940), P(220, 0, 940), P(220, 0, 1700), P(-220, 0, 1700)], "thin")
    # posts
    posts = [(-550, 100), (550, 100), (0, 1150)]
    for (x, d) in posts:
        a, b = P(x, d, 0), P(x, d, 2000)
        s.add(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#1a1a1a" stroke-width="5"/>')
        for z in (450, 1250, 1650):
            m = P(x, d, z)
            s.rect(m[0] - 6, m[1] - 9, 12, 18, "of")
    # handles
    for sg in (-1, 1):
        L((sg * 550, 100, 1100), (sg * 330, 260, 1100), "thick")
        a, b = P(sg * 330, 230, 1100), P(sg * 330, 290, 1100)
        s.add(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#1a1a1a" stroke-width="7" stroke-linecap="round"/>')
    # labels
    def lab(pt3, tx, ty, text, anchor="start", lines=None):
        x, y = P(*pt3)
        s.leader(x, y, tx, ty, text, anchor, lines=lines)
    lab((550, 100, 1650), 1225, 200, "", "start", lines=["\"head\" module", "IR dots + IR camera", "+ RGB"])
    lab((550, 100, 1250), 1225, 330, "", "start", lines=["\"torso\" module", "ToF + RGB"])
    lab((550, 100, 450), 1225, 600, "", "start", lines=["\"legs\" module", "ToF"])
    lab((330, 260, 1100), 1225, 450, "", "start", lines=["right handle", "(elbow height)"])
    lab((-250, 0, 1800), 780, 175, "", "end", lines=["mirror", "panel"])
    lab((0, 1150, 1900), 760, 300, "", "end", lines=["rear", "post"])
    lab((-110, 610, 30), 840, 790, "", "end", lines=["foot restraints"])
    lab((-600, 1200, 0), 760, 720, "", "end", lines=["work zone", "1200×1200"])
    # height dim at rear post
    a, b = P(0, 1150, 0), P(0, 1150, 2000)
    s.ext(a[0] - 8, a[1], a[0] - 70, a[1]); s.ext(b[0] - 8, b[1], b[0] - 70, b[1])
    s.dim(a[0] - 60, a[1], b[0] - 60, b[1], "floor to ceiling ≈2000", off=-2)
    return sheet(1, "Station general view", s.out())

# ---------------------------------------------------------------- sheet 2
def sheet2():
    s = S()
    k = 0.31
    floor = 790
    Z = lambda z: floor - z * k
    # ---------- front view
    cx = 330
    X = lambda x: cx + x * k
    s.text(60, 125, "Front view (from panel toward astronaut)", "vh")
    s.line(X(-700), Z(0), X(700), Z(0), "thick")
    s.line(X(-700), Z(2000), X(700), Z(2000), "thick")
    s.rect(X(-700), Z(0), 1400 * k, 10, extra='fill="url(#hatch)" stroke="none"')
    s.rect(X(-700), Z(2000) - 10, 1400 * k, 10, extra='fill="url(#hatch)" stroke="none"')
    s.text(X(-700), Z(0) + 26, "floor", "s"); s.text(X(-700), Z(2000) - 16, "ceiling", "s")
    # rear post (hidden)
    s.line(X(0), Z(0), X(0), Z(2000), "hid")
    # posts
    for px in (-550, 550):
        s.rect(X(px) - 20 * k, Z(2000), 40 * k, 2000 * k, "post")
        for z, nm in ((1650, "H"), (1250, "T"), (450, "L")):
            s.rect(X(px) - 12, Z(z) - 14, 24, 28, "of")
            s.text(X(px), Z(z) + 4, nm, "s", "middle")
    # person
    s.circle(X(0), Z(1630), 100 * k, "hum")
    s.path(f"M{X(-200)},{Z(1440)} L{X(200)},{Z(1440)} L{X(150)},{Z(950)} L{X(-150)},{Z(950)} Z", "hum")
    s.path(f"M{X(-110)},{Z(950)} L{X(-120)},{Z(60)} M{X(110)},{Z(950)} L{X(120)},{Z(60)}", "hum")
    s.path(f"M{X(-200)},{Z(1440)} L{X(-300)},{Z(1110)} M{X(200)},{Z(1440)} L{X(300)},{Z(1110)}", "hum")
    # foot restraints
    for fx in (-120, 120):
        s.rect(X(fx) - 14, Z(80), 28, 80 * k, "thin")
    # handles + brackets
    for sg in (-1, 1):
        s.line(X(sg * 550), Z(1100), X(sg * 330), Z(1100), "thick")
        s.rect(X(sg * 330) - 8, Z(1100) - 14, 16, 28, "ofd", rx=4)
    # panel (transparent outline, astronaut visible behind? front view looks from behind panel: draw panel outline dashed)
    s.rect(X(-250), Z(1800), 500 * k, 900 * k, "o", extra='stroke-dasharray="10 3"')
    s.rect(X(-60), Z(1790), 120 * k, 50 * k, "ofd")
    # dims front
    s.ext(X(-250), Z(900), X(-250), Z(800)); s.ext(X(250), Z(900), X(250), Z(800))
    s.dim(X(-250), Z(830), X(250), Z(830), "500")
    s.ext(X(-550), Z(300), X(-550), Z(200)); s.ext(X(550), Z(300), X(550), Z(200))
    s.dim(X(-550), Z(230), X(550), Z(230), "≈1100 (between posts)")
    s.ext(X(250), Z(900), X(450), Z(900)); s.ext(X(250), Z(1800), X(450), Z(1800))
    s.dim(X(420), Z(900), X(420), Z(1800), "900", off=-2)
    # labels front
    s.leader(X(0), Z(1765), X(-250), Z(2000) + 45, "", "end", lines=[])
    s.text(X(-250) - 4, Z(2000) + 40, "dot projector + IR camera + RGB (face)", "s", "start")
    s.leader(X(250), Z(1350), X(580), Z(1500), "", "start", lines=["panel", "(dashed)"])
    s.leader(X(-330), Z(1100), X(-650), Z(1250), "", "end", lines=["left handle"])
    s.text(X(-640), Z(1650) + 4, "H = head", "s", "end")
    s.text(X(-640), Z(1650) + 20, "T = torso", "s", "end")
    s.text(X(-640), Z(1650) + 36, "L = legs", "s", "end")
    s.leader(X(120), Z(40), X(200), Z(140), "", "start", lines=["foot restraints"])

    # ---------- side view
    x0 = 790
    D = lambda d: x0 + d * k
    s.text(700, 125, "Side view: sensor fields of view", "vh")
    s.line(D(-120), Z(0), D(1300), Z(0), "thick")
    s.line(D(-120), Z(2000), D(1300), Z(2000), "thick")
    s.rect(D(-120), Z(0), 1420 * k, 10, extra='fill="url(#hatch)" stroke="none"')
    s.rect(D(-120), Z(2000) - 10, 1420 * k, 10, extra='fill="url(#hatch)" stroke="none"')
    # FOV cones first (under objects)
    s.poly([(D(40), Z(1765)), (D(520), Z(1800)), (D(520), Z(1460))], "sl")
    s.poly([(D(120), Z(1250)), (D(620), Z(1750)), (D(620), Z(850))], "tof")
    s.poly([(D(120), Z(450)), (D(620), Z(950)), (D(620), Z(0))], "tof")
    s.poly([(D(1130), Z(1250)), (D(450), Z(1800)), (D(450), Z(800))], "tof")

    # panel
    s.rect(D(0), Z(1800), 40 * k, 900 * k, "ofd")
    s.rect(D(40), Z(1790), 20 * k, 50 * k, "of")
    # front post (projected) & rear post
    for d in (100, 1150):
        s.rect(D(d) - 20 * k, Z(2000), 40 * k, 2000 * k, "post")
        for z in (1650, 1250, 450):
            s.rect(D(d) - 9, Z(z) - 14, 18, 28, "of")
    # person facing panel (left)
    s.circle(D(530), Z(1630), 100 * k, "hum")
    s.path(f"M{D(500)},{Z(1450)} L{D(520)},{Z(950)} M{D(560)},{Z(1450)} L{D(570)},{Z(950)}", "hum")
    s.path(f"M{D(520)},{Z(950)} L{D(510)},{Z(60)} M{D(570)},{Z(950)} L{D(560)},{Z(60)}", "hum")
    s.path(f"M{D(520)},{Z(1430)} L{D(480)},{Z(1130)} L{D(300)},{Z(1100)}", "hum")
    s.rect(D(470), Z(80), 120 * k, 80 * k, "thin")
    # handle in side view
    s.line(D(100), Z(1100), D(300), Z(1100), "thick")
    s.rect(D(280), Z(1100) - 10, 18, 20, "ofd", rx=4)
    # dims side: depths under floor
    for d in (0, 500, 1150):
        s.ext(D(d), Z(0) + 12, D(d), Z(0) + 40)
    s.dim(D(0), Z(0) + 32, D(500), Z(0) + 32, "≈500 to face")
    s.dim(D(500), Z(0) + 32, D(1150), Z(0) + 32, "≈650")
    # heights: overall dim + level ticks
    hx = D(1290)
    s.ext(D(1170), Z(0), hx + 8, Z(0)); s.ext(D(1170), Z(2000), hx + 8, Z(2000))
    s.dim(hx, Z(0), hx, Z(2000), "floor to ceiling ≈2000", off=-2)
    for z, nm in ((1650, "head 1650"), (1250, "torso 1250"), (1100, "handles 1100"), (450, "legs 450")):
        s.line(D(1160), Z(z), hx + 10, Z(z), "ex", extra='stroke-dasharray="2 3"')
        s.text(hx + 14, Z(z) + 4, nm, "s")
    s.text(hx + 14, Z(0) - 6, "heights", "s"); s.text(hx + 14, Z(0) + 8, "above floor", "s")
    # cone labels
    s.leader(D(300), Z(1760), D(200), Z(1930), "", "start", lines=[])
    s.text(D(200) + 4, Z(1930) - 2, "structured light: face, ≈0.5 m", "s")
    s.leader(D(560), Z(1300), D(660), Z(1060), "", "start", lines=["ToF front"])
    s.leader(D(560), Z(250), D(660), Z(150), "", "start", lines=["ToF legs"])
    s.leader(D(820), Z(1450), D(900), Z(1720), "", "start", lines=["ToF rear"])

    # legend
    lx, ly = 60, 838
    s.text(lx, ly, "Legend and notes", "b")
    s.rect(lx, ly + 10, 30, 14, "sl"); s.text(lx + 40, ly + 22, "structured light field (IR dot projector + IR camera): face at ≈0.5 m, resolves few-mm changes (facial puffiness)", "s")
    s.rect(lx, ly + 32, 30, 14, "tof"); s.text(lx + 40, ly + 44, "ToF field: body; ToF accuracy stays nearly constant at 1 to 2 m; each ToF on its own modulation frequency", "s")
    s.rect(lx, ly + 54, 30, 14, "of"); s.text(lx + 40, ly + 66, "post module (H/T/L); dot projectors fire in turn; RGB cameras give video pulse (rPPG)", "s")
    s.text(lx, ly + 90, "Heights shown for a ≈1.75 m crew member; modules and handles slide on the post rail ±150.", "s")
    return sheet(2, "Front & side views, FOV", s.out())

# ---------------------------------------------------------------- sheet 3
def sheet3():
    s = S()
    k = 3.6
    x0, yc = 170, 370
    X = lambda mm: x0 + mm * k
    Y = lambda r: yc - r * k   # r>0 = palm side (top)
    R = 22.5
    s.text(60, 125, "Handle longitudinal section (right; left is mirrored)", "vh")
    s.text(60, 145, "palm side on top, fingers wrap underneath", "s")
    # palm outline
    # shell
    s.rect(X(0), Y(R), 160 * k, 2 * R * k, "of", rx=46)
    s.rect(X(3), Y(R - 3), 154 * k, 2 * (R - 3) * k, "o", rx=38, extra='fill="#fff"')
    s.line(X(6), Y(-2), X(154), Y(-2), "thin", extra='stroke-dasharray="2 2"')
    s.line(X(-8), Y(0), X(168), Y(0), "ctr")
    # NFC end cap
    s.rect(X(3), Y(15), 7 * k, 30 * k, "ofd")
    for i in range(4):
        s.line(X(4.5 + i * 1.5), Y(13), X(4.5 + i * 1.5), Y(-13), "thin")
    # doppler window & transducer
    s.rect(X(48), Y(R), 54 * k, 3 * k, "ofd", extra='fill="#cfe3f5"')
    s.rect(X(55), Y(19), 40 * k, 13 * k, "ofd")
    for i in range(9):
        s.line(X(58 + i * 4), Y(19), X(58 + i * 4), Y(15), "thin")
    # gel cassette
    s.circle(X(26), Y(10), 8 * k, "o"); s.circle(X(26), Y(10), 3 * k, "ofd")
    s.circle(X(128), Y(10), 8 * k, "o"); s.circle(X(128), Y(10), 3 * k, "ofd")
    s.path(f"M{X(26)},{Y(18)} L{X(40)},{Y(23.5)} L{X(110)},{Y(23.5)} L{X(128)},{Y(18)}", "gel")
    s.add(f'<circle cx="{X(26)}" cy="{Y(10)}" r="{6*k}" fill="none" stroke="#1a7a4a" stroke-width="5" stroke-opacity="0.5"/>')
    s.add(f'<circle cx="{X(128)}" cy="{Y(10)}" r="{4.5*k}" fill="none" stroke="#1a7a4a" stroke-width="4" stroke-opacity="0.35"/>')
    s.rect(X(14), Y(21), 128 * k, 18 * k, "grp", rx=6)
    s.arrow(X(62), Y(28), X(86), Y(28))
    s.text(X(88) + 4, Y(28) + 4, "advance", "s")
    # motor
    s.rect(X(122), Y(0) - 2, 14 * k, 9 * k, "ofd", rx=3)
    s.text(X(129), Y(0) + 20, "M", "b", "middle")
    # liquid gel reservoir, pump, channel
    s.rect(X(12), Y(-4), 26 * k, 14 * k, "of", rx=3, extra='fill="#e3f1e8"')
    s.rect(X(39), Y(-6), 7 * k, 7 * k, "ofd")
    s.path(f"M{X(46)},{Y(-9)} L{X(47)},{Y(-9)} L{X(47)},{Y(20)} L{X(48)},{Y(22.5)}", "thin", extra='stroke="#1a7a4a" stroke-width="1.6"')
    # load-cell beam
    s.rect(X(55), Y(-4), 50 * k, 4 * k, "ofd", extra='fill="url(#hatch)"')
    s.rect(X(55) - 4, Y(-2) - 6, 6, 18, "ofd"); s.rect(X(105) - 2, Y(-2) - 6, 6, 18, "ofd")
    # PPG window bottom
    s.rect(X(68), Y(-19.5), 20 * k, 3 * k, "ofd", extra='fill="#f6d5d5"')
    s.rect(X(70), Y(-14), 16 * k, 5 * k, "ofd")
    # temp sensor
    s.rect(X(110), Y(R), 6 * k, 4 * k, "ofd", extra='fill="#f5e3c8"')
    # board
    s.rect(X(110), Y(-10), 34 * k, 4 * k, "ofd", extra='fill="#d6e6d0"')
    # bracket
    s.rect(X(160), Y(12), 30 * k, 24 * k, "post")
    s.line(X(190), Y(0), X(215), Y(0), "thick")
    s.text(X(203), Y(0) - 10, "to post", "s", "middle")
    s.path(f"M{X(144)},{Y(-8)} C{X(160)},{Y(-8)} {X(170)},{Y(-8)} {X(175)},{Y(-12)}", "thin")
    # section mark
    s.line(X(78), Y(R) - 22, X(78), Y(-R) + 26, "ctr")
    s.text(X(78) + 9, Y(R) - 10, "A", "b"); s.text(X(78) + 9, Y(-R) + 22, "A", "b")
    # ---- top labels
    s.leader(X(45), Y(23.5), 366, 176, "", "start", lines=["solid hydrogel tape over the window"])
    s.leader(X(75), Y(22), 452, 211, "", "start", lines=["Doppler window (ultrasound → palmar arteries)"])
    s.leader(X(14) + 4, Y(21) + 3, 160, 206, "", "end", lines=[])
    s.text(45, 180, "hydrogel tape cassette (replaceable):", "t")
    s.text(45, 196, "our design (LYRA concept)", "t")
    s.leader(X(22), Y(17), 170, 241, "", "end", lines=["supply spool"])
    s.leader(X(113), Y(R), 596, 246, "", "start", lines=["palm temperature sensor"])
    s.leader(X(128), Y(18), 756, 296, "", "start", lines=["take-up spool", "(used tape)"])
    # ---- bottom labels
    s.leader(X(7), Y(-10), 164, 491, "", "end", lines=["NFC reader", "(end cap)"])
    s.leader(X(25), Y(-8), X(25), 530, "", "start", lines=["backup liquid gel dispenser:", "reservoir + micropump + channel to window"])
    s.leader(X(78), Y(-19.5), X(78), 501, "", "start", lines=["PPG + SpO₂", "(under fingers)"])
    s.leader(X(104), Y(-2), 660, 520, "", "start", lines=["load-cell beam: grip force", "(lower half-shell floats)"])
    s.leader(X(133), Y(0) + 8, 790, 455, "", "start", lines=["tape drive micromotor"])
    s.leader(X(115), Y(-8), 760, 490, "", "start", lines=["board: MCU, ADC, US driver"])
    s.leader(X(175), Y(-12), 880, 396, "", "start", lines=["cable into post"])
    # dims
    s.ext(X(0), Y(-R) + 4, X(0), Y(-R) + 42); s.ext(X(160), Y(-R) + 4, X(160), Y(-R) + 42)
    s.dim(X(0), Y(-R) + 34, X(160), Y(-R) + 34, "", )
    s.text(X(12), Y(-R) + 30, "160", "dl")
    s.ext(X(0) + 30, Y(R), X(-26), Y(R)); s.ext(X(0) + 30, Y(-R), X(-26), Y(-R))
    s.dim(X(-18), Y(R), X(-18), Y(-R), "Ø45", off=-2)

    # ---------- section A-A
    cx, cy, r = 1140, 330, R * 3.2
    s.text(1000, 125, "Section A-A", "vh")
    s.circle(cx, cy, r, "of")
    s.circle(cx, cy, r - 3 * 3.2, "o", extra='fill="#fff"')
    s.line(cx - r - 10, cy + 2 * 3.2, cx + r + 10, cy + 2 * 3.2, "thin", extra='stroke-dasharray="2 2"')
    s.path(f"M{cx-40},{cy-r+2} A {r} {r} 0 0 1 {cx+40},{cy-r+2}", "o", extra='stroke="#5b8fc7" stroke-width="6"')
    s.path(f"M{cx-46},{cy-r-4} A {r+6} {r+6} 0 0 1 {cx+46},{cy-r-4}", "gel")
    s.rect(cx - 36, cy - r + 12, 72, 38, "ofd")
    s.rect(cx - 62, cy + 2, 124, 13, "ofd", extra='fill="url(#hatch)"')
    s.rect(cx - 28, cy + r - 26, 56, 16, "ofd")
    s.path(f"M{cx-30},{cy+r-2} A {r} {r} 0 0 0 {cx+30},{cy+r-2}", "o", extra='stroke="#c97b7b" stroke-width="6"')
    s.path(f"M{cx+r+14},{cy-30} C{cx+r+30},{cy+40} {cx+40},{cy+r+30} {cx-20},{cy+r+18}", "hum")
    s.leader(cx + 40, cy - r - 4, 1230, 190, "", "start", lines=["hydrogel tape"])
    s.leader(cx + 10, cy - r + 30, 1230, 225, "", "start", lines=["US transducer"])
    s.leader(cx + 50, cy + 8, 1230, 330, "", "start", lines=["load-cell beam"])
    s.leader(cx + r + 22, cy + 30, 1250, 380, "", "start", lines=["fingers"])
    s.leader(cx + 20, cy + r - 18, 1230, 430, "", "start", lines=["PPG/SpO₂"])
    s.leader(cx - r - 3, cy + 6, 1060, 420, "", "end", lines=["half-shell", "split line"])

    # ---------- tape cycle and notes
    bx, by = 60, 640
    s.text(bx, by, "Hydrogel tape cycle (primary option)", "b")
    steps = ["1. Before each session the motor advances ≈20 mm of fresh tape",
             "2. Palm rests on the tape: acoustic contact without liquid",
             "3. 30 s session: Doppler, PPG/SpO₂, temperature; then 2 squeezes (grip)",
             "4. Used tape winds onto the take-up spool (closed cassette)",
             "5. Tape counter → reminder to replace the cassette"]
    s.mtext(bx, by + 22, steps, "t", dy=19)
    s.text(bx, by + 130, "Fallback: liquid gel dispenser in the same handle (a drop on the window).", "t")
    nx = 640
    s.text(nx, by, "Honesty notes", "b")
    notes = ["• Hydrogel ultrasound pads and tape-advance mechanisms already exist;",
             "   the handle cassette itself is our design (LYRA concept); no prototype yet.",
             "• Ultrasound does not pass through air: a coupling medium is required.",
             "• Nothing is worn on the body, no electrodes (no ECG);",
             "   HRV comes from PPG/Doppler. Screening, not diagnosis.",
             "• Ultrasound ≈8 to 12 MHz (superficial vessels): our estimate.",
             "• NFC card stays at the station: used only if 3D face ID is unsure."]
    s.mtext(nx, by + 22, notes, "t", dy=19)
    return sheet(3, "Handle cross-section", s.out())

# ---------------------------------------------------------------- sheet 4
def sheet4():
    s = S()
    s.text(60, 125, "Data flow: sensors → onboard computer → crew and flight surgeon on Earth", "vh")
    def blk(x, y, w, h, title, lines=(), cls="blk"):
        s.rect(x, y, w, h, cls, rx=6)
        s.text(x + 10, y + 20, title, "b")
        s.mtext(x + 10, y + 38, list(lines), "s", dy=15)
    # sensors group
    s.rect(45, 140, 330, 560, "grp", rx=8)
    s.text(55, 160, "STATION SENSORS", "b")
    blk(60, 172, 300, 82, "Structured light ×3 (face)", ["IR dot projector + IR camera:", "panel + \"head\" modules on posts", "fire in turn"])
    blk(60, 264, 300, 82, "ToF cameras ×7 (body)", ["\"torso\"/\"legs\" modules on 3 posts,", "\"head\" on the rear post;", "each on its own modulation frequency"])
    blk(60, 356, 300, 52, "RGB cameras ×3", ["video pulse (rPPG), skin tone, facial cues"])
    blk(60, 418, 300, 98, "Handles L / R", ["US Doppler (blood flow, pulse waveform)", "PPG + SpO₂, palm temperature", "load cell (grip), hydrogel tape drive", "NFC reader"])
    blk(60, 526, 300, 52, "Microphone + speaker", ["voice commands and 15 s check-in"])
    blk(60, 588, 300, 52, "Synchronizer (FPGA/MCU)", ["projector slots, ToF frequencies"])
    s.text(60, 668, "No electrodes, no wearables.", "s")
    s.text(60, 684, "Voice is not used for identification.", "s")
    # external dosimeter
    blk(60, 720, 300, 62, "Station dosimeter (external)", ["LYRA does not measure radiation;", "it imports the accumulated dose"], cls="grp")
    # computer
    s.rect(440, 140, 420, 560, "grp", rx=8)
    s.text(450, 160, "LYRA ONBOARD COMPUTER", "b")
    blk(455, 172, 390, 66, "Identification", ["3D face (template updates slowly);", "if unsure → NFC card"])
    blk(455, 248, 390, 66, "3D reconstruction and metrics", ["face/calf/body volume, height, posture;", "pulse, HRV, SpO₂, grip, blood flow"])
    blk(455, 324, 390, 82, "\"Expected adaptation\" model", ["NASA/CSA bands from nasa_reference.json", "(bone 1 to 1.5 %/month, fluid shift, ...)", "+ the astronaut's personal baseline"])
    blk(455, 416, 390, 82, "Status and instructions", ["green / yellow / red: \"are you changing", "faster than NASA expects?\";", "HRP risk cards, \"what to do\" steps"])
    blk(455, 508, 390, 52, "Local storage", ["session history, encrypted"])
    blk(455, 570, 390, 66, "Downlink queue (store-and-forward)", ["session packets, red ones first,", "retry on link loss"])
    s.text(455, 662, "Runs autonomously: onboard guidance never waits for Earth.", "s")
    # outputs
    blk(930, 172, 420, 82, "Display behind the mirror panel", ["short caption + step animation,", "\"you vs NASA expectation\" charts,", "day streak (gamification)"])
    blk(930, 268, 420, 66, "Voice", ["prompts at every step; commands", "\"start\", \"repeat\", \"stop\""])
    blk(930, 360, 420, 66, "Module comm link", ["standard station/vehicle comms"])
    blk(930, 452, 420, 98, "Flight surgeon on Earth", ["receives all data automatically;", "one-way delay: ISS ~seconds,", "Moon ≈1.3 s, Mars up to 20 min", "(NASA, Distance from Earth)"])
    # arrows
    s.arrow(360, 205, 452, 205)
    s.arrow(360, 225, 452, 270)
    s.arrow(360, 305, 452, 280)
    s.arrow(360, 382, 452, 290)
    s.arrow(360, 467, 452, 300)
    s.arrow(360, 552, 452, 457)
    s.add('<line x1="360" y1="614" x2="395" y2="614" class="fl"/>')
    s.add('<line x1="395" y1="614" x2="395" y2="180" class="fl"/>')
    s.arrow(395, 180, 362, 180)
    s.text(380, 172, "sync", "s", "middle")
    s.add(f'<line x1="360" y1="751" x2="410" y2="751" class="fld"/>')
    s.add(f'<line x1="410" y1="751" x2="410" y2="365" class="fld"/>')
    s.arrow(410, 365, 452, 365, "fld")
    s.text(372, 772, "dose import", "s")
    s.arrow(650, 238, 650, 245); s.arrow(650, 314, 650, 321); s.arrow(650, 406, 650, 413)
    s.arrow(650, 498, 650, 505); s.arrow(650, 560, 650, 567)
    s.arrow(845, 440, 927, 213)
    s.arrow(845, 457, 927, 301)
    s.arrow(845, 603, 900, 603)
    s.add('<line x1="900" y1="603" x2="900" y2="393" class="fl"/>')
    s.arrow(900, 393, 927, 393)
    s.arrow(1140, 426, 1140, 449)
    s.text(1150, 442, "queue, delay", "s")
    s.arrow(927, 530, 870, 640, "fld")
    s.text(880, 664, "surgeon guidance", "s")
    s.text(880, 678, "(delayed)", "s")

    # ---------- timing diagram
    tx0, ty0 = 60, 815
    s.text(tx0, ty0, "3D scan timing (excerpt, 0 to 100 ms)", "b")
    s.text(tx0 + 300, ty0, "dot projectors take turns (patterns never overlap); ToF runs continuously, each on its own modulation frequency", "s")
    rows = ["Projector 1", "Projector 2", "Projector 3", "ToF 1 (f1)", "ToF 2 (f2)", "ToF 3…7 (f3…f7)"]
    lx, gx0, gx1 = tx0, tx0 + 110, 950
    gw = gx1 - gx0
    rh = 17
    for i, r in enumerate(rows):
        yb = ty0 + 22 + i * rh
        s.text(lx, yb, r, "s")
        s.line(gx0, yb, gx1, yb, "thin", extra='stroke="#bbb"')
        if i < 3:
            for slot in range(6):
                if slot % 3 == i:
                    xa = gx0 + slot * gw / 6 + 3
                    s.path(f"M{xa:.1f},{yb} L{xa:.1f},{yb-11} L{xa+gw/6-8:.1f},{yb-11} L{xa+gw/6-8:.1f},{yb}", "o")
        else:
            step = 6 if i == 3 else (8 if i == 4 else 5)
            pts = []
            xx = gx0
            hi = False
            while xx < gx1:
                pts.append(f"{xx:.1f},{yb - (11 if hi else 0)}")
                hi = not hi
                pts.append(f"{xx:.1f},{yb - (11 if hi else 0)}")
                xx += step
            s.add(f'<polyline points="{" ".join(pts)}" class="thin" stroke-opacity="0.8"/>')
    yb = ty0 + 22 + (len(rows) - 1) * rh + 8
    s.line(gx0, yb, gx1, yb, "thin")
    for tt in range(0, 101, 25):
        xx = gx0 + gw * tt / 100
        s.line(xx, yb - 3, xx, yb + 3, "thin")
        s.text(xx, yb + 15, f"{tt} ms" if tt == 100 else f"{tt}", "s", "middle")
    return sheet(4, "System block diagram", s.out())

# ---------------------------------------------------------------- sheet 5
def sheet5():
    s = S()
    k = 0.42
    s.text(60, 125, "A. Stowed (transport)", "vh")
    # stowed box front & side
    bx, by = 90, 180
    s.rect(bx, by, 600 * k, 400 * k, "of", rx=6)
    s.rect(bx + 30 * k, by + 30 * k, 300 * k, 340 * k, "ofd")
    s.text(bx + 180 * k, by + 200 * k, "panel", "s", "middle")
    s.rect(bx + 380 * k, by + 40 * k, 180 * k, 60 * k, "o", rx=8)
    s.rect(bx + 380 * k, by + 300 * k, 180 * k, 60 * k, "o", rx=8)
    s.text(bx + 470 * k, by + 82 * k, "left handle", "s", "middle")
    s.text(bx + 470 * k, by + 342 * k, "right handle", "s", "middle")
    s.line(bx + 380 * k, by + 200 * k, bx + 560 * k, by + 200 * k, "hid")
    s.text(bx + 470 * k, by + 190 * k, "arms folded", "s", "middle")
    # side
    sx = bx + 600 * k + 60
    s.rect(sx, by, 120 * k, 400 * k, "of", rx=4)
    s.rect(sx - 10, by, 10, 400 * k, extra='fill="url(#hatch)" stroke="none"')
    s.text(sx - 14, by - 8, "wall / seat rail", "s")
    # dims
    s.ext(bx, by + 400 * k, bx, by + 400 * k + 40); s.ext(bx + 600 * k, by + 400 * k, bx + 600 * k, by + 400 * k + 40)
    s.dim(bx, by + 400 * k + 30, bx + 600 * k, by + 400 * k + 30, "600")
    s.ext(bx, by, bx - 40, by); s.ext(bx, by + 400 * k, bx - 40, by + 400 * k)
    s.dim(bx - 30, by, bx - 30, by + 400 * k, "400", off=-2)
    s.ext(sx, by + 400 * k, sx, by + 400 * k + 40); s.ext(sx + 120 * k, by + 400 * k, sx + 120 * k, by + 400 * k + 40)
    s.dim(sx, by + 400 * k + 30, sx + 120 * k, by + 400 * k + 30, "120")
    s.text(90, 440, "Box ≈600×400×120, mass ≈6 to 8 kg (estimate).", "t")
    s.text(90, 458, "Mounts to the cabin wall or a seat rail.", "t")

    # ---------- deployed side view in capsule
    s.text(720, 125, "B. Deployed in a spacecraft / rover cabin (side view)", "vh")
    k2 = 0.27
    fx0, fy = 800, 700
    D = lambda d: fx0 + d * k2
    Z = lambda z: fy - z * k2
    s.path(f"M{D(0)},{Z(0)} L{D(0)},{Z(1500)} Q{D(0)},{Z(1750)} {D(300)},{Z(1750)} L{D(1600)},{Z(1750)}", "thick")
    s.line(D(0), Z(0), D(1600), Z(0), "thick")
    s.rect(D(0), Z(0), 1600 * k2, 8, extra='fill="url(#hatch)" stroke="none"')
    # FOV first
    s.poly([(D(720), Z(1720)), (D(780), Z(0)), (D(1250), Z(500))], "tof")
    s.poly([(D(585), Z(1300)), (D(1060), Z(1360)), (D(1060), Z(1020))], "sl")
    # wall box + panel arm
    s.rect(D(0), Z(1500), 120 * k2, 400 * k2, "of")
    s.line(D(120), Z(1250), D(550), Z(1250), "thick")
    s.rect(D(550), Z(1450), 30 * k2, 450 * k2, "ofd")
    # handle arm (telescopic) below panel
    s.line(D(120), Z(1150), D(500), Z(950), "thick")
    s.line(D(500), Z(950), D(780), Z(950), "thick")
    s.rect(D(770), Z(950) - 10, 22, 20, "ofd", rx=4)
    # ceiling clip ToF
    s.rect(D(690), Z(1750), 60 * k2, 50 * k2, "of")
    # seat
    s.path(f"M{D(900)},{Z(0)} L{D(900)},{Z(430)} L{D(1220)},{Z(430)} L{D(1300)},{Z(1200)}", "o")
    # seated astronaut
    s.circle(D(1080), Z(1190), 100 * k2, "hum")
    s.path(f"M{D(1110)},{Z(1080)} L{D(1150)},{Z(500)} L{D(820)},{Z(500)} L{D(800)},{Z(60)}", "hum")
    s.path(f"M{D(1100)},{Z(1030)} L{D(960)},{Z(870)} L{D(790)},{Z(950)}", "hum")
    # labels
    s.leader(D(720), Z(1735), 1040, 190, "", "start", lines=["clip-on ToF (handrail)"])
    s.leader(D(565), Z(1450), 900, 180, "", "end", lines=["panel 300×450", "on a swing arm"])
    s.leader(D(780), Z(950), 808, 596, "", "start", lines=["handles on", "telescopic arms"])
    s.leader(D(900), Z(1250), D(1150), Z(1500), "", "start", lines=["structured light: face"])
    s.leader(D(1250), Z(700), D(1350), Z(850), "", "start", lines=["seat / handrail"])
    s.leader(D(60), Z(1400), 790, 340, "", "end", lines=["box", "on the wall"])
    # dims
    s.ext(D(550), Z(0) + 10, D(550), Z(0) + 45); s.ext(D(1080), Z(0) + 10, D(1080), Z(0) + 45)
    s.dim(D(550), Z(0) + 36, D(1080), Z(0) + 36, "≈500 to face")
    s.ext(D(0), Z(0) + 10, D(0), Z(0) + 75); s.ext(D(1600), Z(0) + 10, D(1600), Z(0) + 75)
    s.dim(D(0), Z(0) + 66, D(1600), Z(0) + 66, "zone ≈1600 (seated or at a handrail)")

    # ---------- comparison table
    tx, ty = 60, 520
    s.text(tx, ty, "C. Station vs compact configuration", "b")
    cols = [tx, tx + 170, tx + 400]
    rows = [("", "Station (base)", "Compact (vehicle/rover)"),
            ("Frame", "3 floor-to-ceiling posts", "wall box + arms"),
            ("Panel", "≈500×900", "≈300×450"),
            ("Face", "3 dot projectors", "1 dot projector"),
            ("Body", "ToF ×7, 360° view", "ToF ×1-2, front hemisphere"),
            ("Handles", "L/R, full sensor set", "L/R, full sensor set"),
            ("Session", "90 s / 5 min", "90 s; weekly as space allows"),
            ("Deployment", "fixed", "≈1 min, tool-free"),
            ("Trade-offs", "none", "rear leg volume, 360° posture")]
    for i, r in enumerate(rows):
        yy = ty + 26 + i * 24
        for j, c in enumerate(r):
            s.text(cols[j] + 6, yy, c, "b" if (i == 0 or j == 0) else "t")
        s.line(tx, yy + 7, tx + 630, yy + 7, "thin", extra='stroke="#999"')
    s.rect(tx, ty + 8, 630, len(rows) * 24 + 2, "thin")
    s.line(cols[1], ty + 8, cols[1], ty + 10 + len(rows) * 24, "thin")
    s.line(cols[2], ty + 8, cols[2], ty + 10 + len(rows) * 24, "thin")
    s.text(tx, ty + 26 + len(rows) * 24 + 12, "Same software and \"expected adaptation\" model; compact scans are flagged \"partial scan\".", "s")
    s.text(tx, ty + 26 + len(rows) * 24 + 28, "On Earth: polar stations, submarines, remote clinics, elder care.", "s")
    return sheet(5, "Compact folding configuration", s.out())

files = {
    "01_general_view.svg": sheet1(),
    "02_front_side_fov.svg": sheet2(),
    "03_handle_section.svg": sheet3(),
    "04_system_diagram.svg": sheet4(),
    "05_compact_config.svg": sheet5(),
}
for n, c in files.items():
    with open(os.path.join(OUT, n), "w", encoding="utf-8") as f:
        f.write(c)
print("ok", list(files))
