"""LYRA live feasibility demo: a real camera (e.g. an iPhone via macOS Continuity Camera) instead of the simulation.

    .venv/bin/pip install -r lyra/feasibility/requirements.txt
    .venv/bin/python -m lyra.feasibility.vision.live            # auto-picks the highest-resolution camera
    .venv/bin/python -m lyra.feasibility.vision.live --camera 1 --port 8780 --host 0.0.0.0
    .venv/bin/python -m lyra.feasibility.vision.live --source record3d   # iPhone TrueDepth (Face ID camera) via USB

Two sources:
  camera    any webcam; an iPhone through macOS Continuity Camera gives only its REAR camera (RGB, no IR depth).
  record3d  the FRONT TrueDepth camera (IR dot projector + IR camera, the Face ID hardware) through the Record3D
            app's USB streaming (pip install record3d; enable "USB Streaming mode" in the app, press record).
            Face landmarks are then lifted to real 3D with the measured IR depth: face width, interpupillary
            distance and nose depth in millimetres, distance to the camera.

Open http://127.0.0.1:8780 (with --host 0.0.0.0 also from a phone on the same Wi-Fi).

What runs live (MediaPipe Face Mesh + Pose on RGB video, rPPG by the POS method):
  quality gate (face visible, facing the mirror, light level, holding still), 3D face landmarks (478 points; with
  --source camera depth is estimated from RGB by MediaPipe, with record3d it is measured), face-width / IPD ratio
  ("puffiness" proxy), blink rate, shoulder tilt, camera pulse with a quality score.
A 15 s scan summarizes these with quality; the first scan becomes the personal baseline (memory only) and the
next scans are compared with it. Video frames are never stored or sent anywhere. Screening demo, not a diagnosis.
"""
from __future__ import annotations

import argparse
import collections
import os
import threading
import time
import warnings

import numpy as np

# MediaPipe 0.10.14 calls a deprecated protobuf API on every frame: harmless, but it floods the terminal
warnings.filterwarnings("ignore", message=r"SymbolDatabase\.GetPrototype\(\) is deprecated")

from . import face, pose  # noqa: E402
from .rppg import FS, HIGH_HZ, LOW_HZ, estimate_hr, pos, resample

HERE = os.path.dirname(os.path.abspath(__file__))
WINDOW_S = 20.0          # rolling window for live pulse / blink rate
SCAN_S = 15.0            # one scan
PROC_W = 1280            # processing width (frames are downscaled to this)

# Demo thresholds for the face-width ratio vs the personal baseline (percent). Team estimate for the demo only.
PUFF_REPEAT_PCT, PUFF_REFER_PCT = 2.0, 4.0
MIN_FACE_Q, MIN_HR_Q = 0.6, 0.35
MAX_MOTION = 0.06        # nose spread over ~0.5 s, in interpupillary distances


def pick_camera(max_index: int = 4) -> int:
    """Highest-resolution working camera. On a Mac with Continuity Camera this is usually the iPhone (1920x1080)."""
    import cv2
    best, best_w = 0, -1
    for i in range(max_index):
        cap = cv2.VideoCapture(i, cv2.CAP_AVFOUNDATION) if hasattr(cv2, "CAP_AVFOUNDATION") else cv2.VideoCapture(i)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            for _ in range(10):
                ok, fr = cap.read()
                if ok:
                    print(f"camera {i}: {fr.shape[1]}x{fr.shape[0]}")
                    if fr.shape[1] > best_w:
                        best, best_w = i, fr.shape[1]
                    break
        cap.release()
    return best


