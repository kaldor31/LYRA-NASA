"""Demo scenarios: environment, mission day, anomaly. All data is simulated."""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Anomaly:
    """Faster grip strength and blood flow loss plus facial swelling above the expected range (one astronaut)."""
    astronaut_id: str
    title: str
    grip_onset_day: int = 15        # from this day grip strength drops faster
    grip_extra_pct_per_month: float = -6.0
    edema_days_before: int = 15     # swelling starts growing N days before "today"
    edema_extra_pct: float = 6.0
    flow_days_before: int = 5       # blood flow drops over the last N days
    flow_drop_left_pct: float = -35.0
    flow_drop_right_pct: float = -10.0

    def mods(self, key: str, day: int, today: int) -> tuple[float, float]:
        """-> (relative change in %, absolute change) for the metric on this day."""
        if key.startswith("grip_") and day > self.grip_onset_day:
            return self.grip_extra_pct_per_month * (day - self.grip_onset_day) / 30, 0.0
        e0 = today - self.edema_days_before
        if day > e0 and key in ("face_volume_ml", "periorbital_puffiness_mm"):
            f = 1 - math.exp(-(day - e0) / 5)
            return (self.edema_extra_pct * f, 0.0) if key == "face_volume_ml" else (0.0, 1.2 * f)
        f0 = today - self.flow_days_before
        if day > f0:
            ramp = min((day - f0) / self.flow_days_before, 1.0)
            if key == "doppler_flow_left_cms":
                return self.flow_drop_left_pct * ramp, 0.0
            if key == "doppler_flow_right_cms":
                return self.flow_drop_right_pct * ramp, 0.0
            if key == "hrv_rmssd_ms":
                return -20.0 * ramp, 0.0
            if key == "sleep_score":
                return 0.0, -1.0 * ramp
        return 0.0, 0.0


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    subtitle: str
    env: str
    day: int
    anomaly: Anomaly | None = None
    low_confidence: frozenset[str] = frozenset()  # whom 3D face ID does not recognize confidently (-> NFC card)
    skip_days: dict[str, tuple[int, ...]] = field(default_factory=dict)  # missed sessions (for the streak)
    delay_s: float | None = None  # current comm delay; None means the middle of the reference range
    rejects: dict[str, dict[str, str]] = field(default_factory=dict)  # live session: aid -> {metric: reason}
    seed: int = 7


SCENARIOS: dict[str, Scenario] = {s.id: s for s in [
    Scenario("day1", "Day 1, ISS", "Fluid shift toward the head has just started. The face reference has not "
             "caught up yet, so some crew identify with the NFC card.", "iss", 1,
             low_confidence=frozenset({"a2", "a4"})),
    Scenario("day40", "Day 40, ISS", "Expected adaptation: puffier face, thinner calves, height up 2%. "
             "Everything sits inside the NASA corridor. Leia's camera pulse is not confirmed (low light).",
             "iss", 40, skip_days={"a3": (33,), "a4": (12, 27)}, rejects={"a4": {"hr_rppg": "low light"}}),
    Scenario("mars180", "Day 180, Mars", "Long mission with up to 20 min signal delay; the crew works "
             "autonomously. Slow grip strength loss, as NASA expects.", "mars", 180, delay_s=840,
             skip_days={"a1": (150,), "a3": (95, 170)}),
    Scenario("anomaly", "Anomaly, Moon day 60",
             "Mira Sato's facial swelling is above the expected range; in the research module her grip strength "
             "and palm blood flow drop faster than NASA expects.",
             "moon", 60, anomaly=Anomaly("a2", "Faster grip strength and blood flow loss, swelling above expected"),
             skip_days={"a4": (41,)}),
]}
