"""LYRA backend: управляет сеансом измерения и отдаёт панель зеркала.

Запуск:
  python -m lyra.server --sim                      # без камеры и без ESP32 (демо где угодно)
  python -m lyra.server --palm-sim                 # камера настоящая, ладонь — симуляция
  python -m lyra.server --palm-port /dev/cu.usbserial-0001   # всё настоящее
Открыть http://127.0.0.1:8000 в полноэкранном браузере на мониторе за зеркалом.
"""
from __future__ import annotations

import argparse
import asyncio
import threading
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .core.db import Store
from .core.engine import evaluate
from .core.metrics import METRICS
from .sim.history import generate_history, simulate_session

DASHBOARD = Path(__file__).parent / "dashboard"

# сценарий → (день полёта, есть ли аномалия)
SCENARIOS = {
    "day1": (1, False),
    "day20": (20, False),
    "day40": (40, True),
}


@dataclass
class Config:
    camera: bool = True
    camera_index: int = 0
    palm_port: str | None = None
    db_path: str = ":memory:"
    scan_s: float = 20.0
    palm_s: float = 15.0
    grip_s: float = 8.0
    scenario: str = "day1"


class Lyra:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.store = Store(cfg.db_path)
        self.clients: set[WebSocket] = set()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.busy = False
        self.stop = threading.Event()
        self.anchor: dict[str, float] | None = None  # личные значения после калибровки
        self.palm_hw = None
        if cfg.palm_port:
            from .palm.reader import SerialPalm
            self.palm_hw = SerialPalm(cfg.palm_port)
        self.set_scenario(cfg.scenario)

    # ---- состояние ----
    def set_scenario(self, name: str) -> None:
        if name not in SCENARIOS:
            raise ValueError(name)
        self.scenario = name
        self.day, self.anomaly = SCENARIOS[name]
        generate_history(self.store, until_day=self.day, base=self.anchor)

    def state(self) -> dict:
        return {
            "type": "state",
            "day": self.day,
            "scenario": self.scenario,
            "scenarios": list(SCENARIOS),
            "camera": "real" if self.cfg.camera else "sim",
            "palm": "real" if self.palm_hw else "sim",
            "calibrated": self.anchor is not None,
            "busy": self.busy,
            "durations": {"face": self.cfg.scan_s, "palm": self.cfg.palm_s, "grip": self.cfg.grip_s},
        }

    def trends(self) -> dict:
        return {
            k: {"name": s.name, "unit": s.unit, "series": self.store.series(k),
                "preflight": self.store.preflight_mean(k)}
            for k, s in METRICS.items()
        }

    # ---- рассылка в панель ----
    async def broadcast(self, msg: dict) -> None:
        for ws in list(self.clients):
            try:
                await ws.send_json(msg)
            except Exception:
                self.clients.discard(ws)

    def emit(self, msg: dict) -> None:
        """Потокобезопасно: вызывается из потоков камеры/ладони."""
        if self.loop:
            asyncio.run_coroutine_threadsafe(self.broadcast(msg), self.loop)

    # ---- сеанс измерения ----
    async def measure(self, calibrate: bool = False) -> None:
        self.busy = True
        self.stop.clear()
        try:
            await self._measure(calibrate)
        except Exception as e:  # показываем ошибку на зеркале, а не роняем сервер
            await self.broadcast({"type": "error", "text": f"Ошибка измерения: {e}"})
        finally:
            self.busy = False
            await self.broadcast(self.state())

    async def _measure(self, calibrate: bool) -> None:
        from .palm.reader import SimPalm
        from .vision.capture import camera_scan, simulated_scan

        sim = simulate_session(self.day, anomaly=self.anomaly, base=self.anchor)
        c = self.cfg

        await self.broadcast({"type": "phase", "phase": "face", "duration": c.scan_s,
                              "text": "Смотрите в зеркало и не двигайтесь"})
        on_frame = lambda m: self.emit({"type": "frame", **m})
        if c.camera:
            face = await asyncio.to_thread(camera_scan, c.scan_s, c.camera_index, on_frame, self.stop)
        else:
            face_keys = ["face_puffiness", "blink_rate", "perclos", "yawn_count", "shoulder_tilt",
                         "head_forward", "hr_rppg"]
            face = await asyncio.to_thread(simulated_scan, c.scan_s, {k: sim[k] for k in face_keys},
                                           on_frame, self.stop)

        palm = self.palm_hw or SimPalm(sim)
        on_palm = lambda m: self.emit({"type": "palm", **m})
        await self.broadcast({"type": "phase", "phase": "palm", "duration": c.palm_s,
                              "text": "Положите ладонь на подставку, указательный палец — на датчик"})
        palm_vals = await asyncio.to_thread(palm.measure_palm, c.palm_s, on_palm, self.stop)
        await self.broadcast({"type": "phase", "phase": "grip", "duration": c.grip_s,
                              "text": "Сожмите рукоять изо всех сил 2–3 раза"})
        grip_vals = await asyncio.to_thread(palm.measure_grip, c.grip_s, on_palm, self.stop)

        metrics = {**face, **palm_vals, **grip_vals}
        simulated = not (c.camera and self.palm_hw)

        if calibrate:
            self.anchor = {k: v for k, (v, q) in metrics.items() if v is not None and q >= 0.5}
            generate_history(self.store, until_day=self.day, base=self.anchor)
            await self.broadcast({"type": "calibrated", "values": self.anchor,
                                  "text": "Калибровка готова: история построена вокруг ваших значений"})
            return

        self.store.add_session(f"live-{uuid.uuid4().hex[:8]}", self.day, metrics, simulated=simulated)
        result = evaluate(self.store, self.day, metrics)
        result.update(type="result", simulated=simulated, scenario=self.scenario)
        await self.broadcast(result)


