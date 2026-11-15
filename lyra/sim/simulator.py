"""Measurement simulation along NASA expected-adaptation curves (the same curves as the corridor).

value = personal pre-flight base + adapt x NASA expected change by that day
        + environment posture shift + scenario anomaly + sensor noise (half sigma).
Everything produced here is labeled provenance "simulation".
"""
from __future__ import annotations

import math
import random
import uuid

from ..core.expected import is_modeled, offset
from ..core.assess import EARTH, MICROGRAVITY, PARTIAL, env_mode_for
from ..core.metrics import DAILY, SPECS, SURVEY_KEYS, WEEKLY, keys_for_mode
from ..core.reference import Reference
from ..core.store import Session, Store
from .crew import CREW, Astronaut
from .scenarios import Scenario

PREFLIGHT_DAYS = 7  # days -6 to 0

# Posture shift toward the environment's reference posture (simulated, team estimate):
# in microgravity the body drifts to the neutral body posture; partial gravity gets half of it.
NBP_SHIFT = {"head_forward_deg": 6.0, "trunk_tilt_deg": 4.0, "pelvis_tilt_deg": 3.0, "spine_length_mm": 8.0,
             "pose_return_s": 0.6}
NBP_TAU_DAYS = 2.0


def base_values(a: Astronaut) -> dict[str, float]:
    return {k: a.base.get(k, s.base) for k, s in SPECS.items()}


def env_mode(sc: Scenario, ref: Reference, day: int) -> str:
    return env_mode_for(ref.environment(sc.env).get("gravity_g"), day)


def _value(key: str, day: int, a: Astronaut, sc: Scenario, ref: Reference, rng: random.Random) -> float:
    spec = SPECS[key]
    b = a.base.get(key, spec.base)
    v = b
    exp = ref.expected(key)
    if day > 0 and is_modeled(exp):
        v += a.adapt * offset(exp, b, day)
    mode = env_mode(sc, ref, day)
    if key in NBP_SHIFT and mode != EARTH:
        k = 1.0 if mode == MICROGRAVITY else 0.5 if mode == PARTIAL else 0.0
        v += k * NBP_SHIFT[key] * (1 - math.exp(-day / NBP_TAU_DAYS))
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
    elif key in ("symptoms_flag", "back_pain_flag"):
        v = 0.0
    elif key in ("perclos", "shoulder_asym_deg", "facial_tension", "trunk_tilt_deg", "pelvis_tilt_deg",
                 "scapula_asym_mm", "pose_return_s"):
        v = max(0.0, v)
    return v


def simulate_values(a: Astronaut, day: int, mode: str, sc: Scenario, ref: Reference,
                    rng: random.Random, survey: bool = True, meta_out: dict | None = None,
                    rejects: dict[str, str] | None = None) -> dict[str, tuple[float, float]]:
    """Simulated (value, quality) per metric. If meta_out is given, it receives per-metric details
    (rPPG signal, reject_reason). `rejects` forces a measurement to fail with that reason."""
    keys = keys_for_mode(mode) + (SURVEY_KEYS if survey else [])
    out = {k: (_value(k, day, a, sc, ref, rng), round(rng.uniform(0.82, 0.98), 2))
           for k in keys if k != "flow_asymmetry_pct"}
    rejects = rejects or {}
    if meta_out is not None:
        if "hr_rppg" in out:
            sig = simulate_signal(rng, rejects.get("hr_rppg"))
            q = signal_quality(sig)
            out["hr_rppg"] = (out["hr_rppg"][0], q)
            meta_out["hr_rppg"] = {"signal": sig}
        for k, reason in rejects.items():
            if k in out:
                q = min(out[k][1], 0.3)
                out[k] = (out[k][0], q)
                meta_out.setdefault(k, {})["reject_reason"] = reason
    # left/right asymmetry is derived from the two Doppler readings, not independent noise
    if "doppler_flow_left_cms" in out:
        l, r = out["doppler_flow_left_cms"][0], out["doppler_flow_right_cms"][0]
        asym = 100 * abs(l - r) / ((l + r) / 2) + rng.gauss(0, 0.4)
        out["flow_asymmetry_pct"] = (max(0.0, asym), round(rng.uniform(0.82, 0.98), 2))
    return out


def session_mode(day: int) -> str:
    return WEEKLY if day % 7 == 0 else DAILY


def simulate_signal(rng: random.Random, reject: str | None = None) -> dict:
    """Simulated rPPG signal details for a 30 s window: usable seconds, motion (0..1), light (0..1)."""
    usable = round(rng.uniform(20, 28), 1)
    motion = round(rng.uniform(0.03, 0.15), 2)
    light = round(rng.uniform(0.7, 0.95), 2)
    if reject == "motion":
        usable, motion = round(rng.uniform(4, 9), 1), round(rng.uniform(0.55, 0.8), 2)
    elif reject == "low light":
        usable, light = round(rng.uniform(5, 10), 1), round(rng.uniform(0.1, 0.25), 2)
    elif reject:
        usable = round(rng.uniform(3, 8), 1)
    return {"usable_seconds": usable, "window_seconds": 30, "motion": motion, "light": light}


def signal_quality(sig: dict) -> float:
    """Quality 0..1 from the rPPG signal: enough usable seconds, little motion, enough light."""
    q = min(sig["usable_seconds"] / 20.0, 1.0) * (1 - sig["motion"]) * min(sig["light"] / 0.5, 1.0)
    return round(max(0.0, min(q, 1.0)), 2)


def dose_rate_msv_day(ref: Reference, env: str) -> tuple[float | None, str]:
    """Dose rate for the dosimeter simulation: from the environment, else from the metric (ISS). No invented figures."""
    e = ref.environment(env)
    for k in ("dose_rate_msv_day", "dose_rate_msv_per_day"):
        if isinstance(e.get(k), (int, float)) and e[k] > 0:
            return float(e[k]), f"reference: {e.get('name_ru', env)}"
    exp = ref.expected("radiation_dose_msv")
    rate = exp.get("rate")
    if isinstance(rate, (int, float)) and rate > 0:
        note = "" if env == "iss" else "; this is the ISS rate, the dose on the Moon or Mars is higher and the " \
                                       "dosimeter gives the real value"
        return float(rate), f"reference: {exp.get('rate_unit', 'mSv/day')}{note}"
    return None, "no data in the reference: import the dosimeter value manually"


def generate_history(store: Store, sc: Scenario, ref: Reference) -> None:
    """Days -6 to 0 (pre-flight) and 1 to day-1 (mission) for the whole crew."""
    store.clear()
    rng = random.Random(sc.seed)
    for a in CREW.values():
        skips = set(sc.skip_days.get(a.id, ()))
        for day in range(1 - PREFLIGHT_DAYS, sc.day):
            if day in skips:
                continue
            mode = session_mode(day) if day > 0 else WEEKLY
            store.add(Session(f"sim-{uuid.uuid4().hex[:8]}", a.id, day, mode,
                              simulate_values(a, day, mode, sc, ref, rng), simulated=True,
                              env_mode=env_mode(sc, ref, day)))
        rate, _ = dose_rate_msv_day(ref, sc.env)
        if rate:
            store.add_dose(a.id, sc.day - 1, rate * (sc.day - 1) * rng.uniform(0.95, 1.05),
                           "station dosimeter (simulated)")
