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
    return pts


class FakeMesh:
    def __init__(self, scale): self.scale = scale
    def process(self, rgb): return types.SimpleNamespace(multi_face_landmarks=[types.SimpleNamespace(landmark=fake_face(self.scale))])


class NoPose:
    def process(self, rgb): return types.SimpleNamespace(pose_landmarks=None)


def run_scan(L, kind, scale, bpm=72.0):
    L.start_scan(kind)
    fps = 30.0
    t0 = L.scan["t0"]
    for i in range(int(live.SCAN_S * fps) + 2):
        t = t0 + i / fps
        img = np.full((720, 1280, 3), 128, np.uint8)
        ph = math.sin(2 * math.pi * bpm / 60 * t)  # skin pulse: strongest in green (BGR order)
        img[..., 1] = np.uint8(round(128 + 3 * ph)); img[..., 2] = np.uint8(round(150 + 1 * ph))
        L._frame(cv2, FakeMesh(scale), NoPose(), img, t, i + 1, fps)
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
