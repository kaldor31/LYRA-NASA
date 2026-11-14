"""Синтетическая история измерений: 7 дней до полёта + N дней полёта.

Реальной истории за 40 дней у команды не будет, поэтому личная норма строится на
смоделированных данных. На демо это нужно честно подписывать.

Модель (упрощённая, по открытым данным NASA HRP):
  • отёчность лица быстро растёт в первые дни (перераспределение жидкости к голове),
    затем частично адаптируется;
  • сила хвата медленно падает (~0,25 %/день без идеальной тренировки);
  • остальные показатели — шум вокруг личной нормы.
"""
from __future__ import annotations

import math
import random
import uuid

from ..core.db import Store
from ..core.metrics import METRICS

BASE = {
    "face_puffiness": 2.200,
    "blink_rate": 15.0,
    "perclos": 4.0,
    "yawn_count": 0.0,
    "shoulder_tilt": 1.5,
    "head_forward": 0.62,
    "hr_rppg": 66.0,
    "hr_palm": 65.0,
    "spo2": 98.0,
    "skin_temp": 33.4,
    "grip_strength": 42.0,
}

# Аномалия для сценария «день 40»: усталость + отёк + тахикардия в покое
ANOMALY = {
    "face_puffiness": +0.07,
    "perclos": +9.0,
    "hr_rppg": +17.0,
    "hr_palm": +18.0,
    "grip_strength": -3.0,
}

PREFLIGHT_DAYS = 7


def model_value(key: str, day: int, base: dict[str, float], rng: random.Random, anomaly: bool = False) -> float:
    b = base[key]
    v = b
    if day >= 1:
        if key == "face_puffiness":
            v += 0.11 * (1 - math.exp(-day / 3)) - 0.02 * (day / 40)
        elif key == "grip_strength":
            v *= 1 - 0.0025 * day
        elif key == "skin_temp":
            v += 0.2
    s = METRICS[key]
    v += rng.gauss(0, s.min_sd * 0.8)
    if anomaly:
        v += ANOMALY.get(key, 0.0)
    if key == "yawn_count":
        v = max(0.0, round(v))
    if key == "spo2":
        v = min(100.0, round(v))
    if key in ("perclos", "shoulder_tilt"):
        v = max(0.0, v)
    return v


def simulate_session(day: int, anomaly: bool = False, base: dict[str, float] | None = None,
                     seed: int | None = None, keys: list[str] | None = None) -> dict[str, tuple[float, float]]:
    rng = random.Random(seed)
    base = {**BASE, **(base or {})}
    keys = keys or list(METRICS)
    return {k: (model_value(k, day, base, rng, anomaly), round(rng.uniform(0.8, 0.98), 2)) for k in keys}


def generate_history(store: Store, until_day: int, base: dict[str, float] | None = None, seed: int = 7) -> None:
    """Заполняет базу днями −6…0 (до полёта) и 1…until_day−1 (полёт)."""
    store.clear()
    rng = random.Random(seed)
    for day in range(1 - PREFLIGHT_DAYS, until_day):
        metrics = simulate_session(day, base=base, seed=rng.randrange(1 << 30))
        store.add_session(f"sim-{uuid.uuid4().hex[:8]}", day, metrics, simulated=True)
