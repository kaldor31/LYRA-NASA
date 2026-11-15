"""LyraService: demo state and use cases (no HTTP). The server is a thin layer on top of it."""
from __future__ import annotations

import random
import uuid

from .core.assess import (DISCLAIMER, ENV_MODE_LABELS, PROVENANCE, RETRY, SIMULATION, STATUS_LABELS,
                          env_mode_for)
from .core.comms import DownlinkQueue
from .core.engine import evaluate
from .core.expected import corridor_series, is_modeled
from .core.metrics import DAILY, LOCAL_ONLY, RESEARCH_KEYS, SPECS, WEEKLY
from .core.reference import Reference, get_reference
from .core.store import Session, Store
from .sim.crew import CREW
from .sim.scenarios import SCENARIOS, Scenario
from .sim.simulator import dose_rate_msv_day, generate_history, simulate_values

FACE_ID_THRESHOLD = 0.90
HANDGRIP_MIN_IN_ZONE = 0.5
REPORT_SERIES_POINTS = 14  # time-series points per metric in the medical report


class NotFound(KeyError):
    pass


class LyraService:
    def __init__(self, ref: Reference | None = None, scenario: str = "day40", time_scale: float = 60.0,
                 clock=None):
        self.ref = ref or get_reference()
        self.store = Store()
        self.time_scale = time_scale
        self._clock = clock
        self.live_sessions: dict[str, dict] = {}
        self.set_scenario(scenario)

    # ---------- scenario ----------
    def set_scenario(self, sid: str) -> None:
        if sid not in SCENARIOS:
            raise NotFound(sid)
        self.sc: Scenario = SCENARIOS[sid]
        self.rng = random.Random(self.sc.seed + 1)
        generate_history(self.store, self.sc, self.ref)
        env = self.ref.environment(self.sc.env)
        rng_delay = env.get("comm_delay_one_way_s") or [0, 1]
        kw = {"clock": self._clock} if self._clock else {}
        self.queue = DownlinkQueue(tuple(rng_delay), self.sc.delay_s, self.time_scale, **kw)
        self.live_sessions.clear()
        # yesterday's packets are already on Earth
        for a in CREW.values():
            last = self.store.last(a.id)
            if last:
                latest = self._latest(a.id)  # the real status of that session, not a hard-coded green
                self.queue.enqueue(a.id, a.name, "Session (history)", last.day, latest["overall"]["status"],
                                   delivered=True, report=self.medical_report(a.id, latest, last.mode))

    @property
    def day(self) -> int:
        return self.sc.day

    def _astronaut(self, aid: str):
        if aid not in CREW:
            raise NotFound(aid)
        return CREW[aid]

    # ---------- read ----------
    def meta(self) -> dict:
        envs = self.ref.data.get("environments", {})
        return {
            "scenarios": [{"id": s.id, "title": s.title, "subtitle": s.subtitle, "env": s.env, "day": s.day}
                          for s in SCENARIOS.values()],
            "environments": envs,
            "crew": [{"id": a.id, "name": a.name, "role": a.role, "initials": a.initials} for a in CREW.values()],
            "reference": {"status": self.ref.data.get("_status"), "error": self.ref.error},
            "face_id_threshold": FACE_ID_THRESHOLD,
            "status_labels": STATUS_LABELS,
            "env_mode_labels": ENV_MODE_LABELS,
            "provenance_values": list(PROVENANCE),
            "research_keys": RESEARCH_KEYS,
            "disclaimer": DISCLAIMER,
        }

    def state(self) -> dict:
        env = self.ref.environment(self.sc.env)
        return {
            "type": "state", "scenario": self.sc.id, "scenario_title": self.sc.title,
            "scenario_subtitle": self.sc.subtitle, "day": self.day, "env": self.sc.env,
            "env_name": env.get("name_ru", self.sc.env), "gravity_g": env.get("gravity_g"),
            "env_mode": self.env_mode, "env_mode_label": ENV_MODE_LABELS[self.env_mode], "provenance": SIMULATION,
            "simulated": True, "crew": [self.crew_summary(aid) for aid in CREW],
            "downlink": self.queue.view(),
        }

    def _latest(self, aid: str) -> dict | None:
        if aid in self.live_sessions:
            return self.live_sessions[aid]
        last = self.store.last(aid)
        if not last:
            return None
        r = evaluate(self.store, self.ref, aid, last.day, last.values, last.meta, last.env_mode)
        r.update(session_id=last.id, mode=last.mode, live=False, simulated=True)
        return r

    def crew_summary(self, aid: str) -> dict:
        a = self._astronaut(aid)
        latest = self._latest(aid)
        return {"id": a.id, "name": a.name, "role": a.role, "initials": a.initials,
                "status": latest["overall"]["status"] if latest else None,
                "last_day": latest["day"] if latest else None,
                "done_today": aid in self.live_sessions,
                "streak": self.store.streak(aid, self.day)}

    def astronaut(self, aid: str) -> dict:
        a = self._astronaut(aid)
        return {**self.crew_summary(aid), "latest": self._latest(aid), "dose": self.dose(aid)}

    def series(self, aid: str, key: str) -> dict:
        self._astronaut(aid)
        if key not in SPECS:
            raise NotFound(key)
        spec, m = SPECS[key], self.ref.metric(key)
        exp = m.get("expected", {}) or {}
        pre = self.store.preflight_mean(aid, key)
        horizon = max(self.day + 14, 30)
        corr = corridor_series(exp, pre, range(0, horizon + 1), spec.noise) if pre is not None else []
        return {"key": key, "name": m.get("name_ru") or spec.name, "unit": m.get("unit") or spec.unit,
                "decimals": spec.decimals, "direction": spec.direction, "preflight": pre, "today": self.day,
                "points": self.store.series(aid, key), "corridor": corr, "modeled": is_modeled(exp),
                "expected": {k: exp.get(k) for k in ("model", "rate", "rate_unit", "tau_days", "band", "basis",
                                                     "note_ru")},
                "sources": self.ref.sources(exp.get("source_ids", [])),
                "risks": self.ref.risks_for(key, spec.risk_ids), "why_ru": m.get("why_ru", ""),
                "module": spec.module, "local_only": key in LOCAL_ONLY, "provenance": SIMULATION}

    def dose(self, aid: str) -> dict:
        rate, note = dose_rate_msv_day(self.ref, self.sc.env)
        m = self.ref.metric("radiation_dose_msv")
        rad = self.ref.data.get("radiation", {}) or {}
        return {"last": self.store.dose(aid), "history": self.store.doses.get(aid, []),
                "rate_msv_day": rate, "rate_note": note, "name_ru": m.get("name_ru", "Accumulated dose"),
                "note_ru": (m.get("expected") or {}).get("note_ru", ""), "why_ru": m.get("why_ru", ""),
                "radiation_note_ru": rad.get("note_ru", ""),
                "career_limit_msv": rad.get("career_limit_msv"),
                "sources": self.ref.sources((m.get("expected") or {}).get("source_ids", [])),
                "disclaimer": "LYRA does not measure radiation: the value is imported from the station dosimeter."}

    # ---------- actions ----------
    def identify(self, aid: str) -> dict:
        a = self._astronaut(aid)
        low = aid in self.sc.low_confidence
        conf = round(self.rng.uniform(0.58, 0.72) if low else self.rng.uniform(0.94, 0.99), 2)
        ok = conf >= FACE_ID_THRESHOLD
        return {"astronaut_id": aid, "name": a.name if ok else None, "method": "3d_face", "confidence": conf,
                "threshold": FACE_ID_THRESHOLD, "ok": ok,
                "reason": None if ok else "Face changed (swelling of the first days); the face reference is still "
                                          "updating.",
                "hint": None if ok else "Hold your NFC card to the station reader."}

    def identify_nfc(self, aid: str) -> dict:
        a = self._astronaut(aid)
        return {"astronaut_id": aid, "name": a.name, "method": "nfc", "confidence": 1.0, "ok": True}

    @property
    def env_mode(self) -> str:
        return env_mode_for(self.ref.environment(self.sc.env).get("gravity_g"), self.day)

    def run_session(self, aid: str, mode: str = DAILY, training: bool = False, survey: dict | None = None,
                    handgrip: dict | None = None, include_research: bool = False,
                    skip_research: bool = False) -> dict:
        a = self._astronaut(aid)
        if mode not in (DAILY, WEEKLY):
            raise ValueError("mode must be daily or weekly")
        meta: dict[str, dict] = {}
        values = simulate_values(a, self.day, mode, self.sc, self.ref, self.rng, meta_out=meta,
                                 rejects=self.sc.rejects.get(aid))
        for key, ans in (survey or {}).items():
            if key in ("sleep_score", "wellbeing_score") and ans is not None:
                values[key] = (float(min(5, max(1, int(ans)))), 1.0)
            elif key in ("symptoms_flag", "back_pain_flag") and ans is not None:
                values[key] = (1.0 if ans else 0.0, 1.0)
        if (survey or {}).get("back_pain_flag") is None:  # optional question skipped: not "no back pain"
            values.pop("back_pain_flag", None)
        if mode == WEEKLY:
            frac = float((handgrip or {}).get("in_zone_frac", 1.0))
            if frac < HANDGRIP_MIN_IN_ZONE:  # test not counted: honestly ask to repeat, no averaged value
                for k in ("handgrip_hr_response_bpm", "handgrip_recovery_s"):
                    values[k] = (values[k][0], 0.3)
                    meta.setdefault(k, {})["reject_reason"] = "target zone not held"
        if skip_research:  # research module skipped by the crew: nothing is simulated, stored or sent for it
            for k in RESEARCH_KEYS:
                values.pop(k, None)
                meta.pop(k, None)
        env_mode = self.env_mode
        sid = f"{'train' if training else 'live'}-{uuid.uuid4().hex[:8]}"
        if training:  # training mode: evaluate, but record and send nothing
            result = evaluate(self.store, self.ref, aid, self.day, values, meta, env_mode, include_research)
            result.update(session_id=sid, astronaut_id=aid, mode=mode, training=True, live=True, simulated=True,
                          downlink=None, streak=self.store.streak(aid, self.day))
            return result
        # a repeat session on the same day replaces the earlier live one
        self.store.sessions[aid] = [s for s in self.store.list(aid) if not (s.live and s.day == self.day)]
        result = evaluate(self.store, self.ref, aid, self.day, values, meta, env_mode, include_research)
        self.store.add(Session(sid, aid, self.day, mode, values, simulated=True, live=True, meta=meta,
                               env_mode=env_mode))
        status = result["overall"]["status"]
        title = "Full test (weekly)" if mode == WEEKLY else "Express scan"
        report = self.medical_report(aid, result, mode)
        pkt = self.queue.enqueue(aid, a.name, title, self.day, status, size_kb=420 if mode == WEEKLY else 180,
                                 report=report)
        result.update(session_id=sid, astronaut_id=aid, mode=mode, training=False, live=True, simulated=True,
                      downlink=pkt.view(self.queue.clock(), self.queue.time_scale),
                      streak=self.store.streak(aid, self.day), medical_report=report)
        self.live_sessions[aid] = result
        return result

    def import_dose(self, aid: str, dose_msv: float) -> dict:
        self._astronaut(aid)
        if not (0 <= dose_msv < 10_000):
            raise ValueError("dose out of range")
        self.store.add_dose(aid, self.day, dose_msv, "entered manually (dosimeter import)")
        return self.dose(aid)

    # ---------- medical report for the flight surgeon ----------
    def medical_report(self, aid: str, result: dict, mode: str) -> dict:
        """Downlink payload: time series, signal quality, environment mode, comparison with previous
        measurements and the reason for each flag (not just a color). Screening, not a diagnosis."""
        a = self._astronaut(aid)
        metrics = result["metrics"]
        fields = ("key", "name", "unit", "module", "status", "label", "value", "quality", "confirmed", "reject_reason",
                  "signal", "previous_value", "previous_day", "change_vs_previous", "preflight", "mission_pct",
                  "expected_pct", "corridor", "faster_than_nasa", "flag_reason", "reference_posture", "provenance")
        qualities = [m["quality"] for m in metrics if m["group"] != "self"]
        series = {m["key"]: [{"day": p["day"], "value": p["value"], "quality": p["quality"],
                              "confirmed": p["confirmed"]} for p in self.store.series(aid, m["key"])
                             ][-REPORT_SERIES_POINTS:] for m in metrics if m["group"] != "self"}
        overall = result["overall"]
        return {
            "type": "medical_report", "astronaut": {"id": a.id, "name": a.name, "role": a.role},
            "day": result["day"], "mode": mode, "scenario": self.sc.id, "environment": self.sc.env,
            "env_mode": result["env_mode"], "env_mode_label": result["env_mode_label"],
            "provenance": result["provenance"], "provenance_note": result["provenance_note"],
            "overall": {"status": overall["status"], "label": overall["label"], "summary": overall["summary"],
                        "flag_reasons": overall["flag_reasons"]},
            "research": overall["research"],
            "signal_quality": {"mean": round(sum(qualities) / len(qualities), 3) if qualities else None,
                               "not_confirmed": [m["key"] for m in metrics if not m["confirmed"]]},
            "metrics": [{k: m.get(k) for k in fields} for m in metrics],
            "time_series": series,
            "disclaimer": DISCLAIMER,
        }

    def downlink_report(self, packet_id: str) -> dict:
        p = self.queue.get(packet_id)
        if not p:
            raise NotFound(packet_id)
        return {"packet": p.view(self.queue.clock(), self.queue.time_scale), "report": p.report}


__all__ = ["LyraService", "NotFound", "RETRY"]
