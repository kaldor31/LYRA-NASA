"""Result categories and plain-language explanations.

A metric's status combines two questions:
  (a) personal baseline: do you differ from yourself over the last 14 measurements?
      z = (value - mean) / sigma, harmful direction only; <2 green, 2 to 3 yellow, >=3 red.
      If the metric has a NASA trajectory, the baseline is computed on residuals "value - NASA expectation
      for that day"; otherwise the expected shift of the first days would look like a sudden jump;
  (b) NASA corridor: are you changing faster than NASA expects for this mission day?
      leaving the corridor in the harmful direction: less than one half-width yellow, more red.
Combination rule (when the metric has a corridor):
  * inside the corridor -> green "expected adaptation", even if you differ from yesterday;
    but a sudden jump (z >= 3) -> yellow "repeat measurement";
  * outside the corridor -> the worse of (a) and (b).
Without a corridor (expected.model == "none") only (a) applies. Self-report uses simple thresholds.

Human-facing labels (internal codes stay green/yellow/red/retry):
  green  "Within baseline"
  yellow "Repeat measurement"
  red    "Refer to specialist" (sustained change, for the medical team)
  retry  "Measurement not confirmed" (quality too low; no averaged value is substituted)

Posture is compared with the environment's reference posture (in microgravity: the neutral body
posture, not the Earth upright stance) and only escalates to red if the change repeats across several
measurements or comes together with reported back pain or fatigue.
This is screening, not a diagnosis: LYRA reports "change detected", never a diagnosis.
"""
from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass, field

from .expected import Corridor, corridor, expected_change_pct, is_modeled, offset
from .metrics import CORE, SPECS, SURVEY, MetricSpec
from .reference import Reference

GREEN, YELLOW, RED, RETRY = "green", "yellow", "red", "retry"
RANK = {GREEN: 0, RETRY: 1, YELLOW: 2, RED: 3}
MIN_QUALITY = 0.5
MIN_HISTORY = 7
NORM_WINDOW = 14
POSTURE_REPEAT = 2  # previous measurements that must also deviate for a posture flag to escalate

STATUS_LABELS = {GREEN: "Within baseline", YELLOW: "Repeat measurement", RED: "Refer to specialist",
                 RETRY: "Measurement not confirmed"}
DISCLAIMER = "This is screening, not a diagnosis."
OVERALL_TITLES = {GREEN: STATUS_LABELS[GREEN], YELLOW: STATUS_LABELS[YELLOW], RED: STATUS_LABELS[RED]}

# Where a value came from. In this demo almost everything is "simulation".
PROVENANCE = ("team recording", "open dataset (CameraVitals)", "NASA material", "simulation")
SIMULATION = "simulation"

# Environment mode = second comparison level (the first is the personal baseline).
EARTH, MICROGRAVITY, PARTIAL = "earth", "microgravity", "partial_gravity"
ENV_MODE_LABELS = {EARTH: "Earth", MICROGRAVITY: "Microgravity", PARTIAL: "Partial gravity (rover or base)"}
REFERENCE_POSTURE = {EARTH: "earth_upright", MICROGRAVITY: "microgravity_neutral_body_posture",
                     PARTIAL: "partial_gravity_upright"}
REFERENCE_POSTURE_LABELS = {"earth_upright": "Earth upright stance",
                            "microgravity_neutral_body_posture": "microgravity neutral body posture",
                            "partial_gravity_upright": "partial-gravity upright stance"}

DEFAULT_REJECT = {"face": "face not visible", "body": "pose not reached", "hands": "weak signal",
                  "self": "no answer", "dose": "no data"}


def env_mode_for(gravity_g: float | None, day: int) -> str:
    """Pre-flight days are on Earth; in flight: 0 g is microgravity, below 1 g is partial gravity."""
    if day <= 0 or gravity_g is None:
        return EARTH if day <= 0 else MICROGRAVITY
    if gravity_g <= 0.01:
        return MICROGRAVITY
    return PARTIAL if gravity_g < 0.9 else EARTH


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
    label: str = ""                    # human-facing category label
    module: str = CORE                 # core | research
    confirmed: bool = True             # False when quality is too low (status retry)
    reject_reason: str | None = None   # why the measurement is not usable
    signal: dict | None = None         # rPPG signal details: usable_seconds, motion, light
    provenance: str = SIMULATION
    env_mode: str = EARTH
    reference_posture: str | None = None  # posture metrics only
    previous_value: float | None = None
    previous_day: int | None = None
    change_vs_previous: float | None = None
    flag_reason: str | None = None     # why it is flagged, in words (not just a color)
    repeated: bool = False             # posture: the change also appeared in previous measurements

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
    s = f"{abs(x):,.{d}f}"
    if sign:
        return ("+" if x > 0 else "-" if x < 0 else "+/-") + s
    return ("-" if x < 0 else "") + s


