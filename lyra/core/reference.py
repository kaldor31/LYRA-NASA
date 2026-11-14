"""Справочник NASA (data/nasa_reference.json) — только чтение.

Файл параллельно дополняет Агент B, поэтому:
  • перечитываем его, если изменилось время модификации (без перезапуска сервера);
  • если файл временно битый (запись посередине) — оставляем последнюю удачную версию;
  • отсутствующие поля, model == "none" и url == "TODO-verify" — норма, а не ошибка.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "nasa_reference.json"
EMPTY: dict[str, Any] = {"sources": [], "hazards": [], "risks": [], "metrics": {}, "environments": {}, "radiation": {}}


class Reference:
    def __init__(self, path: Path | str = DEFAULT_PATH):
        self.path = Path(path)
        self._data: dict[str, Any] = dict(EMPTY)
        self._mtime: float | None = None
        self._lock = threading.Lock()
        self.error: str | None = None
        self.reload()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Reference":
        ref = cls.__new__(cls)
        ref.path, ref._mtime, ref._lock, ref.error = Path("<memory>"), None, threading.Lock(), None
        ref._data = {**EMPTY, **data}
        return ref

    def reload(self) -> None:
        with self._lock:
            try:
                mtime = self.path.stat().st_mtime
                if mtime == self._mtime:
                    return
                self._data = {**EMPTY, **json.loads(self.path.read_text(encoding="utf-8"))}
                self._mtime, self.error = mtime, None
            except FileNotFoundError:
                self.error = f"нет файла {self.path}"
            except (json.JSONDecodeError, OSError) as e:  # Агент B мог писать файл прямо сейчас
                self.error = f"не удалось прочитать справочник: {e}"

    @property
    def data(self) -> dict[str, Any]:
        if self.path.name != "<memory>":
            self.reload()
        return self._data

    # ---- удобные выборки ----
    def metric(self, key: str) -> dict[str, Any]:
        return self.data.get("metrics", {}).get(key, {}) or {}

    def expected(self, key: str) -> dict[str, Any]:
        return self.metric(key).get("expected", {}) or {}

    def environment(self, env_id: str) -> dict[str, Any]:
        return self.data.get("environments", {}).get(env_id, {}) or {}

    def risk(self, risk_id: str) -> dict[str, Any] | None:
        return next((r for r in self.data.get("risks", []) if r.get("id") == risk_id), None)

    def source(self, source_id: str) -> dict[str, Any] | None:
        return next((s for s in self.data.get("sources", []) if s.get("id") == source_id), None)

    def sources(self, ids: list[str]) -> list[dict[str, Any]]:
        """Источники для ссылок на экране; url == "TODO-verify" отдаём как None."""
        out = []
        for sid in ids or []:
            s = self.source(sid)
            if s:
                url = s.get("url")
                out.append({"id": sid, "title": s.get("title", sid), "publisher": s.get("publisher", ""),
                            "url": url if url and url.startswith("http") else None})
        return out

    def risks_for(self, key: str) -> list[dict[str, Any]]:
        out = []
        for rid in self.metric(key).get("risk_ids", []) or []:
            r = self.risk(rid)
            if r:
                out.append({"id": rid, "name_ru": r.get("name_ru", rid), "summary_ru": r.get("summary_ru", ""),
                            "hazard_ids": r.get("hazard_ids", []), "sources": self.sources(r.get("source_ids", []))})
        return out


_default: Reference | None = None


def get_reference() -> Reference:
    global _default
    if _default is None:
        _default = Reference()
    return _default
