"""LYRA core: NASA expected-adaptation model, result categories, scenarios, downlink queue."""
import pytest

from lyra.core.assess import GREEN, RED, RETRY, YELLOW, assess_metric, make_baseline, overall_status
from lyra.core.comms import DELIVERED, IN_TRANSIT, DownlinkQueue
from lyra.core.expected import corridor, corridor_series, expected_change_pct, is_modeled
from lyra.core.metrics import LOCAL_ONLY, RESEARCH, SPECS, keys_for_mode
from lyra.core.reference import Reference, get_reference
from lyra.service import LyraService
from lyra.sim.scenarios import SCENARIOS

REF = get_reference()
SAT = {"model": "saturating", "rate": 4.0, "rate_unit": "% of baseline to plateau", "tau_days": 3, "band": 2.0}
LIN = {"model": "linear", "rate": -1.0, "rate_unit": "%/month"}
FAKE = Reference.from_dict({"metrics": {
    "face_volume_ml": {"name_ru": "Face volume", "unit": "mL", "risk_ids": ["fluid"], "expected": SAT},
    "grip_left_kg": {"name_ru": "Grip strength (left)", "unit": "kg", "expected": LIN},
    "hr_rppg": {"name_ru": "Pulse (camera)", "unit": "bpm", "expected": {"model": "none"}},
}, "risks": [{"id": "fluid", "name_ru": "Fluid shift", "source_ids": ["s1"]},
             {"id": "sensorimotor", "name_ru": "Sensorimotor", "source_ids": []}],
    "sources": [{"id": "s1", "title": "T", "url": "TODO-verify"}]})


# ---------- reference ----------
def test_reference_loads_canonical_keys():
    assert set(SPECS) - LOCAL_ONLY <= set(REF.data["metrics"]), "local metrics must match the reference keys"
    for env in ("iss", "moon", "mars"):
        assert REF.environment(env)


def test_reference_tolerates_todo_urls_and_missing_file(tmp_path):
    assert FAKE.risks_for("face_volume_ml")[0]["sources"][0]["url"] is None
    missing = Reference(tmp_path / "nope.json")
    assert missing.error and missing.metric("face_volume_ml") == {}
    broken = tmp_path / "b.json"
    broken.write_text("{oops")
    assert Reference(broken).error


# ---------- expected-adaptation model ----------
def test_saturating_corridor_reaches_plateau():
    assert corridor(SAT, 1000, 0, 5) is None or corridor(SAT, 1000, 0, 5).center == 1000
    c1, c30 = corridor(SAT, 1000, 1, 5), corridor(SAT, 1000, 30, 5)
    assert 1000 < c1.center < c30.center
    assert c30.center == pytest.approx(1040, abs=0.1)        # +4% plateau
    assert (c30.hi - c30.lo) / 2 == pytest.approx(20)         # band = 2% of base


def test_linear_corridor_and_noise_floor():
    c = corridor(LIN, 40, 60, 0.8)
    assert c.center == pytest.approx(40 * 0.98)               # -1%/month x 2 months
    assert (c.hi - c.lo) / 2 == pytest.approx(1.6)            # no band -> not narrower than 2 sigma of noise
    assert expected_change_pct(LIN, 40, 30) == pytest.approx(-1.0)


def test_absolute_units_and_none_model():
    mm = {"model": "saturating", "rate": 1.0, "rate_unit": "mm to plateau", "tau_days": 3, "band": 0.6}
    assert corridor(mm, 2.0, 100, 0.1).center == pytest.approx(3.0)
    assert not is_modeled({"model": "none"}) and corridor({"model": "none"}, 1, 5, 1) is None
    assert not is_modeled({"model": "linear", "rate": 0.0})
    assert not is_modeled({"model": "saturating", "rate": "TODO"})
    assert len(corridor_series(SAT, 1000, range(0, 11), 5)) == 11


# ---------- result categories ----------
HIST = [70, 72, 68, 71, 69, 70, 73, 67, 70, 71]


def test_personal_norm_levels_without_corridor():
    assert make_baseline([70, 71], SPECS["hr_rppg"]).kind == "reference"
    st = lambda v, q=0.9: assess_metric("hr_rppg", v, q, HIST, ref=FAKE).status  # noqa: E731
    assert (st(71), st(78), st(85), st(85, 0.2)) == (GREEN, YELLOW, RED, RETRY)