def _danger(z: float, direction: str) -> float:
    return {"up": z, "down": -z, "both": abs(z)}[direction]


def _z_status(z: float, direction: str) -> str:
    danger = _danger(z, direction)
    return GREEN if danger < 2 else YELLOW if danger < 3 else RED


def _corridor_excess(value: float, c: Corridor, direction: str) -> float:
    """How many corridor half-widths the value is outside the corridor in the harmful direction (<=0: inside)."""
    half = (c.hi - c.lo) / 2 or 1e-9
    up, down = (value - c.hi) / half, (c.lo - value) / half
    return {"up": up, "down": down, "both": max(up, down)}[direction]


def _survey_status(key: str, value: float) -> str:
    if key in ("symptoms_flag", "back_pain_flag"):
        return YELLOW if value >= 1 else GREEN
    return RED if value <= 1 else YELLOW if value <= 2 else GREEN


def _name(ref: Reference, spec: MetricSpec) -> tuple[str, str]:
    m = ref.metric(spec.key)
    return m.get("name_ru") or spec.name, m.get("unit") or spec.unit


def _change(value: float, preflight: float, unit: str, relative: bool, d: int) -> str:
    """Change versus the pre-flight norm in clear units: %, percentage points, or mm/degrees."""
    if unit == "%":
        return f"{fmt(value - preflight, 1, True)} pp"
    if relative and preflight:
        return f"{fmt(100 * (value - preflight) / preflight, 1, True)}%"
    return f"{fmt(value - preflight, max(d, 1), True)} {unit}".strip()


