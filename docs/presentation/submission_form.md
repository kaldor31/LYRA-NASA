# LYRA: texts for the Space Apps 2026 submission form

> The form and all related materials must be in **English**. Fields follow the Project Submission Guide: https://www.spaceappschallenge.org/resources/project-submission-guide/
> Before pasting: replace the `<...>` placeholders (links). Check every link in a private browser window.
> Team: **Alina Dmitriyeva, Daniil Shabalin**. Source of truth for the concept: `docs/research/LYRA_concept_paper_ru.pdf` (summarized in `docs/DECISIONS.md`).

---

## Project Name
LYRA

## High-Level Project Summary
LYRA (Life-signs & Yield-based Readiness Analytics, also "Lunar-to-orbit Your Readiness Assessment") is a touch mirror for contactless crew readiness checks on space missions, delivered as software with a hardware concept. The crew member stands between three camera pillars (two in front, one behind) facing the mirror; the mirror shows contours for the feet, torso and palms so every scan uses the same pose. Structured infrared light builds a 3D face mesh, an RGB camera reads expression and pulse (rPPG), and three synced views build a body skeleton for posture in three planes. Separate AI modules check signal quality, compare each person with their own baseline and the current environment (Earth, microgravity, partial gravity), and return one of three statuses: Within baseline, Repeat measurement, or Refer to specialist, each with the indicator that changed, how reliable it is and what to do. When the signal is poor LYRA says "Measurement not confirmed" instead of guessing. Reports queue to the medical team with ISS, Moon or Mars delay. LYRA detects change; the medical team decides.

## Link to Project Demo
<public link to the 7-slide deck (PDF or Google Slides) from docs/presentation/LYRA_deck.pptx>
*(Demo = 7-slide deck including the title slide. If we make a video of 30 s or less, put its link in the Detailed Description.)*

## Link to Final Project
<public GitHub repository / deployed web app link>

## Detailed Project Description
**What it does.** LYRA turns a short, repeatable check at a touch mirror into a readiness trend for the crew and the medical team. Demo flow (2 to 3 minutes): position check (feet, torso and palms on the mirror contours; cameras check pose, light and stillness) → face (RGB, infrared dots, depth map, point cloud, mesh) → three synced pillar views (two front, one back) → comparison with the previous measurement, the personal baseline and the environment mode → one of three statuses with an explanation → report queued to Earth.

**How it works.**
- *Face:* an infrared projector casts an invisible dot pattern; an infrared camera captures it deformed by the face; software finds correspondences, triangulates depth, builds a point cloud and reconstructs a triangle mesh (OpenCV for calibration and depth; Open3D or PCL for the cloud and mesh). The projector does not build the mesh. We track key regions (eyes, brows, nose, cheeks, lips, chin), not 30,000 polygons. The RGB camera is a separate channel for expression, skin tone, head position and rPPG pulse; RGB, infrared and depth are fused.
- *Body:* skeletal keypoints (head, shoulders, elbows, pelvis, knees, feet) from three synced camera pillars (two in front at ±60°, one behind; RGB + IR depth modules at head, torso and leg height) merged in one coordinate system: shoulder and pelvis symmetry, head and trunk tilt, scapulae and spine symmetry. The crew member does not turn; all views are captured at once.
- *AI modules (each testable on its own):* (1) camera and infrared processing, (2) RGB + infrared fusion, (3) rPPG with quality outputs (signal quality, usable duration, motion, light, reject reason), (4) body and posture, (5) a change classifier with three statuses. The microgravity neutral body posture differs from Earth's, so posture is compared with the person's baseline and the environment mode, and only sustained or repeated change, or change combined with pain or fatigue, is escalated. A human makes every medical decision.
- *Provenance:* every result is tagged team recording, open dataset (CameraVitals), NASA material, or simulation. The web app runs on simulated crew data.

**Tested live (feasibility).** The face channel already runs on real hardware: an iPhone TrueDepth camera (the IR dot projector + IR camera behind Face ID, the same principle as the LYRA mirror face module) streams RGB + measured depth over USB (Record3D app) into our Python pipeline. Face landmarks are lifted to 3D with the IR depth, giving face width, nose depth and interpupillary distance in millimetres (a team member measured 62 mm, a typical adult value) and the distance to the camera; the same page shows camera pulse (rPPG) with a quality score, the quality gate (face visible, facing the mirror, light, holding still), and a 15 s baseline scan followed by compare scans that return the LYRA statuses or "Measurement not confirmed" with the reason. Frames are processed locally and never stored. An iPhone rear camera via macOS Continuity Camera can serve as a body pillar.

**3D model.** The v3 station is modelled in Blender (touch mirror with the face module, two front pillars and one back pillar with camera modules, bolted bases), with glTF exports and renders in the repository (`docs/model/`).

**Optional research module.** Ultrasound Doppler transducers in vertical grips on the mirror stand legs, coupled to the palm by a solid hydrogel cassette with four parts (holder on the transducer, thin replaceable pad, soft rim, membrane). It is a contact research channel, not part of the contactless core, and its values never set the overall status. Hackathon demo: a mock cassette and a signal path diagram; a real transducer only after a phantom or ground test bench. We make no heart, vein or cardiovascular claims through the palm.

**Benefits.** Short, self-guided and contactless; knows when its own measurement is unreliable; separates expected space adaptation from sustained change; gives the crew a clear next step when Earth is minutes away. On Earth it fits analog stations, remote clinics and older adults.

