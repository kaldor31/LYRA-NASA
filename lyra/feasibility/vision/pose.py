"""Posture from MediaPipe Pose: shoulder tilt and head position (front-facing camera)."""
from __future__ import annotations

import math

import numpy as np

NOSE, SHOULDER_L, SHOULDER_R = 0, 11, 12


def frame_metrics(landmarks, w: int, h: int) -> dict | None:
    nose, sl, sr = landmarks[NOSE], landmarks[SHOULDER_L], landmarks[SHOULDER_R]
    vis = min(nose.visibility, sl.visibility, sr.visibility)
    if vis < 0.5:
        return None
    lx, ly, rx, ry = sl.x * w, sl.y * h, sr.x * w, sr.y * h
    width = math.hypot(lx - rx, ly - ry)
    if width < 1:
        return None
    tilt = math.degrees(math.atan2(abs(ly - ry), abs(lx - rx)))
    # Nose-to-shoulder-line distance relative to shoulder width: smaller means the head is lowered or pushed forward
    head = ((ly + ry) / 2 - nose.y * h) / width
    return {
        "tilt": tilt,
        "head": head,
        "vis": vis,
        "shoulders": [[round(sl.x, 3), round(sl.y, 3)], [round(sr.x, 3), round(sr.y, 3)]],
    }


def summarize(frames: list[dict], n_total: int) -> dict[str, tuple[float | None, float]]:
    if len(frames) < 10:
        return {"shoulder_tilt": (None, 0.0), "head_forward": (None, 0.0)}
    q = min(1.0, len(frames) / max(n_total, 1)) * float(np.mean([f["vis"] for f in frames]))
    return {
        "shoulder_tilt": (float(np.median([f["tilt"] for f in frames])), q),
        "head_forward": (float(np.median([f["head"] for f in frames])), q),
    }
