# LYRA: web demo architecture (1 page)

```
data/nasa_reference.json --(read only, re-read when it changes)--------+
                                                                       v
 lyra/core: pure logic, no HTTP and no randomness                  reference.py
   metrics.py   engineering parameters per metric (group, harmful direction, noise, advice, module core|research)
   expected.py  NASA "expected adaptation" model -> corridor by day (linear / saturating / none)
   assess.py    result category = personal baseline (z, adjusted for the NASA trajectory) + corridor exit;
                labels, quality and reject reasons, environment mode, posture rule, provenance
   engine.py    session -> metric results, overall result, 3D point-cloud params, skeletal keypoints (3 views)
   store.py     sessions and doses in memory (narrow interface, easy to swap for a database)
   comms.py     downlink queue to Earth: delay from the reference, "in transit / delivered", medical report payload
 lyra/sim: everything simulated
   crew.py      4 fictional astronauts (personal baselines)
   scenarios.py day 1 (ISS), day 40 (ISS), day 180 (Mars), anomaly (Moon, day 60); forced rejects for the demo
   simulator.py history along the same NASA curves + environment posture shift + anomalies + noise; rPPG signal
 lyra/service.py   use cases (identify, session, chart series, dose import, medical report)
 lyra/server.py    thin FastAPI: REST + WebSocket /ws (state, downlink)
 lyra/dashboard    plain JS, no build: app.js (session flow, chart, queue, voice),
                   body3d.js (Three.js 0.160.0 from CDN: body point cloud)
 lyra/feasibility  real camera (MediaPipe, rPPG) and ESP32 grip prototype: feasibility check, not imported by the demo
```

**Decisions**
- *Result categories.* Internal codes stay `green / yellow / red / retry`; human-facing labels are
  "Within baseline", "Repeat measurement", "Refer to specialist" (sustained change, for the medical team) and
  "Measurement not confirmed". Wording is "change detected", never "diagnosis".
- *NASA corridor.* Base = mean of the 7 pre-flight days. Half-width = `band` from the reference, but not narrower
  than 2 sigma of sensor noise (otherwise noise looks like "faster than NASA"); without `band`:
  max(2 sigma, half the expected change). `model: none`, `rate: 0` or non-numeric fields mean no corridor, only
  the personal baseline.
- *Combining.* Inside the corridor: green "expected adaptation" (a sudden jump z >= 3 gives yellow). Outside the
  corridor in the harmful direction: the worse of (corridor: < 1 half-width yellow, >= 1 red) and
  (z: 2 to 3 yellow, >= 3 red). The personal baseline uses residuals "value - NASA expectation", so the shift of
  the first days does not raise false alarms, and a slow drift faster than NASA is caught by the corridor even
  though the personal baseline does not see it.
- *Measurement quality.* Each metric result carries `quality` (0..1). Below 0.5 the status is `retry` with a
  `reject_reason` ("motion", "low light", "face not visible", "pose not reached", "weak signal", "target zone
  not held"). No averaged value is ever substituted. The camera pulse (`hr_rppg`) also returns
  `signal: {usable_seconds, window_seconds, motion, light}`.
- *Two comparison levels.* Personal baseline (pre-flight, updated in mission) plus `env_mode`
  (`earth`, `microgravity`, `partial_gravity`) derived from the environment's gravity and the day (pre-flight days
  are Earth). In space, posture metrics are compared only with in-mission history against the environment's
  reference posture (microgravity: neutral body posture), not with the Earth upright stance; their `preflight` is
  `null`. A posture flag stays "Repeat measurement" unless it repeats in the previous 2 measurements or comes with
  reported back pain or fatigue (survey: back pain, sleep <= 2, wellbeing <= 2); then it escalates to red.
- *Body model.* `body.skeleton` holds simulated keypoints (head, shoulders, elbows, pelvis, knees, feet) for the
  front, side and back views in mm, plus posture features. Local posture metrics `trunk_tilt_deg`,
  `pelvis_tilt_deg`, `scapula_asym_mm`, `spine_length_mm`, `pose_return_s` and the survey item `back_pain_flag`
  live in `metrics.LOCAL_ONLY`; the code tolerates them being absent from the reference JSON.
- *Core vs research module.* Core LYRA is contactless (RGB + structured IR + depth). Grip strength, Doppler,
  grip PPG/SpO₂, palm temperature and the handgrip test are `module: "research"`: shown separately in
  `overall.research` and excluded from the overall result unless the session request sets `include_research: true`.
  No heart assessment through the palm.
- *Provenance.* Every result and metric carries `provenance`, one of "team recording",
  "open dataset (CameraVitals)", "NASA material", "simulation". In this demo it is always "simulation".
- *Medical report.* Each live session produces `medical_report` (time series, signal quality, environment mode,
  comparison with previous measurements, reason for each flag). It travels with the downlink packet
  (`GET /api/downlink/{packet_id}`); the queue view leaves it out and sets `has_report`.
- *Session flow* is driven by the frontend (timers, game, survey); at the end the backend receives
  `POST /api/sessions` and simulates sensor values. Training mode is the same call with `training: true`: nothing
  is stored or sent.
- *Comm time.* The delay is inside the reference range; for the demo it is sped up with `--time-scale`
  (default x60), and the screen says so.
- *Honesty.* The UI marks everything "simulated data"; wording is "screening, not a diagnosis"; `basis: cited /
  estimated` and sources are shown next to each trajectory. LYRA does not measure radiation: it imports the
  dosimeter value.
- *Language.* All backend strings are English. Reference keys named `*_ru` (`name_ru`, `why_ru`, `summary_ru`,
  `note_ru`, `status_ru`) are kept for API compatibility; their values are English text.
- *Packet status.* `status_light` holds the overall status code (`green / yellow / red`), not an emoji.