class OpenCVSource:
    """Webcam / Continuity Camera through OpenCV. read() -> (ok, bgr, depth_m | None, K | None)."""
    name = "camera"

    def __init__(self, index: int):
        import cv2
        self.cap = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION) if hasattr(cv2, "CAP_AVFOUNDATION") else cv2.VideoCapture(index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        if not self.cap.isOpened():
            raise RuntimeError(f"camera {index} failed to open")

    def read(self):
        ok, bgr = self.cap.read()
        return ok, bgr, None, None

    def release(self):
        self.cap.release()


class Record3DSource:
    """iPhone front TrueDepth camera (Face ID hardware) through the Record3D app, USB streaming mode.
    Depth is in metres; K is the 3x3 intrinsic matrix reported by the app."""
    name = "truedepth"

    def __init__(self, device: int = 0):
        from record3d import Record3DStream
        devs = Record3DStream.get_connected_devices()
        if not devs:
            raise RuntimeError("no Record3D device: connect the iPhone by USB, open Record3D, "
                               "Settings: enable USB Streaming mode, then press the record button")
        self.ev = threading.Event()
        self.stopped = False
        self.s = Record3DStream()
        self.s.on_new_frame = self.ev.set
        self.s.on_stream_stopped = self._stopped
        self.s.connect(devs[device])
        self.device_type = self.s.get_device_type()  # 0 = TrueDepth (front), 1 = LiDAR (rear)
        if self.device_type != 0:
            self.name = "lidar"

    def _stopped(self):
        self.stopped = True
        self.ev.set()

    def read(self):
        import cv2
        if not self.ev.wait(1.0) or self.stopped:
            return False, None, None, None
        self.ev.clear()
        depth = np.array(self.s.get_depth_frame(), dtype=np.float32)
        rgb = np.array(self.s.get_rgb_frame())
        c = self.s.get_intrinsic_mat()
        K = np.array([[c.fx, 0, c.tx], [0, c.fy, c.ty], [0, 0, 1]], dtype=float)
        return True, cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), depth, K

    def release(self):
        try:
            self.s.disconnect()
        except Exception:
            pass


# Landmarks for depth metrics: inside the face, away from the silhouette edge where depth jumps to the background
CHEEKBONE_L, CHEEKBONE_R = 123, 352
# Required for the millimetre metrics. The irises are optional: TrueDepth often has holes on the eyes.
DEPTH_KEYS = (face.NOSE_TIP, CHEEKBONE_L, CHEEKBONE_R, face.ROI_CHEEK_L, face.ROI_CHEEK_R)


def lift_to_3d(xy_norm: np.ndarray, depth: np.ndarray, K: np.ndarray, flipped: bool = True) -> np.ndarray:
    """Normalized landmark positions (N, 2) in the (mirrored) frame -> camera-space points (N, 3) in metres
    using the measured depth map (median of a 5x5 patch). Points without valid depth are NaN.
    The intrinsics are rescaled to the depth map size (principal point assumed near the image centre)."""
    dh, dw = depth.shape[:2]
    scale = dw / (2 * K[0, 2]) if K[0, 2] > 0 else 1.0
    fx, fy, cx, cy = K[0, 0] * scale, K[1, 1] * scale, K[0, 2] * scale, K[1, 2] * scale
    if flipped:
        cx = dw - cx
    depth = np.where(depth > 0, depth, np.nan)  # 0 = no depth at this pixel
    u = np.clip((xy_norm[:, 0] * dw).astype(int), 3, dw - 4)
    v = np.clip((xy_norm[:, 1] * dh).astype(int), 3, dh - 4)
    with warnings.catch_warnings():  # all-NaN patches are expected (holes in the depth map)
        warnings.simplefilter("ignore", RuntimeWarning)
        z = np.array([np.nanmedian(depth[b - 3:b + 4, a - 3:a + 4]) for a, b in zip(u, v)], dtype=float)
    z[(z < 0.1) | (z > 1.5) | ~np.isfinite(z)] = np.nan
    ref = np.nanmedian(z[list(DEPTH_KEYS)]) if np.isfinite(z[list(DEPTH_KEYS)]).any() else np.nan
    z[np.abs(z - ref) > 0.08] = np.nan  # background or hair behind the face
    return np.stack([(u - cx) * z / fx, (v - cy) * z / fy, z], axis=1)


