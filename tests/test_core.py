"""Ядро LYRA: модель ожидаемой адаптации NASA, статусы, сценарии, очередь связи."""
import pytest

from lyra.core.assess import GREEN, RED, RETRY, YELLOW, assess_metric, make_baseline, overall_status
from lyra.core.comms import DELIVERED, IN_TRANSIT, DownlinkQueue
from lyra.core.expected import corridor, corridor_series, expected_change_pct, is_modeled
from lyra.core.metrics import SPECS, keys_for_mode
from lyra.core.reference import Reference, get_reference
from lyra.service import LyraService
from lyra.sim.scenarios import SCENARIOS

REF = get_reference()
SAT = {"model": "saturating", "rate": 4.0, "rate_unit": "% от исходного к плато", "tau_days": 3, "band": 2.0}
LIN = {"model": "linear", "rate": -1.0, "rate_unit": "%/мес"}
FAKE = Reference.from_dict({"metrics": {
    "face_volume_ml": {"name_ru": "Объём лица", "unit": "мл", "risk_ids": ["fluid"], "expected": SAT},
    "grip_left_kg": {"name_ru": "Сила хвата (левая)", "unit": "кг", "expected": LIN},
    "hr_palm": {"name_ru": "Пульс (ладонь)", "unit": "уд/мин", "expected": {"model": "none"}},
}, "risks": [{"id": "fluid", "name_ru": "Сдвиг жидкости", "source_ids": ["s1"]}],
    "sources": [{"id": "s1", "title": "T", "url": "TODO-verify"}]})


# ---------- справочник ----------
def test_reference_loads_canonical_keys():
    assert set(SPECS) <= set(REF.data["metrics"]), "локальные метрики должны совпадать с ключами справочника"
    for env in ("iss", "moon", "mars"):
        assert REF.environment(env)


def test_reference_tolerates_todo_urls_and_missing_file(tmp_path):
    assert FAKE.risks_for("face_volume_ml")[0]["sources"][0]["url"] is None
    missing = Reference(tmp_path / "nope.json")
    assert missing.error and missing.metric("face_volume_ml") == {}
    broken = tmp_path / "b.json"
    broken.write_text("{oops")
    assert Reference(broken).error


# ---------- модель ожидаемой адаптации ----------
def test_saturating_corridor_reaches_plateau():
    assert corridor(SAT, 1000, 0, 5) is None or corridor(SAT, 1000, 0, 5).center == 1000
    c1, c30 = corridor(SAT, 1000, 1, 5), corridor(SAT, 1000, 30, 5)
    assert 1000 < c1.center < c30.center
    assert c30.center == pytest.approx(1040, abs=0.1)        # +4 % плато
    assert (c30.hi - c30.lo) / 2 == pytest.approx(20)         # band 2 % от базы


def test_linear_corridor_and_noise_floor():
    c = corridor(LIN, 40, 60, 0.8)
    assert c.center == pytest.approx(40 * 0.98)               # −1 %/мес × 2 мес
    assert (c.hi - c.lo) / 2 == pytest.approx(1.6)            # нет band → не уже 2σ шума
    assert expected_change_pct(LIN, 40, 30) == pytest.approx(-1.0)


def test_absolute_units_and_none_model():
    mm = {"model": "saturating", "rate": 1.0, "rate_unit": "мм к плато", "tau_days": 3, "band": 0.6}
    assert corridor(mm, 2.0, 100, 0.1).center == pytest.approx(3.0)
    assert not is_modeled({"model": "none"}) and corridor({"model": "none"}, 1, 5, 1) is None
    assert not is_modeled({"model": "linear", "rate": 0.0})
    assert not is_modeled({"model": "saturating", "rate": "TODO"})
    assert len(corridor_series(SAT, 1000, range(0, 11), 5)) == 11


# ---------- статусы ----------
HIST = [70, 72, 68, 71, 69, 70, 73, 67, 70, 71]


def test_personal_norm_levels_without_corridor():
    assert make_baseline([70, 71], SPECS["hr_palm"]).kind == "reference"
    st = lambda v, q=0.9: assess_metric("hr_palm", v, q, HIST, ref=FAKE).status  # noqa: E731
    assert (st(71), st(78), st(85), st(85, 0.2)) == (GREEN, YELLOW, RED, RETRY)


