# LYRA: 3D health scan for long-duration missions

**Step in. Scan. Know.** A web app running on simulated data, built for the NASA Space Apps Challenge 2026
("Create Health Monitoring Software for Astronauts on Space Missions"). Team: Alina Dmitriyeva, Daniil Shabalin.

The LYRA station (drawings v3) is a full-height touch mirror on its own stand plus three free-standing camera
pillars around the astronaut: two in front at ±60° and one behind, each with RGB + IR depth modules at head, torso
and leg height, bases bolted to the floor. The core scan is **contactless**: the face module in the mirror bezel
uses structured IR light (a dot projector, like Face ID, for millimeter-level facial swelling) plus an RGB camera,
and the three pillars build a skeletal keypoint model of the body from three synced views. The palms rest on marked zones of the touch mirror only to standardize the pose. Nothing is
worn on the body.

An optional **contact research module** (vertical grips on the mirror stand legs with Doppler ultrasound and a hydrogel
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

English drawings (v3: touch mirror + three camera pillars) are the primary set in [`docs/drawings/`](docs/drawings/):
SVG sources, PNG in `docs/drawings/png/`, PDF per sheet in `docs/drawings/pdf/` and all five sheets in one file,
[`docs/drawings/LYRA_drawings.pdf`](docs/drawings/LYRA_drawings.pdf). Rebuild:

```bash
python3 docs/drawings/_src/gen_drawings.py && python3 docs/drawings/_src/render_png.py && python3 docs/drawings/_src/render_pdf.py
```
Older drawings are kept in `docs/drawings/archive/`. Dimensions are approximate.

## Feasibility check (not the center of the demo)

`lyra/feasibility/vision`: MediaPipe (facial swelling, blinking, PERCLOS, posture) and video pulse (rPPG);
`lyra/feasibility/palm`: ESP32 prototype of the research-module grip. Dependencies:
`pip install -r lyra/feasibility/requirements.txt`.

**Live camera demo (real person, no simulation).** An iPhone works as the camera through macOS Continuity Camera
(same Apple ID, Wi-Fi and Bluetooth on, iPhone near the Mac, e.g. on a stand in landscape):

```bash
.venv/bin/pip install -r lyra/feasibility/requirements.txt
.venv/bin/python -m lyra.feasibility.vision.live          # picks the highest-resolution camera, usually the iPhone
.venv/bin/python -m lyra.feasibility.vision.live --camera 1   # or choose the index explicitly
```
Open http://127.0.0.1:8780. The page shows the mirrored video with face landmarks, the quality gate (face visible,
facing the mirror, light level, holding still), live camera pulse with a quality score, blink rate, face width /
IPD ratio, shoulder tilt and the 478 face landmarks in 3D. "Baseline scan" (15 s) stores your personal baseline in
memory; "Compare scan" returns Within baseline / Repeat measurement / Refer to specialist / Measurement not
confirmed with the reason. Frames are processed locally and never stored. Continuity Camera only streams the
iPhone's **rear** RGB camera, so in this mode depth is estimated from RGB by MediaPipe.

**Real IR depth: iPhone TrueDepth (the Face ID camera) through Record3D.** Face ID itself is closed to apps, but
the TrueDepth camera behind it (IR dot projector + IR camera, the same principle as the LYRA mirror face module)
streams RGB + measured depth through the Record3D app:

1. Install **Record3D** (App Store) on a Face ID iPhone; buy the in-app option that unlocks **USB Streaming**
   (the app's Wi-Fi streaming is lossy and not used here).
2. In Record3D: Settings, enable **USB Streaming mode**; choose the front (selfie / TrueDepth) camera; connect the
   iPhone to the Mac by cable, tap "Trust" on the phone, press the record button.
3. On the Mac:
   ```bash
   .venv/bin/pip install record3d        # builds a small native library (needs cmake: brew install cmake)
   .venv/bin/python -m lyra.feasibility.vision.live --source record3d
   ```
The page then says "iPhone TrueDepth (IR depth)", shows an IR depth inset over the video, lifts the face landmarks
to real 3D and reports face width, nose depth and interpupillary distance in millimetres and the distance to the
camera; scans compare the measured face width with your baseline. `--host 0.0.0.0` makes the page reachable from a phone on the
same Wi-Fi, which also exposes the camera stream to that network: use it only on a trusted network.
If MediaPipe cannot download its pose model on first run, fetch it once:
`curl -o .venv/lib/python3.12/site-packages/mediapipe/modules/pose_landmark/pose_landmark_lite.tflite https://storage.googleapis.com/mediapipe-assets/pose_landmark_lite.tflite`.

## Use of AI

An AI assistant (Claude) helped with code, docs, drawings and research, under the team's direction. The idea and
the decisions are the team's own.