def create_app(cfg: Config) -> FastAPI:
    lyra = Lyra(cfg)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        lyra.loop = asyncio.get_running_loop()
        yield
        lyra.stop.set()

    app = FastAPI(title="LYRA", lifespan=lifespan)
    app.state.lyra = lyra
    app.mount("/static", StaticFiles(directory=DASHBOARD), name="static")

    @app.get("/")
    async def index():
        return FileResponse(DASHBOARD / "index.html")

    @app.get("/api/state")
    async def get_state():
        return lyra.state()

    @app.get("/api/trends")
    async def get_trends():
        return lyra.trends()

    @app.post("/api/measure")
    async def start_measure(calibrate: bool = False):
        if lyra.busy:
            raise HTTPException(409, "Измерение уже идёт")
        lyra.busy = True
        asyncio.create_task(lyra.measure(calibrate=calibrate))
        return {"ok": True}

    @app.post("/api/cancel")
    async def cancel():
        lyra.stop.set()
        return {"ok": True}

    @app.post("/api/scenario/{name}")
    async def scenario(name: str):
        if lyra.busy:
            raise HTTPException(409, "Дождитесь окончания измерения")
        try:
            lyra.set_scenario(name)
        except ValueError:
            raise HTTPException(404, f"Нет сценария {name}")
        await lyra.broadcast(lyra.state())
        return lyra.state()

    @app.websocket("/ws")
    async def ws(socket: WebSocket):
        await socket.accept()
        lyra.clients.add(socket)
        await socket.send_json(lyra.state())
        try:
            while True:
                await socket.receive_text()
        except WebSocketDisconnect:
            lyra.clients.discard(socket)

    return app


def main() -> None:
    p = argparse.ArgumentParser(description="LYRA — умное зеркало")
    p.add_argument("--sim", action="store_true", help="без камеры и без ESP32")
    p.add_argument("--palm-sim", action="store_true", help="камера настоящая, ладонь — симуляция")
    p.add_argument("--palm-port", help="порт ESP32, напр. /dev/cu.usbserial-0001")
    p.add_argument("--camera", type=int, default=0, help="индекс камеры")
    p.add_argument("--scenario", default="day1", choices=list(SCENARIOS))
    p.add_argument("--fast", action="store_true", help="короткие фазы (для отладки)")
    p.add_argument("--db", default=":memory:", help="файл SQLite (по умолчанию в памяти)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    a = p.parse_args()

    cfg = Config(camera=not a.sim, camera_index=a.camera, palm_port=None if (a.sim or a.palm_sim) else a.palm_port,
                 db_path=a.db, scenario=a.scenario)
    if a.fast:
        cfg.scan_s, cfg.palm_s, cfg.grip_s = 6.0, 4.0, 3.0
    if not a.sim and not a.palm_sim and not a.palm_port:
        print("ESP32 не указан (--palm-port) — данные ладони будут смоделированы.")

    import uvicorn
    uvicorn.run(create_app(cfg), host=a.host, port=a.port, log_level="info")


if __name__ == "__main__":
    main()
