"""Live camera demo (lyra.feasibility.vision.live) without a camera: MediaPipe is replaced by fake landmarks."""
import math
import types

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")
live = pytest.importorskip("lyra.feasibility.vision.live")


def fake_face(scale=1.0, t=0.0):
    """478 landmarks shaped roughly like a face (normalized coords), with a 1.2 Hz skin-tone pulse handled by the image."""
    pts = []
    for i in range(478):
        a = i * 2.399963
        r = 0.12 * math.sqrt(i / 478)
        pts.append(types.SimpleNamespace(x=0.5 + r * math.cos(a) * scale, y=0.45 + r * 1.3 * math.sin(a), z=-0.02 * (1 - r / 0.12)))
    F = live.face
    def put(i, x, y):
        pts[i].x, pts[i].y = x, y
    put(F.CHEEK_L, 0.5 - 0.09 * scale, 0.45); put(F.CHEEK_R, 0.5 + 0.09 * scale, 0.45)
    put(F.JAW_L, 0.5 - 0.08 * scale, 0.52); put(F.JAW_R, 0.5 + 0.08 * scale, 0.52)
    put(F.NOSE_TIP, 0.5, 0.47); put(F.IRIS_L, 0.47, 0.42); put(F.IRIS_R, 0.53, 0.42)
    for idx, x0 in ((F.LEFT_EYE, 0.47), (F.RIGHT_EYE, 0.53)):
        p1, p2, p3, p4, p5, p6 = idx
        put(p1, x0 - 0.015, 0.42); put(p4, x0 + 0.015, 0.42)
        put(p2, x0 - 0.005, 0.415); put(p3, x0 + 0.005, 0.415); put(p5, x0 + 0.005, 0.425); put(p6, x0 - 0.005, 0.425)
    put(F.MOUTH_TOP, 0.5, 0.5); put(F.MOUTH_BOTTOM, 0.5, 0.505); put(F.MOUTH_L, 0.48, 0.5); put(F.MOUTH_R, 0.52, 0.5)
    put(F.ROI_FOREHEAD, 0.5, 0.36); put(F.ROI_CHEEK_L, 0.46, 0.47); put(F.ROI_CHEEK_R, 0.54, 0.47)
    put(live.CHEEKBONE_L, 0.5 - 0.1 * scale, 0.45); put(live.CHEEKBONE_R, 0.5 + 0.1 * scale, 0.45)
    return pts


class FakeMesh:
    def __init__(self, scale): self.scale = scale
    def process(self, rgb): return types.SimpleNamespace(multi_face_landmarks=[types.SimpleNamespace(landmark=fake_face(self.scale))])


class NoPose:
    def process(self, rgb): return types.SimpleNamespace(pose_landmarks=None)


def fake_depth():
    """Portrait TrueDepth-like map: face plane at 0.40 m, nose tip 20 mm closer. K for this size."""
    d = np.full((640, 480), 0.40, np.float32)
    v, u = int(0.47 * 640), int(0.5 * 480)
    d[v - 6:v + 7, u - 6:u + 7] = 0.38
    K = np.array([[500.0, 0, 240.0], [0, 500.0, 320.0], [0, 0, 1]])
    return d, K


def run_scan(L, kind, scale, bpm=72.0, depth=None):
    L.start_scan(kind)
    fps = 30.0
    t0 = L.scan["t0"]
    for i in range(int(live.SCAN_S * fps) + 2):
        t = t0 + i / fps
        img = np.full((720, 1280, 3), 128, np.uint8)
        ph = math.sin(2 * math.pi * bpm / 60 * t)  # skin pulse: strongest in green (BGR order)
        img[..., 1] = np.uint8(round(128 + 3 * ph)); img[..., 2] = np.uint8(round(150 + 1 * ph))
        d, K = (None, None) if depth is None else depth
        L._frame(cv2, FakeMesh(scale), NoPose(), img, t, i + 1, fps, d, K)
    return L.last_scan


