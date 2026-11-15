"""Session result assembly: metric statuses, overall result, 3D model and skeleton parameters."""
from __future__ import annotations

import math

from .assess import (EARTH, ENV_MODE_LABELS, MICROGRAVITY, MIN_QUALITY, RANK, REFERENCE_POSTURE, SIMULATION,
                     assess_metric, overall_status, worst)
from .metrics import SPECS
from .reference import Reference
from .store import Store

ZONES = ("face", "body", "legs", "hands", "posture")
KEYPOINTS = ("head", "shoulder_left", "shoulder_right", "elbow_left", "elbow_right", "pelvis",
             "knee_left", "knee_right", "foot_left", "foot_right")
VIEWS = ("front", "side", "back")


def skeleton(by: dict[str, dict], env_mode: str) -> dict:
    """Skeletal keypoint model from 3 synced views (front, side, back), in mm, simulated.

    Front/back: x = lateral (subject's left positive on the front view), y = up.
    Side: x = forward, y = up. Microgravity draws the neutral body posture (hips and knees flexed).
    """
    def val(k: str, default: float) -> float:
        r = by.get(k)
        return float(r["value"]) if r and r.get("value") is not None else default

    h = val("height_cm", SPECS["height_cm"].base) * 10
    head_fwd = math.radians(val("head_forward_deg", SPECS["head_forward_deg"].base))
    trunk = math.radians(val("trunk_tilt_deg", SPECS["trunk_tilt_deg"].base))
    pelvis_tilt = math.radians(val("pelvis_tilt_deg", SPECS["pelvis_tilt_deg"].base))
    sh_asym = math.radians(val("shoulder_asym_deg", SPECS["shoulder_asym_deg"].base))
    nbp = env_mode == MICROGRAVITY
    hip_flex, knee_flex = (math.radians(40), math.radians(50)) if nbp else (0.0, 0.0)

    sh_w, hip_w = 0.23 * h, 0.11 * h
    pelvis_y = 0.53 * h
    thigh, shin = 0.245 * h, 0.245 * h
    trunk_len, neck = 0.29 * h, 0.11 * h
    sh_dy = math.tan(sh_asym) * sh_w

    # side view (x forward)
    knee_x, knee_y = thigh * math.sin(hip_flex), pelvis_y - thigh * math.cos(hip_flex)
    foot_x, foot_y = knee_x - shin * math.sin(knee_flex - hip_flex), knee_y - shin * math.cos(knee_flex - hip_flex)
    sh_x, sh_y = trunk_len * math.sin(trunk + pelvis_tilt), pelvis_y + trunk_len * math.cos(trunk + pelvis_tilt)
    head_x, head_y = sh_x + neck * math.sin(head_fwd), sh_y + neck * math.cos(head_fwd)
    elbow_dx = 0.12 * h if nbp else 0.0  # arms float forward in microgravity
    side = {"head": [head_x, head_y], "shoulder_left": [sh_x, sh_y + sh_dy / 2],
            "shoulder_right": [sh_x, sh_y - sh_dy / 2], "elbow_left": [sh_x + elbow_dx, sh_y - 0.17 * h],
            "elbow_right": [sh_x + elbow_dx, sh_y - 0.17 * h], "pelvis": [0.0, pelvis_y],
            "knee_left": [knee_x, knee_y], "knee_right": [knee_x, knee_y],
            "foot_left": [foot_x, foot_y], "foot_right": [foot_x, foot_y]}
    lat_tilt = math.tan(pelvis_tilt) * hip_w / 2
    front = {"head": [0.0, head_y], "shoulder_left": [sh_w / 2, sh_y + sh_dy / 2],
             "shoulder_right": [-sh_w / 2, sh_y - sh_dy / 2], "elbow_left": [sh_w / 2 + 0.03 * h, sh_y - 0.17 * h],
             "elbow_right": [-sh_w / 2 - 0.03 * h, sh_y - 0.17 * h], "pelvis": [0.0, pelvis_y],
             "knee_left": [hip_w / 2, knee_y + lat_tilt], "knee_right": [-hip_w / 2, knee_y - lat_tilt],
             "foot_left": [hip_w / 2, foot_y + lat_tilt], "foot_right": [-hip_w / 2, foot_y - lat_tilt]}
    back = {k: [-x, y] for k, (x, y) in front.items()}
    rnd = lambda pts: {k: [round(x, 1), round(y, 1)] for k, (x, y) in pts.items()}  # noqa: E731
    return {"keypoints": list(KEYPOINTS), "units": "mm", "views": {"front": rnd(front), "side": rnd(side),
                                                                    "back": rnd(back)},
            "reference_posture": REFERENCE_POSTURE.get(env_mode), "simulated": True,
            "features": {k: (round(by[k]["value"], 2) if k in by and by[k].get("value") is not None
                             and by[k].get("confirmed", True) else None)
                         for k in ("head_forward_deg", "trunk_tilt_deg", "shoulder_asym_deg", "pelvis_tilt_deg",
                                   "scapula_asym_mm", "spine_length_mm", "pose_return_s")}}


