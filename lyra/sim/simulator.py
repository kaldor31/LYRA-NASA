"""Симуляция измерений по кривым ожидаемой адаптации NASA (те же кривые, что и коридор).

значение = личная база до полёта + adapt × ожидаемое изменение NASA к этому дню
           + аномалия сценария + шум датчика (½σ).
Всё, что отсюда выходит, помечается как «смоделированные данные».
"""
from __future__ import annotations

import random
import uuid

from ..core.expected import is_modeled, offset
from ..core.metrics import DAILY, SPECS, SURVEY_KEYS, WEEKLY, keys_for_mode
from ..core.reference import Reference
from ..core.store import Session, Store
from .crew import CREW, Astronaut
from .scenarios import Scenario

PREFLIGHT_DAYS = 7  # дни −6…0


def base_values(a: Astronaut) -> dict[str, float]:
    return {k: a.base.get(k, s.base) for k, s in SPECS.items()}


def _value(key: str, day: int, a: Astronaut, sc: Scenario, ref: Reference, rng: random.Random) -> float:
    spec = SPECS[key]
    b = a.base.get(key, spec.base)
    v = b
    exp = ref.expected(key)
    if day > 0 and is_modeled(exp):
        v += a.adapt * offset(exp, b, day)
    if day > 0 and key == "skin_temp":
        v += 0.2
    if sc.anomaly and sc.anomaly.astronaut_id == a.id:
        rel, ab = sc.anomaly.mods(key, day, sc.day)
        v = v * (1 + rel / 100) + ab
    v += rng.gauss(0, spec.noise * 0.5)
    if key == "yawn_count":
        v = max(0.0, float(round(v)))
    elif key == "spo2":
        v = min(100.0, float(round(v)))
    elif key in ("sleep_score", "wellbeing_score"):
        v = float(min(5, max(1, round(v))))
    elif key == "symptoms_flag":
        v = 0.0
    elif key in ("perclos", "shoulder_asym_deg", "facial_tension"):
        v = max(0.0, v)
    return v


def simulate_values(a: Astronaut, day: int, mode: str, sc: Scenario, ref: Reference,
                    rng: random.Random, survey: bool = True) -> dict[str, tuple[float, float]]:
    keys = keys_for_mode(mode) + (SURVEY_KEYS if survey else [])
    out = {k: (_value(k, day, a, sc, ref, rng), round(rng.uniform(0.82, 0.98), 2))
           for k in keys if k != "flow_asymmetry_pct"}
    # асимметрия Л/П — из двух допплеров, а не независимый шум
    if "doppler_flow_left_cms" in out:
        l, r = out["doppler_flow_left_cms"][0], out["doppler_flow_right_cms"][0]
        asym = 100 * abs(l - r) / ((l + r) / 2) + rng.gauss(0, 0.4)
        out["flow_asymmetry_pct"] = (max(0.0, asym), round(rng.uniform(0.82, 0.98), 2))
    return out


def session_mode(day: int) -> str:
    return WEEKLY if day % 7 == 0 else DAILY


def dose_rate_msv_day(ref: Reference, env: str) -> tuple[float | None, str]:
    """Ставка дозы для симуляции дозиметра: из среды, иначе из метрики (МКС). Не выдумываем."""
    e = ref.environment(env)
    for k in ("dose_rate_msv_day", "dose_rate_msv_per_day"):
        if isinstance(e.get(k), (int, float)) and e[k] > 0:
            return float(e[k]), f"справочник: {e.get('name_ru', env)}"
    exp = ref.expected("radiation_dose_msv")
    rate = exp.get("rate")
    if isinstance(rate, (int, float)) and rate > 0:
        note = "" if env == "iss" else " — ставка МКС; на Луне/Марсе доза выше, реальные значения даёт дозиметр"
        return float(rate), f"справочник: {exp.get('rate_unit', 'мЗв/сут')}{note}"
    return None, "нет данных в справочнике — импортируйте значение дозиметра вручную"


def generate_history(store: Store, sc: Scenario, ref: Reference) -> None:
    """Дни −6…0 (до полёта) и 1…day−1 (полёт) для всего экипажа."""
    store.clear()
    rng = random.Random(sc.seed)
    for a in CREW.values():
        skips = set(sc.skip_days.get(a.id, ()))
        for day in range(1 - PREFLIGHT_DAYS, sc.day):
            if day in skips:
                continue
            mode = session_mode(day) if day > 0 else WEEKLY
            store.add(Session(f"sim-{uuid.uuid4().hex[:8]}", a.id, day, mode,
                              simulate_values(a, day, mode, sc, ref, rng), simulated=True))
        rate, _ = dose_rate_msv_day(ref, sc.env)
        if rate:
            store.add_dose(a.id, sc.day - 1, rate * (sc.day - 1) * rng.uniform(0.95, 1.05),
                           "дозиметр станции (смоделировано)")
