"""In-memory session store (per astronaut). Enough for the demo; the interface is narrow, easy to swap for a database."""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field

PREFLIGHT_LAST_DAY = 0  # days <= 0 are pre-flight (Earth)


@dataclass
class Session:
    id: str
    astronaut_id: str
    day: int
    mode: str                                   # daily | weekly
    values: dict[str, tuple[float | None, float]]  # key -> (value, quality 0..1)
    simulated: bool = True
    live: bool = False                          # session run in the demo (not history)
    meta: dict[str, dict] = field(default_factory=dict)  # key -> {reject_reason, signal}
    env_mode: str = "earth"                     # earth | microgravity | partial_gravity
    provenance: str = "simulation"


@dataclass
class Store:
    sessions: dict[str, list[Session]] = field(default_factory=dict)
    doses: dict[str, list[dict]] = field(default_factory=dict)

    def clear(self) -> None:
        self.sessions.clear()
        self.doses.clear()

    def add(self, s: Session) -> None:
        lst = self.sessions.setdefault(s.astronaut_id, [])
        lst.append(s)
        lst.sort(key=lambda x: x.day)

    def list(self, aid: str) -> list[Session]:
        return self.sessions.get(aid, [])

    def last(self, aid: str) -> Session | None:
        lst = self.list(aid)
        return lst[-1] if lst else None

    def _vals(self, aid: str, key: str, cond) -> list[float]:
        out = []
        for s in self.list(aid):
            v = s.values.get(key)
            if v and v[0] is not None and v[1] >= 0.5 and cond(s):
                out.append(v[0])
        return out

    def history(self, aid: str, key: str, before_day: int, since_day: int | None = None) -> list[tuple[int, float]]:
        """(day, value) of good measurements before `before_day` (and from `since_day`, if given)."""
        out = []
        for s in self.list(aid):
            v = s.values.get(key)
            if since_day is not None and s.day < since_day:
                continue
            if s.day < before_day and v and v[0] is not None and v[1] >= 0.5:
                out.append((s.day, v[0]))
        return out

    def preflight_mean(self, aid: str, key: str) -> float | None:
        vals = self._vals(aid, key, lambda s: s.day <= PREFLIGHT_LAST_DAY)
        return statistics.fmean(vals) if vals else None

    def series(self, aid: str, key: str) -> list[dict]:
        out = []
        for s in self.list(aid):
            v = s.values.get(key)
            if v and v[0] is not None:
                out.append({"day": s.day, "value": round(v[0], 3), "quality": v[1], "mode": s.mode, "live": s.live,
                            "confirmed": v[1] >= 0.5, "env_mode": s.env_mode, "provenance": s.provenance})
        return out

    def streak(self, aid: str, today: int) -> int:
        """Streak: consecutive mission days (up to and including today) with at least one session."""
        days = {s.day for s in self.list(aid)}
        d = today if today in days else today - 1
        n = 0
        while d >= 1 and d in days:
            n, d = n + 1, d - 1
        return n

    def add_dose(self, aid: str, day: int, dose_msv: float, source: str) -> dict:
        rec = {"day": day, "dose_msv": round(dose_msv, 2), "source": source}
        self.doses.setdefault(aid, []).append(rec)
        return rec

    def dose(self, aid: str) -> dict | None:
        lst = self.doses.get(aid)
        return lst[-1] if lst else None
