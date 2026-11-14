"""Сканирование перед зеркалом: камера → лицо + поза + rPPG за `duration` секунд."""
from __future__ import annotations

import math
import random
import threading
import time
from typing import Callable

import numpy as np

from . import face, pose
from .rppg import estimate_hr

OnFrame = Callable[[dict], None]


def camera_scan(duration: float = 20.0, camera_index: int = 0, on_frame: OnFrame | None = None,
                stop: threading.Event | None = None) -> dict[str, tuple[float | None, float]]:
    import cv2
    import mediapipe as mp

    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)
    if not cap.isOpened():
        raise RuntimeError(f"Камера {camera_index} не открылась")

    face_frames, pose_frames, rgb, times = [], [], [], []
    n_total = 0
    t0 = time.monotonic()
    with mp.solutions.face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True,
                                         min_detection_confidence=0.5, min_tracking_confidence=0.5) as fm, \
            mp.solutions.pose.Pose(model_complexity=0, min_detection_confidence=0.5) as pm:
        while (elapsed := time.monotonic() - t0) < duration:
            if stop is not None and stop.is_set():
                break
            ok, bgr = cap.read()
            if not ok:
                continue
            n_total += 1
            h, w = bgr.shape[:2]
            frame = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            frame.flags.writeable = False
            msg = {"progress": round(elapsed / duration, 3)}

            fr = fm.process(frame)
            if fr.multi_face_landmarks:
                p = face.to_px(fr.multi_face_landmarks[0].landmark, w, h)
                fm_ = face.frame_metrics(p)
                fm_["t"] = elapsed
                face_frames.append(fm_)
                c = face.skin_rgb(frame, p, fm_["ipd"])
                if c is not None:
                    rgb.append(c)
                    times.append(elapsed)
                if n_total % 3 == 0:
                    msg["face"] = face.preview_points(p, w, h)

            if n_total % 2 == 0:  # поза медленнее и меняется медленно
                pr = pm.process(frame)
                if pr.pose_landmarks:
                    pf = pose.frame_metrics(pr.pose_landmarks.landmark, w, h)
                    if pf:
                        pose_frames.append(pf)
                        msg["shoulders"] = pf["shoulders"]

            if on_frame is not None and (n_total % 3 == 0):
                on_frame(msg)
    cap.release()

    span = time.monotonic() - t0
    t_face = np.array([f["t"] for f in face_frames])
    result = face.summarize(face_frames, t_face, span)
    result.update(pose.summarize(pose_frames, n_total // 2))
    hr, q = estimate_hr(np.array(rgb), np.array(times)) if len(rgb) > 30 else (None, 0.0)
    result["hr_rppg"] = (hr, q)
    return result


def simulated_scan(duration: float, values: dict[str, tuple[float, float]], on_frame: OnFrame | None = None,
                   stop: threading.Event | None = None) -> dict[str, tuple[float, float]]:
    """Без камеры: анимированная «сетка» лица и готовые значения из симуляции."""
    t0 = time.monotonic()
    base = [(math.cos(a), math.sin(a)) for a in np.linspace(0, 2 * math.pi, 48, endpoint=False)]
    eyes = [(-0.38, -0.15), (0.38, -0.15), (0, 0.1), (-0.2, 0.42), (0, 0.48), (0.2, 0.42)]
    while (elapsed := time.monotonic() - t0) < duration:
        if stop is not None and stop.is_set():
            break
        sway = 0.006 * math.sin(elapsed * 1.3)
        pts = [[round(0.5 + sway + 0.11 * x, 3), round(0.36 + 0.15 * y, 3)] for x, y in base]
        pts += [[round(0.5 + sway + 0.11 * x + random.uniform(-0.002, 0.002), 3), round(0.36 + 0.15 * y, 3)]
                for x, y in eyes]
        if on_frame:
            on_frame({"progress": round(elapsed / duration, 3), "face": pts,
                      "shoulders": [[0.33, 0.66], [0.67, 0.665]]})
        time.sleep(0.1)
    return values