def assess_metric(key: str, value: float | None, quality: float, history: list, *,
                  preflight: float | None = None, day: int = 0, ref: Reference, meta: dict | None = None,
                  env_mode: str | None = None, pain_or_fatigue: bool = False,
                  provenance: str = SIMULATION) -> MetricResult:
    """history: list of (day, value) or bare values (then no trajectory correction).

    meta: optional per-measurement details: reject_reason, signal (rPPG usable_seconds, motion, light).
    """
    spec = SPECS[key]
    meta = meta or {}
    env_mode = env_mode or (EARTH if day <= 0 else MICROGRAVITY)
    name, unit = _name(ref, spec)
    u = f" {unit}" if unit and spec.session != SURVEY else ""
    expected = ref.expected(key)
    pairs = [h if isinstance(h, tuple) else (None, h) for h in history][-NORM_WINDOW:]
    detrend = is_modeled(expected) and preflight is not None and all(d is not None for d, _ in pairs)
    shift = (lambda d: offset(expected, preflight, d)) if detrend else (lambda d: 0.0)
    resid = [v - shift(d) for d, v in pairs]
    base = make_baseline(resid, spec)
    if detrend and base.kind == "reference":  # too little history: nothing to compare residuals with
        base = Baseline(0.0, max(spec.noise, 1e-9), len(resid), "reference")
    risks = ref.risks_for(key, spec.risk_ids)
    posture = spec.zone == "posture"
    ref_posture = REFERENCE_POSTURE.get(env_mode) if posture else None
    prev_day, prev_val = pairs[-1] if pairs else (None, None)
    common = dict(key=key, name=name, unit=unit, group=spec.group, zone=spec.zone, quality=quality,
                  norm_mean=base.mean, norm_sd=base.sd, norm_kind=base.kind, preflight=preflight,
                  risks=risks, basis=expected.get("basis"), module=spec.module, signal=meta.get("signal"),
                  provenance=provenance, env_mode=env_mode, reference_posture=ref_posture,
                  previous_value=prev_val, previous_day=prev_day)

    if value is None or quality < MIN_QUALITY:
        reason = meta.get("reject_reason") or DEFAULT_REJECT.get(spec.group, "motion")
        return MetricResult(**common, value=value, status=RETRY, z=None, z_status=None, corridor_status=None,
                            mission_pct=None, expected_pct=None, corridor=None, faster_than_nasa=False,
                            text=f"{name}: measurement not confirmed ({reason}). No averaged value is used "
                                 f"in its place.",
                            action="Repeat the measurement.", label=STATUS_LABELS[RETRY], confirmed=False,
                            reject_reason=reason, flag_reason=f"Measurement not confirmed: {reason}.")

    common["change_vs_previous"] = round(value - prev_val, 4) if prev_val is not None else None
    mission_pct = 100 * (value - preflight) / preflight if preflight else None

    # ---- self-report: simple thresholds, no corridor ----
    if spec.session == SURVEY:
        status = _survey_status(key, value)
        yes_no = key in ("symptoms_flag", "back_pain_flag")
        shown = ("yes" if value >= 1 else "no") if yes_no else f"{fmt(value, 0)} of 5"
        text = f"{name}: {shown}." + ("" if status == GREEN else " Noted in the report for the flight surgeon.")
        return MetricResult(**common, value=value, status=status, z=None, z_status=None, corridor_status=None,
                            mission_pct=None, expected_pct=None, corridor=None, faster_than_nasa=False, text=text,
                            action="" if status == GREEN else spec.advice,
                            steps=list(spec.steps) if status == RED else [], label=STATUS_LABELS[status],
                            flag_reason=None if status == GREEN else
                            f"Self-report: {_low(name.split(' (')[0])}, {shown}.")

    # ---- (a) personal baseline ----
    z = (value - shift(day) - base.mean) / base.sd
    z_status = _z_status(z, spec.direction) if not (detrend and len(resid) < MIN_HISTORY) else GREEN
    norm_value = base.mean + shift(day)  # today's personal norm, including expected adaptation
    common["norm_mean"] = norm_value
    # ---- (b) NASA corridor ----
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

    # ---- posture: escalate only if repeated or combined with back pain / fatigue ----
    repeated = False
    if posture and status != GREEN:
        recent = resid[-POSTURE_REPEAT:]
        # judge the recent values against the history before them, so a sustained change cannot
        # inflate the baseline it is compared with
        older = resid[:-POSTURE_REPEAT]
        rb = make_baseline(older, spec) if len(older) >= MIN_HISTORY else base
        repeated = len(recent) == POSTURE_REPEAT and all(
            _danger((v - rb.mean) / rb.sd, spec.direction) >= 2 for v in recent)
        # a single posture change stays "Repeat measurement"; repeated or with pain/fatigue it escalates
        status = RED if (repeated or pain_or_fatigue) else YELLOW

    # ---- explanation ----
    relative = "%" in str(expected.get("rate_unit", "%")) or not is_modeled(expected)
    parts = [f"{name}: {fmt(value, spec.decimals)}{u}"]
    if preflight is not None and day > 0 and abs(value - preflight) >= spec.noise:
        parts[0] += f" ({_change(value, preflight, unit, relative, spec.decimals)} vs pre-flight norm)"
    parts[0] += "."
    reasons: list[str] = []
    if c:
        ch = lambda x: _change(x, preflight, unit, relative, spec.decimals)  # noqa: E731
        band = f"corridor {ch(c.lo)} to {ch(c.hi)}"
        if faster:
            msg = f"Changing faster than NASA expects: for day {day} the expectation is {ch(c.center)} ({band})."
            parts.append(msg)
            reasons.append(msg)
        elif _corridor_excess(value, c, {"up": "down", "down": "up", "both": "both"}[spec.direction]) > 0:
            parts.append(f"Change is smaller than NASA expects ({band}), which is good.")
        else:
            parts.append(f"Within the NASA expected-adaptation corridor for day {day} ({band}).")
    if posture and ref_posture:
        parts.append(f"Compared with the {REFERENCE_POSTURE_LABELS[ref_posture]}.")
    if z_status != GREEN:
        word = "above" if z > 0 else "below"
        norm = "your baseline for the last 14 measurements" if base.kind == "personal" else "the population range"
        msg = f"Change detected: clearly {word} {norm} ({fmt(norm_value, spec.decimals)}{u})."
        parts.append(msg)
        reasons.append(msg)
    elif not c:
        parts.append("Within your personal baseline." if base.kind == "personal" else "Within the population range.")
    if posture and status != GREEN:
        if repeated:
            reasons.append(f"Posture change repeated in the previous {POSTURE_REPEAT} measurements.")
        if pain_or_fatigue:
            reasons.append("Reported together with back pain or fatigue.")
        if not repeated and not pain_or_fatigue:
            parts.append("A single posture change is not escalated; repeat to confirm.")
    if spec.module != CORE:
        parts.append("Research module: shown separately, not part of the overall result.")
    if status != GREEN and risks:
        parts.append(f'Related NASA risk: "{risks[0]["name_ru"]}".')

    if status == GREEN:
        action = ""
    elif status == YELLOW:
        action = (spec.advice + " Repeat the scan tomorrow.").strip() if faster else \
                 (spec.advice + " Repeat the measurement in 15 minutes.").strip()
    else:
        action = "Follow the steps below. The medical team receives this result."

    return MetricResult(**common, value=value, status=status, z=round(z, 2), z_status=z_status,
                        corridor_status=c_status, mission_pct=mission_pct, expected_pct=exp_pct,
                        corridor=c.to_dict() if c else None, faster_than_nasa=faster, text=" ".join(parts),
                        action=action, steps=list(spec.steps or (spec.advice, "Repeat the session.",
                                                                  "Tell the flight surgeon.")) if status == RED else [],
                        label=STATUS_LABELS[status], flag_reason=(" ".join(reasons) or "Change detected.") if status != GREEN else None,
                        repeated=repeated)


