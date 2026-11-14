"""rPPG — пульс по видео: микро-изменения цвета кожи при каждом ударе сердца.

Метод POS (Wang et al., 2017, «Algorithmic Principles of Remote PPG»):
средний RGB кожи → проекция, подавляющая блики и освещение → полоса 0,7–3 Гц → пик спектра.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, filtfilt

LOW_HZ, HIGH_HZ = 0.7, 3.0  # 42–180 уд/мин
FS = 30.0


def resample(rgb: np.ndarray, t: np.ndarray, fs: float = FS) -> np.ndarray:
    """Кадры приходят неравномерно — переводим на ровную сетку fs Гц."""
    grid = np.arange(t[0], t[-1], 1 / fs)
    return np.stack([np.interp(grid, t, rgb[:, c]) for c in range(3)], axis=1)


def pos(rgb: np.ndarray, fs: float = FS) -> np.ndarray:
    n = len(rgb)
    win = int(1.6 * fs)
    h = np.zeros(n)
    proj = np.array([[0, 1, -1], [-2, 1, 1]], dtype=float)
    for start in range(0, n - win + 1):
        c = rgb[start:start + win].T
        mean = c.mean(axis=1, keepdims=True)
        mean[mean == 0] = 1e-9
        s = proj @ (c / mean)
        std1 = s[1].std() or 1e-9
        p = s[0] + (s[0].std() / std1) * s[1]
        h[start:start + win] += p - p.mean()
    return h


def estimate_hr(rgb: np.ndarray, t: np.ndarray) -> tuple[float | None, float]:
    """rgb: (N, 3) средний цвет кожи по кадрам, t: время кадров в секундах.
    Возвращает (пульс уд/мин | None, качество 0…1)."""
    rgb, t = np.asarray(rgb, float), np.asarray(t, float)
    if len(t) < 2 or t[-1] - t[0] < 8:
        return None, 0.0
    x = resample(rgb, t)
    sig = pos(x)
    b, a = butter(3, [LOW_HZ / (FS / 2), HIGH_HZ / (FS / 2)], btype="band")
    sig = filtfilt(b, a, sig)

    n = 1 << int(np.ceil(np.log2(len(sig) * 4)))  # дополнение нулями — точнее частота
    spec = np.abs(np.fft.rfft(sig * np.hanning(len(sig)), n)) ** 2
    freqs = np.fft.rfftfreq(n, 1 / FS)
    band = (freqs >= LOW_HZ) & (freqs <= HIGH_HZ)
    if not band.any() or spec[band].sum() == 0:
        return None, 0.0
    f_band, p_band = freqs[band], spec[band]
    peak = f_band[np.argmax(p_band)]
    near = np.abs(f_band - peak) <= 0.1
    snr = p_band[near].sum() / p_band.sum()  # доля мощности у пика
    quality = float(np.clip((snr - 0.15) / 0.35, 0, 1))
    return float(peak * 60), quality