def _face_history(day, base=1000.0):
    """History: 7 pre-flight days at base + mission days exactly on the NASA trajectory."""
    pre = [(d, base) for d in range(-6, 1)]
    return pre + [(d, corridor(SAT, base, d, 6).center) for d in range(1, day)]


def test_expected_adaptation_is_green_even_if_far_from_preflight():
    # day 2: face +2.1% vs pre-flight, a sharp shift, but NASA expects it
    v = corridor(SAT, 1000, 2, 6).center
    r = assess_metric("face_volume_ml", v, 0.9, _face_history(2), preflight=1000, day=2, ref=FAKE)
    assert r.status == GREEN and not r.faster_than_nasa
    assert "corridor" in r.text and r.label == "Within baseline"


def test_faster_than_nasa_is_flagged_with_risk():
    r = assess_metric("face_volume_ml", 1100, 0.9, _face_history(40), preflight=1000, day=40, ref=FAKE)
    assert r.status == RED and r.faster_than_nasa
    assert "faster than NASA expects" in r.text and "Fluid shift" in r.text
    assert r.label == "Refer to specialist" and "faster than NASA expects" in r.flag_reason
    y = assess_metric("face_volume_ml", 1070, 0.9, _face_history(40), preflight=1000, day=40, ref=FAKE)
    assert y.corridor_status == YELLOW and y.faster_than_nasa
    assert y.status == RED  # plus a sharp jump vs the personal baseline (perfectly flat history) -> the worse of the two


def test_safe_side_outside_corridor_is_green():
    r = assess_metric("face_volume_ml", 1000, 0.9, _face_history(40), preflight=1000, day=40, ref=FAKE)
    assert r.status == GREEN and "smaller than NASA expects" in r.text


def test_slow_drift_caught_by_corridor_not_by_personal_norm():
    """Key idea: grip strength slowly drops faster than NASA expects; the personal baseline misses it, the corridor sees it."""
    hist = [(d, 40.0) for d in range(-6, 1)] + [(d, 40 * (1 - 0.0025 * d)) for d in range(1, 60)]
    r = assess_metric("grip_left_kg", 40 * (1 - 0.0025 * 60), 0.9, hist, preflight=40, day=60, ref=FAKE)
    assert r.z_status == GREEN
    assert r.corridor_status in (YELLOW, RED) and r.status != GREEN


def test_overall_rules():
    y = assess_metric("hr_rppg", 78, 0.9, HIST, ref=FAKE)
    g = assess_metric("hr_rppg", 70, 0.9, HIST, ref=FAKE)
    assert overall_status([g])["status"] == GREEN
    assert overall_status([g, y])["status"] == YELLOW
    o = overall_status([y, y])
    assert o["status"] == RED and o["steps"] and "not a diagnosis" in o["disclaimer"]
    assert o["label"] == "Refer to specialist" and len(o["flag_reasons"]) == 2


def test_modes():
    daily, weekly = keys_for_mode("daily"), keys_for_mode("weekly")
    assert "handgrip_recovery_s" not in daily and "handgrip_recovery_s" in weekly
    assert "radiation_dose_msv" not in weekly


# ---------- scenarios ----------
@pytest.mark.parametrize("sid", ["day1", "day40", "mars180"])
def test_normal_scenarios_mostly_green(sid):
    svc = LyraService(scenario=sid)
    statuses = [svc.run_session(aid, "weekly")["overall"]["status"] for aid in ("a1", "a2", "a3", "a4")]
    assert statuses.count(RED) == 0 and statuses.count(GREEN) >= 3


def test_anomaly_scenario_flags_faster_than_nasa():
    svc = LyraService(scenario="anomaly")
    r = svc.run_session("a2", "daily")
    assert r["overall"]["status"] == RED
    faster = set(r["overall"]["faster_than_nasa"])
    assert "face_volume_ml" in faster
    # grip and Doppler are research-module metrics: shown separately, not in the overall result
    assert not {"grip_left_kg", "grip_right_kg"} & faster
    assert {"grip_left_kg", "grip_right_kg"} & set(r["overall"]["research"]["faster_than_nasa"])
    assert r["body"]["zones"]["face"] == RED and r["body"]["face_pct"] > 6
    assert svc.run_session("a1", "daily")["overall"]["status"] != RED


