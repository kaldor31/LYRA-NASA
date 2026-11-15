# LYRA: concept specification

> **LYRA: Life-signs & Yield-based Readiness Analytics** (also: Lunar-to-orbit Your Readiness Assessment). "Step in. Scan. Know."
> Team: Alina Dmitriyeva, Daniil Shabalin. NASA Space Apps 2026, challenge "Create Health Monitoring Software for Astronauts on Space Missions".
> Status: concept + web app running on simulated crew data. Source of truth: the team concept paper `docs/research/LYRA_concept_paper_ru.pdf`, summarized in `docs/DECISIONS.md`. Numbers and links: `data/nasa_reference.json`, `docs/research/nasa_sources.md`.
> **LYRA detects changes and checks measurement quality. It does not diagnose.** The medical team makes medical decisions.

---

## 1. Problem

On long missions the body adapts continuously: fluid shifts toward the head, the spine elongates (NASA: stature up to about 3%), muscle and bone are lost (bone 1 to 1.5% per month, NASA Gravity hazard), and the relaxed body in microgravity takes a **neutral body posture** that differs from standing on Earth. On Mars, a message to the flight surgeon takes up to 20 minutes one way. The crew needs a short, repeatable, **contactless** check that separates expected adaptation from a sustained change, tells when its own measurement is unreliable, and hands a structured report to the medical team.

## 2. Solution in one paragraph

LYRA is a stationary **touch mirror between three camera frames** (front, side, back). The crew member steps into the marked area; the mirror shows **contours for the feet, torso and palms**, and the cameras check pose and frame quality. LYRA then captures RGB video, **structured IR depth of the face** and a **3-view skeleton of the body**, filters motion, checks quality, and **AI modules** compare the result with the person's **own baseline** and the current **environment mode** (Earth, microgravity, partial gravity; rover or module context). The mirror shows one of three statuses: **Within baseline**, **Repeat measurement**, or **Refer to specialist**, with an explanation: which indicator changed, how reliable the signal is, and what to do. A low-quality capture gives **"Measurement not confirmed"**, never a made-up number. A report (time series, quality, environment mode, comparison with earlier scans) queues to the medical team on Earth.

## 3. Station

Drawings: `docs/drawings/01_general_view.svg`, `02_front_side_views.svg`.

| Element | Design (dimensions approximate) |
|---|---|
| Touch mirror | Display behind a mirror surface; shows foot, torso and palm contours, light cues, live mesh and skeleton, results. Touch passes commands to the UI; it does not measure physiology. |
| Palm zones | Standardize pose and body orientation for repeatable scans. Not a medical sensor. |
| Front frame | Face, chest, arms: RGB camera, IR camera, structured IR projector, illumination |
| Side frame | Profile: head and trunk tilt, chest position, spine curve |
| Back frame | Shoulders, scapulae, pelvis, visible back symmetry |
| Identification | 3D face recognition; fallback **NFC reader on the mirror frame** (card kept at the station) |
| Mounting | Frames attached to the module structure (ISS seat tracks), foot restraints for microgravity |
| Research option | **Vertical Doppler grips** in the side posts (section 6) |

## 4. Face: structured IR light to a mesh

Drawing: `docs/drawings/04_face_pipeline.svg`.

1. The IR projector sends an invisible pattern (dots, stripes or coded elements) onto the face.
2. The IR camera captures the pattern deformed by the nose, cheeks, forehead and lips.
3. Software matches projected elements with the image (correspondence).
4. Triangulation computes the distance to each surface region (camera-projector geometry).
5. The result is a depth map and a **point cloud**.
6. Surface reconstruction joins neighbouring points into triangles: a **mesh**.
7. The mesh is aligned with the RGB image.
8. On the next frames, vertex displacement describes expression.

**The projector does not build the mesh**; it provides the optical pattern used to measure shape. Software: **OpenCV** for calibration, pattern decoding and depth; **Open3D or PCL** for the point cloud and mesh. No need for 30,000 polygons: LYRA tracks stable **key regions** (eyes, brows, nose, cheeks, lips, chin) as a few dozen features; the dense mesh is a visual layer.

