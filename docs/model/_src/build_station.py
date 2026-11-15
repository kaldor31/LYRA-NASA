"""Build the LYRA station 3D model (v3 layout) in Blender 5.x.

Run inside Blender (Text Editor or MCP):
    exec(compile(open(PATH).read(), PATH, "exec"), {"__name__": "__main__"})

Two scenes share one station:
  V1_Empty  - empty station, hardware and sensor placement
  V2_Human  - crew member in scanning pose, structured-light grid on the body,
              3D face mesh shown on the mirror

Units: metres. Crew member stands near the origin facing +Y (toward the mirror).
Dimensions follow docs/drawings (v3): touch mirror approx. 700 x 1800 on its own
stand at 600 from the crew member, three camera pillars approx. 2000 high on
R approx. 750 (two front at +/-60 deg, one back), vertical Doppler grips on the
mirror stand legs, face module in the mirror top bezel.
"""
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

# ------------------------------------------------------------------ dimensions
MIR_HW, MIR_Z0, MIR_Z1 = 0.35, 0.10, 1.90   # mirror half width, bottom, top
MIR_Y = 0.60                                # mirror centre, distance from crew
MIR_R = 1.20                                # mirror curvature radius in plan (concave)
ARCH_Z = MIR_Z1 - MIR_HW                    # arched top starts here
MS_X, MS_Y, MS_TOP, LEG = 0.39, 0.555, 2.0, 0.05   # mirror stand legs
PIL_R, PIL_TOP, PIL_W = 0.75, 2.0, 0.08            # camera pillars
CAM_Z = (1.65, 1.15, 0.55)                         # head / torso / legs modules
PILLARS = (("Pillar_FrontR", 60.0), ("Pillar_FrontL", -60.0), ("Pillar_Back", 180.0))
CREW_Y = 0.12                               # crew stands slightly forward, palms on mirror
UI_D = 0.012                                # UI layer offset in front of the glass

CYAN = (0.0, 0.78, 1.0)
AMBER = (1.0, 0.50, 0.04)
RED = (1.0, 0.03, 0.03)
IRRED = (1.0, 0.02, 0.06)
WHITE = (0.80, 0.95, 1.0)

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else None
FONT_PATHS = (
    "/System/Library/Fonts/Supplemental/DIN Alternate Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
)

M = {}          # materials
SCR = None      # scratch collection (evaluated, then emptied)
S1 = None       # V1 scene (its view layer evaluates the scratch objects)
FONT = None


# ------------------------------------------------------------------ housekeeping
def clear_file():
    # Show an empty temp scene first: removing the scene a window displays crashes Blender.
    tmp = bpy.data.scenes.new("_tmp_build")
    wins = [w for w in bpy.context.window_manager.windows] if bpy.context.window_manager else []
    for w in wins:
        w.scene = tmp
    for sc in list(bpy.data.scenes):
        if sc != tmp:
            bpy.data.scenes.remove(sc)
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    for block in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.lights,
                  bpy.data.cameras, bpy.data.metaballs, bpy.data.worlds):
        for item in list(block):
            block.remove(item)
    for ng in list(bpy.data.node_groups):
        if ng.bl_idname == "CompositorNodeTree":
            bpy.data.node_groups.remove(ng)
    s1 = bpy.data.scenes.new("V1_Empty")
    s2 = bpy.data.scenes.new("V2_Human")
    for w in wins:
        w.scene = s1
    bpy.data.scenes.remove(tmp)
    return s1, s2


def new_coll(name, parents):
    c = bpy.data.collections.new(name)
    for p in parents:
        (p.collection if isinstance(p, bpy.types.Scene) else p).children.link(c)
    return c


def place(ob, coll):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    coll.objects.link(ob)
    return ob


def smooth(ob, angle=35):
    me = ob.data
    for p in me.polygons:
        p.use_smooth = True
    try:
        me.set_sharp_from_angle(angle=math.radians(angle))
    except Exception:
        pass


