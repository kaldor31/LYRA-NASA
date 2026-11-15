# LYRA: 3D health scan for long-duration missions

**Step in. Scan. Know.** A web app running on simulated data, built for the NASA Space Apps Challenge 2026
("Create Health Monitoring Software for Astronauts on Space Missions"). Team: Alina Dmitriyeva, Daniil Shabalin.

The LYRA station is three slim posts around the astronaut and a mirror panel with a screen behind it. The core scan
is **contactless**: RGB cameras, structured IR light (a dot projector, like Face ID, for millimeter-level facial
swelling) and depth (ToF) cameras that build a skeletal keypoint model of the body from three synced views
(front, side, back). The palms rest on marked zones of the touch mirror only to standardize the pose. Nothing is
worn on the body.

An optional **contact research module** (vertical grips in the side posts with Doppler ultrasound and a hydrogel
cassette, PPG/SpO₂, palm temperature and a load cell) is shown separately and is not part of the overall result
by default. LYRA makes no heart assessment through the palm.

The main idea: LYRA compares you not only with **your own baseline** but also with **NASA expected adaptation**,
the published adaptation trajectories (headward fluid shift, "bird legs", spinal elongation, strength loss).
The question is "are you changing faster than NASA expects?" Every metric is linked to a NASA HRP risk.

> Screening and self-monitoring, **not a medical device and not a diagnosis**. LYRA reports "change detected",
> never a diagnosis. All data in the demo is **simulated**.