def test_day1_low_face_confidence_falls_back_to_nfc():
    svc = LyraService(scenario="day1")
    assert not svc.identify("a2")["ok"] and "NFC" in svc.identify("a2")["hint"]
    assert svc.identify("a1")["ok"]
    assert svc.identify_nfc("a2")["ok"]


def test_training_session_is_not_recorded():
    svc = LyraService(scenario="day40")
    n = len(svc.store.list("a1"))
    r = svc.run_session("a1", "daily", training=True)
    assert r["training"] and r["downlink"] is None
    assert len(svc.store.list("a1")) == n and "a1" not in svc.live_sessions


def test_live_session_recorded_streak_and_survey():
    svc = LyraService(scenario="day40")
    r = svc.run_session("a1", "daily", survey={"sleep_score": 1, "wellbeing_score": 4, "symptoms_flag": True})
    by = {m["key"]: m for m in r["metrics"]}
    assert by["sleep_score"]["status"] == RED and by["symptoms_flag"]["status"] == YELLOW
    assert r["streak"] == 40 and r["downlink"]["status"] in (IN_TRANSIT, DELIVERED)
    svc.run_session("a1", "daily")  # a repeat on the same day replaces, not duplicates
    assert sum(s.live for s in svc.store.list("a1")) == 1
    assert svc.crew_summary("a3")["streak"] == 6  # missed day 33


def test_handgrip_game_failure_asks_to_repeat():
    svc = LyraService(scenario="day40")
    r = svc.run_session("a1", "weekly", handgrip={"in_zone_frac": 0.2})
    by = {m["key"]: m for m in r["metrics"]}
    assert by["handgrip_hr_response_bpm"]["status"] == RETRY


def test_series_has_points_and_corridor():
    s = LyraService(scenario="day40").series("a1", "leg_volume_ml")
    assert s["modeled"] and len(s["points"]) >= 40 and s["corridor"][0]["day"] == 0
    assert s["corridor"][-1]["day"] >= 40 + 14
    assert not LyraService(scenario="day40").series("a1", "hr_palm")["modeled"]


def test_all_scenarios_defined():
    assert {"day1", "day40", "mars180", "anomaly"} <= set(SCENARIOS)
    assert {SCENARIOS[s].env for s in SCENARIOS} == {"iss", "moon", "mars"}


# ---------- downlink queue ----------
class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_downlink_delay_and_delivery():
    clk = Clock()
    q = DownlinkQueue((180, 1200), current_delay_s=840, time_scale=60, clock=clk)
    p = q.enqueue("a1", "Alex", "Express scan", 180, "green")
    assert p.status == IN_TRANSIT
    clk.t = 13.0  # 13 s x 60 = 780 s < 840
    assert q.tick() == [] and q.view()["items"][0]["remaining_s"] == pytest.approx(60)
    clk.t = 14.1
    assert q.tick() == [p] and p.status == DELIVERED
    assert q.view()["round_trip_s"] == 1680


def test_mars_scenario_uses_reference_delay():
    svc = LyraService(scenario="mars180")
    lo, hi = REF.environment("mars")["comm_delay_one_way_s"]
    assert lo <= svc.queue.delay_s <= hi
    r = svc.run_session("a1", "daily")
    assert r["downlink"]["status"] == IN_TRANSIT and r["downlink"]["delay_s"] == svc.queue.delay_s


def test_dose_import():
    svc = LyraService(scenario="day40")
    d = svc.import_dose("a1", 12.5)
    assert d["last"]["dose_msv"] == 12.5 and "does not measure radiation" in d["disclaimer"]
    with pytest.raises(ValueError):
        svc.import_dose("a1", -1)


# ---------- concept paper requirements (2026-11-15) ----------
def test_labels_and_not_confirmed_measurement():
    r = assess_metric("hr_rppg", 70, 0.2, HIST, ref=FAKE, meta={"reject_reason": "motion"})
    assert r.status == RETRY and r.label == "Measurement not confirmed"
    assert not r.confirmed and r.reject_reason == "motion" and "No averaged value" in r.text
    d = assess_metric("face_volume_ml", None, 0.0, [], ref=FAKE)
    assert d.reject_reason == "face not visible"
    assert assess_metric("hr_rppg", 70, 0.9, HIST, ref=FAKE).label == "Within baseline"
    assert assess_metric("hr_rppg", 78, 0.9, HIST, ref=FAKE).label == "Repeat measurement"


