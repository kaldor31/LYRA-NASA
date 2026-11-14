"""Сборка результата сеанса: статусы метрик, общий итог, параметры 3D-модели."""
from __future__ import annotations

from .assess import GREEN, RANK, assess_metric, overall_status, worst
from .metrics import SPECS
from .reference import Reference
from .store import Store

ZONES = ("face", "body", "legs", "hands", "posture")


def body_params(results: list[dict]) -> dict:
    """Что подсветить на облаке точек: изменение к норме до полёта и худший статус зоны."""
    by = {r["key"]: r for r in results}

    def pct(k: str) -> float:
        r = by.get(k)
        return round(r["mission_pct"], 2) if r and r.get("mission_pct") is not None else 0.0

    def delta(k: str) -> float:
        r = by.get(k)
        if not r or r.get("value") is None or r.get("preflight") is None:
            return 0.0
        return round(r["value"] - r["preflight"], 2)

    zones: dict[str, str | None] = {}
    for z in ZONES:
        st = [r["status"] for r in results if r["zone"] == z and r["status"] in RANK]
        zones[z] = worst(*st) if st else None
    return {"face_pct": pct("face_volume_ml"), "periorbital_mm": delta("periorbital_puffiness_mm"),
            "legs_pct": pct("leg_volume_ml"), "body_pct": pct("body_volume_l"), "height_pct": pct("height_cm"),
            "head_forward_deg": delta("head_forward_deg"), "shoulder_asym_deg": delta("shoulder_asym_deg"),
            "zones": zones}


def evaluate(store: Store, ref: Reference, aid: str, day: int,
             values: dict[str, tuple[float | None, float]]) -> dict:
    results = []
    for key in SPECS:
        if key not in values or SPECS[key].group == "dose":
            continue
        v, q = values[key]
        results.append(assess_metric(key, v, q, store.history(aid, key, before_day=day),
                                     preflight=store.preflight_mean(aid, key), day=day, ref=ref))
    dicts = [r.to_dict() for r in results]
    return {"day": day, "overall": overall_status(results), "metrics": dicts, "body": body_params(dicts)}


__all__ = ["evaluate", "body_params", "GREEN"]