def _low(n: str) -> str:
    return n[:1].lower() + n[1:] if n[:2] != n[:2].upper() else n


def _status_of(results: list[MetricResult]) -> str:
    statuses = [r.status for r in results]
    # posture metrics move together (one posture change shifts several angles); a single, not yet
    # escalated posture change counts as one "Repeat measurement", not as several
    posture_yellows = sum(1 for r in results if r.status == YELLOW and r.zone == "posture")
    yellows = statuses.count(YELLOW) - max(0, posture_yellows - 1)
    if RED in statuses or yellows >= 2:
        return RED
    if yellows == 1 or RETRY in statuses:
        return YELLOW
    return GREEN


def _flags(results: list[MetricResult]) -> list[dict]:
    return [{"key": r.key, "name": r.name, "status": r.status, "label": r.label, "module": r.module,
             "reason": r.flag_reason or r.text} for r in results if r.status in (YELLOW, RED, RETRY)]


def overall_status(results: list[MetricResult], include_research: bool = False) -> dict:
    """Overall result. Research-module metrics are excluded by default and summarized separately."""
    research = [r for r in results if r.module != CORE]
    scored = results if include_research else [r for r in results if r.module == CORE]
    status = _status_of(scored)

    flagged = [r for r in scored if r.status in (YELLOW, RED)]
    faster = [r for r in flagged if r.faster_than_nasa]
    retries = [r for r in scored if r.status == RETRY]
    if status == GREEN:
        summary = "All core measurements are within your baseline and NASA expected adaptation."
        steps: list[str] = []
    else:
        parts = []
        if faster:
            parts.append("Change detected, faster than NASA expects: " + ", ".join(_low(r.name) for r in faster) + ".")
        selfrep = [r for r in flagged if r.group == "self" and r not in faster]
        rest = [r for r in flagged if r not in faster and r not in selfrep]
        if selfrep:
            parts.append("Self-report: " + ", ".join(_low(r.name.split(" (")[0]) for r in selfrep) + ".")
        if rest:
            parts.append("Change detected versus your baseline: " + ", ".join(_low(r.name) for r in rest) + ".")
        if retries:
            parts.append("Measurement not confirmed, repeat: " + ", ".join(_low(r.name) for r in retries) + ".")
        summary = " ".join(parts)
        if status == RED:
            steps = ["Stop and hold on at the station; breathe calmly for 5 minutes.",
                     "Follow the steps in the cards marked Refer to specialist.",
                     "Repeat the session in 15 minutes.",
                     "The flight surgeon already receives the data; if the change persists, call the medical team."]
        else:
            steps = ["Do the action in the card marked Repeat measurement.",
                     "Repeat the scan tomorrow (or in 15 minutes)."]
    r_status = _status_of(research) if research else None
    return {"status": status, "title": OVERALL_TITLES[status], "label": STATUS_LABELS[status], "summary": summary,
            "steps": steps, "disclaimer": DISCLAIMER, "flagged": [r.key for r in flagged],
            "faster_than_nasa": [r.key for r in faster], "flag_reasons": _flags(scored),
            "include_research": include_research,
            "research": {"status": r_status, "label": STATUS_LABELS.get(r_status) if r_status else None,
                         "flagged": [r.key for r in research if r.status in (YELLOW, RED)],
                         "faster_than_nasa": [r.key for r in research if r.faster_than_nasa],
                         "flag_reasons": _flags(research),
                         "note": "Optional contact research module (grips with Doppler ultrasound, PPG, load cell). "
                                 "Shown separately and not part of the overall result. "
                                 "LYRA makes no heart assessment through the palm."}}