def test_rppg_signal_fields_and_forced_reject():
    svc = LyraService(scenario="day40")
    r = svc.run_session("a1", "daily")
    rppg = next(m for m in r["metrics"] if m["key"] == "hr_rppg")
    assert {"usable_seconds", "motion", "light"} <= set(rppg["signal"])
    leia = svc.run_session("a4", "daily")
    m = next(m for m in leia["metrics"] if m["key"] == "hr_rppg")
    assert m["status"] == RETRY and m["reject_reason"] == "low light" and m["signal"]["light"] < 0.3
    assert "hr_rppg" in leia["medical_report"]["signal_quality"]["not_confirmed"]


def test_env_mode_and_provenance():
    for sid, mode in (("day40", "microgravity"), ("anomaly", "partial_gravity"), ("mars180", "partial_gravity")):
        r = LyraService(scenario=sid).run_session("a1", "daily")
        assert r["env_mode"] == mode and r["provenance"] == "simulation"
        assert all(m["env_mode"] == mode and m["provenance"] == "simulation" for m in r["metrics"])
    posture = next(m for m in LyraService(scenario="day40").run_session("a1", "daily")["metrics"]
                   if m["key"] == "head_forward_deg")
    assert posture["reference_posture"] == "microgravity_neutral_body_posture"
    assert posture["preflight"] is None  # not compared with the Earth upright stance


def test_posture_escalates_only_if_repeated_or_with_pain():
    hist = [(d, 3.0 + 0.1 * (d % 3)) for d in range(1, 15)]
    single = assess_metric("trunk_tilt_deg", 12.0, 0.9, hist, day=15, ref=FAKE, env_mode="microgravity")
    assert single.z_status == RED and single.status == YELLOW and not single.repeated
    pain = assess_metric("trunk_tilt_deg", 12.0, 0.9, hist, day=15, ref=FAKE, env_mode="microgravity",
                         pain_or_fatigue=True)
    assert pain.status == RED and "back pain" in pain.flag_reason
    rep = hist + [(15, 11.0), (16, 11.5)]
    repeated = assess_metric("trunk_tilt_deg", 12.0, 0.9, rep, day=17, ref=FAKE, env_mode="microgravity")
    assert repeated.repeated and repeated.status == RED
    assert repeated.risks and repeated.risks[0]["id"] == "sensorimotor"  # local-only metric, fallback risk


def test_research_module_excluded_by_default():
    assert SPECS["doppler_flow_left_cms"].module == RESEARCH and SPECS["grip_left_kg"].module == RESEARCH
    assert SPECS["hr_rppg"].module == "core"
    svc = LyraService(scenario="anomaly")
    r = svc.run_session("a2", "daily")
    assert not any(SPECS[k].module == RESEARCH for k in r["overall"]["flagged"])
    assert r["overall"]["research"]["status"] == RED and "palm" in r["overall"]["research"]["note"]
    r2 = svc.run_session("a2", "daily", include_research=True)
    assert r2["overall"]["include_research"] and {"grip_left_kg", "grip_right_kg"} & set(
        r2["overall"]["faster_than_nasa"])


def test_skeleton_keypoints_three_views():
    r = LyraService(scenario="day40").run_session("a1", "daily")
    sk = r["body"]["skeleton"]
    assert set(sk["views"]) == {"front", "side", "back"}
    for kp in ("head", "shoulder_left", "elbow_right", "pelvis", "knee_left", "foot_right"):
        assert all(kp in sk["views"][v] for v in sk["views"])
    assert sk["reference_posture"] == "microgravity_neutral_body_posture"
    assert {"trunk_tilt_deg", "pelvis_tilt_deg", "scapula_asym_mm", "pose_return_s"} <= set(sk["features"])


def test_back_pain_survey_and_medical_report():
    svc = LyraService(scenario="day40")
    r = svc.run_session("a1", "daily", survey={"back_pain_flag": True})
    by = {m["key"]: m for m in r["metrics"]}
    assert by["back_pain_flag"]["status"] == YELLOW
    rep = r["medical_report"]
    assert rep["env_mode"] == "microgravity" and rep["provenance"] == "simulation"
    assert rep["time_series"]["face_volume_ml"][-1]["day"] == 40
    assert {"previous_value", "change_vs_previous", "flag_reason", "quality"} <= set(rep["metrics"][0])
    assert any(f["key"] == "back_pain_flag" and f["reason"] for f in rep["overall"]["flag_reasons"])
    pid = r["downlink"]["id"]
    assert r["downlink"]["has_report"] and "report" not in r["downlink"]
    assert svc.downlink_report(pid)["report"]["astronaut"]["id"] == "a1"


