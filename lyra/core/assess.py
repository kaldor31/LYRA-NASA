"""Статусы и объяснения простым языком.

Статус метрики = комбинация двух вопросов:
  (а) личная норма: отличаешься ли ты от себя за последние 14 измерений?
      z = (значение − среднее) / σ, только опасное направление; <2 🟢, 2–3 🟡, ≥3 🔴.
      Если у метрики есть траектория NASA, норма считается по остаткам «значение − ожидание NASA
      на тот день» — иначе ожидаемый сдвиг первых дней выглядел бы как резкий скачок;
  (б) коридор NASA: меняешься ли ты быстрее, чем ожидает NASA для этого дня полёта?
      выход за коридор в опасную сторону: меньше полуширины 🟡, больше 🔴.
Правило комбинации (если у метрики есть коридор):
  • внутри коридора → 🟢 «ожидаемая адаптация», даже если от вчерашнего ты отличаешься;
    но резкий скачок (z ≥ 3) → 🟡 «повторите»;
  • вне коридора → худший из (а) и (б).
Без коридора (expected.model == "none") — только (а). Самоотчёт — простые пороги.
Это скрининг, не диагноз.
"""
from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass, field

from .expected import Corridor, corridor, expected_change_pct, is_modeled, offset
from .metrics import SPECS, SURVEY, MetricSpec
from .reference import Reference

GREEN, YELLOW, RED, RETRY = "green", "yellow", "red", "retry"
RANK = {GREEN: 0, RETRY: 1, YELLOW: 2, RED: 3}
MIN_QUALITY = 0.5
MIN_HISTORY = 7
NORM_WINDOW = 14

DISCLAIMER = "Это скрининг, а не диагноз."
OVERALL_TITLES = {GREEN: "Стабильно", YELLOW: "Нужна повторная проверка", RED: "Возможное отклонение"}


@dataclass
class Baseline:
    mean: float
    sd: float
    n: int
    kind: str  # personal | reference


@dataclass
class MetricResult:
    key: str
    name: str
    unit: str
    group: str
    zone: str
    value: float | None
    quality: float
    status: str
    z: float | None
    z_status: str | None
    corridor_status: str | None
    norm_mean: float
    norm_sd: float
    norm_kind: str
    preflight: float | None
    mission_pct: float | None
    expected_pct: float | None
    corridor: dict | None
    faster_than_nasa: bool
    text: str
    action: str
    steps: list[str] = field(default_factory=list)
    risks: list[dict] = field(default_factory=list)
    basis: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def worst(*statuses: str | None) -> str:
    return max((s for s in statuses if s), key=lambda s: RANK[s], default=GREEN)


def make_baseline(values: list[float], spec: MetricSpec) -> Baseline:
    if len(values) < MIN_HISTORY:
        lo, hi = spec.ref
        return Baseline((lo + hi) / 2, max((hi - lo) / 4, spec.noise), len(values), "reference")
    sd = statistics.stdev(values) if len(values) > 1 else 0.0
    return Baseline(statistics.fmean(values), max(sd, spec.noise), len(values), "personal")


def fmt(x: float, d: int = 1, sign: bool = False) -> str:
    s = f"{abs(x):,.{d}f}".replace(",", " ").replace(".", ",")
    if sign:
        return ("+" if x > 0 else "−" if x < 0 else "±") + s
    return ("−" if x < 0 else "") + s


def _z_status(z: float, direction: str) -> str:
    danger = {"up": z, "down": -z, "both": abs(z)}[direction]
    return GREEN if danger < 2 else YELLOW if danger < 3 else RED


def _corridor_excess(value: float, c: Corridor, direction: str) -> float:
    """На сколько полуширин коридора значение вышло за него в опасную сторону (≤0 — не вышло)."""
    half = (c.hi - c.lo) / 2 or 1e-9
    up, down = (value - c.hi) / half, (c.lo - value) / half
    return {"up": up, "down": down, "both": max(up, down)}[direction]


def _survey_status(key: str, value: float) -> str:
    if key == "symptoms_flag":
        return YELLOW if value >= 1 else GREEN
    return RED if value <= 1 else YELLOW if value <= 2 else GREEN


