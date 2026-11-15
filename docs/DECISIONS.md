# LYRA: recorded decisions (source of truth)

> v2, 2026-11-15. The team's concept paper `docs/research/LYRA_concept_paper_ru.pdf` (Russian, 22 pages) is authoritative: where this file and the paper differ, the paper wins. One explicit team instruction on top of the paper: **the Doppler transducers are oriented vertically** (vertical grips built into the vertical side posts).
> v1 decisions (2026-11-14 survey) are superseded where they conflict; the main changes are listed in section 12.
> The hackathon is under way (deadline Sun 15 Nov 23:59 local): we work fast, and the priority is what the judges see.

## Language
- **All materials, UI and docs are in English** (official Space Apps rule). The concept paper stays in Russian as the team's source document.

## 0. Scope
- We build a **concept**: drawings, a presentation, and a **web app running on simulation**. There is no physical MVP. A small feasibility module (real camera with OpenCV/MediaPipe, ESP32 grip) exists but is not the center of the demo.
- Challenge: **"Create Health Monitoring Software for Astronauts on Space Missions"**. Judging focuses on **software**.
- Criteria (5 points each): **Impact**, **Creativity**, **Validity**, **Relevance** (substantial use of NASA data), **Presentation**.
- LYRA is presented as a working concept that **needs validation**, not as a finished medical device. Wording: "change detected", never "diagnosis".

## 1. Name
**LYRA** = **Life-signs & Yield-based Readiness Analytics** / **Lunar-to-orbit Your Readiness Assessment** (both expansions from the paper).
One-liner: "LYRA is a touch mirror for contactless crew readiness checks on space missions."
Tagline: **"Step in. Scan. Know."**

## 2. Station (hardware concept)
- **Touch mirror between 3 frames: front, side, back.** The crew member steps into the marked area. The mirror shows **contours for the feet, the torso and the palms**. Palms on the marked zones **standardize the pose and body orientation; they are not a medical sensor.** Light cues show where to turn or how close to stand.
- **Frames** are a camera placement and synchronization system, not medical sensors:
  - front frame: face, chest, arms (RGB camera + IR camera + structured IR projector + illumination);
  - side frame: profile, head and trunk tilt, spine;
  - back frame: shoulders, scapulae, pelvis, back symmetry.
- **Cameras check pose and frame quality before capture.** If the person cannot reach the pose, this is stored as a measurement condition, not as pathology.
- **Identification:** 3D face recognition; fallback is an **NFC reader on the mirror frame** (station reader, card kept at the station). Voice is not used for identification.
- Mounting: frames attach to the module structure (on the ISS, the standard seat tracks), foot restraints for microgravity. Dimensions in the drawings are approximate.

## 3. Sensing (contactless core)
- **Face: structured IR light.** Projector sends an invisible dot/stripe pattern → IR camera captures the pattern deformed by the face → correspondence projector vs image → triangulation → depth map → point cloud → surface reconstruction joins neighbouring points into triangles (mesh). Software: **OpenCV** (calibration, pattern decoding, depth) + **Open3D or PCL** (point cloud, mesh). **The projector does not build the mesh.**
- No need for 30,000 polygons: track stable **key regions** (eyes, brows, nose, cheeks, lips, chin); a few dozen features from a denser surface. The dense mesh is a visual layer on the mirror.
- **RGB camera is a separate channel**: visible expression, skin color, head position, rPPG pulse. IR is less dependent on color texture and part of ambient light. **RGB + IR + depth are fused**; channels stay separate until each passes its quality check.
- **Body: skeletal keypoints** (head, shoulders, elbows, pelvis, knees, feet) from **3 synchronized views** merged into one coordinate system. Structured light is possible for the body; **ToF is an alternative** for whole-body depth at larger distance; this is an engineering choice to verify on a prototype.
- **Posture in 3 planes:** front (shoulder and pelvis symmetry), side (head and trunk tilt), back (scapulae, visible spine symmetry). One view can hide a deviation.
- **The camera does not measure bone density, discs or muscle strength.** It records external geometry and movement.

## 4. Optional contact research module: vertical Doppler grips
- Ultrasound Doppler transducers built into the **vertical side posts as vertical grips**. This is a **contact research channel, not part of the core**, and contradicts a strict "fully contactless" definition, so it is shown separately.
- **Solid hydrogel cassette, 4 parts:** (1) holder fixed on the transducer body; (2) **thin replaceable hydrogel pad**; (3) soft protective rim limiting material displacement; (4) thin membrane protecting the gel and keeping skin contact. Gel must fully cover the acoustic path (no air gap). Pad thickness and press force: **to be determined experimentally on a ground mock-up**.
- **Workflow (8 steps):** pad into holder on the transducer face → check for bubbles/damage → palm on the marked zone → cassette gently pressed to the skin (not a standalone sensor) → pulses through the hydrogel → receiver registers the echo → software checks contact quality and signal stability → if poor, ask to reposition the hand or repeat.
- **Two hackathon versions:** **demo** = mock cassette on the grip + on-screen signal path diagram; **extended** = real transducer only after a phantom / ground test-bench check.
- **Never claim** heart, venous or cardiovascular assessment through the palm. Research metrics (grip strength, Doppler flow, flow asymmetry, palm pulse, HRV, SpO₂, palm temperature, handgrip test) are **excluded from the overall status**.
- The v1 tape cassette and liquid gel dispenser are archived (`docs/drawings/archive/v1/`).

