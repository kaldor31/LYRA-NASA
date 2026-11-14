# LYRA: recorded decisions (source of truth)

> Result of the team survey, 2026-11-14. Everything below is **confirmed by the team**. If anything here needs to change, ask the team; do not decide on your own.
> The NASA Space Apps hackathon is already under way: we work fast, and the priority is what the judges see.

## Language
- **All materials, UI and docs are in English** (official Space Apps rule).

## 0. Scope
- For now we are building a **concept**: drawings, a presentation, and a **web app running on simulation**. There is **no** physical MVP/hardware.
- Judging focuses first of all on **software** (challenge: "Create Health Monitoring Software for Astronauts on Space Missions").
- Judging criteria (5 points each): **Impact** (scalability), **Creativity**, **Validity** (scientific rigor, feasibility, intuitiveness), **Relevance** (how deeply and **substantially** NASA data are used), **Presentation** (clarity, storytelling).
- Challenge hints (to address): different environments (spacecraft, station, rover, Moon/Mars base); measurement reminders as part of the routine; **gamification**; **dynamic charts**; **color coding**; simple instructions and explanations ("do not assume astronauts know everything").
- Risks from the challenge text that must be covered: radiation, isolation and confinement, altered gravity, hostile closed environment → immune changes, bone loss, cardiovascular events, behavioral health.

## 1. Name
**LYRA**, not an acronym. Tagline: "LYRA: 3D health scan for long-duration missions" / "Step in. Grip. Know."

## 2. Station (hardware concept)
- **Form:** three planes around the person. In front, a **mirror panel about 500 x 900 mm** with a display behind it (head + torso). Around the person, **three slim posts** (profile about 40 x 40 mm): two front posts at the sides + one rear post, giving a 360° view.
- The posts **attach to the module structure** (floor to ceiling about 2 m, on the ISS the standard mounting rails), **no legs**; they fold on hinges against the wall. Working area about 1.2 x 1.2 m. Foot restraints (microgravity).
- Each post carries **modules at three heights** (head, torso, legs).
- **Sensors (hybrid):**
  - **Face: structured light, an IR dot projector + IR camera** (the Face ID principle). Reason: facial puffiness means changes of a few mm at about 0.5 m, which ToF cannot resolve.
  - **Body: ToF cameras** (at 1-2 m ToF accuracy is nearly constant, while structured light degrades).
  - **RGB cameras** in addition (pulse from video, rPPG; skin color).
  - Dot projectors fire **in turn** (patterns do not overlap); ToF cameras use **different modulation frequencies**.
  - A "structured light vs ToF" table (for a slide): accuracy at close range / at distance, resolution, baseline, calibration drift from launch vibration, ToF multipath errors, mutual interference.
- **Two handles** (left/right) on the front posts at elbow height. Each contains:
  - **ultrasound Doppler** at the palmar arteries (blood flow velocity, pulse waveform shape, L/R asymmetry);
  - PPG + SpO₂ under the finger; palm temperature; **load cell** (grip strength); **NFC reader**.
  - **Gel is required** (ultrasound does not pass through air). Primary option: a **cassette with a tape of solid hydrogel**, a fresh section advanced before every session. This is **our design** (hydrogel pads for ultrasound and tape-advance mechanisms exist, the cassette itself does not; label this honestly). Backup: a **liquid gel dispenser** in the same handle.
- **Principle: nothing is worn on the body**, **no electrodes** (ECG/AD8232 removed completely, HRV from PPG/Doppler).
- **Identification:** 3D face recognition (dot projector); if not confident, tap an **NFC card** (kept at the station, not carried). **Voice is NOT used for identification.** The face reference updates slowly (the face changes from puffiness in the first days).

## 3. Session
- **Daily express scan, about 90 s:** step in → 20 s 3D scan of face and body → 30 s at rest with hands on the handles (blood flow, pulse, SpO₂, temperature) → 2 short maximal squeezes (grip strength) → result.
- **Weekly full test, about 5 min:** all of the above + an **isometric handgrip test** (2 min holding 30% of maximum using a "keep it in the green zone" indicator, gamification) + 1 min recovery → pulse and blood flow response.
- Unscheduled run: at will or at the system's request after Recheck/Deviation.
- **15 s voice check-in:** 3 questions: sleep, wellbeing, symptoms.

## 4. Metrics
- **Face:** face volume (ml), puffiness around the eyes, blinking, PERCLOS, yawning, facial expression ("likely signs of strain", never the words "diagnosis"/"mental state"), pulse from video.
- **Body:** volume/girth of the lower legs and thighs ("bird legs", muscle atrophy), total body volume (indirect substitute for weighing, since scales do not work in microgravity), **height** (spinal elongation; check the number against NASA), posture (head forward, shoulder symmetry, back curvature).
- **Handles:** grip strength L/R, Doppler (blood flow velocity, asymmetry), pulse, HRV, SpO₂, palm temperature; in the weekly test, the response to the handgrip test and recovery.
- **Plus:** self-report (sleep/wellbeing/symptoms); **import of station dosimeter data** (LYRA does not measure radiation itself).

