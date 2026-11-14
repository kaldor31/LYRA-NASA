"""Личная норма, статусы и объяснения простым языком.

Логика:
  личная норма = среднее и σ последних 14 измерений этого человека (минимум 7);
  z = (значение − среднее) / σ, учитываем только опасное направление;
  |z| < 2 → норма, 2…3 → повторить, ≥ 3 → возможное отклонение;
  измерение с низким качеством не влияет на статус, просим повторить.
"""
from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass

from .metrics import METRICS, MetricSpec

GREEN, YELLOW, RED, RETRY = "green", "yellow", "red", "retry"
MIN_QUALITY = 0.5
MIN_HISTORY = 7

OVERALL_TITLES = {
    GREEN: "Стабильное состояние",
    YELLOW: "Нужна повторная проверка",
    RED: "Возможное отклонение",
}
DISCLAIMER = "Это предварительная оценка, а не диагноз."


@dataclass
class Baseline:
    mean: float
    sd: float
    n: int
    kind: str  # "personal" | "reference"


@dataclass
class MetricResult:
    key: str
    name: str
    unit: str
    group: str
    value: float | None
    quality: float
    status: str
    z: float | None
    mean: float
    sd: float
    baseline_kind: str
    delta: float | None
    delta_pct: float | None
    mission_pct: float | None
    text: str

    def to_dict(self) -> dict:
        return asdict(self)


def make_baseline(values: list[float], spec: MetricSpec) -> Baseline:
    if len(values) < MIN_HISTORY:
        lo, hi = spec.ref
        return Baseline(mean=(lo + hi) / 2, sd=(hi - lo) / 4, n=len(values), kind="reference")
    sd = statistics.stdev(values) if len(values) > 1 else 0.0
    return Baseline(mean=statistics.fmean(values), sd=max(sd, spec.min_sd), n=len(values), kind="personal")


def _fmt(x: float, d: int) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def assess_metric(
    key: str,
    value: float | None,
    quality: float,
    history: list[float],
    preflight_mean: float | None = None,
) -> MetricResult:
    s = METRICS[key]
    base = make_baseline(history, s)
    unit = f" {s.unit}" if s.unit else ""

    if value is None or quality < MIN_QUALITY:
        return MetricResult(
            key, s.name, s.unit, s.group, value, quality, RETRY, None, base.mean, base.sd, base.kind,
            None, None, None,
            f"{s.name}: измерение ненадёжное (движение, свет или положение). "
            "Повторите, стоя неподвижно при ровном освещении.",
        )

    z = (value - base.mean) / base.sd
    danger = {"up": z, "down": -z, "both": abs(z)}[s.direction]
    status = GREEN if danger < 2 else YELLOW if danger < 3 else RED

    delta = value - base.mean
    delta_pct = 100 * delta / base.mean if base.mean else None
    mission_pct = 100 * (value - preflight_mean) / preflight_mean if preflight_mean else None

    norm_word = "вашей нормы" if base.kind == "personal" else "общего диапазона"
    if status == GREEN:
        text = f"{s.name}: {_fmt(value, s.decimals)}{unit} — в пределах {norm_word}."
    else:
        word = "выше" if delta > 0 else "ниже"
        show_pct = delta_pct is not None and s.unit != "%" and abs(base.mean) > 1e-9
        pct = f" ({_fmt(abs(delta_pct), 0)} %)" if show_pct else ""
        text = (
            f"{s.name}: {_fmt(value, s.decimals)}{unit} — на {_fmt(abs(delta), s.decimals)}{unit}{pct} "
            f"{word} {norm_word} ({_fmt(base.mean, s.decimals)}). {s.advice}"
        )
    if mission_pct is not None and abs(mission_pct) >= 3:
        sign = "+" if mission_pct > 0 else "−"
        text += f" С начала полёта: {sign}{_fmt(abs(mission_pct), 0)} %."

    return MetricResult(
        key, s.name, s.unit, s.group, value, quality, status, round(z, 2), base.mean, base.sd, base.kind,
        delta, delta_pct, mission_pct, text,
    )


def overall_status(results: list[MetricResult]) -> dict:
    statuses = [r.status for r in results]
    yellows = statuses.count(YELLOW)
    if RED in statuses or yellows >= 2:
        status = RED
    elif yellows == 1 or RETRY in statuses:
        status = YELLOW
    else:
        status = GREEN

    flagged = [r for r in results if r.status in (YELLOW, RED)]
    retries = [r for r in results if r.status == RETRY]
    if status == GREEN:
        summary = "Все показатели в пределах вашей нормы."
    else:
        def low(name: str) -> str:  # «Пульс (камера)» → «пульс (камера)», аббревиатуры не трогаем
            return name[0].lower() + name[1:]

        parts = []
        if flagged:
            parts.append("Отклонились: " + ", ".join(low(r.name) for r in flagged) + ".")
        if retries:
            parts.append("Нужно переизмерить: " + ", ".join(low(r.name) for r in retries) + ".")
        if status == RED:
            parts.append("Повторите проверку через 10–15 минут в покое; если отклонение сохранится — свяжитесь с лётным врачом.")
        else:
            parts.append("Повторите проверку через 10–15 минут.")
        summary = " ".join(parts)
    return {"status": status, "title": OVERALL_TITLES[status], "summary": f"{summary} {DISCLAIMER}"}