**Honest limits.** LYRA detects change; it does not diagnose. The camera does not measure bone density, discs or muscle strength. No single NASA dataset contains infrared face points, RGB video, 3D posture and medical references, so LYRA is a prototype that needs validation. CameraVitals is Earth data, not microgravity. The web app's crew data are simulated; the live feasibility test is a short team self-test, not a validation study. Five concept drawings (SVG, PNG, PDF) and a 3D model are included (dimensions approximate).

**Tools.** Web app: Python 3.12, FastAPI, Uvicorn, Pydantic, NumPy, SciPy, vanilla JavaScript, Three.js 0.160.0 (3D body point cloud), Web Speech API (voice prompts), pytest. Feasibility module: OpenCV, MediaPipe 0.10.14 (Face Mesh, Pose), rPPG (POS method), iPhone TrueDepth via the Record3D app and its `record3d` Python library, pyserial, ESP32. Drawings: SVG generated by Python, exported to PNG and PDF. 3D model: Blender, glTF. Deck: pptxgenjs. References: `data/nasa_reference.json` (47 sources, every number tagged cited or estimated).

## Use of Super Intelligence (SI)
Yes. An AI assistant (Claude, Anthropic, via Claude Code) helped under the team's direction with code (parts of the web app and tests), documentation and slide text, the SVG concept drawings (written as code), the Blender 3D model and its renders (built by scripting Blender), and research (finding and reading NASA and partner pages; every number was checked against the linked source and tagged "cited" or "estimated"). The idea and the concept are the team's own (team concept paper; decisions in `docs/DECISIONS.md`). AI-assisted drawings carry a visible "AI (SI) assisted drawing" label; app screenshots are labelled as AI (SI) assisted code with simulated data. No NASA logos, flags or mission identifiers were generated or modified. No AI-generated images of people.

## NASA Data
- **NASA OSDR, OSD-575: SpaceX Inspiration4 Blood Serum Metabolic Panel** (https://osdr.nasa.gov/bio/repo/data/studies/OSD-575). Our one concrete NASA dataset. File `LSDS-8_Comprehensive_Metabolic_Panel_CMP.upload_SUBMITTED.csv`: variables ANALYTE, VALUE, RANGE_MIN, RANGE_MAX, UNITS, SUBJECT_ID, SEX, timepoint; 4 crew, 19 analytes (mg/dL, mmol/L, g/dL, U/L), pre-flight L-92, L-44, L-3 and post-flight R+1 to R+194. Role: shows LYRA's personal-baseline logic on real crew data (for example serum sodium, pre-flight mean vs R+1, inside the lab range yet below the person's own baseline). Not used for camera training.
- **NASA Life Sciences Portal / Life Sciences Data Archive** (https://nlsp.nasa.gov/): human research in spaceflight and ground analogs since 1961; context and choice of indicators.
- **NASA Open Data Portal** (https://data.nasa.gov/): catalog of NASA open datasets.
- **NASA OSDR and the Inspiration4 datasets** (https://osdr.nasa.gov/bio/, https://www.nasa.gov/osdr-latest-news-i4-mission-datasets/): visualizing spaceflight changes.
- **NASA neutral body posture and anthropometry:** Human Integration Design Handbook (https://www.nasa.gov/organizations/ochmo/human-integration-design-handbook/), NASA-STD-3001 Vol. 2 (https://www.nasa.gov/reference/nasa-std-3001v2/), NTRS 20150020939 (in-flight anthropometry and neutral body posture; stature up to about 3%), NTRS 20040200967 (neutral body posture on STS-57) → environment mode and posture rules.
- **NASA HRP: 5 Hazards of Human Spaceflight and Risks of Human Spaceflight** (https://www.nasa.gov/hrp/hazards/, https://www.nasa.gov/hrp/risks/), Gravity Fields (bone 1 to 1.5% per month), Distance from Earth (up to 20 min one-way delay), Skylab 4 anthropometry (more than 2 L of fluid leaves the legs by day 3), Ongoing HRP Research (Spinal Health, Standard Measures, Thigh Cuff, CIPHER, Tempus Pro and others) → risk cards, expected-adaptation corridors, comm-delay queue.
Full list with URLs: `docs/research/nasa_sources.md`.

## Space Agency Partner Data and Other References
- **CSA, Why do we conduct science experiments in space?** (https://www.asc-csa.gc.ca/eng/iss/science/why-do-we-conduct-science-experiments-in-space.asp): spaceflight effects resemble accelerated aging → Earth applications.
- **CSA, Monitoring radiation for astronaut health** (https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp): LYRA imports the station dosimeter value and does not measure radiation.
- **CameraVitals (COHFACE)**: RGB video synchronized with cardiac (PPG) and respiratory signals, 160 one-minute sequences from 40 participants (https://cameravitals.github.io/datasets.html, https://www.idiap.ch/en/scientific-research/data/cohface; Heusch, Anjos, Marcel, 2016) → rPPG validation on Earth.
- **Wang C. et al., "Bioadhesive ultrasound for long-term continuous imaging of diverse organs", Science 377:517 (2022)** (https://news.mit.edu/2022/ultrasound-stickers-0728) → solid hydrogel acoustic coupling principle for the research module.
- Software: FastAPI, Uvicorn, Pydantic, NumPy, SciPy, Three.js, pytest, OpenCV, MediaPipe, pyserial, pptxgenjs (open-source licences).
- **Record3D** iOS app (Marek Šimoník) and its open-source `record3d` library: streams iPhone TrueDepth RGB + depth for the live feasibility test.
- No copyrighted images used; all drawings, the 3D model and its renders are our own (AI (SI) assisted, labelled).