## Run with one command

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python -m lyra.server
```
Open http://127.0.0.1:8000 (16:9 laptop, full-screen browser; narrow screens work too).
Internet access is needed for Three.js from the CDN (`three@0.160.0`, jsdelivr).

Flags: `--scenario day1|day40|mars180|anomaly` (default day40), `--fast` for short session phases,
`--time-scale 60` to speed up the comm delay for the demo, `--port 8000`.

## Result categories

| Code | Label | Meaning |
|---|---|---|
| green | **Within baseline** | Within your personal baseline and the NASA expected-adaptation corridor. |
| yellow | **Repeat measurement** | A change was detected once; do the suggested action and repeat. |
| red | **Refer to specialist** | A sustained change, beyond what NASA expects; the medical team reviews it. |
| retry | **Measurement not confirmed** | Quality too low (motion, low light, face not visible, pose not reached, weak signal). No averaged value is substituted; repeat. |

Every result says **why** it is flagged (not just a color), shows its measurement quality and its data
provenance ("team recording", "open dataset (CameraVitals)", "NASA material" or "simulation"; in this demo it is
"simulation").

## Two comparison levels

1. **Personal baseline**: the pre-flight mean, updated during the mission (last 14 measurements, adjusted for the
   NASA trajectory).
2. **Environment mode**: Earth, microgravity, or partial gravity (rover or base). Posture is interpreted against
   the **microgravity neutral body posture**, not the Earth upright stance. A posture flag escalates only if it
   repeats across several measurements or comes together with reported back pain or fatigue.

## Scenarios (switch with the buttons in the header)

| Scenario | Environment | What to show |
|---|---|---|
| **Day 1, ISS** | microgravity, ~1 s delay | Fluid shift has just started, everything is Within baseline. For Mira and Leia, 3D face ID is not confident (swelling), so they use the NFC card. |
| **Day 40, ISS** | microgravity | Face +4%, calves -8%, height +2%: big changes, but **expected**, so Within baseline. Streaks, with missed days for Ivan and Leia. Leia's camera pulse is "Measurement not confirmed" (low light). |
| **Day 180, Mars** | partial gravity 0.38 g, 14 min delay (3 to 20 min) | Downlink queue: packet "in transit", then "delivered"; the surgeon's reply cannot come sooner than 28 min. The crew gets instructions immediately. |
| **Anomaly, Moon day 60** | partial gravity 0.17 g | **Mira Sato**: facial swelling above the NASA corridor, so Refer to specialist with step-by-step instructions. In the research module her grip strength and palm blood flow also drop faster than NASA expects (shown separately). |

Demo path for judges: "Anomaly" -> pick Mira -> "Full test" -> go through it -> "You vs. NASA" tab
(the trajectory leaves the corridor).

## What is in the interface

- **3D body point cloud** (Three.js): front / side / top / rotate views, highlighted changing zones (face, calves,
  height, posture) in the status color with a label such as "Face +4.1%". The backend also returns a skeletal
  keypoint model (head, shoulders, elbows, pelvis, knees, feet) for the front, side and back views.
- **Session**: 3D face ID (NFC card when confidence is low; voice is not used for identification) -> 3D scan ->
  palms on the marked mirror zones -> (full test, research module) handgrip test "hold it in the green zone"
  (**Space** or mouse button) + recovery -> 15 s survey of 3 questions plus optional back pain (voice or buttons)
  -> result. Express scan about 90 s, full test about 5 min (phases are shortened in the demo, and labeled so).
- **Voice**: prompts via `speechSynthesis`; commands "start / repeat / stop" via `webkitSpeechRecognition`
  (turned on with a button); every voice action has a button too. Keys: Enter starts, Esc stops.
- **Training mode** on an astronaut's first run (offered automatically): nothing is recorded or sent.
- **"Why it matters"** cards: explanation, NASA HRP risk, hazard from the 5 Hazards, source, and a "cited" or
  "team estimate" marker.
- **"You vs. NASA" chart**: corridor, expected line, your trajectory, points outside the corridor, values on hover.
- **Downlink to Earth**: packets to the flight surgeon with the environment's delay. Each packet carries a medical
  report (time series, signal quality, environment mode, comparison with previous measurements, reason for each
  flag). **Dosimeter dose** is imported: LYRA does not measure radiation.

## What is simulated

The whole history (7 pre-flight days + mission days), sensor values in the session, rPPG signal quality,
identification confidence, the dosimeter dose, and the comm delay (inside the reference range, sped up for the
demo). The simulation curves are **the same** as the NASA corridor (plus individual variation, sensor noise, the
environment posture shift and the scenario anomaly). NASA figures come only from
[`data/nasa_reference.json`](data/nasa_reference.json) (each figure has a source and a `basis` of `cited` or
`estimated`).

## Architecture

Short version: [lyra/ARCHITECTURE.md](lyra/ARCHITECTURE.md).

```
lyra/core        NASA reference, expected-adaptation model, result categories, downlink queue, store
lyra/sim         crew, scenarios, simulator
lyra/service.py  use cases (incl. the medical report); lyra/server.py: FastAPI REST + WebSocket
lyra/dashboard   index.html, style.css, app.js, body3d.js (no build step)
lyra/feasibility real camera (MediaPipe, rPPG) and ESP32 grip prototype: feasibility check, the demo does not depend on it
```

API: `GET /api/meta`, `GET /api/state`, `POST /api/scenario/{id}`, `GET /api/reference`, `GET /api/astronauts/{id}`,
`GET /api/astronauts/{id}/series/{metric}`, `POST /api/identify`, `POST /api/identify/nfc`, `POST /api/sessions`,
`POST /api/astronauts/{id}/dose`, `GET /api/downlink`, `GET /api/downlink/{packet_id}`, WebSocket `/ws`.
Details at the top of `lyra/server.py`; interactive docs at http://127.0.0.1:8000/docs.

## Stack

Python 3.12, FastAPI, Uvicorn, Pydantic, NumPy, SciPy, pytest; vanilla JS (no build step), Three.js 0.160.0 via
jsdelivr, Web Speech API. Feasibility module: OpenCV, MediaPipe 0.10.14, pyserial, ESP32 (Arduino).

## Tests

```bash
.venv/bin/python -m pytest -q
```
Expected-adaptation model (plateau, linear, absolute units, "none"), result categories and labels, "slow drift is
caught only by the corridor", measurement quality and reject reasons, rPPG signal fields, environment mode and
the neutral body posture, posture escalation rule, research module excluded from the overall result, skeletal
keypoints, medical report, scenarios (normal / anomaly / NFC / training / streak), downlink queue, REST and
WebSocket.

## Drawings

English drawings are the primary set in [`docs/drawings/`](docs/drawings/) (PNG exports in `docs/drawings/png/`).
Older drawings are kept in `docs/drawings/archive/`. Dimensions are approximate.

## Feasibility check (not the center of the demo)

`lyra/feasibility/vision`: MediaPipe (facial swelling, blinking, PERCLOS, posture) and video pulse (rPPG);
`lyra/feasibility/palm`: ESP32 prototype of the research-module grip. Dependencies:
`pip install -r lyra/feasibility/requirements.txt`. Not yet tested on real hardware.

## Use of AI

An AI assistant (Claude) helped with code, docs, drawings and research, under the team's direction. The idea and
the decisions are the team's own.