def _name(ref: Reference, spec: MetricSpec) -> tuple[str, str]:
    m = ref.metric(spec.key)
    return m.get("name_ru") or spec.name, m.get("unit") or spec.unit


def _change(value: float, preflight: float, unit: str, relative: bool, d: int) -> str:
    """Изменение к норме до полёта понятными единицами: %, п.п. или мм/°."""
    if unit == "%":
        return f"{fmt(value - preflight, 1, True)} п.п."
    if relative and preflight:
        return f"{fmt(100 * (value - preflight) / preflight, 1, True)} %"
    return f"{fmt(value - preflight, max(d, 1), True)} {unit}".strip()


def assess_metric(key: str, value: float | None, quality: float, history: list, *,
                  preflight: float | None = None, day: int = 0, ref: Reference) -> MetricResult:
    """history — список (день, значение) или просто значений (тогда без поправки на траекторию)."""
    spec = SPECS[key]
    name, unit = _name(ref, spec)
    u = f" {unit}" if unit and spec.session != SURVEY else ""
    expected = ref.expected(key)
    pairs = [h if isinstance(h, tuple) else (None, h) for h in history][-NORM_WINDOW:]
    detrend = is_modeled(expected) and preflight is not None and all(d is not None for d, _ in pairs)
    shift = (lambda d: offset(expected, preflight, d)) if detrend else (lambda d: 0.0)
    resid = [v - shift(d) for d, v in pairs]
    base = make_baseline(resid, spec)
    if detrend and base.kind == "reference":  # мало истории: остатки не с чем сравнить
        base = Baseline(0.0, max(spec.noise, 1e-9), len(resid), "reference")
    risks = ref.risks_for(key)
    common = dict(key=key, name=name, unit=unit, group=spec.group, zone=spec.zone, quality=quality,
                  norm_mean=base.mean, norm_sd=base.sd, norm_kind=base.kind, preflight=preflight,
                  risks=risks, basis=expected.get("basis"))

    if value is None or quality < MIN_QUALITY:
        return MetricResult(**common, value=value, status=RETRY, z=None, z_status=None, corridor_status=None,
                            mission_pct=None, expected_pct=None, corridor=None, faster_than_nasa=False,
                            text=f"{name}: измерение ненадёжное (движение или положение). Повторите, стоя неподвижно.",
                            action="Повторите измерение.")

    mission_pct = 100 * (value - preflight) / preflight if preflight else None

    # ---- самоотчёт: простые пороги, без коридора ----
    if spec.session == SURVEY:
        status = _survey_status(key, value)
        shown = ("да" if value >= 1 else "нет") if key == "symptoms_flag" else f"{fmt(value, 0)} из 5"
        text = f"{name}: {shown}." + ("" if status == GREEN else " Отмечено в отчёте для лётного врача.")
        return MetricResult(**common, value=value, status=status, z=None, z_status=None, corridor_status=None,
                            mission_pct=None, expected_pct=None, corridor=None, faster_than_nasa=False, text=text,
                            action="" if status == GREEN else spec.advice,
                            steps=list(spec.steps) if status == RED else [])

    # ---- (а) личная норма ----
    z = (value - shift(day) - base.mean) / base.sd
    z_status = _z_status(z, spec.direction) if not (detrend and len(resid) < MIN_HISTORY) else GREEN
    norm_value = base.mean + shift(day)  # личная норма «на сегодня» с учётом ожидаемой адаптации
    common["norm_mean"] = norm_value
    # ---- (б) коридор NASA ----
    c = corridor(expected, preflight, day, spec.noise) if preflight is not None and day > 0 else None
    c_status, excess = None, 0.0
    if c:
        excess = _corridor_excess(value, c, spec.direction)
        c_status = GREEN if excess <= 0 else YELLOW if excess < 1 else RED
        status = (YELLOW if z_status == RED else GREEN) if c_status == GREEN else worst(c_status, z_status)
    else:
        status = z_status
    faster = bool(c and excess > 0)
    exp_pct = expected_change_pct(expected, preflight, day) if preflight else None

    # ---- объяснение ----
    relative = "%" in str(expected.get("rate_unit", "%")) or not is_modeled(expected)
    parts = [f"{name}: {fmt(value, spec.decimals)}{u}"]
    if preflight is not None and day > 0 and abs(value - preflight) >= spec.noise:
        parts[0] += f" ({_change(value, preflight, unit, relative, spec.decimals)} к норме до полёта)"
    parts[0] += "."
    if c:
        ch = lambda x: _change(x, preflight, unit, relative, spec.decimals)  # noqa: E731
        band = f"коридор {ch(c.lo)} … {ch(c.hi)}"
        if faster:
            parts.append(f"Меняется быстрее, чем ожидает NASA: на день {day} ожидается "
                         f"{ch(c.center)} ({band}).")
        elif _corridor_excess(value, c, {"up": "down", "down": "up", "both": "both"}[spec.direction]) > 0:
            parts.append(f"Изменение меньше ожидаемого NASA ({band}) — хорошо.")
        else:
            parts.append(f"В коридоре ожидаемой адаптации NASA на день {day} ({band}).")
    if z_status != GREEN:
        word = "выше" if z > 0 else "ниже"
        norm = "вашей нормы за последние 14 дней" if base.kind == "personal" else "общего диапазона"
        parts.append(f"Резко {word} {norm} ({fmt(norm_value, spec.decimals)}{u}).")
    elif not c:
        parts.append("В пределах вашей личной нормы." if base.kind == "personal" else "В пределах общего диапазона.")
    if status != GREEN and risks:
        parts.append(f"Связано с риском NASA: «{risks[0]['name_ru']}».")

    if status == GREEN:
        action = ""
    elif status == YELLOW:
        action = (spec.advice + " Повторите скан завтра.").strip() if faster else \
                 (spec.advice + " Повторите измерение через 15 минут.").strip()
    else:
        action = "Выполните шаги ниже."

    return MetricResult(**common, value=value, status=status, z=round(z, 2), z_status=z_status,
                        corridor_status=c_status, mission_pct=mission_pct, expected_pct=exp_pct,
                        corridor=c.to_dict() if c else None, faster_than_nasa=faster, text=" ".join(parts),
                        action=action, steps=list(spec.steps or (spec.advice, "Повторите сеанс.",
                                                                  "Сообщите лётному врачу.")) if status == RED else [])


