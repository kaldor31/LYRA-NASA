import numpy as np

from lyra.core.assess import GREEN, RED, RETRY, YELLOW, assess_metric, make_baseline, overall_status
from lyra.core.db import Store
from lyra.core.engine import evaluate
from lyra.core.metrics import METRICS
from lyra.sim.history import generate_history, simulate_session
from lyra.vision.rppg import estimate_hr

HIST = [70, 72, 68, 71, 69, 70, 73, 67, 70, 71]


def test_reference_baseline_before_calibration():
    b = make_baseline([70, 71], METRICS["hr_palm"])
    assert b.kind == "reference" and b.mean == 75


def test_status_levels():
    assert assess_metric("hr_palm", 71, 0.9, HIST).status == GREEN
    assert assess_metric("hr_palm", 78, 0.9, HIST).status == YELLOW
    assert assess_metric("hr_palm", 85, 0.9, HIST).status == RED
    assert assess_metric("hr_palm", 85, 0.2, HIST).status == RETRY


def test_direction_only_flags_dangerous_side():
    grip = [42, 41.5, 42.3, 41.8, 42.1, 42, 41.7]
    assert assess_metric("grip_strength", 50, 0.9, grip).status == GREEN  # сильнее — не тревога
    assert assess_metric("grip_strength", 37, 0.9, grip).status == RED


def test_overall_two_yellows_is_red():
    y = assess_metric("hr_palm", 78, 0.9, HIST)
    g = assess_metric("hr_palm", 70, 0.9, HIST)
    assert overall_status([g, y])["status"] == YELLOW
    assert overall_status([y, y])["status"] == RED


def test_scenarios():
    store = Store()
    generate_history(store, until_day=40)
    normal = evaluate(store, 40, simulate_session(40, seed=1))
    anomaly = evaluate(store, 40, simulate_session(40, anomaly=True, seed=1))
    assert normal["overall"]["status"] in (GREEN, YELLOW)
    assert anomaly["overall"]["status"] == RED
    grip = next(m for m in anomaly["metrics"] if m["key"] == "grip_strength")
    assert grip["mission_pct"] < -5  # сила хвата снизилась с начала полёта


def test_rppg_recovers_pulse_from_synthetic_signal():
    fps, secs, bpm = 30, 15, 72
    t = np.arange(fps * secs) / fps
    rng = np.random.default_rng(0)
    pulse = 0.004 * np.sin(2 * np.pi * bpm / 60 * t)
    rgb = np.stack([120 + 0.3 * pulse * 120, 90 + pulse * 90, 70 + 0.2 * pulse * 70], axis=1)
    rgb += rng.normal(0, 0.15, rgb.shape)
    hr, quality = estimate_hr(rgb, t)
    assert abs(hr - bpm) < 3
    assert quality > 0.5
