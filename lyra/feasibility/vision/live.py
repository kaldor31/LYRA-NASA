"""LYRA live feasibility demo: a real camera (e.g. an iPhone via macOS Continuity Camera) instead of the simulation.

    .venv/bin/pip install -r lyra/feasibility/requirements.txt
    .venv/bin/python -m lyra.feasibility.vision.live            # auto-picks the highest-resolution camera
    .venv/bin/python -m lyra.feasibility.vision.live --camera 1 --port 8780 --host 0.0.0.0

Open http://127.0.0.1:8780 (with --host 0.0.0.0 also from a phone on the same Wi-Fi).

What runs live (MediaPipe Face Mesh + Pose on RGB video, rPPG by the POS method):
  quality gate (face visible, facing the mirror, light level, holding still), 3D face landmarks (478 points; depth
  is estimated from RGB by MediaPipe, not measured by an IR projector), face-width / interpupillary-distance ratio
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

import numpy as np

from . import face, pose
from .rppg import FS, HIGH_HZ, LOW_HZ, estimate_hr, pos, resample

HERE = os.path.dirname(os.path.abspath(__file__))
WINDOW_S = 20.0          # rolling window for live pulse / blink rate
SCAN_S = 15.0            # one scan
PROC_W = 1280            # processing width (frames are downscaled to this)

# Demo thresholds for the face-width ratio vs the personal baseline (percent). Team estimate for the demo only.
PUFF_REPEAT_PCT, PUFF_REFER_PCT = 2.0, 4.0
MIN_FACE_Q, MIN_HR_Q = 0.6, 0.35


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


class Live:
    """Camera loop in a background thread; the web layer reads snapshots from it."""

    def __init__(self, camera: int):
        self.camera = camera
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
    def _run(self):
        import cv2
        import mediapipe as mp
        cap = cv2.VideoCapture(self.camera, cv2.CAP_AVFOUNDATION) if hasattr(cv2, "CAP_AVFOUNDATION") else cv2.VideoCapture(self.camera)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        cap.set(cv2.CAP_PROP_FPS, 30)
        if not cap.isOpened():
            with self.lock:
                self.state = {"status": "error", "error": f"camera {self.camera} failed to open"}
            return
        fm = mp.solutions.face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True,
                                             min_detection_confidence=0.5, min_tracking_confidence=0.5)
        pm = mp.solutions.pose.Pose(model_complexity=0, min_detection_confidence=0.5)
        n, fps_t, fps = 0, time.monotonic(), 0.0
        self._last_pose, self._last_hr_t, self._hr = None, 0.0, (None, 0.0, [])
        t0 = time.monotonic()
        try:
            while not self.stop.is_set():
                ok, bgr = cap.read()
                if not ok:
                    time.sleep(0.01)
                    continue
                now = time.monotonic() - t0
                n += 1
                if n % 15 == 0:
                    t = time.monotonic()
                    fps, fps_t = 15 / (t - fps_t), t
                try:
                    self._frame(cv2, fm, pm, bgr, now, n, fps)
                except Exception as e:  # keep the camera loop alive; show the error on the page
                    with self.lock:
                        self.state = dict(self.state, error=f"{type(e).__name__}: {e}")
        finally:
            cap.release()
            fm.close()
            pm.close()

    def _frame(self, cv2, fm, pm, bgr, now, n, fps):
        bgr = cv2.flip(bgr, 1)  # mirror view
        if bgr.shape[1] > PROC_W:
            bgr = cv2.resize(bgr, (PROC_W, int(bgr.shape[0] * PROC_W / bgr.shape[1])), interpolation=cv2.INTER_AREA)
        h, w = bgr.shape[:2]
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        fr = fm.process(rgb)
        if n % 2 == 0:
            pr = pm.process(rgb)
            self._last_pose = pose.frame_metrics(pr.pose_landmarks.landmark, w, h) if pr.pose_landmarks else None

        st = {"status": "ok", "fps": round(fps, 1), "t": round(now, 2), "w": w, "h": h, "face": False}
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
            motion = float(np.linalg.norm(np.diff(np.array(self.nose), axis=0), axis=1).mean()) if len(self.nose) > 3 else 0.0
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
            self._draw(cv2, bgr, p, m)
            if self.scan is not None:
                self.scan["face"].append(dict(m, t=now))
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
                         "pose": [], "luma": [], "motion": [], "n": 0}

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
        if motion > 0.03:
            reasons.append("too much motion")
        res["metrics"] = {
            "face_ratio": metric(fsum["face_puffiness"], MIN_FACE_Q),
            "hr_rppg": metric((hr, hq), MIN_HR_Q, unit="bpm"),
            "blink_rate": metric(fsum["blink_rate"], 0.5, unit="/min"),
            "shoulder_tilt": metric(psum["shoulder_tilt"], 0.4, unit="deg"),
        }
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
         "still": st.get("motion", 1) <= 0.03}
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
    b = base["metrics"]["face_ratio"]["value"]
    pct = 100 * (cur - b) / b
    res["face_ratio_change_pct"] = round(pct, 2)
    txt = f"Face width / IPD ratio {pct:+.1f}% vs your baseline (demo thresholds {PUFF_REPEAT_PCT:.0f}% / {PUFF_REFER_PCT:.0f}%)."
    if abs(pct) < PUFF_REPEAT_PCT:
        return "green", txt
    if abs(pct) < PUFF_REFER_PCT:
        return "yellow", txt + " Repeat the scan."
    return "red", txt + " Change persists: the medical team reviews it."


def make_app(live: Live):
    from fastapi import FastAPI
    from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

    app = FastAPI(title="LYRA live camera demo")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(HERE, "live.html"))

    @app.get("/api/live")
    def api_live():
        st, mesh, last, has_base = live.snapshot()
        return JSONResponse({"state": st, "mesh": mesh, "last_scan": last, "has_baseline": has_base})

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
    ap.add_argument("--camera", type=int, default=None, help="camera index (default: highest resolution, usually the iPhone)")
    ap.add_argument("--host", default="127.0.0.1", help="0.0.0.0 to open the page from a phone on the same Wi-Fi")
    ap.add_argument("--port", type=int, default=8780)
    a = ap.parse_args()
    cam = pick_camera() if a.camera is None else a.camera
    print(f"using camera {cam}")
    live = Live(cam)
    live.thread.start()
    import uvicorn
    print(f"LYRA live demo: http://{'127.0.0.1' if a.host in ('127.0.0.1', 'localhost') else a.host}:{a.port}")
    uvicorn.run(make_app(live), host=a.host, port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
