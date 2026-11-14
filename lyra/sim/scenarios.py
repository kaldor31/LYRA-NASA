"""Сценарии демо: среда, день миссии, аномалия. Все данные — смоделированные."""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Anomaly:
    """Ускоренная потеря силы хвата и кровотока + отёк лица сильнее ожидаемого (у одного астронавта)."""
    astronaut_id: str
    title: str
    grip_onset_day: int = 15        # с этого дня сила хвата падает быстрее
    grip_extra_pct_per_month: float = -6.0
    edema_days_before: int = 15     # отёк начинает расти за N дней до «сегодня»
    edema_extra_pct: float = 6.0
    flow_days_before: int = 5       # кровоток падает за последние N дней
    flow_drop_left_pct: float = -35.0
    flow_drop_right_pct: float = -10.0

    def mods(self, key: str, day: int, today: int) -> tuple[float, float]:
        """→ (относительное изменение в %, абсолютное изменение) для метрики в этот день."""
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
    low_confidence: frozenset[str] = frozenset()  # кого 3D-лицо не узнает уверенно (→ NFC-карта)
    skip_days: dict[str, tuple[int, ...]] = field(default_factory=dict)  # пропущенные сеансы (для серии)
    delay_s: float | None = None  # текущая задержка связи; None — середина диапазона справочника
    seed: int = 7


SCENARIOS: dict[str, Scenario] = {s.id: s for s in [
    Scenario("day1", "День 1 · МКС", "Начало сдвига жидкости к голове. Эталон лица ещё не обновился — "
             "у части экипажа опознание по NFC-карте.", "iss", 1,
             low_confidence=frozenset({"a2", "a4"})),
    Scenario("day40", "День 40 · МКС", "Ожидаемая адаптация: лицо отекло, голени похудели, рост +2 % — "
             "всё в коридоре NASA.", "iss", 40, skip_days={"a3": (33,), "a4": (12, 27)}),
    Scenario("mars180", "День 180 · Марс", "Долгая миссия: задержка связи до 20 мин, экипаж автономен. "
             "Медленная потеря силы хвата — по ожиданию NASA.", "mars", 180, delay_s=840,
             skip_days={"a1": (150,), "a3": (95, 170)}),
    Scenario("anomaly", "Аномалия · Луна/Gateway, день 60",
             "У Миры Сато сила хвата и кровоток падают быстрее, чем ожидает NASA, отёк лица сильнее ожидаемого.",
             "moon", 60, anomaly=Anomaly("a2", "Ускоренная потеря силы хвата и кровотока, отёк сильнее ожидаемого"),
             skip_days={"a4": (41,)}),
]}
