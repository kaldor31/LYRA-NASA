"""Сводит измерение сессии в результат: статусы, объяснения, тренды."""
from __future__ import annotations

from .assess import assess_metric, overall_status
from .db import Store
from .metrics import METRICS


def evaluate(store: Store, day: int, metrics: dict[str, tuple[float | None, float]]) -> dict:
    results = []
    for key in METRICS:
        if key not in metrics:
            continue
        value, quality = metrics[key]
        r = assess_metric(key, value, quality, store.history(key, before_day=day), store.preflight_mean(key))
        d = r.to_dict()
        d["series"] = store.series(key)
        results.append((r, d))
    return {
        "day": day,
        "overall": overall_status([r for r, _ in results]),
        "metrics": [d for _, d in results],
    }
