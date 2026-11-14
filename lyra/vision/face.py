"""Метрики лица по 478 точкам MediaPipe Face Mesh (refine_landmarks=True даёт зрачки).

Индексы точек: https://github.com/google-ai-edge/mediapipe (canonical_face_model_uv_visualization.png)
"""
from __future__ import annotations

import numpy as np

LEFT_EYE = [33, 160, 158, 133, 153, 144]  # p1..p6 для EAR
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
IRIS_L, IRIS_R = 468, 473
CHEEK_L, CHEEK_R = 234, 454  # ширина лица на уровне скул
JAW_L, JAW_R = 93, 323  # ширина на уровне нижней части щёк
NOSE_TIP = 1
MOUTH_TOP, MOUTH_BOTTOM, MOUTH_L, MOUTH_R = 13, 14, 78, 308
# Точки для участков кожи под rPPG: лоб и две щеки
ROI_FOREHEAD, ROI_CHEEK_L, ROI_CHEEK_R = 151, 50, 280


def to_px(landmarks, w: int, h: int) -> np.ndarray:
    return np.array([(p.x * w, p.y * h) for p in landmarks], dtype=float)


def _d(p: np.ndarray, a: int, b: int) -> float:
    return float(np.linalg.norm(p[a] - p[b]))


def eye_aspect_ratio(p: np.ndarray, idx: list[int]) -> float:
    p1, p2, p3, p4, p5, p6 = idx
    return (_d(p, p2, p6) + _d(p, p3, p5)) / (2 * _d(p, p1, p4) + 1e-9)


def frame_metrics(p: np.ndarray) -> dict:
    """Метрики одного кадра. p — (478, 2) в пикселях."""
    ipd = _d(p, IRIS_L, IRIS_R)  # межзрачковое расстояние — «линейка», не меняется от отёка
    width = (_d(p, CHEEK_L, CHEEK_R) + _d(p, JAW_L, JAW_R)) / 2
    # фронтальность: нос посередине между скулами (0,5 = анфас)
    span = p[CHEEK_R, 0] - p[CHEEK_L, 0]
    yaw = (p[NOSE_TIP, 0] - p[CHEEK_L, 0]) / span if abs(span) > 1e-6 else 0.0
    return {
        "ipd": ipd,
        "puffiness": width / (ipd + 1e-9),
        "ear": (eye_aspect_ratio(p, LEFT_EYE) + eye_aspect_ratio(p, RIGHT_EYE)) / 2,
        "mar": _d(p, MOUTH_TOP, MOUTH_BOTTOM) / (_d(p, MOUTH_L, MOUTH_R) + 1e-9),
        "frontal": 0.4 <= yaw <= 0.6,
    }


def skin_rgb(frame_rgb: np.ndarray, p: np.ndarray, ipd: float) -> np.ndarray | None:
    """Средний цвет кожи по трём участкам (лоб, щёки)."""
    h, w = frame_rgb.shape[:2]
    patches = []
    for idx, hw, hh in ((ROI_FOREHEAD, 0.35, 0.15), (ROI_CHEEK_L, 0.18, 0.18), (ROI_CHEEK_R, 0.18, 0.18)):
        cx, cy = p[idx]
        x0, x1 = int(max(cx - hw * ipd, 0)), int(min(cx + hw * ipd, w))
        y0, y1 = int(max(cy - hh * ipd, 0)), int(min(cy + hh * ipd, h))
        if x1 - x0 > 2 and y1 - y0 > 2:
            patches.append(frame_rgb[y0:y1, x0:x1].reshape(-1, 3))
    if not patches:
        return None
    return np.concatenate(patches).mean(axis=0)


def summarize(frames: list[dict], t: np.ndarray, duration_s: float) -> dict[str, tuple[float | None, float]]:
    """Итог за сканирование: отёчность, моргание, PERCLOS, зевота."""
    if len(frames) < 10:
        return {k: (None, 0.0) for k in ("face_puffiness", "blink_rate", "perclos", "yawn_count")}

    frontal = [f for f in frames if f["frontal"]]
    q_face = len(frontal) / len(frames)
    puff = float(np.median([f["puffiness"] for f in frontal])) if frontal else None

    ear = np.array([f["ear"] for f in frames])
    open_level = float(np.percentile(ear, 80))  # «открытые глаза» этого человека
    closed = ear < 0.6 * open_level
    blinks = int(np.sum(closed[1:] & ~closed[:-1]))
    minutes = max(duration_s, 1e-6) / 60
    perclos = 100 * float(np.mean(ear < 0.5 * open_level))

    mar = np.array([f["mar"] for f in frames])
    yawning = mar > 0.6
    yawns, start = 0, None
    for i, y in enumerate(yawning):
        if y and start is None:
            start = t[i]
        if not y and start is not None:
            yawns += int(t[i] - start >= 1.5)
            start = None
    if start is not None and t[-1] - start >= 1.5:
        yawns += 1

    q_eyes = min(1.0, len(frames) / (duration_s * 15))  # нужно ≥ 15 кадров/с
    return {
        "face_puffiness": (puff, q_face),
        "blink_rate": (blinks / minutes, q_eyes),
        "perclos": (perclos, q_eyes),
        "yawn_count": (float(yawns), q_eyes),
    }


def preview_points(p: np.ndarray, w: int, h: int, step: int = 4) -> list[list[float]]:
    """Прореженные нормированные точки для «сетки» на зеркале."""
    return [[round(x / w, 3), round(y / h, 3)] for x, y in p[:468:step]]