def test_scan_baseline_then_compare():
    L = live.Live(camera=-1)
    L._last_pose, L._last_hr_t, L._hr = None, 0.0, (None, 0.0, [])
    L.state = {"t": 0.0}
    L._clock = 0.0
    st, mesh, _, _ = L.snapshot()
    base = run_scan(L, "baseline", 1.0)
    assert base["status"] == "baseline", base
    assert L.baseline is not None
    hr = base["metrics"]["hr_rppg"]
    assert hr["value"] is not None and abs(hr["value"] - 72) < 4
    same = run_scan(L, "scan", 1.0)
    assert same["status"] == "green" and abs(same["face_ratio_change_pct"]) < 0.5
    wide = run_scan(L, "scan", 1.06)
    assert wide["status"] == "red" and wide["face_ratio_change_pct"] > 4
    st, mesh, last, has_base = L.snapshot()
    assert has_base and len(mesh) == 468 and st["gate"]["face"]


def test_gate_and_classify_retry():
    assert live.gate({"face": False})["ok"] is False
    g = live.gate({"face": True, "frontal": True, "luma": 120, "motion": 0.0})
    assert g["ok"]
    res = {"quality": {"reasons": ["too much motion"]}, "metrics": {"face_ratio": {"value": 1.9}}}
    status, why = live.classify(res, None)
    assert status == "retry" and "Measurement not confirmed" in why
    m = live.metric((70.0, 0.1), 0.35, "bpm")
    assert m["value"] is None and m["note"] == "Measurement not confirmed"


def test_truedepth_lift_and_metrics():
    d, K = fake_depth()
    xy = np.array([(q.x, q.y) for q in fake_face(1.0)])
    P = live.lift_to_3d(xy, d, K)
    m = live.face_3d_metrics(P)
    assert m is not None
    assert abs(m["face_width_mm"] - 0.2 * 480 * 0.40 / 500 * 1000) < 1.0   # 76.8 mm
    assert abs(m["nose_depth_mm"] - 20.0) < 1.0
    assert abs(m["distance_cm"] - 38.0) < 0.5
    # background behind the face is rejected
    d2 = d.copy(); d2[:, :int(0.42 * 480)] = 1.4
    assert live.face_3d_metrics(live.lift_to_3d(xy, d2, K)) is None


def test_scan_with_depth_uses_measured_width():
    L = live.Live(camera=-1)
    L._last_pose, L._last_hr_t, L._hr = None, 0.0, (None, 0.0, [])
    L.state = {"t": 0.0}
    base = run_scan(L, "baseline", 1.0, depth=fake_depth())
    assert base["status"] == "baseline" and base["metrics"]["face_width_mm"]["value"] is not None
    wide = run_scan(L, "scan", 1.06, depth=fake_depth())
    assert wide["status"] == "red" and "IR depth" in wide["why"] and wide["face_width_change_pct"] > 4
    st, mesh, _, _ = L.snapshot()
    assert st["depth"] and st["mesh_measured"] and "face_width_mm" in st


def test_depth_holes_on_eyes_and_nan_safe_json():
    d, K = fake_depth()
    pts = fake_face(1.0)
    for i in (live.face.IRIS_L, live.face.IRIS_R):  # TrueDepth often has no depth on the eyes
        v, u = int(pts[i].y * 640), int((1 - pts[i].x) * 480)
        d[v - 8:v + 9, u - 8:u + 9] = 0.0
    m = live.face_3d_metrics(live.lift_to_3d(np.array([(q.x, q.y) for q in pts]), d, K))
    assert m is not None and m["ipd_mm"] is None and m["face_width_mm"] > 0
    out = live.clean({"a": float("nan"), "b": [np.float32(1.5), np.int64(2), np.bool_(True)]})
    assert out == {"a": None, "b": [1.5, 2, True]}


def test_display_mesh_fills_depth_holes():
    d, K = fake_depth()
    pts = fake_face(1.0)
    xy = np.array([(q.x, q.y) for q in pts])
    z_rel = np.array([q.z for q in pts])
    d[: int(0.44 * 640), :] = 0.0  # no depth on the upper part of the face
    P, Pf = live.lift_to_3d(xy, d, K, z_rel=z_rel)
    assert np.isnan(P[:, 2]).any() and Pf is not None and np.isfinite(Pf).all()
    assert np.allclose(Pf[np.isfinite(P[:, 2])], P[np.isfinite(P[:, 2])])  # measured points unchanged