# ---------- review follow-ups ----------
def _posture_values(svc, aid, **over):
    last = svc.store.last(aid)
    vals = dict(last.values)
    vals.update(over)
    return vals


def test_evaluate_wires_back_pain_into_posture_escalation():
    from lyra.core.engine import evaluate
    svc = LyraService(scenario="day40")
    tilt = svc.store.history("a1", "trunk_tilt_deg", before_day=40, since_day=1)
    big = max(v for _, v in tilt) + 15.0
    calm = _posture_values(svc, "a1", trunk_tilt_deg=(big, 0.95), back_pain_flag=(0.0, 1.0),
                           sleep_score=(4.0, 1.0), wellbeing_score=(4.0, 1.0))
    r = evaluate(svc.store, svc.ref, "a1", 40, calm, env_mode="microgravity")
    m = next(x for x in r["metrics"] if x["key"] == "trunk_tilt_deg")
    assert m["status"] == YELLOW and not m["repeated"]
    pain = dict(calm, back_pain_flag=(1.0, 1.0))
    m = next(x for x in evaluate(svc.store, svc.ref, "a1", 40, pain, env_mode="microgravity")["metrics"]
             if x["key"] == "trunk_tilt_deg")
    assert m["status"] == RED and "back pain" in m["flag_reason"]
    tired = dict(calm, sleep_score=(1.0, 1.0))
    m = next(x for x in evaluate(svc.store, svc.ref, "a1", 40, tired, env_mode="microgravity")["metrics"]
             if x["key"] == "trunk_tilt_deg")
    assert m["status"] == RED


def test_single_posture_change_counts_once_in_overall():
    hist = [(d, 3.0 + 0.1 * (d % 3)) for d in range(1, 15)]
    a = assess_metric("trunk_tilt_deg", 12.0, 0.9, hist, day=15, ref=FAKE, env_mode="microgravity")
    b = assess_metric("pelvis_tilt_deg", 12.0, 0.9, hist, day=15, ref=FAKE, env_mode="microgravity")
    assert a.status == b.status == YELLOW
    assert overall_status([a, b])["status"] == YELLOW


def test_previous_value_and_change_are_correct():
    svc = LyraService(scenario="day40")
    r = svc.run_session("a1", "daily")
    m = next(x for x in r["metrics"] if x["key"] == "face_volume_ml")
    pday, pval = svc.store.history("a1", "face_volume_ml", before_day=40)[-1]
    assert m["previous_day"] == pday and m["previous_value"] == pytest.approx(pval)
    assert m["change_vs_previous"] == pytest.approx(m["value"] - pval, abs=1e-3)


def test_latest_history_result_uses_stored_env_mode():
    svc = LyraService(scenario="day40")
    latest = svc.astronaut("a1")["latest"]
    assert not latest["live"] and latest["env_mode"] == "microgravity"
    m = next(x for x in latest["metrics"] if x["key"] == "head_forward_deg")
    assert m["preflight"] is None and m["reference_posture"] == "microgravity_neutral_body_posture"


def test_history_packets_carry_real_status_and_report():
    svc = LyraService(scenario="anomaly")
    for p in svc.queue.packets:
        assert p.status_light == svc.crew_summary(p.astronaut_id)["status"]
        assert p.report and p.report["astronaut"]["id"] == p.astronaut_id


def test_skipped_back_pain_and_research_are_not_recorded():
    svc = LyraService(scenario="day40")
    r = svc.run_session("a1", "daily", survey={"sleep_score": 4, "back_pain_flag": None}, skip_research=True)
    keys = {m["key"] for m in r["metrics"]}
    assert "back_pain_flag" not in keys
    assert not keys & {k for k, s in SPECS.items() if s.module == RESEARCH}
    assert r["overall"]["research"]["status"] is None
    r2 = svc.run_session("a1", "weekly", skip_research=True, handgrip={"in_zone_frac": 0.1})
    assert "handgrip_hr_response_bpm" not in {m["key"] for m in r2["metrics"]}