**RGB is a separate channel**: visible expression, skin color, head position, light conditions and **rPPG** (pulse from tiny changes in reflected light). IR is less dependent on color texture and part of ambient light, so RGB and IR do not duplicate each other. **RGB + IR + depth are fused** at the feature level after each channel passes its own quality check.

## 5. Body and posture in 3 planes

- **Skeletal keypoints** (head, shoulders, elbows, pelvis, knees, feet) from the 3 synchronized views, merged into one coordinate system. A full body mesh would need more cameras, compute and calibration; joint positions are enough for posture.
- Depth for the body: structured light is possible; **ToF is an alternative** for larger distance, motion and full coverage. An engineering choice to verify on a prototype.
- **Front:** shoulder height difference, pelvis position, lateral symmetry. **Side:** head and trunk tilt, chest position, spine curve. **Back:** scapulae, shoulder girdle, visible back symmetry. One view can hide a deviation (equal shoulders in front, trunk tilt in profile).

| Posture metric (key) | View | Meaning |
|---|---|---|
| `head_forward_deg` | side | Forward head tilt |
| `trunk_tilt_deg` | side | Trunk tilt |
| `shoulder_asym_deg` | front | Shoulder height difference |
| `pelvis_tilt_deg` | front | Pelvis tilt |
| `scapula_asym_mm` | back | Scapula / back asymmetry |
| `spine_length_mm` | side + back | Distance between spine keypoints (expected elongation in microgravity) |
| `pose_return_s` | all | Time to return to the usual pose |
| `back_pain_flag` | self-report | Back pain (combines with posture change) |

**Interpretation rules.** Two comparison levels: the **personal baseline** (pre-flight, updated in the mission) and the **environment mode** (Earth upright stance vs microgravity neutral body posture vs partial gravity). Flag only **sustained or repeated** changes, a growing deviation, or a change **combined with pain or fatigue**. If the person cannot reach the pose, that is stored as a measurement condition, not pathology. **The camera does not measure bone density, discs or muscle strength**; it sees external geometry and movement.

## 6. Optional contact research module: vertical Doppler grips

Drawing: `docs/drawings/03_doppler_cassette.svg`.

- Ultrasound Doppler transducers are built into the **vertical side posts as vertical grips**. Doppler is a contact device even when its housing is in a post, so this is an **optional research channel**, not part of the contactless core. Its metrics are shown separately and **excluded from the overall status**.
- **Solid hydrogel cassette (4 parts)** held on the transducer itself: **holder** fixed on the transducer body; **thin replaceable hydrogel pad**; **soft protective rim** limiting material displacement; **thin membrane** protecting the gel and keeping skin contact. The gel must fill the acoustic path; an air gap blocks ultrasound. A thin pad, not a thick block: a thick layer increases distance and deforms under pressure. **Thickness and press force are to be found experimentally on a ground mock-up.**
- **Workflow:** 1 pad into the holder on the transducer face; 2 check for bubbles and damage; 3 palm on the marked zone; 4 cassette gently pressed to the skin (not a standalone sensor); 5 pulses through the hydrogel; 6 receiver registers the echo; 7 software checks contact quality and signal stability; 8 if poor, reposition the hand or repeat.
- **Hackathon versions:** demo = mock cassette on the grip + on-screen signal path diagram; extended = real transducer only after a phantom or ground test bench.
- **Honest limits:** hydrogel acoustic coupling is published (e.g. MIT, Wang et al., *Science* 2022), but not for this cassette, transducer or palm contact. Behaviour in long storage, heating, reuse and microgravity is unverified. **LYRA does not claim heart, venous or cardiovascular-risk assessment through the palm.** Clinical accuracy requires comparison with standard ultrasound and controlled trials.

## 7. AI modules

Drawing: `docs/drawings/05_system_ai.svg`. AI is a set of separate modules, each testable on its own, not one model that "diagnoses".

