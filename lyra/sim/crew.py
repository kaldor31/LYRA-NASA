"""Вымышленный экипаж (нейтральные имена). Личные базовые значения до полёта — смоделированы."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Astronaut:
    id: str
    name: str
    role: str
    initials: str
    base: dict[str, float] = field(default_factory=dict)  # отличия от типичных значений SPECS.base
    adapt: float = 1.0  # насколько сильно человек следует траектории NASA (0.8–1.2 — индивидуальность)


CREW: dict[str, Astronaut] = {a.id: a for a in [
    Astronaut("a1", "Алекс Ривера", "Командир", "АР",
              {"height_cm": 181, "grip_left_kg": 46, "grip_right_kg": 49, "leg_volume_ml": 2600,
               "body_volume_l": 80, "face_volume_ml": 1210, "hr_palm": 60, "hr_rppg": 61}, adapt=1.0),
    Astronaut("a2", "Мира Сато", "Бортинженер", "МС",
              {"height_cm": 166, "grip_left_kg": 31, "grip_right_kg": 33, "leg_volume_ml": 2150,
               "body_volume_l": 60, "face_volume_ml": 1060, "hr_palm": 66, "hr_rppg": 67, "hrv_rmssd_ms": 52},
              adapt=1.1),
    Astronaut("a3", "Иван Коваль", "Врач экипажа", "ИК",
              {"height_cm": 177, "grip_left_kg": 42, "grip_right_kg": 44, "leg_volume_ml": 2450,
               "body_volume_l": 74, "face_volume_ml": 1160, "hr_palm": 58, "hr_rppg": 59}, adapt=0.85),
    Astronaut("a4", "Лея Окафор", "Специалист миссии", "ЛО",
              {"height_cm": 171, "grip_left_kg": 35, "grip_right_kg": 36, "leg_volume_ml": 2300,
               "body_volume_l": 64, "face_volume_ml": 1100, "hr_palm": 64, "hr_rppg": 65}, adapt=1.2),
]}
