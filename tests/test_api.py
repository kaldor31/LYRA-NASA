"""REST + WebSocket."""
from fastapi.testclient import TestClient

from lyra.server import create_app


def client():
    return TestClient(create_app("day40"))


def test_meta_state_reference():
    c = client()
    m = c.get("/api/meta").json()
    assert len(m["crew"]) == 4 and len(m["scenarios"]) == 4
    st = c.get("/api/state").json()
    assert st["day"] == 40 and st["simulated"] and st["downlink"]["items"]
    assert "metrics" in c.get("/api/reference").json()


def test_session_flow_and_errors():
    c = client()
    assert c.post("/api/identify", json={"astronaut_id": "a1"}).json()["ok"]
    r = c.post("/api/sessions", json={"astronaut_id": "a1", "mode": "weekly",
                                      "survey": {"sleep_score": 4, "wellbeing_score": 5, "symptoms_flag": False},
                                      "handgrip": {"in_zone_frac": 0.8}})
    assert r.status_code == 200 and r.json()["overall"]["status"] in ("green", "yellow", "red")
    assert c.post("/api/sessions", json={"astronaut_id": "zz"}).status_code == 404
    assert c.post("/api/sessions", json={"astronaut_id": "a1", "mode": "monthly"}).status_code == 422
    assert c.post("/api/sessions", json={"astronaut_id": "a1", "survey": {"sleep_score": 9}}).status_code == 422
    assert c.get("/api/astronauts/a1").json()["latest"]["live"]


def test_scenario_switch_series_dose():
    c = client()
    assert c.post("/api/scenario/mars180").json()["env"] == "mars"
    assert c.post("/api/scenario/nope").status_code == 404
    s = c.get("/api/astronauts/a2/series/grip_left_kg").json()
    assert s["corridor"] and s["points"]
    assert c.get("/api/astronauts/a2/series/nope").status_code == 404
    assert c.post("/api/astronauts/a2/dose", json={"dose_msv": 63.0}).json()["last"]["dose_msv"] == 63.0
    assert c.post("/api/astronauts/a2/dose", json={"dose_msv": -3}).status_code == 422


def test_websocket_sends_state():
    with client() as c, c.websocket_connect("/ws") as ws:
        assert ws.receive_json()["type"] == "state"


def test_session_new_fields_and_medical_report_endpoint():
    c = client()
    r = c.post("/api/sessions", json={"astronaut_id": "a1", "survey": {"back_pain_flag": True},
                                      "include_research": True}).json()
    assert r["env_mode"] == "microgravity" and r["overall"]["include_research"]
    assert r["overall"]["label"] in ("Within baseline", "Repeat measurement", "Refer to specialist")
    m = r["metrics"][0]
    assert {"label", "module", "quality", "confirmed", "reject_reason", "provenance", "env_mode"} <= set(m)
    rep = c.get(f"/api/downlink/{r['downlink']['id']}").json()
    assert rep["report"]["type"] == "medical_report" and rep["packet"]["status_light"] == r["overall"]["status"]
    assert c.get("/api/downlink/pkt-9999").status_code == 404
    meta = c.get("/api/meta").json()
    assert meta["status_labels"]["retry"] == "Measurement not confirmed"


def test_session_skip_research_flag():
    c = client()
    r = c.post("/api/sessions", json={"astronaut_id": "a1", "skip_research": True,
                                      "survey": {"sleep_score": 4}}).json()
    keys = {m["key"] for m in r["metrics"]}
    assert not keys & set(c.get("/api/meta").json()["research_keys"]) and "back_pain_flag" not in keys