| # | Module | Input → output |
|---|---|---|
| 1 | Camera / IR processing | Face detection and segmentation, IR point detection, rejection of points broken by motion or reflections, refinement over neighbouring frames → depth, point cloud, mesh |
| 2 | RGB + IR fusion | Color features (RGB), geometry features (IR depth), temporal features → expression movement vs lighting change; one channel covers when the other degrades |
| 3 | rPPG with quality | RGB (and near-IR) video → heart rate **plus** signal quality, usable duration, motion, light level, reject reason; poor quality → "Measurement not confirmed" |
| 4 | Body / posture | 3-view keypoints → skeleton in one coordinate system → posture features vs baseline and environment mode |
| 5 | Change classifier | All features + self-report → **Within baseline / Repeat measurement / Refer to specialist** with explanation |

**A human makes the medical decision.** The chain shown to judges: camera captures → algorithm builds geometry → models extract features → classifier rates the change → the medical specialist decides.

## 8. Data and provenance

Every result is labelled with its **provenance**: **team recording**, **open dataset (CameraVitals)**, **NASA material**, or **simulation**. The live web demo is **simulation** throughout.

| Data | Provenance | Role |
|---|---|---|
| **NASA OSDR OSD-575** (Inspiration4 Comprehensive Metabolic Panel; 4 crew, 19 analytes with units, pre-flight L-92/L-44/L-3 and post-flight R+1 to R+194) | NASA material | **The one concrete NASA dataset**: shows the personal-baseline logic on real crew data (pre-flight baseline vs R+1, with lab reference ranges). Details in `docs/research/nasa_sources.md` §6.1 |
| NASA Life Sciences Portal (LSDA) | NASA material | Human research in spaceflight and ground analogs since 1961: context, indicator choice |
| NASA Open Data Portal | NASA material | Catalog of NASA open datasets |
| NASA OSDR incl. Inspiration4 | NASA material | Visualizing spaceflight changes; **not** camera training data |
| NASA neutral body posture and anthropometry (HIDH, NASA-STD-3001 Vol. 2, NTRS studies), HRP hazards and risks | NASA material | Environment-mode rules, risk cards, expected adaptation corridors |
| CameraVitals (COHFACE): RGB video synced with cardiac and respiratory signals, 160 one-minute sequences, 40 participants | Open dataset | rPPG validation on Earth (not microgravity) |
| Team recordings on the mirror mock-up | Team recording | Mirror demo: rest, talking, head turn, exercise, recovery, lighting, distances; split by person |
| Simulated crew in the web app | Simulation | Live demo time series |

**No single NASA dataset contains IR face points, RGB video, 3D posture and medical references together.** LYRA is therefore a prototype that requires validation, and we never claim it is trained on NASA data.

## 9. Demo flow (2 to 3 minutes)

1. Position check: feet, torso and palms on the mirror contours; quality check.
2. Face: RGB, IR dots, depth map, point cloud, mesh.
3. Three posture views (front, side, back) and the skeleton.
4. Comparison with the previous measurement, personal baseline and environment mode.
5. One of three statuses + explanation (indicator, reliability, action); report queued to Earth with the communication delay (ISS under 1 s, Moon about 1 to 2 s, Mars 3 to 20 min one way).

## 10. Environments and scalability

| Environment | Gravity | Mode |
|---|---|---|
| ISS / Gateway | ~0 g | microgravity (neutral body posture reference) |
| Moon | 0.166 g | partial gravity |
| Mars base | 0.38 g | partial gravity, autonomous (long delay) |
| Rover / module | 0 or partial | same mirror logic, context noted in the report |
| Earth | 1 g | analogs (polar stations, bed rest), remote clinics, older adults |

## 11. What LYRA does not do

- Does not diagnose; it reports "change detected" or "measurement not confirmed".
- Does not measure bone density, intervertebral discs, muscle strength (camera), eye or intracranial pressure, or radiation (dosimeter values are imported).
- The palm zones are not a sensor; the Doppler grips are an unverified research option.
- rPPG accuracy depends on motion and light; CameraVitals is Earth data.
- All demo data are simulated; there are no real crew camera data.

## 12. Roadmap

1. Mirror mock-up with RGB + structured IR camera; team recordings; per-person train/test split.
2. rPPG validation on CameraVitals (COHFACE) and team recordings, with quality and reject reasons.
3. Posture baselines in analog settings (bed rest, parabolic flight) against NASA neutral body posture data.
4. Doppler research module: phantom and ground test bench, then comparison with standard ultrasound.
5. Integration with the flight surgeon's report format and onboard medical systems.