def face_3d_metrics(P: np.ndarray) -> dict | None:
    """Millimetre metrics from lifted landmarks; None if the key points have no depth."""
    if not np.isfinite(P[list(DEPTH_KEYS)]).all():
        return None
    d = lambda a, b: float(np.linalg.norm(P[a] - P[b]) * 1000)
    cheek_z = (P[face.ROI_CHEEK_L, 2] + P[face.ROI_CHEEK_R, 2]) / 2
    ipd = d(face.IRIS_L, face.IRIS_R) if np.isfinite(P[[face.IRIS_L, face.IRIS_R]]).all() else None
    return {"face_width_mm": d(CHEEKBONE_L, CHEEKBONE_R), "ipd_mm": ipd,
            "nose_depth_mm": float((cheek_z - P[face.NOSE_TIP, 2]) * 1000),
            "distance_cm": float(P[face.NOSE_TIP, 2] * 100)}


class Live:
    """Camera loop in a background thread; the web layer reads snapshots from it."""

    def __init__(self, camera: int, source: str = "camera"):
        self.camera = camera
        self.source_kind = source
        self.lock = threading.Lock()
        self.jpeg: bytes | None = None
        self.state: dict = {"status": "starting"}
        self.mesh: list | None = None
        self.rgb = collections.deque()       # (t, r, g, b) skin colour for rPPG
        self.ear = collections.deque()       # (t, ear)
        self.nose = collections.deque(maxlen=15)
        self.scan: dict | None = None        # running scan buffers
        self.baseline: dict | None = None
        self.last_scan: dict | None = None
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    # ------------------------------------------------------------------ camera loop
    def _open_source(self, timeout: float = 4.0):
        """Open the frame source without letting a hung USB connect block the loop forever.
        Returns the source or None (state then says what to do)."""
        box = {}

        def worker():
            try:
                box["src"] = Record3DSource() if self.source_kind == "record3d" else OpenCVSource(self.camera)
            except Exception as e:
                box["err"] = str(e)
        th = threading.Thread(target=worker, daemon=True)
        th.start()
        th.join(timeout)
        if "src" in box:
            return box["src"]
        with self.lock:
            self.state = {"status": "waiting", "error": box.get("err") or "the phone did not answer: in Record3D tap the "
                          "red button so it shows 'Started, Waiting for Connection'"}
        return None

    def _waiting(self, msg: str):
        with self.lock:
            self.state = {"status": "waiting", "error": msg}

    def _run(self):
        import cv2
        import mediapipe as mp
        fm = mp.solutions.face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True,
                                             min_detection_confidence=0.5, min_tracking_confidence=0.5)
        pm = mp.solutions.pose.Pose(model_complexity=0, min_detection_confidence=0.5)
        n, fps_t, fps = 0, time.monotonic(), 0.0
        self._last_pose, self._last_hr_t, self._hr = None, 0.0, (None, 0.0, [])
        t0 = time.monotonic()
        src, last_frame = None, time.monotonic()
        try:
            while not self.stop.is_set():
                if src is None:  # (re)connect, keep trying: the phone may start streaming later
                    src = self._open_source()
                    if src is None:
                        time.sleep(1.5)
                        continue
                    self.depth_source = src.name
                    last_frame = time.monotonic()
                ok, bgr, depth, K = src.read()
                if not ok:
                    silent = time.monotonic() - last_frame
                    if getattr(src, "stopped", False) or (self.source_kind == "record3d" and silent > 4):
                        # stream stopped on the phone (red button) or a stale connection: drop it and reconnect
                        self._waiting("no frames from the iPhone: in Record3D tap the red button once so it shows "
                                      "'Started, Waiting for Connection'; LYRA reconnects by itself")
                        threading.Thread(target=src.release, daemon=True).start()  # disconnect may block too
                        src = None
                        time.sleep(1.0)
                    elif silent > 4:
                        self._waiting("camera sends no frames")
                    else:
                        time.sleep(0.01)
                    continue
                last_frame = time.monotonic()
                now = time.monotonic() - t0
                n += 1
                if n % 15 == 0:
                    t = time.monotonic()
                    fps, fps_t = 15 / (t - fps_t), t
                try:
                    self._frame(cv2, fm, pm, bgr, now, n, fps, depth, K)
                except Exception as e:  # keep the camera loop alive; show the error on the page
                    with self.lock:
                        self.state = dict(self.state, error=f"{type(e).__name__}: {e}")
        finally:
            if src is not None:
                src.release()
            fm.close()
            pm.close()

    def _frame(self, cv2, fm, pm, bgr, now, n, fps, depth=None, K=None):
        bgr = cv2.flip(bgr, 1)  # mirror view
        if depth is not None:
            depth = cv2.flip(depth, 1)
        if bgr.shape[1] > PROC_W:
            bgr = cv2.resize(bgr, (PROC_W, int(bgr.shape[0] * PROC_W / bgr.shape[1])), interpolation=cv2.INTER_AREA)
        h, w = bgr.shape[:2]
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        fr = fm.process(rgb)
        if n % 2 == 0:
            pr = pm.process(rgb)
            self._last_pose = pose.frame_metrics(pr.pose_landmarks.landmark, w, h) if pr.pose_landmarks else None

        st = {"status": "ok", "fps": round(fps, 1), "t": round(now, 2), "w": w, "h": h, "face": False,
              "source": getattr(self, "depth_source", "camera"), "depth": depth is not None}
        if fr.multi_face_landmarks:
            lm = fr.multi_face_landmarks[0].landmark
            p = face.to_px(lm, w, h)
            m = face.frame_metrics(p)
            c = face.skin_rgb(rgb, p, m["ipd"])
            # light: mean luma over the face box
            x0, y0 = np.clip(p.min(0).astype(int), 0, [w - 1, h - 1])
            x1, y1 = np.clip(p.max(0).astype(int), 0, [w - 1, h - 1])
            luma = float(cv2.cvtColor(bgr[y0:y1 + 1, x0:x1 + 1], cv2.COLOR_BGR2GRAY).mean()) if x1 > x0 and y1 > y0 else 0.0
            self.nose.append(p[face.NOSE_TIP] / max(m["ipd"], 1e-6))
            # steadiness: spread of the nose position over the last ~0.5 s, in IPD units (landmark jitter averages out)
            motion = float(np.linalg.norm(np.array(self.nose).std(axis=0))) if len(self.nose) > 5 else 0.0
            if c is not None:
                self.rgb.append((now, *c))
            self.ear.append((now, m["ear"]))
            while self.rgb and now - self.rgb[0][0] > WINDOW_S:
                self.rgb.popleft()
            while self.ear and now - self.ear[0][0] > 60:
                self.ear.popleft()
            span = p[face.CHEEK_R, 0] - p[face.CHEEK_L, 0]
            yaw = (p[face.NOSE_TIP, 0] - p[face.CHEEK_L, 0]) / span if abs(span) > 1e-6 else 0.5
            st.update(face=True, ipd_px=round(m["ipd"], 1), puffiness=round(m["puffiness"], 4),
                      ear=round(m["ear"], 3), frontal=bool(m["frontal"]), yaw=round(float(yaw), 3),
                      luma=round(luma, 1), motion=round(motion, 4))
            mesh = [[round(q.x - 0.5, 4), round(q.y - 0.5, 4), round(q.z, 4)] for q in lm[:468]]
            m3 = None
            if depth is not None and K is not None:
                P = lift_to_3d(np.array([(q.x, q.y) for q in lm]), depth, K)
                m3 = face_3d_metrics(P)
                if m3:
                    st.update({k: (round(v, 1) if v is not None else None) for k, v in m3.items()})
                    c3 = np.nanmean(P[:468], axis=0)
                    mesh = [[round(float(x - c3[0]), 4), round(float(y - c3[1]), 4), round(float(z - c3[2]), 4)]
                            if np.isfinite(z) else [None, None, None] for x, y, z in P[:468]]
                st["mesh_measured"] = m3 is not None
            self._draw(cv2, bgr, p, m)
            if self.scan is not None:
                self.scan["face"].append(dict(m, t=now))
                if depth is not None:
                    self.scan["d3"].append(m3)
                if c is not None:
                    self.scan["rgb"].append(c)
                    self.scan["rgb_t"].append(now)
                self.scan["luma"].append(luma)
                self.scan["motion"].append(motion)
        else:
            mesh = None
            self.nose.clear()
        if self._last_pose:
            st.update(shoulder_tilt=round(self._last_pose["tilt"], 2), head=round(self._last_pose["head"], 3))
            (lx, ly), (rx, ry) = self._last_pose["shoulders"]
            cv2.line(bgr, (int(lx * w), int(ly * h)), (int(rx * w), int(ry * h)), (232, 178, 143), 2, cv2.LINE_AA)
            if self.scan is not None:
                self.scan["pose"].append(self._last_pose)
        if self.scan is not None:
            self.scan["n"] += 1
        # live pulse once per second
        if now - self._last_hr_t > 1.0:
            self._last_hr_t = now
            self._hr = self._live_hr()
        st["gate"] = gate(st)
        st["hr"], st["hr_q"], st["wave"] = self._hr[0], self._hr[1], self._hr[2]
        st["blinks_min"] = self._blink_rate(now)
        if self.scan is not None:
            el = now - self.scan["t0"]
            st["scan"] = {"kind": self.scan["kind"], "progress": round(min(el / SCAN_S, 1), 3)}
            if el >= SCAN_S:
                self._finish_scan(now)
        if depth is not None:  # small IR depth inset, top right: near = warm
            d = np.nan_to_num(depth, nan=1.5)
            d8 = (255 * (1 - np.clip((d - 0.2) / 0.8, 0, 1))).astype(np.uint8)
            iw = w // 4
            inset = cv2.applyColorMap(cv2.resize(d8, (iw, int(d8.shape[0] * iw / d8.shape[1]))), cv2.COLORMAP_TURBO)
            ih = min(inset.shape[0], h - 10)
            bgr[10:10 + ih, w - iw - 10:w - 10] = inset[:ih]
            cv2.putText(bgr, "IR depth (TrueDepth)", (w - iw - 8, 26 + ih), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (240, 240, 240), 1, cv2.LINE_AA)
        ok, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 75])
        with self.lock:
            self.jpeg = buf.tobytes() if ok else self.jpeg
            self.state, self.mesh = st, mesh

    @staticmethod
    def _draw(cv2, bgr, p, m):
        for x, y in p[:468:2]:
            cv2.circle(bgr, (int(x), int(y)), 1, (232, 178, 143), -1, cv2.LINE_AA)
        for i in (face.CHEEK_L, face.CHEEK_R, face.JAW_L, face.JAW_R):
            cv2.circle(bgr, (int(p[i, 0]), int(p[i, 1])), 4, (80, 200, 120), -1, cv2.LINE_AA)
        cv2.line(bgr, tuple(p[face.IRIS_L].astype(int)), tuple(p[face.IRIS_R].astype(int)), (60, 180, 250), 1, cv2.LINE_AA)
        ipd = m["ipd"]
        for idx, hw, hh in ((face.ROI_FOREHEAD, 0.35, 0.15), (face.ROI_CHEEK_L, 0.18, 0.18), (face.ROI_CHEEK_R, 0.18, 0.18)):
            cx, cy = p[idx]
            cv2.rectangle(bgr, (int(cx - hw * ipd), int(cy - hh * ipd)), (int(cx + hw * ipd), int(cy + hh * ipd)), (90, 90, 230), 1)

    def _live_hr(self):
        if len(self.rgb) < 60:
            return (None, 0.0, [])
        a = np.array(self.rgb)
        t, c = a[:, 0], a[:, 1:]
        if t[-1] - t[0] < 8:
            return (None, 0.0, [])
        hr, q = estimate_hr(c, t)
        wave = []
        try:
            from scipy.signal import butter, filtfilt
            x = pos(resample(c, t))
            b, a2 = butter(3, [LOW_HZ / (FS / 2), HIGH_HZ / (FS / 2)], btype="band")
            sig = filtfilt(b, a2, x)[-int(6 * FS):]
            sig = sig / (np.abs(sig).max() or 1)
            wave = [round(float(v), 3) for v in sig[::2]]
        except Exception:
            pass
        return (round(hr, 1) if hr else None, round(q, 2), wave)

    def _blink_rate(self, now):
        if len(self.ear) < 60:
            return None
        e = np.array([v for _, v in self.ear])
        closed = e < 0.6 * np.percentile(e, 80)
        span = max(now - self.ear[0][0], 1.0)
        return round(int(np.sum(closed[1:] & ~closed[:-1])) * 60 / span, 1)

    # ------------------------------------------------------------------ scans
    def start_scan(self, kind: str):
        with self.lock:
            self.scan = {"kind": kind, "t0": self.state.get("t", 0.0), "face": [], "rgb": [], "rgb_t": [],
                         "pose": [], "luma": [], "motion": [], "d3": [], "n": 0}

    def _finish_scan(self, now):
        s, self.scan = self.scan, None
        frames = s["face"]
        res = {"kind": s["kind"], "duration_s": SCAN_S, "frames": len(frames), "time": time.strftime("%H:%M:%S")}
        t = np.array([f["t"] for f in frames]) if frames else np.array([])
        fsum = face.summarize(frames, t, SCAN_S)
        psum = pose.summarize(s["pose"], max(s["n"] // 2, 1))
        hr, hq = estimate_hr(np.array(s["rgb"]), np.array(s["rgb_t"])) if len(s["rgb"]) > 30 else (None, 0.0)
        light = float(np.median(s["luma"])) if s["luma"] else 0.0
        motion = float(np.median(s["motion"])) if s["motion"] else 1.0
        reasons = []
        if len(frames) < 0.5 * s["n"]:
            reasons.append("face not visible for most of the scan")
        if fsum["face_puffiness"][1] < MIN_FACE_Q:
            reasons.append("not facing the mirror for most of the scan")
        if not 50 <= light <= 220:
            reasons.append("light level out of range")
        if motion > MAX_MOTION:
            reasons.append("too much motion")
        res["metrics"] = {
            "face_ratio": metric(fsum["face_puffiness"], MIN_FACE_Q),
            "hr_rppg": metric((hr, hq), MIN_HR_Q, unit="bpm"),
            "blink_rate": metric(fsum["blink_rate"], 0.5, unit="/min"),
            "shoulder_tilt": metric(psum["shoulder_tilt"], 0.4, unit="deg"),
        }
        if s["d3"]:  # measured IR depth (TrueDepth)
            ok3 = [x for x in s["d3"] if x]
            q3 = len(ok3) / len(s["d3"])
            for k, unit in (("face_width_mm", "mm"), ("nose_depth_mm", "mm"), ("ipd_mm", "mm"), ("distance_cm", "cm")):
                vals = [x[k] for x in ok3 if x[k] is not None]
                v = float(np.median(vals)) if vals else None
                res["metrics"][k] = metric((v, q3), MIN_FACE_Q, unit=unit)
        res["quality"] = {"light": round(light, 1), "motion": round(motion, 4), "reasons": reasons}
        res["status"], res["why"] = classify(res, self.baseline)
        if s["kind"] == "baseline" and not reasons and res["metrics"]["face_ratio"]["value"] is not None:
            self.baseline = res
            res["status"], res["why"] = "baseline", "Saved as your personal baseline (memory only)."
        self.last_scan = res

    def snapshot(self):
        with self.lock:
            return dict(self.state), self.mesh, self.last_scan, self.baseline is not None


def gate(st: dict) -> dict:
    """Quality gate checks shown before and during a scan."""
    if not st.get("face"):
        return {"face": False, "frontal": False, "light": False, "still": False, "ok": False}
    g = {"face": True, "frontal": bool(st.get("frontal")), "light": 50 <= st.get("luma", 0) <= 220,
         "still": st.get("motion", 1) <= MAX_MOTION}
    g["ok"] = all(g.values())
    return g


def metric(vq: tuple, min_q: float, unit: str = "") -> dict:
    v, q = vq
    ok = v is not None and q >= min_q
    return {"value": round(float(v), 4) if ok else None, "quality": round(float(q), 2), "unit": unit,
            "note": None if ok else "Measurement not confirmed"}


def classify(res: dict, base: dict | None) -> tuple[str, str]:
    if res["quality"]["reasons"]:
        return "retry", "Measurement not confirmed: " + "; ".join(res["quality"]["reasons"]) + ". Repeat the scan."
    cur = res["metrics"]["face_ratio"]["value"]
    if cur is None:
        return "retry", "Measurement not confirmed: face ratio quality too low. Repeat the scan."
    if base is None:
        return "no_baseline", "No baseline yet: take a baseline scan first."
    w_now = res["metrics"].get("face_width_mm", {}).get("value")
    w_base = base["metrics"].get("face_width_mm", {}).get("value")
    if w_now is not None and w_base is not None:  # measured IR depth wins over the 2D ratio
        pct = 100 * (w_now - w_base) / w_base
        res["face_width_change_pct"] = round(pct, 2)
        what = f"Face width (IR depth) {w_now:.1f} mm, {pct:+.1f}% vs your baseline {w_base:.1f} mm"
    else:
        b = base["metrics"]["face_ratio"]["value"]
        pct = 100 * (cur - b) / b
        what = f"Face width / IPD ratio {pct:+.1f}% vs your baseline"
    res["face_ratio_change_pct"] = round(100 * (cur - base["metrics"]["face_ratio"]["value"]) / base["metrics"]["face_ratio"]["value"], 2)
    txt = f"{what} (demo thresholds {PUFF_REPEAT_PCT:.0f}% / {PUFF_REFER_PCT:.0f}%)."
    if abs(pct) < PUFF_REPEAT_PCT:
        return "green", txt
    if abs(pct) < PUFF_REFER_PCT:
        return "yellow", txt + " Repeat the scan."
    return "red", txt + " Change persists: the medical team reviews it."


def clean(x):
    """JSON-safe: NaN / inf -> None (browsers reject NaN in JSON), numpy scalars -> Python."""
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, (float, np.floating)):
        return float(x) if np.isfinite(x) else None
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def make_app(live: Live):
    from fastapi import FastAPI
    from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

    app = FastAPI(title="LYRA live camera demo")

    NOCACHE = {"Cache-Control": "no-store"}

    @app.get("/")
    def index():
        return FileResponse(os.path.join(HERE, "live.html"), headers=NOCACHE)

    @app.get("/frame.jpg")
    def frame():
        """Latest annotated frame. The page polls this (works in every browser, unlike MJPEG in Safari)."""
        from fastapi import Response
        with live.lock:
            j = live.jpeg
        if j is None:
            return Response(status_code=204, headers=NOCACHE)
        return Response(content=j, media_type="image/jpeg", headers=NOCACHE)

    @app.get("/api/live")
    def api_live():
        st, mesh, last, has_base = live.snapshot()
        return JSONResponse(clean({"state": st, "mesh": mesh, "last_scan": last, "has_baseline": has_base}))

    @app.post("/api/scan/{kind}")
    def api_scan(kind: str):
        if kind not in ("baseline", "scan"):
            return JSONResponse({"error": "kind must be baseline or scan"}, status_code=400)
        live.start_scan(kind)
        return {"started": kind, "duration_s": SCAN_S}

    @app.post("/api/baseline/reset")
    def api_reset():
        live.baseline, live.last_scan = None, None
        return {"ok": True}

    @app.get("/video")
    def video():
        def gen():
            last = None
            while True:
                with live.lock:
                    j = live.jpeg
                if j is not None and j is not last:
                    last = j
                    yield b"--f\r\nContent-Type: image/jpeg\r\n\r\n" + j + b"\r\n"
                time.sleep(1 / 30)
        return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=f")

    return app


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--source", choices=("camera", "record3d"), default="camera",
                    help="camera: webcam / Continuity Camera (rear, RGB); record3d: iPhone front TrueDepth (IR depth) via USB")
    ap.add_argument("--camera", type=int, default=None, help="camera index (default: highest resolution, usually the iPhone)")
    ap.add_argument("--host", default="127.0.0.1", help="0.0.0.0 to open the page from a phone on the same Wi-Fi")
    ap.add_argument("--port", type=int, default=8780)
    a = ap.parse_args()
    if a.source == "record3d":
        cam = -1
        print("using Record3D (iPhone TrueDepth over USB)")
    else:
        cam = pick_camera() if a.camera is None else a.camera
        print(f"using camera {cam}")
    live = Live(cam, a.source)
    live.thread.start()
    import uvicorn
    print(f"LYRA live demo: http://{'127.0.0.1' if a.host in ('127.0.0.1', 'localhost') else a.host}:{a.port}")
    uvicorn.run(make_app(live), host=a.host, port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