## 5. NASA data: a substantial role (Relevance)
- **Risk map:** each metric ↔ HRP risk ("Risks of Human Spaceflight") ↔ hazard from the "5 Hazards" (Radiation, Isolation & Confinement, Distance from Earth, Gravity, Hostile/Closed Environments). On-screen explanations reference the risk.
- **"Expected adaptation" model:** published NASA/CSA trajectories of change (bone 1 to 1.5%/month, fluid shift toward the head, muscles, heart and vessels) → a corridor of "normal adaptation". **Status = "are you changing faster than NASA expects"**, not just "are you different from yourself yesterday". The same curves drive the simulation.
- Everything is in `data/nasa_reference.json`: every number has a source (URL) and a `cited` marker (number taken from the source) or `estimated` (our estimate). **Do not present invented numbers as citations.**
- Related HRP studies from the resource pages (must be mentioned/used where relevant): Standard Measures (and Artemis II Standard Measures), CIPHER, Thigh Cuff, Spinal Health, Venous Haemostasis, Brain Fluid Pressure, Spinal Fluid Biomarkers, ARCHeR, Immune Biomarkers, Zero T2, Tempus Pro, Omics Archive.

## 6. Actions and instructions
- **All data automatically go to the flight surgeon on Earth**, accounting for communication delay (queue). Mars: up to 20 min one way (NASA, Distance from Earth).
- The astronaut **always gets clear instructions**: voice prompts at every step, a screen with a short caption and animation, a **training mode** on first launch (nothing recorded), **"why it matters" cards** (2-3 sentences + the NASA risk), **voice commands** ("start", "repeat", "stop") because the hands are busy.
- Normal: brief summary + day streak (gamification); Recheck: a specific action from the onboard measures + a reminder to repeat; Deviation: a step-by-step "what to do now" instruction; Remeasure: repeat the measurement when the scan was not reliable.
- Wording: "screening, not a diagnosis"; never "diagnoses", "measures bone density", "determines mental state".

## 7. Environment
The primary one is a **long-duration station/base** (ISS, Gateway, Moon, Mars). For scalability, a **compact folding configuration** for a spacecraft/rover; use on Earth (polar stations, submarines, remote hospitals, older adults; CSA: the effects of microgravity resemble accelerated aging).

## 8. Code (web app on simulation)
1. 3D body point cloud (Three.js), three projections, highlighting of changing zones (the face swells, the legs get thinner).
2. Express scan and weekly test with voice (Web Speech API) and a game-style indicator for the handgrip test.
3. A "you vs NASA expectation" chart (trajectory over the expected adaptation corridor).
4. Color-coded statuses, explanations, HRP risk cards.
5. Transmission queue to Earth with simulated delay (ISS / Moon / Mars).
6. Several astronauts and scenarios (day 1, day 40, day 180 on Mars).
The existing real-camera code (MediaPipe, `lyra/vision`, `lyra/palm`) → a "feasibility check" folder, not the center of the demo.

## 9. Drawings (5 sheets, SVG; English versions are primary at `docs/drawings/*.svg`, PNG exports at `docs/drawings/png/`, Russian originals at `docs/drawings/ru/`; old ones → `docs/drawings/archive/`)
1. General view: top view + isometric, three posts, mirror panel, working area 1.2 x 1.2 m, folded position, foot restraints.
2. Front and side view: modules at three heights, **fields of view** of the projectors (face) and ToF (body), handle heights.
3. Handle cross-section: Doppler window, hydrogel cassette, backup dispenser, PPG/SpO₂, temperature, load cell, NFC.
4. System block diagram: sensors → onboard computer → screen/voice → communication queue to Earth + station dosimeter; projector/ToF timing.
5. Compact folding configuration (spacecraft/rover).
Dimensions are "approximate"; label them as such.

## 10. Roles
- **Agent A: software** (`lyra/`, `tests/`, `README.md`).
- **Agent B: concept and rationale** (`docs/`, `PLAN.md`, `data/nasa_reference.json`, presentation, video script).
- Shared boundary: `data/nasa_reference.json` is written **only by B**; A **only reads** it (the schema below does not change without agreement).

## 11. Schema of `data/nasa_reference.json`
```json
{
  "sources":  [{"id": "str", "title": "str", "publisher": "NASA|CSA", "url": "str"}],
  "hazards":  [{"id": "radiation|isolation|distance|gravity|hostile", "name_ru": "str", "name_en": "str", "source_ids": ["str"]}],
  "risks":    [{"id": "str", "name_ru": "str", "name_en": "str", "hazard_ids": ["str"], "summary_ru": "str", "source_ids": ["str"]}],
  "metrics":  {"<metric_key>": {"name_ru": "str", "unit": "str", "risk_ids": ["str"],
               "expected": {"model": "linear|saturating|none", "rate": 0.0, "rate_unit": "str",
                            "tau_days": 0, "band": 0.0, "basis": "cited|estimated",
                            "note_ru": "str", "source_ids": ["str"]},
               "why_ru": "str"}},
  "environments": {"<env_id>": {"name_ru": "str", "gravity_g": 0.0, "comm_delay_one_way_s": [0, 0], "source_ids": ["str"]}},
  "radiation": {"note_ru": "str", "neutron_share_iss": 0.3, "source_ids": ["str"]}
}
```
Note: the *_ru keys are kept for API compatibility; since 2026-11-14 their values are English text.
