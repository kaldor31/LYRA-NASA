"""Модель «ожидаемой адаптации» NASA: коридор нормального приспособления по дням полёта.

Для метрики с expected.model:
  linear      — центр = база × (1 + rate·t), rate в «%/мес» (или абсолютные единицы в мес/сут);
  saturating  — центр = база × (1 + rate·(1 − e^(−день/τ))), rate — изменение к плато;
  none        — коридора нет, работает только личная норма.
Полуширина коридора = band из справочника (в тех же единицах, что rate), но не уже 2σ шума
измерения (иначе шум датчика выглядел бы как «быстрее NASA»). Если band нет — max(2σ, ½ ожидаемого изменения).
База — среднее личных измерений до полёта (дни −6…0).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Corridor:
    day: int
    center: float
    lo: float
    hi: float

    def to_dict(self) -> dict:
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in asdict(self).items()}


def _num(x: Any) -> float | None:
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def is_modeled(expected: dict[str, Any]) -> bool:
    model = expected.get("model")
    if model == "linear":
        return _num(expected.get("rate")) not in (None, 0.0)
    if model == "saturating":
        return _num(expected.get("rate")) is not None and (_num(expected.get("tau_days")) or 0) > 0
    return False


def offset(expected: dict[str, Any], base: float, day: float) -> float:
    """Ожидаемое изменение к дню `day` в абсолютных единицах метрики."""
    if day <= 0:
        return 0.0
    rate = _num(expected.get("rate")) or 0.0
    unit = str(expected.get("rate_unit", ""))
    relative = "%" in unit
    if expected.get("model") == "linear":
        per_day = rate / 30.0 if "мес" in unit or "month" in unit else rate
        amount = per_day * day
    else:
        tau = _num(expected.get("tau_days")) or 1.0
        amount = rate * (1 - math.exp(-day / tau))
    return base * amount / 100.0 if relative else amount


def _band(expected: dict[str, Any], base: float) -> float | None:
    band = _num(expected.get("band"))
    if band is None:
        return None
    return abs(base * band / 100.0) if "%" in str(expected.get("rate_unit", "")) else abs(band)


def corridor(expected: dict[str, Any], base: float, day: int, noise: float) -> Corridor | None:
    if not is_modeled(expected):
        return None
    center = base + offset(expected, base, day)
    band = _band(expected, base)
    floor = 2 * noise
    half = max(band, floor) if band is not None else max(floor, 0.5 * abs(center - base))
    return Corridor(day, center, center - half, center + half)


def corridor_series(expected: dict[str, Any], base: float, days: range, noise: float) -> list[dict]:
    out = []
    for d in days:
        c = corridor(expected, base, d, noise)
        if c:
            out.append(c.to_dict())
    return out


def expected_change_pct(expected: dict[str, Any], base: float, day: int) -> float | None:
    if not is_modeled(expected) or not base:
        return None
    return 100.0 * offset(expected, base, day) / base