# ------------------------------------------------------------------ materials
def _bsdf(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def set_blend(m):
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "BLENDED"
    if hasattr(m, "use_transparency_overlap"):
        m.use_transparency_overlap = True


def principled(name, color, metal=0.0, rough=0.5, alpha=1.0, emit=None, estr=0.0,
               trans=0.0, coat=0.0, ior=1.45, sheen=0.0):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    b = _bsdf(m)
    vals = {"Base Color": (*color, 1.0), "Metallic": metal, "Roughness": rough,
            "Alpha": alpha, "Transmission Weight": trans, "Coat Weight": coat,
            "IOR": ior, "Sheen Weight": sheen}
    if emit:
        vals["Emission Color"] = (*emit, 1.0)
        vals["Emission Strength"] = estr
    for k, v in vals.items():
        if k in b.inputs:
            b.inputs[k].default_value = v
    m.diffuse_color = (*color, alpha)
    if alpha < 1.0 or trans > 0:
        set_blend(m)
    M[name] = m
    return m


def emissive(name, color, strength):
    m = principled(name, (0.0, 0.0, 0.0), rough=1.0, emit=color, estr=strength)
    m.diffuse_color = (*color, 1.0)
    return m


def carbon(name):
    m = principled(name, (0.02, 0.02, 0.022), rough=0.38, coat=0.7)
    nt = m.node_tree
    b = _bsdf(m)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    ck = nt.nodes.new("ShaderNodeTexChecker")
    ck.inputs["Scale"].default_value = 260.0
    ck.inputs["Color1"].default_value = (0.010, 0.010, 0.012, 1)
    ck.inputs["Color2"].default_value = (0.040, 0.041, 0.046, 1)
    nt.links.new(tc.outputs["Object"], ck.inputs["Vector"])
    nt.links.new(ck.outputs["Color"], b.inputs["Base Color"])
    return m


def scan_grid_material(name):
    """Structured-light grid: horizontal rings + meridians around the crew member."""
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])

    def op(kind, a, b=None):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = kind
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                nt.links.new(v, n.inputs[i])
        return n.outputs[0]

    rings = op("LESS_THAN", op("FRACT", op("MULTIPLY", sep.outputs["Z"], 38.0)), 0.07)
    yy = op("SUBTRACT", sep.outputs["Y"], CREW_Y)
    ang = op("ARCTAN2", sep.outputs["X"], yy)
    mer = op("LESS_THAN", op("FRACT", op("MULTIPLY", ang, 56.0 / (2 * math.pi))), 0.06)
    fac = op("MAXIMUM", rings, mer)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*CYAN, 1)
    em.inputs["Strength"].default_value = 4.0
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(fac, mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    set_blend(m)
    m.diffuse_color = (*CYAN, 0.3)
    M[name] = m
    return m


def make_materials():
    carbon("Carbon")
    principled("SpaceGrey", (0.085, 0.09, 0.10), metal=1.0, rough=0.32)
    principled("Anodized", (0.025, 0.027, 0.03), metal=1.0, rough=0.42)
    principled("Chrome", (0.62, 0.63, 0.66), metal=1.0, rough=0.12)
    principled("LensGlass", (0.004, 0.005, 0.008), rough=0.02, coat=1.0)
    principled("IRLens", (0.09, 0.0, 0.025), rough=0.04, coat=1.0)
    principled("SensorGlass", (0.006, 0.007, 0.009), rough=0.06, coat=1.0)
    principled("MirrorGlass", (0.02, 0.03, 0.04), metal=0.15, rough=0.02, alpha=0.30, ior=1.52)
    principled("Hydrogel", (0.35, 0.95, 0.80), rough=0.12, alpha=0.55, trans=0.6,
               emit=(0.1, 0.9, 0.7), estr=0.6)
    principled("Floor", (0.016, 0.017, 0.019), metal=0.4, rough=0.45)
    principled("Suit", (0.72, 0.74, 0.78), rough=0.65, sheen=0.4)
    emissive("UI_Cyan", CYAN, 7.0)
    emissive("UI_CyanDim", CYAN, 1.2)
    emissive("UI_Panel", CYAN, 0.025)
    emissive("UI_White", WHITE, 4.0)
    emissive("UI_Amber", AMBER, 7.0)
    emissive("UI_AmberDim", AMBER, 0.8)
    emissive("UI_Red", RED, 9.0)
    emissive("UI_RedFill", RED, 2.2)
    emissive("Neon_Cyan", CYAN, 12.0)
    emissive("Neon_Amber", AMBER, 10.0)
    emissive("IR_Emitter", IRRED, 5.0)
    emissive("IR_Flood", IRRED, 1.5)
    emissive("Floor_Mark", CYAN, 2.5)
    scan_grid_material("ScanGrid")


# ------------------------------------------------------------------ primitives
def mesh_obj(name, verts, faces, coll, mat=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    if mat:
        me.materials.append(mat)
    return ob


def box(name, size, loc, coll, mat, bevel=0.0, rot=(0, 0, 0), parent=None):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ob.location, ob.rotation_euler = loc, rot
    me.materials.append(mat)
    if bevel > 0:
        md = ob.modifiers.new("Bevel", "BEVEL")
        md.width, md.segments, md.limit_method = bevel, 3, "ANGLE"
        smooth(ob, 30)
    if parent:
        ob.parent = parent
    return ob


def cyl(name, r, depth, loc, coll, mat, rot=(0, 0, 0), seg=40, parent=None, r2=None):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                          radius1=r, radius2=r if r2 is None else r2, depth=depth)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ob.location, ob.rotation_euler = loc, rot
    me.materials.append(mat)
    smooth(ob, 40)
    if parent:
        ob.parent = parent
    return ob


def to_mesh(ob, name=None):
    """Evaluate a curve / text / metaball object into a plain mesh object."""
    vl = S1.view_layers[0]                 # the scratch collection lives in V1_Empty
    vl.update()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(vl.depsgraph))
    name = name or ob.name
    new = bpy.data.objects.new(name + "_m", me)
    new.matrix_basis = ob.matrix_basis.copy()
    SCR.objects.link(new)
    data = ob.data
    bpy.data.objects.remove(ob)
    try:
        if data.users == 0:
            (bpy.data.curves if isinstance(data, bpy.types.Curve) else bpy.data.metaballs).remove(data)
    except Exception:
        pass
    new.name = name
    me.name = name
    return new


# ------------------------------------------------------------------ curved mirror mapping
CEN_Y = MIR_Y - MIR_R


def bend_pt(u, z, d=0.0):
    """Flat mirror coords (u along the glass, z height, d toward the crew) -> world."""
    t = u / MIR_R
    r = MIR_R - d
    return Vector((r * math.sin(t), CEN_Y + r * math.cos(t), z))


def bend_obj(ob):
    """Mesh built flat in the XZ plane (y = -d) -> wrapped onto the curved mirror."""
    mb = ob.matrix_basis.copy()
    for v in ob.data.vertices:
        w = mb @ v.co
        v.co = bend_pt(w.x, w.z, -w.y)
    ob.matrix_basis = Matrix.Identity(4)
    ob.data.update()
    return ob


def densify(pts, step=0.01, closed=False):
    seq = list(pts) + ([pts[0]] if closed else [])
    out = []
    for a, b in zip(seq[:-1], seq[1:]):
        n = max(1, int(math.dist(a, b) / step))
        for i in range(n):
            f = i / n
            out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
    if not closed:
        out.append(seq[-1])
    return out