## 5. AI: separate, checkable modules
1. **Camera/IR processing:** find the face and separate it from the background; detect IR pattern points; reject points corrupted by motion or reflections; refine the surface over neighbouring frames.
2. **RGB + IR fusion:** color features (RGB), geometry features (IR depth), temporal features. Tells real expression movement from lighting change; if one channel degrades, the other keeps tracking.
3. **rPPG with quality outputs:** heart rate plus signal quality, usable duration, motion, light level, reject reason. Poor quality → **"Measurement not confirmed"**, never a substituted value.
4. **Body/posture:** 3-view skeleton in one coordinate system, compared with the personal baseline and the environment mode.
5. **Change classifier, 3 categories:** **"Within baseline"**, **"Repeat measurement"**, **"Refer to specialist"** (sustained change for the medical team). Plus the quality outcome **"Measurement not confirmed"**.
- **A human (the medical team) makes the medical decision.** Each result explains which indicator changed, how reliable the signal is, and what action is suggested.

## 6. Comparison logic
- **Two levels:** (1) **personal baseline** formed before flight and updated during the mission; (2) **environment mode**: Earth, microgravity, partial gravity (Moon, Mars), plus rover / module context. In code: `earth | microgravity | partial_gravity`.
- The microgravity **neutral body posture** differs from Earth's; NASA describes anthropometry changes (spine elongation, fluid shift, muscle atrophy, bone changes). The Earth upright stance is not the only reference.
- **Flag only sustained or repeated changes**, growing deviation from baseline, or **combinations with reported pain or fatigue**. A single asymmetry can be the person's normal build.
- The NASA "expected adaptation" corridor from v1 (`data/nasa_reference.json`) stays as context for the metrics that have a NASA trajectory.
- The report to the medical team holds the time series, image/signal quality, environment mode, comparison with previous measurements and the reason for each flag, not only a color.

## 7. Data and provenance
- Every result shows its **provenance**: **team recording**, **open dataset (CameraVitals)**, **NASA material**, **simulation**. In the live demo everything is simulation.
- **One concrete NASA dataset:** **NASA OSDR OSD-575** (Inspiration4 Comprehensive Metabolic Panel): variables, units and role in `docs/research/nasa_sources.md` §6.1.
- NASA Life Sciences Portal (LSDA): human research in spaceflight and ground analogs since 1961, for context and indicator choice. NASA Open Data Portal: catalog. NASA OSDR incl. Inspiration4: visualizing spaceflight changes, **not camera training data**. NASA neutral body posture and anthropometry (HIDH, NASA-STD-3001 Vol. 2, NTRS studies): environment-mode rules.
- **CameraVitals (COHFACE):** RGB video synced with cardiac and respiratory signals, 160 one-minute sequences from 40 participants: rPPG validation on Earth only.
- Team recordings on the mirror mock-up: rest, talking, head turn, exercise and recovery, lighting changes, distances; never mix one person between training and testing.
- **No single NASA dataset contains IR face points + RGB + 3D posture + medical references**, so LYRA is a prototype requiring validation. We never say the model is trained on NASA data.

## 8. Session (demo)
Position check (feet, torso, palms on the mirror contours) → face: RGB, IR dots, depth, mesh → 3 posture views → quality check → comparison with baseline and environment mode → one of 3 statuses + explanation → report queued to the medical team on Earth (one-way delay: ISS under 1 s, Moon about 1 to 2 s, Mars 3 to 20 min). Short self-report (sleep, wellbeing, back pain/symptoms). Voice prompts, training mode, "why it matters" cards.

## 9. Code (web app on simulation)
Owned by the software agents (`lyra/`, `tests/`, `README.md`). Statuses, environment modes, provenance values and research-module handling follow sections 5 to 7. The research module is excluded from the overall status and can be skipped in a session (`skip_research`). Metric keys are canonical in `data/nasa_reference.json`; new posture keys: `trunk_tilt_deg`, `pelvis_tilt_deg`, `scapula_asym_mm`, `spine_length_mm`, `pose_return_s`, `back_pain_flag`.

## 10. Drawings (5 sheets, English, `docs/drawings/*.svg`, PNG in `docs/drawings/png/`)
1. `01_general_view`: plan, mirror face with foot/torso/palm contours and NFC reader, isometric of the 3 frames.
2. `02_front_side_views`: elevations, camera modules and fields of view, vertical Doppler grips (research module).
3. `03_doppler_cassette`: vertical grip section, 4-part hydrogel cassette, 8-step workflow, demo vs extended.
4. `04_face_pipeline`: IR dots → depth → point cloud → mesh, RGB channel, fusion.
5. `05_system_ai`: AI modules, quality gate, comparison, 3 statuses, data provenance, report queue.
Generator: `python3 docs/drawings/_src/gen_drawings.py && python3 docs/drawings/_src/render_png.py`. Each sheet carries "AI (SI) assisted drawing". v1 sheets and the Russian set: `docs/drawings/archive/v1/`.

## 11. Schema of `data/nasa_reference.json` (unchanged)
```json
{
  "sources":  [{"id": "str", "title": "str", "publisher": "NASA|CSA|Other", "url": "str"}],
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
The `*_ru` keys are kept for API compatibility; their values are English text. Only the concept agent writes this file; code only reads it.

## 12. What changed from v1
- Handles with Doppler + PPG/SpO₂ + load cell + NFC → **touch mirror with palm contours (pose only)**; Doppler moved to an **optional vertical-grip research module**; NFC moved to the mirror frame.
- Tape hydrogel cassette + liquid gel dispenser → **4-part cassette with a thin replaceable pad** on the transducer.
- Statuses Normal / Recheck / Deviation / Remeasure → **Within baseline / Repeat measurement / Refer to specialist / Measurement not confirmed**.
- "LYRA, not an acronym" and "Step in. Grip. Know." → the paper's two expansions and **"Step in. Scan. Know."**
- Added: AI modules with quality outputs, 3-plane posture with environment mode, data provenance, one concrete NASA dataset.
