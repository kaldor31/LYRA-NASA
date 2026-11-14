"""LYRA — веб-приложение на симуляции (FastAPI + WebSocket).

Запуск:  .venv/bin/python -m lyra.server            → http://127.0.0.1:8000
Флаги:   --scenario day1|day40|mars180|anomaly  --time-scale 60  --port 8000  --fast (короткие фазы)

REST (JSON):
  GET  /api/meta                         сценарии, среды, экипаж, статус справочника
  GET  /api/state                        текущий сценарий, сводка экипажа, очередь связи
  POST /api/scenario/{id}                переключить сценарий (история пересчитывается)
  GET  /api/reference                    справочник NASA как есть (риски, источники)
  GET  /api/astronauts/{id}              профиль, последний результат, доза
  GET  /api/astronauts/{id}/series/{key} «ты против ожидания NASA»: точки + коридор
  POST /api/identify                     {astronaut_id} → 3D-лицо, уверенность
  POST /api/identify/nfc                 {astronaut_id} → опознание NFC-картой
  POST /api/sessions                     {astronaut_id, mode, training, survey, handgrip} → результат
  POST /api/astronauts/{id}/dose         {dose_msv} → импорт дозиметра
  GET  /api/downlink                     очередь передачи на Землю
WebSocket /ws: {"type":"state"} при смене сценария/сеанса, {"type":"downlink"} при доставке пакетов.
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .service import LyraService, NotFound
from .sim.scenarios import SCENARIOS

DASHBOARD = Path(__file__).parent / "dashboard"


class IdentifyIn(BaseModel):
    astronaut_id: str


class SurveyIn(BaseModel):
    sleep_score: int | None = Field(None, ge=1, le=5)
    wellbeing_score: int | None = Field(None, ge=1, le=5)
    symptoms_flag: bool | None = None


class HandgripIn(BaseModel):
    in_zone_frac: float = Field(1.0, ge=0, le=1)


class SessionIn(BaseModel):
    astronaut_id: str
    mode: Literal["daily", "weekly"] = "daily"
    training: bool = False
    survey: SurveyIn | None = None
    handgrip: HandgripIn | None = None


class DoseIn(BaseModel):
    dose_msv: float = Field(..., ge=0, lt=10000)


class Hub:
    """Рассылка событий всем открытым панелям."""

    def __init__(self):
        self.clients: set[WebSocket] = set()

    async def broadcast(self, msg: dict) -> None:
        for ws in list(self.clients):
            try:
                await ws.send_json(msg)
            except Exception:
                self.clients.discard(ws)


def create_app(scenario: str = "day40", time_scale: float = 60.0, fast: bool = False,
               service: LyraService | None = None) -> FastAPI:
    svc = service or LyraService(scenario=scenario, time_scale=time_scale)
    hub = Hub()

    async def downlink_watcher():
        while True:
            await asyncio.sleep(0.5)
            if svc.queue.tick() or svc.queue.view()["in_transit"]:
                await hub.broadcast({"type": "downlink", **svc.queue.view()})

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = asyncio.create_task(downlink_watcher())
        yield
        task.cancel()

    app = FastAPI(title="LYRA", version="2.0", lifespan=lifespan)
    app.state.service = svc
    app.mount("/static", StaticFiles(directory=DASHBOARD), name="static")

    def nf(e: Exception):
        return HTTPException(404, f"Не найдено: {e}")

    @app.get("/")
    async def index():
        return FileResponse(DASHBOARD / "index.html", headers={"Cache-Control": "no-store"})

    @app.get("/api/meta")
    async def meta():
        return {**svc.meta(), "fast": fast, "time_scale": svc.time_scale}

    @app.get("/api/state")
    async def state():
        return svc.state()

    @app.post("/api/scenario/{sid}")
    async def set_scenario(sid: str):
        try:
            svc.set_scenario(sid)
        except NotFound as e:
            raise nf(e)
        st = svc.state()
        await hub.broadcast(st)
        return st

    @app.get("/api/reference")
    async def reference():
        return svc.ref.data

    @app.get("/api/astronauts/{aid}")
    async def astronaut(aid: str):
        try:
            return svc.astronaut(aid)
        except NotFound as e:
            raise nf(e)

    @app.get("/api/astronauts/{aid}/series/{key}")
    async def series(aid: str, key: str):
        try:
            return svc.series(aid, key)
        except NotFound as e:
            raise nf(e)

    @app.post("/api/identify")
    async def identify(body: IdentifyIn):
        try:
            return svc.identify(body.astronaut_id)
        except NotFound as e:
            raise nf(e)

    @app.post("/api/identify/nfc")
    async def identify_nfc(body: IdentifyIn):
        try:
            return svc.identify_nfc(body.astronaut_id)
        except NotFound as e:
            raise nf(e)

    @app.post("/api/sessions")
    async def sessions(body: SessionIn):
        try:
            res = svc.run_session(body.astronaut_id, body.mode, body.training,
                                  body.survey.model_dump() if body.survey else None,
                                  body.handgrip.model_dump() if body.handgrip else None)
        except NotFound as e:
            raise nf(e)
        except ValueError as e:
            raise HTTPException(422, str(e))
        if not body.training:
            await hub.broadcast(svc.state())
        return res

    @app.post("/api/astronauts/{aid}/dose")
    async def dose(aid: str, body: DoseIn):
        try:
            return svc.import_dose(aid, body.dose_msv)
        except NotFound as e:
            raise nf(e)
        except ValueError as e:
            raise HTTPException(422, str(e))

    @app.get("/api/downlink")
    async def downlink():
        return svc.queue.view()

    @app.websocket("/ws")
    async def ws(socket: WebSocket):
        await socket.accept()
        hub.clients.add(socket)
        await socket.send_json(svc.state())
        try:
            while True:
                await socket.receive_text()
        except WebSocketDisconnect:
            hub.clients.discard(socket)

    return app


def main() -> None:
    p = argparse.ArgumentParser(description="LYRA — 3D health scan (симуляция)")
    p.add_argument("--scenario", default="day40", choices=list(SCENARIOS))
    p.add_argument("--time-scale", type=float, default=60.0, help="ускорение задержки связи для демо (×)")
    p.add_argument("--fast", action="store_true", help="короткие фазы сеанса (для отладки)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--sim", action="store_true", help="совместимость со старой командой (всегда симуляция)")
    a = p.parse_args()
    import uvicorn
    uvicorn.run(create_app(a.scenario, a.time_scale, a.fast), host=a.host, port=a.port, log_level="info")


if __name__ == "__main__":
    main()
