"""Станция ладони: чтение JSON-строк от ESP32 по USB-Serial (или симуляция).

Формат строки от прошивки (1 раз в секунду):
{"finger":1,"hr":72,"hr_ok":1,"spo2":98,"spo2_ok":1,"temp":33.21,"grip":0.12}
"""
from __future__ import annotations

import json
import statistics
import threading
import time
from typing import Callable

OnUpdate = Callable[[dict], None]


class SerialPalm:
    def __init__(self, port: str, baud: int = 115200):
        import serial

        self.ser = serial.Serial(port, baud, timeout=1.5)
        time.sleep(2)  # ESP32 перезагружается при открытии порта
        self.ser.reset_input_buffer()

    def _lines(self, duration: float, stop: threading.Event | None):
        t0 = time.monotonic()
        while (elapsed := time.monotonic() - t0) < duration:
            if stop is not None and stop.is_set():
                return
            raw = self.ser.readline().decode(errors="ignore").strip()
            if not raw.startswith("{"):
                continue
            try:
                yield elapsed, json.loads(raw)
            except json.JSONDecodeError:
                continue

    def tare(self) -> None:
        self.ser.write(b"t")

    def measure_palm(self, duration: float = 15.0, on_update: OnUpdate | None = None,
                     stop: threading.Event | None = None) -> dict[str, tuple[float | None, float]]:
        hr, spo2, temp, n = [], [], [], 0
        for elapsed, d in self._lines(duration, stop):
            n += 1
            if d.get("finger"):
                if d.get("hr_ok") and 35 <= d.get("hr", 0) <= 200:
                    hr.append(d["hr"])
                if d.get("spo2_ok") and 80 <= d.get("spo2", 0) <= 100:
                    spo2.append(d["spo2"])
                if d.get("temp") is not None:
                    temp.append(d["temp"])
            if on_update:
                on_update({"progress": round(elapsed / duration, 3), "finger": bool(d.get("finger")),
                           "hr": d.get("hr") if d.get("hr_ok") else None, "temp": d.get("temp")})
        n = max(n, 1)
        # Первые секунды датчик «прогревается» — берём медиану второй половины, если хватает данных
        def tail_median(xs):
            xs = xs[len(xs) // 2:] if len(xs) >= 6 else xs
            return float(statistics.median(xs)) if xs else None
        return {
            "hr_palm": (tail_median(hr), min(1.0, len(hr) / (0.6 * n))),
            "spo2": (tail_median(spo2), min(1.0, len(spo2) / (0.6 * n))),
            "skin_temp": (tail_median(temp), min(1.0, len(temp) / (0.6 * n))),
        }

    def measure_grip(self, duration: float = 8.0, on_update: OnUpdate | None = None,
                     stop: threading.Event | None = None) -> dict[str, tuple[float | None, float]]:
        peak, n = 0.0, 0
        for elapsed, d in self._lines(duration, stop):
            g = d.get("grip")
            if g is not None:
                n += 1
                peak = max(peak, g)
            if on_update:
                on_update({"progress": round(elapsed / duration, 3), "grip": g, "peak": peak})
        ok = n > 0 and peak > 3  # меньше 3 кг — скорее всего рукоять не сжимали
        return {"grip_strength": (peak if ok else None, 1.0 if ok else 0.0)}


class SimPalm:
    """Без железа: прогресс-бар и заранее рассчитанные значения из симуляции."""

    def __init__(self, values: dict[str, tuple[float, float]]):
        self.values = values

    def tare(self) -> None:
        pass

    def _tick(self, duration, on_update, stop, extra):
        t0 = time.monotonic()
        while (elapsed := time.monotonic() - t0) < duration:
            if stop is not None and stop.is_set():
                return
            if on_update:
                on_update({"progress": round(elapsed / duration, 3), **extra(elapsed / duration)})
            time.sleep(0.2)

    def measure_palm(self, duration=15.0, on_update=None, stop=None):
        hr = self.values["hr_palm"][0]
        self._tick(duration, on_update, stop,
                   lambda p: {"finger": True, "hr": round(hr) if p > 0.3 else None,
                              "temp": round(self.values["skin_temp"][0], 1)})
        return {k: self.values[k] for k in ("hr_palm", "spo2", "skin_temp")}

    def measure_grip(self, duration=8.0, on_update=None, stop=None):
        g = self.values["grip_strength"][0]
        self._tick(duration, on_update, stop, lambda p: {"grip": round(g * min(1, p * 2), 1), "peak": round(g * min(1, p * 2), 1)})
        return {"grip_strength": self.values["grip_strength"]}