def _face_history(day, base=1000.0):
    """История: 7 дней до полёта на базе + дни полёта точно по траектории NASA."""
    pre = [(d, base) for d in range(-6, 1)]
    return pre + [(d, corridor(SAT, base, d, 6).center) for d in range(1, day)]


def test_expected_adaptation_is_green_even_if_far_from_preflight():
    # день 2: лицо +2,1 % к норме до полёта — резкий сдвиг, но NASA этого ожидает
    v = corridor(SAT, 1000, 2, 6).center
    r = assess_metric("face_volume_ml", v, 0.9, _face_history(2), preflight=1000, day=2, ref=FAKE)
    assert r.status == GREEN and not r.faster_than_nasa
    assert "коридоре" in r.text


def test_faster_than_nasa_is_flagged_with_risk():
    r = assess_metric("face_volume_ml", 1100, 0.9, _face_history(40), preflight=1000, day=40, ref=FAKE)
    assert r.status == RED and r.faster_than_nasa
    assert "быстрее, чем ожидает NASA" in r.text and "Сдвиг жидкости" in r.text
    y = assess_metric("face_volume_ml", 1070, 0.9, _face_history(40), preflight=1000, day=40, ref=FAKE)
    assert y.corridor_status == YELLOW and y.faster_than_nasa
    assert y.status == RED  # плюс резкий скачок к личной норме (история идеально ровная) → худший из двух


def test_safe_side_outside_corridor_is_green():
    r = assess_metric("face_volume_ml", 1000, 0.9, _face_history(40), preflight=1000, day=40, ref=FAKE)
    assert r.status == GREEN and "меньше ожидаемого" in r.text


def test_slow_drift_caught_by_corridor_not_by_personal_norm():
    """Главная идея: сила хвата медленно падает быстрее NASA — личная норма этого не видит, коридор видит."""
    hist = [(d, 40.0) for d in range(-6, 1)] + [(d, 40 * (1 - 0.0025 * d)) for d in range(1, 60)]
    r = assess_metric("grip_left_kg", 40 * (1 - 0.0025 * 60), 0.9, hist, preflight=40, day=60, ref=FAKE)
    assert r.z_status == GREEN
    assert r.corridor_status in (YELLOW, RED) and r.status != GREEN


def test_overall_rules():
    y = assess_metric("hr_palm", 78, 0.9, HIST, ref=FAKE)
    g = assess_metric("hr_palm", 70, 0.9, HIST, ref=FAKE)
    assert overall_status([g])["status"] == GREEN
    assert overall_status([g, y])["status"] == YELLOW
    o = overall_status([y, y])
    assert o["status"] == RED and o["steps"] and "не диагноз" in o["disclaimer"]


def test_modes():
    daily, weekly = keys_for_mode("daily"), keys_for_mode("weekly")
    assert "handgrip_recovery_s" not in daily and "handgrip_recovery_s" in weekly
    assert "radiation_dose_msv" not in weekly


# ---------- сценарии ----------
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
    assert "face_volume_ml" in faster and {"grip_left_kg", "grip_right_kg"} & faster
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
    svc.run_session("a1", "daily")  # повтор в тот же день заменяет, а не дублирует
    assert sum(s.live for s in svc.store.list("a1")) == 1
    assert svc.crew_summary("a3")["streak"] == 6  # пропуск на дне 33


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


# ---------- очередь связи ----------
class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_downlink_delay_and_delivery():
    clk = Clock()
    q = DownlinkQueue((180, 1200), current_delay_s=840, time_scale=60, clock=clk)
    p = q.enqueue("a1", "Алекс", "Экспресс-скан", 180, "🟢")
    assert p.status == IN_TRANSIT
    clk.t = 13.0  # 13 с × 60 = 780 с < 840
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
    assert d["last"]["dose_msv"] == 12.5 and "не измеряет" in d["disclaimer"]
    with pytest.raises(ValueError):
        svc.import_dose("a1", -1)
