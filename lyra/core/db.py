"""Хранилище измерений (SQLite). День ≤ 0 — до полёта, день ≥ 1 — полёт."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    day INTEGER NOT NULL,
    ts TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    quality REAL NOT NULL,
    simulated INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_metric_day ON measurements(metric, day);
"""


class Store:
    def __init__(self, path: str | Path = ":memory:"):
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.executescript(SCHEMA)

    def clear(self) -> None:
        self.conn.execute("DELETE FROM measurements")
        self.conn.commit()

    def add_session(
        self, session_id: str, day: int, metrics: dict[str, tuple[float | None, float]], simulated: bool
    ) -> None:
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        rows = [
            (session_id, day, ts, k, v, q, int(simulated))
            for k, (v, q) in metrics.items()
            if v is not None
        ]
        self.conn.executemany(
            "INSERT INTO measurements(session_id, day, ts, metric, value, quality, simulated) "
            "VALUES (?,?,?,?,?,?,?)",
            rows,
        )
        self.conn.commit()

    def history(self, metric: str, before_day: int, limit: int = 14, min_quality: float = 0.5) -> list[float]:
        """Последние `limit` измерений до дня `before_day` (не включая) — для личной нормы."""
        cur = self.conn.execute(
            "SELECT value FROM measurements WHERE metric=? AND day<? AND quality>=? "
            "ORDER BY day DESC, id DESC LIMIT ?",
            (metric, before_day, min_quality, limit),
        )
        return [r[0] for r in cur.fetchall()][::-1]

    def preflight_mean(self, metric: str) -> float | None:
        cur = self.conn.execute("SELECT AVG(value) FROM measurements WHERE metric=? AND day<=0", (metric,))
        v = cur.fetchone()[0]
        return float(v) if v is not None else None

    def series(self, metric: str) -> list[tuple[int, float]]:
        """Среднее значение по дням — для графиков трендов."""
        cur = self.conn.execute(
            "SELECT day, AVG(value) FROM measurements WHERE metric=? GROUP BY day ORDER BY day", (metric,)
        )
        return [(int(d), float(v)) for d, v in cur.fetchall()]