def rrect_pts(x0, z0, x1, z1, r, seg=6):
    r = min(r, (x1 - x0) / 2, (z1 - z0) / 2)
    if r <= 0:
        return [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
    pts = []
    for cx, cz, a0 in ((x1 - r, z0 + r, -90), (x1 - r, z1 - r, 0),
                       (x0 + r, z1 - r, 90), (x0 + r, z0 + r, 180)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return pts


def ui_fill(name, pts, mat, coll, d=UI_D, convex=True):
    raw = densify(pts, 0.015, closed=True)
    pts = []
    for p in raw:                          # drop coincident points (pill shapes)
        if not pts or math.dist(p, pts[-1]) > 1e-5:
            pts.append(p)
    if math.dist(pts[0], pts[-1]) <= 1e-5:
        pts.pop()
    n = len(pts)
    verts = [(x, -d, z) for x, z in pts]
    if convex:                             # triangle fan from the centre: clean after bending
        verts.append((sum(p[0] for p in pts) / n, -d, sum(p[1] for p in pts) / n))
        faces = [(n, i, (i + 1) % n) for i in range(n)]
    else:
        faces = [list(range(n))]
    ob = mesh_obj(name, verts, faces, SCR, mat)
    if not convex:
        bm = bmesh.new()                   # triangulate while flat, so bending keeps the shape
        bm.from_mesh(ob.data)
        bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="EAR_CLIP")
        bm.to_mesh(ob.data)
        bm.free()
    bm = bmesh.new()                       # split long chords so the surface follows the curve
    bm.from_mesh(ob.data)
    long_edges = [e for e in bm.edges if e.calc_length() > 0.02]
    if long_edges:
        bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=6, use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()
    bend_obj(ob)
    return place(ob, coll)


def ui_line(name, pts, width, mat, coll, d=UI_D, closed=False):
    pts = densify(pts, 0.008, closed=False) if not closed else densify(pts, 0.008, closed=True)
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = width
    cu.bevel_resolution = 1
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, (x, z) in zip(sp.points, pts):
        p.co = (x, -d, z, 1.0)
    sp.use_cyclic_u = closed
    cu.materials.append(mat)
    ob = bpy.data.objects.new(name, cu)
    SCR.objects.link(ob)
    ob = to_mesh(ob)
    bend_obj(ob)
    return place(ob, coll)


def ui_text(name, body, u, z, size, mat, coll, align="LEFT", d=UI_D + 0.001):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = align
    if FONT:
        cu.font = FONT
    cu.materials.append(mat)
    ob = bpy.data.objects.new(name, cu)
    SCR.objects.link(ob)
    ob.location = (u, -d, z)
    ob.rotation_euler = (math.radians(90), 0, 0)
    ob = to_mesh(ob)
    bend_obj(ob)
    return place(ob, coll)


def floor_line(name, pts, width, mat, coll, z=0.004, closed=True):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = width
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, (x, y) in zip(sp.points, pts):
        p.co = (x, y, z, 1.0)
    sp.use_cyclic_u = closed
    cu.materials.append(mat)
    ob = bpy.data.objects.new(name, cu)
    coll.objects.link(ob)
    return ob


# ------------------------------------------------------------------ station parts
def build_mirror(c):
    # curved glass with an arched top
    n = 64
    us = [-MIR_HW * math.cos(math.pi * i / n) for i in range(n + 1)]

    def top(u):
        return ARCH_Z + math.sqrt(max(MIR_HW ** 2 - u * u, 0.0))

    verts, faces = [], []
    for i, u in enumerate(us):
        verts += [bend_pt(u, MIR_Z0), bend_pt(u, top(u))]
        if i:
            a = 2 * (i - 1)
            faces.append((a, a + 2, a + 3, a + 1))
    glass = mesh_obj("Mirror_Glass", verts, faces, c, M["MirrorGlass"])
    sol = glass.modifiers.new("Thickness", "SOLIDIFY")
    sol.thickness = 0.008
    sol.offset = 0.0
    smooth(glass, 60)

    # frame + neon inner edge
    def outline(inset):
        hw, z0 = MIR_HW - inset, MIR_Z0 + inset
        pts = [(-hw, z0), (hw, z0), (hw, ARCH_Z)]
        for i in range(1, 48):
            a = math.pi * i / 48
            pts.append((hw * math.cos(a), ARCH_Z + hw * math.sin(a)))
        pts.append((-hw, ARCH_Z))
        return pts

    frame = ui_line("Mirror_Frame", outline(0.0), 0.012, M["SpaceGrey"], c, d=0.0, closed=True)
    smooth(frame, 60)
    ui_line("Mirror_NeonEdge", outline(0.018), 0.0018, M["Neon_Cyan"], c, d=0.006, closed=True)

    # face module in the top bezel: RGB + IR camera + structured IR projector + flood
    fz = 1.80
    fy = bend_pt(0, fz).y - 0.018
    box("FaceModule_Housing", (0.19, 0.026, 0.05), (0, fy, fz), c, M["Anodized"], bevel=0.008)
    box("FaceModule_Window", (0.175, 0.003, 0.038), (0, fy - 0.0135, fz), c, M["SensorGlass"], bevel=0.002)
    lens_y = fy - 0.0155
    rx = (math.radians(90), 0, 0)
    for nm, x, r, mat in (("IRProjector", -0.065, 0.006, "IR_Emitter"),
                          ("IRCamera", -0.035, 0.009, "IRLens"),
                          ("RGBCamera", 0.0, 0.011, "LensGlass"),
                          ("FloodIlluminator", 0.035, 0.006, "IR_Flood")):
        cyl(f"FaceModule_{nm}_Ring", r + 0.0025, 0.003, (x, lens_y, fz), c, M["Chrome"], rot=rx)
        cyl(f"FaceModule_{nm}", r, 0.004, (x, lens_y - 0.001, fz), c, M[mat], rot=rx)
    cyl("FaceModule_StatusLED", 0.0025, 0.003, (0.07, lens_y, fz), c, M["Neon_Amber"], rot=rx)

    # NFC reader on the frame (identification fallback)
    ui_fill("NFC_Pad", rrect_pts(0.20, 0.42, 0.31, 0.53, 0.012), M["UI_Panel"], c, d=0.004)
    ui_line("NFC_Outline", rrect_pts(0.20, 0.42, 0.31, 0.53, 0.012), 0.0012, M["UI_CyanDim"], c, closed=True)
    ui_text("NFC_Label", "NFC ID", 0.255, 0.465, 0.016, M["UI_CyanDim"], c, align="CENTER")


def build_stand(c):
    for side in (-1, 1):
        x = side * MS_X
        box(f"Stand_Leg_{'R' if side > 0 else 'L'}", (LEG, LEG, MS_TOP - 0.02),
            (x, MS_Y, (MS_TOP - 0.02) / 2 + 0.012), c, M["Carbon"], bevel=0.006)
        # floor plate bolted to the seat track
        box(f"Stand_BasePlate_{'R' if side > 0 else 'L'}", (0.16, 0.26, 0.012),
            (x, MS_Y - 0.02, 0.006), c, M["Anodized"], bevel=0.003)
        for bx in (-0.055, 0.055):
            for by in (-0.10, 0.10):
                cyl("Bolt", 0.008, 0.008, (x + bx, MS_Y - 0.02 + by, 0.014), c, M["Chrome"], seg=6)
        # brackets to the mirror frame
        for z in (0.40, 1.00, 1.45):
            box("Stand_Bracket", (0.035, 0.02, 0.03), (side * 0.363, MS_Y - 0.004, z), c,
                M["SpaceGrey"], bevel=0.003)
        build_grip(c, side)
    box("Stand_TopBar", (2 * MS_X + LEG, LEG, 0.04), (0, MS_Y, MS_TOP - 0.02), c, M["Carbon"], bevel=0.006)
    box("Stand_TopBar_Neon", (2 * MS_X, 0.003, 0.004), (0, MS_Y - LEG / 2 - 0.002, MS_TOP - 0.02), c,
        M["Neon_Cyan"])
    box("Stand_BottomBar", (2 * MS_X + LEG, LEG, 0.05), (0, MS_Y, 0.045), c, M["Carbon"], bevel=0.006)


def build_grip(c, side):
    """Vertical Doppler grip with a translucent hydrogel cassette (research module)."""
    x, gy = side * MS_X, MS_Y - LEG / 2 - 0.045
    tag = "R" if side > 0 else "L"
    z0, z1 = 0.92, 1.24
    for z in (z0 + 0.012, z1 - 0.012):
        box(f"Grip_{tag}_Standoff", (0.026, 0.05, 0.022), (x, gy + 0.025, z), c, M["SpaceGrey"], bevel=0.004)
    cyl(f"Grip_{tag}_Core", 0.017, z1 - z0, (x, gy, (z0 + z1) / 2), c, M["Anodized"])
    for z in (z0, z1):
        cyl(f"Grip_{tag}_EndCap", 0.021, 0.014, (x, gy, z), c, M["SpaceGrey"])
        cyl(f"Grip_{tag}_LEDRing", 0.0215, 0.003, (x, gy, z + (0.009 if z == z0 else -0.009)), c,
            M["Neon_Cyan"])
    # hydrogel cassette + clips
    cz0, cz1 = 1.00, 1.16
    cyl(f"Grip_{tag}_HydrogelCassette", 0.027, cz1 - cz0, (x, gy, (cz0 + cz1) / 2), c, M["Hydrogel"])
    for z in (cz0, cz1):
        cyl(f"Grip_{tag}_CassetteClip", 0.029, 0.008, (x, gy, z), c, M["Chrome"])
    # Doppler transducer facing the palm (toward the crew)
    box(f"Grip_{tag}_DopplerTransducer", (0.016, 0.004, 0.11), (x, gy - 0.019, (cz0 + cz1) / 2), c,
        M["Neon_Amber"])


def build_pillar(c, name, ang):
    a = math.radians(ang)
    pos = Vector((PIL_R * math.sin(a), PIL_R * math.cos(a), 0.0))
    e = bpy.data.objects.new(name, None)
    c.objects.link(e)
    e.empty_display_type = "PLAIN_AXES"
    e.empty_display_size = 0.15
    e.location = pos
    e.rotation_euler = (0, 0, math.atan2(pos.x, -pos.y))   # local +Y toward the crew
    w = PIL_W
    box(f"{name}_Column", (w, w, PIL_TOP - 0.05), (0, 0, (PIL_TOP - 0.05) / 2 + 0.02), c, M["Carbon"],
        bevel=0.008, parent=e)
    box(f"{name}_Cap", (w + 0.02, w + 0.02, 0.035), (0, 0, PIL_TOP - 0.0175), c, M["SpaceGrey"],
        bevel=0.006, parent=e)
    box(f"{name}_CapNeon", (w + 0.022, w + 0.022, 0.004), (0, 0, PIL_TOP - 0.04), c, M["Neon_Cyan"],
        parent=e)
    cyl(f"{name}_BasePlate", 0.13, 0.014, (0, 0, 0.007), c, M["Anodized"], parent=e, seg=48)
    box(f"{name}_Collar", (w + 0.024, w + 0.024, 0.05), (0, 0, 0.04), c, M["SpaceGrey"], bevel=0.005,
        parent=e)
    for i in range(4):
        t = math.radians(45 + 90 * i)
        cyl(f"{name}_Bolt", 0.009, 0.008, (0.1 * math.cos(t), 0.1 * math.sin(t), 0.018), c,
            M["Chrome"], seg=6, parent=e)
    for sx in (-1, 1):
        box(f"{name}_NeonStrip", (0.003, 0.002, PIL_TOP - 0.2), (sx * 0.031, w / 2 + 0.001, PIL_TOP / 2),
            c, M["Neon_Cyan"], parent=e)
    rx = (math.radians(-90), 0, 0)
    for z, lvl in zip(CAM_Z, ("Head", "Torso", "Legs")):
        build_camera_module(c, e, f"{name}_Cam{lvl}", z, rx)
    return e


def build_camera_module(c, parent, name, z, rx):
    """RGB camera + IR depth camera + structured-light IR projector + flood illuminator."""
    fy = PIL_W / 2
    box(f"{name}_Housing", (0.112, 0.05, 0.16), (0, fy + 0.02, z), c, M["SpaceGrey"], bevel=0.009,
        parent=parent)
    box(f"{name}_Window", (0.096, 0.004, 0.142), (0, fy + 0.046, z), c, M["SensorGlass"], bevel=0.003,
        parent=parent)
    ly = fy + 0.049
    for nm, x, dz, r, mat in (("RGB", 0.0, 0.035, 0.017, "LensGlass"),
                              ("IRCam", -0.026, -0.026, 0.011, "IRLens"),
                              ("IRProjector", 0.026, -0.026, 0.008, "IR_Emitter"),
                              ("Flood", 0.0, -0.058, 0.005, "IR_Flood")):
        cyl(f"{name}_{nm}_Ring", r + 0.003, 0.004, (x, ly, z + dz), c, M["Chrome"], rot=rx, parent=parent)
        cyl(f"{name}_{nm}", r, 0.005, (x, ly + 0.001, z + dz), c, M[mat], rot=rx, parent=parent)
    cyl(f"{name}_StatusLED", 0.0028, 0.004, (0.038, ly, z + 0.064), c, M["Neon_Amber"], rot=rx,
        parent=parent)


def build_floor(c):
    box("Floor", (14, 14, 0.02), (0, 0, -0.01), c, M["Floor"])
    cyl("Platform", 1.02, 0.008, (0, 0.05, 0.004), c, M["Carbon"], seg=96)
    ring = [(PIL_R * math.cos(2 * math.pi * i / 120), PIL_R * math.sin(2 * math.pi * i / 120))
            for i in range(120)]
    floor_line("Platform_PillarRing", ring, 0.0025, M["Floor_Mark"], c, z=0.009)
    # seat tracks (ISS-style rails the bases bolt to)
    for y in (-0.75, 0.43):
        box("SeatTrack", (2.4, 0.03, 0.012), (0, y, 0.011), c, M["SpaceGrey"], bevel=0.002)
    # foot contours
    for sx in (-1, 1):
        cx, cy = sx * 0.115, CREW_Y + 0.07
        pts = []
        for i in range(48):
            t = 2 * math.pi * i / 48
            half_w = 0.048 if math.sin(t) > 0 else 0.040
            pts.append((cx + half_w * math.cos(t) + sx * 0.008 * math.sin(t), cy + 0.135 * math.sin(t)))
        floor_line(f"FootContour_{'R' if sx > 0 else 'L'}", pts, 0.0022, M["Floor_Mark"], c, z=0.009)


HAND_MM = [(35, 0), (42, 40), (46, 80), (48, 118), (43, 134), (35, 130), (32, 100), (31, 148),
           (25, 161), (16, 157), (13, 104), (10, 163), (2, 175), (-7, 168), (-8, 104), (-13, 157),
           (-21, 165), (-29, 156), (-29, 98), (-36, 84), (-52, 96), (-68, 110), (-77, 104),
           (-72, 90), (-56, 62), (-42, 30), (-35, 0)]


def build_ui(c):
    """Mirror interface: readiness 1-10, rPPG waveform, stress bars, posture, advice, SOS."""
    cy, cyd, wh, am = M["UI_Cyan"], M["UI_CyanDim"], M["UI_White"], M["UI_Amber"]
    L, R = -0.30, 0.30
    # header
    ui_text("UI_Logo", "LYRA", L, 1.655, 0.034, cy, c)
    ui_text("UI_Title", "CREW READINESS CHECK", L + 0.105, 1.66, 0.0145, wh, c)
    ui_text("UI_Clock", "SOL 142  06:42 UTC", R, 1.66, 0.013, cyd, c, align="RIGHT")
    ui_line("UI_HeaderRule", [(L, 1.645), (R, 1.645)], 0.0007, cyd, c)
    # readiness 1-10
    ui_text("UI_ReadyLabel", "READINESS", L, 1.605, 0.013, cyd, c)
    ui_text("UI_ReadyValue", "8", L, 1.475, 0.115, cy, c)
    ui_text("UI_ReadyMax", "/10", L + 0.075, 1.48, 0.034, cyd, c)
    ui_text("UI_ReadyStatus", "GO  /  NOMINAL", L + 0.165, 1.585, 0.0125, am, c, align="CENTER")
    seg_w = (0.28 - 9 * 0.004) / 10
    for i in range(10):
        x0 = L + i * (seg_w + 0.004)
        ui_fill(f"UI_ReadySeg{i + 1}", rrect_pts(x0, 1.448, x0 + seg_w, 1.458, 0.002),
                cy if i < 8 else M["UI_Panel"], c)
    ui_text("UI_ReadyMin", "1", L, 1.430, 0.009, cyd, c)
    ui_text("UI_ReadyTop", "10", L + 0.28, 1.430, 0.009, cyd, c, align="RIGHT")
    # face mesh panel (content differs per version)
    ui_fill("UI_FacePanel", rrect_pts(0.02, 1.43, R, 1.625, 0.01), M["UI_Panel"], c, d=UI_D - 0.001)
    ui_line("UI_FacePanelOutline", rrect_pts(0.02, 1.43, R, 1.625, 0.01), 0.0008, cyd, c, closed=True)
    ui_text("UI_FacePanelLabel", "3D FACE MESH  /  IR DEPTH", 0.032, 1.607, 0.0105, cyd, c)
    # cardiac waveform (rPPG from the face camera)
    ui_text("UI_PulseLabel", "PULSE  (rPPG, FACE)", L, 1.398, 0.0115, cyd, c)
    ui_text("UI_PulseValue", "68 BPM", R, 1.398, 0.0135, cy, c, align="RIGHT")
    shape = [(0, 0), (0.10, 0), (0.14, 0.10), (0.18, 0), (0.30, 0), (0.33, -0.12), (0.36, 1.0),
             (0.39, -0.30), (0.42, 0), (0.55, 0), (0.62, 0.22), (0.70, 0), (1.0, 0)]
    beats, base, amp = 4, 1.322, 0.05
    span = (R - L) / beats
    ecg = []
    for b in range(beats):
        for f, v in shape:
            if b and f == 0:
                continue
            ecg.append((L + span * (b + f), base + amp * v))
    ui_line("UI_PulseWave", ecg, 0.0011, cy, c)
    ui_line("UI_PulseBase", [(L, base - 0.025), (R, base - 0.025)], 0.0004, cyd, c)
    # palm contours (pose standardisation, not a sensor)
    for sx in (-1, 1):
        pts = [(sx * 0.22 + sx * x * 0.00105, 1.02 + z * 0.00105) for x, z in HAND_MM]
        if sx < 0:
            pts = pts[::-1]
        tag = "R" if sx > 0 else "L"
        ui_fill(f"UI_PalmFill_{tag}", pts, M["UI_Panel"], c, d=UI_D - 0.001, convex=False)
        ui_line(f"UI_PalmContour_{tag}", pts, 0.0014, cy, c, closed=True)
    ui_text("UI_PalmHint", "PLACE PALMS", 0, 1.003, 0.0095, cyd, c, align="CENTER")
    # stress / fatigue / recovery bars between the palms
    for i, (lbl, val, mat) in enumerate((("STRESS", 0.32, am), ("FATIGUE", 0.24, cy),
                                         ("RECOVERY", 0.82, cy))):
        z = 1.205 - i * 0.055
        ui_text(f"UI_Bar{lbl}_Label", lbl, -0.115, z + 0.012, 0.0105, cyd, c)
        ui_text(f"UI_Bar{lbl}_Value", f"{int(val * 100)}%", 0.115, z + 0.012, 0.0105, wh, c, align="RIGHT")
        ui_fill(f"UI_Bar{lbl}_Track", rrect_pts(-0.115, z, 0.115, z + 0.007, 0.0035), M["UI_Panel"], c,
                d=UI_D - 0.001)
        ui_fill(f"UI_Bar{lbl}_Fill", rrect_pts(-0.115, z, -0.115 + 0.23 * val, z + 0.007, 0.0035), mat, c)
    # posture overlay
    ui_text("UI_PostureLabel", "POSTURE", L, 0.975, 0.0115, cyd, c)
    px = -0.235
    ui_line("UI_PostureRef", [(px, 0.84), (px, 0.955)], 0.0004, cyd, c)
    ui_line("UI_PostureHead", [(px + 0.012 * math.cos(t), 0.94 + 0.012 * math.sin(t))
                               for t in [2 * math.pi * i / 24 for i in range(24)]], 0.0009, cy, c, closed=True)
    ui_line("UI_PostureSpine", [(px, 0.927), (px + 0.002, 0.875)], 0.0009, cy, c)
    ui_line("UI_PostureShoulders", [(px - 0.035, 0.918), (px + 0.035, 0.912)], 0.0011, am, c)
    ui_line("UI_PostureHips", [(px - 0.022, 0.875), (px + 0.022, 0.875)], 0.0009, cy, c)
    for sx in (-1, 1):
        ui_line("UI_PostureArm", [(px + sx * 0.035, 0.915 - (0.003 if sx > 0 else 0)),
                                  (px + sx * 0.045, 0.875)], 0.0008, cyd, c)
        ui_line("UI_PostureLeg", [(px + sx * 0.02, 0.875), (px + sx * 0.024, 0.835)], 0.0008, cyd, c)
    ui_text("UI_PostureTilt", "SHOULDER TILT 1.8 deg", -0.175, 0.92, 0.0095, am, c)
    ui_text("UI_PostureSpineTxt", "SPINE  ALIGNED", -0.175, 0.90, 0.0095, cy, c)
    ui_text("UI_PostureBase", "vs BASELINE: +0.6 cm", -0.175, 0.88, 0.0095, cyd, c)
    # recommendations
    ui_text("UI_AdviceLabel", "RECOMMENDATIONS", 0.04, 0.975, 0.0115, cyd, c)
    for i, line in enumerate(("> Hydrate 300 ml", "> 10 min spine mobility", "> Re-scan after sleep")):
        ui_text(f"UI_Advice{i + 1}", line, 0.04, 0.945 - i * 0.025, 0.0115, wh if i else am, c)
    # emergency medical call
    btn = rrect_pts(-0.17, 0.70, 0.17, 0.78, 0.02)
    ui_fill("UI_SOS_Fill", btn, M["UI_RedFill"], c)
    ui_line("UI_SOS_Outline", btn, 0.0016, M["UI_Red"], c, closed=True)
    ui_text("UI_SOS_Label", "EMERGENCY MEDICAL CALL", 0, 0.731, 0.0175, M["UI_White"], c, align="CENTER",
            d=UI_D + 0.002)


def build_face_mask(c):
    """Generated 3D face mesh shown on the mirror (V2): wireframe hologram."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=22, v_segments=16, radius=1.0)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y > 0.25], context="VERTS")
    for v in bm.verts:
        x, y, z = v.co
        if y < -0.55 and abs(x) < 0.22 and -0.45 < z < 0.2:        # nose
            y -= 0.28 * (1 - abs(x) / 0.22) * (1 - abs(z + 0.12) / 0.33)
        for ex in (-0.36, 0.36):                                    # eye sockets
            dd = math.hypot(x - ex, z - 0.18)
            if dd < 0.2 and y < 0:
                y += 0.12 * (1 - dd / 0.2)
        if z < -0.3:                                                # jaw / chin
            x *= 1 - 0.5 * (-0.3 - z)
        v.co = Vector((x * 0.74, y * 0.6, z * 1.0))
    me = bpy.data.meshes.new("UI_FaceMesh")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("UI_FaceMesh", me)
    c.objects.link(ob)
    me.materials.append(M["UI_Cyan"])
    ob.scale = (0.062, 0.062, 0.062)
    u = 0.16
    ob.location = bend_pt(u, 1.515, 0.045)
    ob.rotation_euler = (0, 0, -u / MIR_R)
    wf = ob.modifiers.new("Wire", "WIREFRAME")
    wf.thickness = 0.012
    wf.use_replace = True
    return ob


def build_v1_ui(c):
    ui_text("UI_FaceIdle", "AWAITING CREW", 0.16, 1.515, 0.0145, M["UI_CyanDim"], c, align="CENTER")
    ui_text("UI_FaceIdle2", "step in  /  scan  /  know", 0.16, 1.49, 0.0095, M["UI_CyanDim"], c,
            align="CENTER")


def build_v2_ui(c):
    build_face_mask(c)
    ui_text("UI_FaceStatus", "IR DOTS 30k  /  MESH OK", 0.16, 1.44, 0.0095, M["UI_Amber"], c, align="CENTER")
    ui_text("UI_ScanStatus", "SCAN 3/3 PILLARS SYNCED", 0.16, 1.585, 0.0095, M["UI_Cyan"], c, align="CENTER")


# ------------------------------------------------------------------ crew member (V2)
def capsule(mb, a, b, r):
    a, b = Vector(a), Vector(b)
    e = mb.elements.new(type="CAPSULE")
    e.co = (a + b) / 2
    e.radius = r
    e.size_x = (b - a).length / 2
    e.rotation = Vector((1, 0, 0)).rotation_difference((b - a).normalized())
    return e


def ellipsoid(mb, co, r, sx, sy, sz):
    e = mb.elements.new(type="ELLIPSOID")
    e.co, e.radius = co, r
    e.size_x, e.size_y, e.size_z = sx, sy, sz
    return e


def build_human(c):
    mb = bpy.data.metaballs.new("Crew")
    mb.resolution = 0.02
    mb.render_resolution = 0.01
    y = CREW_Y
    ellipsoid(mb, (0, y + 0.03, 1.665), 0.115, 0.82, 0.92, 1.05)                # head
    capsule(mb, (0, y + 0.01, 1.52), (0, y + 0.02, 1.59), 0.065)               # neck
    ellipsoid(mb, (0, y, 1.29), 0.215, 1.05, 0.62, 1.15)                        # chest
    ellipsoid(mb, (0, y, 1.02), 0.20, 1.0, 0.70, 0.75)                         # pelvis
    ellipsoid(mb, (0, y, 1.15), 0.17, 0.95, 0.62, 0.9)                         # abdomen
    capsule(mb, (-0.17, y + 0.01, 1.45), (0.17, y + 0.01, 1.45), 0.08)        # shoulders
    for s in (-1, 1):
        sh, el, wr = (s * 0.19, y + 0.02, 1.43), (s * 0.215, y + 0.24, 1.26), (s * 0.22, y + 0.415, 1.06)
        capsule(mb, sh, el, 0.068)
        capsule(mb, el, wr, 0.057)
        ellipsoid(mb, (s * 0.22, 0.548, 1.10), 0.05, 1.0, 0.36, 1.15)           # palm on the contour
        capsule(mb, (s * 0.218, 0.552, 1.14), (s * 0.218, 0.556, 1.185), 0.028)  # fingers (glove)
        capsule(mb, (s * 0.19, 0.546, 1.09), (s * 0.165, 0.548, 1.125), 0.016)   # thumb
        capsule(mb, wr, (s * 0.22, 0.53, 1.07), 0.04)
        hip, kn, an = (s * 0.10, y, 0.95), (s * 0.11, y + 0.01, 0.52), (s * 0.115, y, 0.10)
        capsule(mb, hip, kn, 0.098)
        capsule(mb, kn, an, 0.074)
        capsule(mb, (s * 0.115, y - 0.03, 0.05), (s * 0.12, y + 0.17, 0.05), 0.062)  # boot
    ob = bpy.data.objects.new("Crew", mb)
    SCR.objects.link(ob)
    ob = to_mesh(ob, "Crew_Body")
    ob.data.materials.clear()
    ob.data.materials.append(M["Suit"])
    smooth(ob, 80)
    place(ob, c)
    # structured-light grid: a slightly inflated shell with the grid shader
    grid = bpy.data.objects.new("Crew_ScanGrid", ob.data.copy())
    c.objects.link(grid)
    grid.data.materials.clear()
    grid.data.materials.append(M["ScanGrid"])
    dsp = grid.modifiers.new("Inflate", "DISPLACE")
    dsp.strength = 0.003
    # cyan projector wash from every camera module
    tgt = bpy.data.objects.new("ScanTarget", None)
    c.objects.link(tgt)
    tgt.location = (0, CREW_Y, 1.15)
    for name, ang in PILLARS:
        a = math.radians(ang)
        for z in CAM_Z:
            ld = bpy.data.lights.new(f"{name}_IRWash", "SPOT")
            ld.energy, ld.color = 12.0, CYAN
            ld.spot_size, ld.spot_blend = math.radians(55), 0.9
            lo = bpy.data.objects.new(f"{name}_IRWash", ld)
            c.objects.link(lo)
            lo.location = ((PIL_R - 0.1) * math.sin(a), (PIL_R - 0.1) * math.cos(a), z)
            tc = lo.constraints.new("TRACK_TO")
            tc.target, tc.track_axis, tc.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
    return ob


# ------------------------------------------------------------------ lights, cameras, render
def area(c, name, loc, target, energy, color, size):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy, ld.color, ld.size = energy, color, size
    ob = bpy.data.objects.new(name, ld)
    c.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    for attr in ("visible_glossy", "visible_camera"):   # no light panels mirrored in the glass
        if hasattr(ob, attr):
            setattr(ob, attr, False)
    return ob


def camera(c, name, loc, target, lens=35):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    ob = bpy.data.objects.new(name, cd)
    c.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


def build_env(c, scenes):
    world = bpy.data.worlds.new("LYRA_Dark")
    try:
        world.use_nodes = True
    except Exception:
        pass
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.004, 0.005, 0.008, 1)
    bg.inputs["Strength"].default_value = 1.0
    area(c, "Key_Cool", (-2.4, -1.8, 3.0), (0, 0.2, 1.0), 260, (0.82, 0.9, 1.0), 1.6)
    area(c, "Rim_Amber", (2.3, 2.4, 2.3), (0, 0.2, 1.0), 320, (1.0, 0.55, 0.2), 1.2)
    area(c, "Rim_Cyan", (-2.2, 2.6, 1.9), (0, 0.2, 1.0), 260, (0.2, 0.75, 1.0), 1.2)
    area(c, "Top_Soft", (0, 0.0, 3.3), (0, 0.0, 0.0), 90, (0.9, 0.95, 1.0), 2.5)
    cam_hero = camera(c, "Cam_Hero", (1.95, -2.35, 1.62), (0.0, 0.38, 1.12), lens=32)
    camera(c, "Cam_Front", (-1.45, 2.85, 1.70), (0.0, 0.25, 1.05), lens=30)
    camera(c, "Cam_MirrorUI", (0.0, -0.55, 1.30), (0.0, 0.6, 1.24), lens=35)
    for sc in scenes:
        sc.world = world
        sc.camera = cam_hero
        setup_render(sc)


def setup_render(sc):
    r = sc.render
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            r.engine = eng
            break
        except TypeError:
            continue
    r.resolution_x, r.resolution_y, r.resolution_percentage = 1920, 1080, 100
    try:
        sc.eevee.taa_render_samples = 96
        sc.eevee.use_raytracing = True
        sc.eevee.use_shadows = True
    except Exception:
        pass
    vs = sc.view_settings
    try:
        vs.view_transform = "AgX"
        looks = [i.identifier for i in vs.bl_rna.properties["look"].enum_items]
        for want in ("AgX - Punchy", "AgX - High Contrast", "Punchy"):
            if want in looks:
                vs.look = want
                break
    except Exception:
        pass
    vs.exposure = 0.0
    setup_glare(sc)


def setup_glare(sc):
    """Neon bloom via the compositor (Blender 5 node-group API, 4.x fallback)."""
    try:
        if hasattr(sc, "compositing_node_group"):
            ng = bpy.data.node_groups.new(f"{sc.name}_Bloom", "CompositorNodeTree")
            ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
            sc.compositing_node_group = ng
            out = ng.nodes.new("NodeGroupOutput")
        else:
            sc.use_nodes = True
            ng = sc.node_tree
            ng.nodes.clear()
            out = ng.nodes.new("CompositorNodeComposite")
        rl = ng.nodes.new("CompositorNodeRLayers")
        rl.scene = sc                      # otherwise it renders the first scene
        gl = ng.nodes.new("CompositorNodeGlare")
        if hasattr(gl, "glare_type"):
            gl.glare_type = "FOG_GLOW"
            gl.quality = "HIGH"
            gl.threshold = 1.0
            gl.size = 7
        else:
            for k, v in (("Type", "Fog Glow"), ("Quality", "High"), ("Threshold", 1.0),
                         ("Strength", 0.6), ("Size", 0.6)):
                if k in gl.inputs:
                    try:
                        gl.inputs[k].default_value = v
                    except Exception as ex:
                        print("glare input", k, ex)
        ng.links.new(rl.outputs["Image"], gl.inputs["Image"])
        ng.links.new(gl.outputs["Image"], out.inputs[0])
    except Exception as ex:
        print("glare skipped:", ex)


# ------------------------------------------------------------------ main
RENDERS = {"V1_Empty": ("Cam_Hero", "Cam_Front", "Cam_MirrorUI"),
           "V2_Human": ("Cam_Hero", "Cam_Front", "Cam_MirrorUI")}


def render_all(out_dir, percent=100, samples=96):
    os.makedirs(out_dir, exist_ok=True)
    for sc_name, cams in RENDERS.items():
        sc = bpy.data.scenes[sc_name]
        sc.render.resolution_percentage = percent
        sc.eevee.taa_render_samples = samples
        for cam in cams:
            sc.camera = bpy.data.objects[cam]
            sc.render.filepath = os.path.join(out_dir, f"{sc_name}_{cam}.png")
            with bpy.context.temp_override(scene=sc, view_layer=sc.view_layers[0]):
                bpy.ops.render.render(write_still=True, scene=sc.name)
            print("rendered", sc.render.filepath)
        sc.camera = bpy.data.objects["Cam_Hero"]
        sc.render.resolution_percentage, sc.eevee.taa_render_samples = 100, 96


def export_glb(out_dir):
    """One GLB per version (modifiers applied). The scan-grid shader cannot be expressed
    in glTF, so the grid shell is left out; procedural carbon exports as flat dark."""
    os.makedirs(out_dir, exist_ok=True)
    grid = bpy.data.objects.get("Crew_ScanGrid")
    if grid:
        grid.hide_render = True
    for sc_name in RENDERS:
        sc = bpy.data.scenes[sc_name]
        path = os.path.join(out_dir, f"LYRA_{sc_name}.glb")
        with bpy.context.temp_override(scene=sc, view_layer=sc.view_layers[0]):
            bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_active_scene=True,
                                      use_renderable=True, export_apply=True, export_lights=False,
                                      export_cameras=False, export_yup=True)
        print("glb", path, round(os.path.getsize(path) / 1e6, 2), "MB")
    if grid:
        grid.hide_render = False


def cli():
    """blender -b --factory-startup --python build_station.py -- [--save F.blend] [--render DIR]
    [--glb DIR] [--preview]"""
    import sys
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    build()
    if "--render" in argv:
        pv = "--preview" in argv
        render_all(argv[argv.index("--render") + 1], percent=40 if pv else 100, samples=16 if pv else 96)
    if "--glb" in argv:
        export_glb(argv[argv.index("--glb") + 1])
    if "--save" in argv:
        path = os.path.abspath(argv[argv.index("--save") + 1])
        bpy.context.window_manager  # noqa
        bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
        print("saved", path)


def build():
    global SCR, FONT, S1
    s1, s2 = clear_file()
    S1 = s1
    SCR = new_coll("_scratch", [s1])
    FONT = None
    for p in FONT_PATHS:
        if os.path.exists(p):
            try:
                FONT = bpy.data.fonts.load(p, check_existing=True)
                break
            except Exception:
                pass
    make_materials()
    st = new_coll("LYRA_Station", [s1, s2])
    c_mirror = new_coll("Mirror_Stand", [st])
    c_ui = new_coll("Mirror_UI", [st])
    c_pil = new_coll("Camera_Pillars", [st])
    c_floor = new_coll("Floor_Platform", [st])
    c_env = new_coll("Lights_Cameras", [s1, s2])
    c_v1 = new_coll("V1_Only", [s1])
    c_v2 = new_coll("V2_Only", [s2])

    build_floor(c_floor)
    build_mirror(c_mirror)
    build_stand(c_mirror)
    for name, ang in PILLARS:
        build_pillar(c_pil, name, ang)
    build_ui(c_ui)
    build_v1_ui(c_v1)
    build_v2_ui(c_v2)
    build_human(c_v2)
    build_env(c_env, [s1, s2])

    bpy.data.collections.remove(SCR)
    print("objects:", len(bpy.data.objects))


if __name__ == "__main__":
    if bpy.app.background:
        cli()
    else:
        build()
