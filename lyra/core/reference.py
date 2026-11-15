"""NASA reference (data/nasa_reference.json), read only.

The file is maintained in parallel by the concept team, so:
  * it is re-read when its modification time changes (no server restart needed);
  * if the file is temporarily broken (written mid-way), the last good version is kept;
  * missing fields, model == "none" and url == "TODO-verify" are normal, not errors.
Keys named *_ru are kept for API compatibility; since 2026-11-14 their values are English text.
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
                self.error = f"file not found: {self.path}"
            except (json.JSONDecodeError, OSError) as e:  # the file may be mid-write right now
                self.error = f"could not read the reference: {e}"

    @property
    def data(self) -> dict[str, Any]:
        if self.path.name != "<memory>":
            self.reload()
        return self._data

    # ---- convenience lookups ----
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
        """Sources for on-screen links; url == "TODO-verify" is returned as None."""
        out = []
        for sid in ids or []:
            s = self.source(sid)
            if s:
                url = s.get("url")
                out.append({"id": sid, "title": s.get("title", sid), "publisher": s.get("publisher", ""),
                            "url": url if url and url.startswith("http") else None})
        return out

    def risks_for(self, key: str, fallback_ids: tuple[str, ...] | list[str] = ()) -> list[dict[str, Any]]:
        """Risks linked to a metric; local-only metrics may pass fallback risk ids."""
        out = []
        for rid in self.metric(key).get("risk_ids") or list(fallback_ids):
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