def overall_status(results: list[MetricResult]) -> dict:
    statuses = [r.status for r in results]
    yellows = statuses.count(YELLOW)
    if RED in statuses or yellows >= 2:
        status = RED
    elif yellows == 1 or RETRY in statuses:
        status = YELLOW
    else:
        status = GREEN

    def low(n: str) -> str:
        return n[0].lower() + n[1:] if n[:2] != n[:2].upper() else n

    flagged = [r for r in results if r.status in (YELLOW, RED)]
    faster = [r for r in flagged if r.faster_than_nasa]
    retries = [r for r in results if r.status == RETRY]
    if status == GREEN:
        summary = "Все показатели в пределах вашей нормы и ожидаемой адаптации NASA."
        steps: list[str] = []
    else:
        parts = []
        if faster:
            parts.append("Быстрее, чем ожидает NASA: " + ", ".join(low(r.name) for r in faster) + ".")
        selfrep = [r for r in flagged if r.group == "self" and r not in faster]
        rest = [r for r in flagged if r not in faster and r not in selfrep]
        if selfrep:
            parts.append("Самоотчёт: " + ", ".join(low(r.name.split(" (")[0]) for r in selfrep) + ".")
        if rest:
            parts.append("Отклонились от вашей нормы: " + ", ".join(low(r.name) for r in rest) + ".")
        if retries:
            parts.append("Нужно переизмерить: " + ", ".join(low(r.name) for r in retries) + ".")
        summary = " ".join(parts)
        if status == RED:
            steps = ["Остановитесь и зафиксируйтесь у станции, 5 минут спокойного дыхания.",
                     "Выполните шаги в карточках, отмеченных 🔴.",
                     "Повторите сеанс через 15 минут.",
                     "Лётный врач уже получает данные; если отклонение сохранится — выйдите на связь."]
        else:
            steps = ["Выполните действие из карточки 🟡.", "Повторите скан завтра (или через 15 минут)."]
    return {"status": status, "title": OVERALL_TITLES[status], "summary": summary, "steps": steps,
            "disclaimer": DISCLAIMER, "flagged": [r.key for r in flagged], "faster_than_nasa": [r.key for r in faster]}
