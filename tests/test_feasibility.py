"""Feasibility check: heart rate from video (rPPG) on a synthetic signal."""
import pytest

np = pytest.importorskip("numpy")
rppg = pytest.importorskip("lyra.feasibility.vision.rppg")


def test_rppg_recovers_pulse_from_synthetic_signal():
    fps, secs, bpm = 30, 15, 72
    t = np.arange(fps * secs) / fps
    rng = np.random.default_rng(0)
    pulse = 0.004 * np.sin(2 * np.pi * bpm / 60 * t)
    rgb = np.stack([120 + 0.3 * pulse * 120, 90 + pulse * 90, 70 + 0.2 * pulse * 70], axis=1)
    rgb += rng.normal(0, 0.15, rgb.shape)
    hr, quality = rppg.estimate_hr(rgb, t)
    assert abs(hr - bpm) < 3 and quality > 0.5