def body_params(results: list[dict], env_mode: str = EARTH) -> dict:
    """What to highlight on the point cloud: change versus the pre-flight norm and the worst status per zone."""
    by = {r["key"]: r for r in results}

    def pct(k: str) -> float:
        r = by.get(k)
        return round(r["mission_pct"], 2) if r and r.get("mission_pct") is not None else 0.0

    def delta(k: str) -> float:
        r = by.get(k)
        if not r or r.get("value") is None or not r.get("confirmed", True):
            return 0.0
        # in space posture has no pre-flight reference: show the change versus the in-mission baseline
        ref_v = r["preflight"] if r.get("preflight") is not None else r.get("norm_mean")
        return round(r["value"] - ref_v, 2) if ref_v is not None else 0.0

    zones: dict[str, str | None] = {}
    for z in ZONES:
        st = [r["status"] for r in results if r["zone"] == z and r["status"] in RANK]
        zones[z] = worst(*st) if st else None
    return {"face_pct": pct("face_volume_ml"), "periorbital_mm": delta("periorbital_puffiness_mm"),
            "legs_pct": pct("leg_volume_ml"), "body_pct": pct("body_volume_l"), "height_pct": pct("height_cm"),
            "head_forward_deg": delta("head_forward_deg"), "shoulder_asym_deg": delta("shoulder_asym_deg"),
            "zones": zones, "skeleton": skeleton(by, env_mode)}


def _pain_or_fatigue(values: dict[str, tuple[float | None, float]]) -> bool:
    def v(k: str) -> float | None:
        x = values.get(k)
        return x[0] if x and x[1] >= MIN_QUALITY else None
    back, sleep, well = v("back_pain_flag"), v("sleep_score"), v("wellbeing_score")
    return bool((back is not None and back >= 1) or (sleep is not None and sleep <= 2)
                or (well is not None and well <= 2))


def evaluate(store: Store, ref: Reference, aid: str, day: int,
             values: dict[str, tuple[float | None, float]], meta: dict[str, dict] | None = None,
             env_mode: str = EARTH, include_research: bool = False, provenance: str = SIMULATION) -> dict:
    """Two comparison levels: the personal baseline (pre-flight, updated in mission) and the environment mode.

    Posture metrics outside Earth are compared only with in-mission history (the environment's reference
    posture), not with the Earth upright stance recorded before flight.
    """
    meta = meta or {}
    pain = _pain_or_fatigue(values)
    results = []
    for key in SPECS:
        if key not in values or SPECS[key].group == "dose":
            continue
        v, q = values[key]
        posture_in_space = SPECS[key].zone == "posture" and env_mode != EARTH
        hist = store.history(aid, key, before_day=day, since_day=1 if posture_in_space else None)
        pre = None if posture_in_space else store.preflight_mean(aid, key)
        results.append(assess_metric(key, v, q, hist, preflight=pre, day=day, ref=ref, meta=meta.get(key),
                                     env_mode=env_mode, pain_or_fatigue=pain, provenance=provenance))
    dicts = [r.to_dict() for r in results]
    return {"day": day, "env_mode": env_mode, "env_mode_label": ENV_MODE_LABELS[env_mode],
            "provenance": provenance,
            "provenance_note": "All values in this demo are simulated. NASA material sets the expected-adaptation "
                               "corridors; no team recordings or open-dataset values are used here.",
            "overall": overall_status(results, include_research), "metrics": dicts,
            "body": body_params(dicts, env_mode)}


__all__ = ["evaluate", "body_params", "skeleton"]
