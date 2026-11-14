"""Очередь передачи на Землю: все данные сеанса уходят лётному врачу автоматически.

Задержка в одну сторону — из справочника (environments.<env>.comm_delay_one_way_s, диапазон [мин, макс]).
Конкретная задержка «сейчас» выбирается внутри диапазона (зависит от взаимного положения планет).
Для демо время можно ускорить (time_scale): Марс 14 мин → 14 с при ×60. Это подписывается на экране.
"""
from __future__ import annotations

import itertools
import time
from dataclasses import asdict, dataclass
from typing import Callable

IN_TRANSIT, DELIVERED = "in_transit", "delivered"
STATUS_RU = {IN_TRANSIT: "в пути", DELIVERED: "доставлено"}


@dataclass
class Packet:
    id: str
    astronaut_id: str
    astronaut_name: str
    title: str
    day: int
    status_light: str     # 🟢🟡🔴 итог сеанса — врач видит приоритет сразу
    size_kb: int
    sent_at: float        # время отправки (часы очереди)
    delay_s: float        # задержка в одну сторону, реальные секунды
    status: str = IN_TRANSIT

    def view(self, now: float, time_scale: float) -> dict:
        elapsed = (now - self.sent_at) * time_scale
        d = asdict(self)
        d.update(status_ru=STATUS_RU[self.status], elapsed_s=round(min(elapsed, self.delay_s), 1),
                 remaining_s=round(max(self.delay_s - elapsed, 0.0), 1),
                 progress=1.0 if self.delay_s <= 0 else round(min(elapsed / self.delay_s, 1.0), 3))
        return d


class DownlinkQueue:
    def __init__(self, delay_range_s: tuple[float, float] = (0, 1), current_delay_s: float | None = None,
                 time_scale: float = 1.0, clock: Callable[[], float] = time.monotonic):
        lo, hi = float(delay_range_s[0]), float(delay_range_s[-1])
        self.delay_range_s = (lo, hi)
        self.delay_s = current_delay_s if current_delay_s is not None else (lo + hi) / 2
        self.time_scale = max(time_scale, 1e-6)
        self.clock = clock
        self.packets: list[Packet] = []
        self._ids = itertools.count(1)

    def enqueue(self, astronaut_id: str, astronaut_name: str, title: str, day: int, status_light: str,
                size_kb: int = 180, delivered: bool = False) -> Packet:
        p = Packet(f"pkt-{next(self._ids):04d}", astronaut_id, astronaut_name, title, day, status_light,
                   size_kb, self.clock(), self.delay_s, DELIVERED if delivered or self.delay_s <= 0 else IN_TRANSIT)
        if delivered:  # исторический пакет: «отправлен» давно
            p.sent_at -= self.delay_s / self.time_scale + 1
        self.packets.append(p)
        return p

    def tick(self) -> list[Packet]:
        """Обновляет статусы; возвращает пакеты, которые только что доставлены."""
        now, done = self.clock(), []
        for p in self.packets:
            if p.status == IN_TRANSIT and (now - p.sent_at) * self.time_scale >= p.delay_s:
                p.status = DELIVERED
                done.append(p)
        return done

    def view(self, limit: int = 12) -> dict:
        self.tick()
        now = self.clock()
        items = [p.view(now, self.time_scale) for p in reversed(self.packets[-limit:])]
        return {"delay_s": self.delay_s, "delay_range_s": list(self.delay_range_s), "time_scale": self.time_scale,
                "round_trip_s": 2 * self.delay_s, "in_transit": sum(p.status == IN_TRANSIT for p in self.packets),
                "items": items}
