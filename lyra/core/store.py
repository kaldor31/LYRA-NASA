"""Хранилище сеансов в памяти (по астронавтам). Для демо достаточно; интерфейс узкий — легко заменить на БД."""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field

PREFLIGHT_LAST_DAY = 0  # дни ≤ 0 — до полёта


@dataclass
class Session:
    id: str
    astronaut_id: str
    day: int
    mode: str                                   # daily | weekly
    values: dict[str, tuple[float | None, float]]  # ключ → (значение, качество 0–1)
    simulated: bool = True
    live: bool = False                          # сеанс, пройденный в демо (не история)


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

    def history(self, aid: str, key: str, before_day: int) -> list[tuple[int, float]]:
        """(день, значение) хороших измерений до дня `before_day`."""
        out = []
        for s in self.list(aid):
            v = s.values.get(key)
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
                out.append({"day": s.day, "value": round(v[0], 3), "quality": v[1], "mode": s.mode, "live": s.live})
        return out

    def streak(self, aid: str, today: int) -> int:
        """Серия: сколько дней полёта подряд (до сегодня включительно) есть хотя бы один сеанс."""
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
