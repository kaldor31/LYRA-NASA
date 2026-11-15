"""Downlink queue to Earth: all session data goes to the flight surgeon automatically.

One-way delay comes from the reference (environments.<env>.comm_delay_one_way_s, range [min, max]).
The current delay is picked inside the range (it depends on planetary positions).
For the demo, time can be accelerated (time_scale): Mars 14 min becomes 14 s at x60. The screen says so.
Each packet carries a medical report (time series, signal quality, environment mode, comparison with
previous measurements, reasons for flags); the queue view leaves it out to stay small.
"""
from __future__ import annotations

import itertools
import time
from dataclasses import asdict, dataclass, field
from typing import Callable

IN_TRANSIT, DELIVERED = "in_transit", "delivered"
STATUS_LABELS = {IN_TRANSIT: "In transit", DELIVERED: "Delivered"}
STATUS_RU = STATUS_LABELS  # legacy name; values are English


@dataclass
class Packet:
    id: str
    astronaut_id: str
    astronaut_name: str
    title: str
    day: int
    status_light: str     # overall session status code (green | yellow | red): the surgeon sees priority at once
    size_kb: int
    sent_at: float        # send time (queue clock)
    delay_s: float        # one-way delay, real seconds
    status: str = IN_TRANSIT
    report: dict | None = field(default=None, repr=False)  # medical report payload (see service.medical_report)

    def view(self, now: float, time_scale: float) -> dict:
        elapsed = (now - self.sent_at) * time_scale
        d = asdict(self)
        d.pop("report", None)
        d.update(status_ru=STATUS_LABELS[self.status], status_label=STATUS_LABELS[self.status],
                 has_report=self.report is not None, elapsed_s=round(min(elapsed, self.delay_s), 1),
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
                size_kb: int = 180, delivered: bool = False, report: dict | None = None) -> Packet:
        p = Packet(f"pkt-{next(self._ids):04d}", astronaut_id, astronaut_name, title, day, status_light,
                   size_kb, self.clock(), self.delay_s, DELIVERED if delivered or self.delay_s <= 0 else IN_TRANSIT,
                   report)
        if delivered:  # historical packet: "sent" long ago
            p.sent_at -= self.delay_s / self.time_scale + 1
        self.packets.append(p)
        return p

    def tick(self) -> list[Packet]:
        """Updates statuses; returns the packets that were just delivered."""
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

    def get(self, packet_id: str) -> Packet | None:
        return next((p for p in self.packets if p.id == packet_id), None)
