# LYRA: concept specification

> "LYRA: 3D health scan for long-duration missions" · "Step in. Grip. Know."
> Status: concept for NASA Space Apps 2026 (challenge "Create Health Monitoring Software for Astronauts on Space Missions"). There is no hardware; the software runs on simulation. Source of decisions: `docs/DECISIONS.md`; numbers and links: `data/nasa_reference.json` and `docs/research/nasa_sources.md`.
> **LYRA is a screening and self-monitoring system. The result is not a diagnosis.** Health decisions are made by the flight surgeon.

---

## 1. Problem

On a long mission (ISS 6 months, Moon, Mars about 3 years) the body changes continuously: bone loses **1 to 1.5% of mineral density per month** (NASA, Gravity Fields), fluids shift toward the head (facial puffiness, pressure on the eyes, the leading SANS risk), legs lose volume ("bird legs": more than 2 L of fluid leaves the legs by day 3, Skylab 4), and blood vessels "age" faster (CSA). On Mars, communication with a doctor takes **up to 20 min one way** (NASA, Distance From Earth), so the crew must notice deviations on its own.

Today many things are measured episodically, with heavy equipment and with an operator involved. What is needed is **daily, fast, (almost) contactless screening** that understands **which changes are expected** and which are not.

## 2. The solution in one paragraph

LYRA is a "smart frame" by the module wall: a mirror panel with a display and three slim posts with 3D cameras. The astronaut steps in, stands in front of the mirror for 20 s (3D scan of face and body), holds two handles for 30 s (ultrasound Doppler, PPG/SpO₂, temperature, grip strength), and in **about 90 s** gets a color-coded status and an instruction. The core idea: status = **"are you changing faster than NASA expects"**. The personal trajectory is compared with a corridor of expected adaptation built from published NASA/CSA data. All data automatically go to the flight surgeon through a queue that accounts for communication delay.

## 3. Station (hardware, concept)

See drawings: `docs/drawings/01_general_view.svg`, `02_front_side_fov.svg`.

| Element | Design (dimensions approximate) |
|---|---|
| Front | Mirror panel about 500 x 900 mm, display behind it (head + torso) |
| Posts | 3 posts, profile about 40 x 40 mm: 2 front posts at the sides + 1 rear post, giving a 360° view |
| Mounting | Floor to ceiling about 2 m, attached to the module structure (on the ISS, the standard mounting rails), **no legs**; they fold on hinges against the wall |
| Working area | About 1.2 x 1.2 m; foot restraints (microgravity) |
| Modules | On each post, at three heights (head, torso, legs) |
| Handles | Left/right on the front posts at elbow height |
| Identification | 3D face recognition; if uncertain, an NFC card (kept at the station). **Voice is not used for identification.** The face reference updates slowly (the face changes from puffiness in the first days) |
| Principle | **Nothing is worn on the body, no electrodes** (no ECG; HRV from PPG/Doppler) |

### 3.1 Sensors: hybrid

- **Face: structured light** (IR dot projector + IR camera, the Face ID principle): facial puffiness means changes of a few mm at about 0.5 m.
- **Body: ToF cameras**: at 1-2 m, ToF accuracy is nearly constant. ToF has already flown on the ISS: the HazCam/PerchCam cameras of the **Astrobee** robot are pmd PicoFlexx ToF sensors (NASA Astrobee docs). We did not find structured light on the ISS; this is our proposal.
- **RGB cameras**: pulse from video (rPPG), skin color.
- Dot projectors fire **in turn** (patterns do not overlap); ToF cameras use **different modulation frequencies** (see `04_system_diagram.svg`, timing diagram).

| Parameter | Structured light (face) | ToF (body) |
|---|---|---|
| Accuracy at close range (0.3-0.6 m) | High, sub-mm to mm | Lower, about mm to cm, depth noise |
| Accuracy at distance (1-2 m) | Drops roughly quadratically with distance | Nearly constant |
| Resolution | High (dense dot pattern) | Lower (typically about 0.04-0.3 Mpx) |
| Baseline (projector to camera) | Required, sets accuracy | Not required, compact module |
| Calibration drift from launch vibration | Sensitive (baseline geometry), so self-calibration against a reference target on the station | Less sensitive |
| Multipath errors | Few | Present (corners, shiny module surfaces) |
| Mutual interference | Patterns overlap, so sensors fire in turn | Different modulation frequencies |
| Role in LYRA | Face volume, puffiness around the eyes, identification | Leg volume/girth, body volume, height, posture |

*Numbers in the table are typical characteristics of the sensor classes (team estimate), not LYRA measurements.*

## 4. Handles and gel

See `docs/drawings/03_handle_section.svg`.

- **Ultrasound Doppler** at the palmar arteries: blood flow velocity, pulse waveform shape, L/R asymmetry.
- **PPG + SpO₂** under the finger; **palm temperature**; **load cell** (grip strength); **NFC**.
- **Gel is required**: ultrasound does not pass through air.
  - **Primary option: a cassette with a tape of solid hydrogel**: a fresh section is advanced before every session (like tape in a cartridge). **This is our design**: hydrogel pads for ultrasound and tape-advance mechanisms exist, but such a cassette does not. Material rationale: MIT, Wang et al., *Science* 377:517 (2022): a solid hydrogel under an elastomer provides ultrasound contact without liquid gel for 48 h or more.
  - **Backup option: a liquid gel dispenser** in the same handle (reservoir + micropump; in microgravity the liquid is held by surface tension, but the risk of droplets is higher, hence backup only).

## 5. Session

| Mode | Duration | Steps |
|---|---|---|
| Daily express scan | About 90 s | Step in and identification → 20 s 3D scan of face and body → 30 s at rest with hands on the handles (blood flow, pulse, SpO₂, temperature) → 2 short maximal squeezes → 15 s voice check-in (sleep, wellbeing, symptoms) → result |
| Weekly full test | About 5 min | All of the above + an isometric handgrip test: 2 min holding 30% of maximum ("keep it in the green zone" gamification) + 1 min recovery → pulse and blood flow response |
| Unscheduled | On request | At will or after Recheck/Deviation |

Instructions always include: voice prompts at every step, a screen with a short caption and animation, a **training mode** on first launch (nothing recorded), **"why it matters" cards** (2-3 sentences + the NASA risk), and voice commands "start", "repeat", "stop".

## 6. Metrics ↔ HRP risks ↔ hazards

The full machine-readable version is `data/nasa_reference.json` (metric keys are canonical).

| Metric (key) | HRP risk | Hazard (5 Hazards) | NASA expectation / model |
|---|---|---|---|
| Face volume `face_volume_ml`, puffiness around the eyes `periorbital_puffiness_mm` | Fluid shift, SANS (`fluid_shift_eyes`) | Gravity | Saturates over days (mechanism cited; magnitude estimated) |
| Lower leg volume `leg_volume_ml` | `fluid_shift_eyes`, `bone_muscle` | Gravity | Fast drop to a plateau (Skylab: more than 2 L out of the legs by day 3, cited; -8% is our conversion) |
| Height `height_cm` | `bone_muscle` | Gravity | Up to +3% (NASA, cited); 2% in the model |
| Body volume `body_volume_l` | `bone_muscle` | Gravity | Estimated; indirect substitute for a scale |
| Posture `head_forward_deg`, `shoulder_asym_deg` | `bone_muscle` (spine, Spinal Health) | Gravity | Personal baseline |
| Grip strength `grip_left_kg`, `grip_right_kg` | `bone_muscle` | Gravity | Estimated -1%/month; bone -1 to 1.5%/month is cited context |
| Blood flow `doppler_flow_*`, asymmetry `flow_asymmetry_pct` | `cardiovascular` (Venous Haemostasis, Thigh Cuff) | Gravity, Radiation | Personal baseline |
| Pulse `hr_rppg`, `hr_palm`, HRV `hrv_rmssd_ms`, test `handgrip_*` | `cardiovascular`, `behavioral` | Gravity, Isolation | Personal baseline |
| SpO₂ `spo2`, temperature `skin_temp`, symptoms `symptoms_flag` | `immune` | Hostile/Closed | Personal baseline |
| Blinking, PERCLOS, yawning, sleep `sleep_score` | `sleep` | Isolation | Personal baseline |
| Facial expression `facial_tension` ("likely signs of strain"), wellbeing | `behavioral` | Isolation, Distance | Personal baseline |
| Dose `radiation_dose_msv` (imported from the station dosimeter) | `radiation_cancer` | Radiation | ISS about 0.2-0.5 mSv/day (NASA NTRS), 0.35 in the model |

**Status:** Normal: within the expected adaptation corridor and within the personal baseline → brief summary + day streak. Recheck: outside the corridor or a jump → a specific onboard measure + repeat tomorrow. Deviation: strong deviation or several signals → step-by-step "what to do now" instruction and priority in the queue to the doctor. Remeasure: the scan could not be completed reliably → repeat the measurement.

## 7. Data flow to the doctor

See `docs/drawings/04_system_diagram.svg`.

Sensors → onboard computer (identification → 3D reconstruction and metrics → expected adaptation model → status and instruction → local storage) → screen/voice to the astronaut **and** a store-and-forward queue → flight surgeon on Earth. Delay: ISS seconds, Moon about 1-2 s, Mars up to 20 min one way; Deviation results go first. Data from the station dosimeter (on the ISS, for example CSA CANS, a neutron spectrometer; neutrons are about 30% of the dose on the ISS) are imported; LYRA **does not measure** radiation. The NASA analog of this flow is Tempus Pro (telemedicine); the export format follows the Standard Measures model (roadmap).

## 8. Environments and scalability

| Environment | Gravity | Delay (one way) | Configuration |
|---|---|---|---|
| ISS | ~0 g | Seconds | Full station |
| Gateway / Moon | 0.166 g | About 1-2 s | Full station |
| Mars (base) | 0.38 g | Up to 20 min | Full station, autonomous mode |
| Spacecraft / rover | 0 / partial | Any | **Compact folding** (`05_compact_config.svg`) |
| Earth | 1 g | n/a | Polar stations, submarines, remote hospitals, older adults |

CSA: the effects of microgravity resemble accelerated aging and a sedentary lifestyle (bone, vessels, muscles, insulin resistance), so the same metrics are useful on Earth (osteoporosis, balance in older adults, cardiovascular disease, type 2 diabetes).

## 9. Limitations and "what LYRA does not measure"

- **Not a diagnosis.** Screening and trends for the doctor.
- **Does not measure bone density**: only functional markers (grip strength, posture, leg volume).
- **Does not measure intraocular/intracranial pressure or vision**: facial puffiness is only an indirect marker of fluid shift (SANS requires OCT/ophthalmoscopy).
- **Does not measure radiation**: dosimeter data are imported. No ECG, no blood/saliva tests or omics (that is Immune Biomarkers, Omics Archive).
- **Does not determine mental state**: only "likely signs of fatigue/strain" + self-report.
- Most corridors are **team estimates** (`basis: estimated`): NASA provides mechanisms and some individual numbers (bone, height, Skylab), but not trajectories for every metric. Calibration on real data (LSDA/OSDR, Standard Measures) is on the roadmap.
- The hydrogel cassette and the whole station are a **concept**; the accuracy of 3D volume in microgravity (pose, floating hair/clothing) has not been verified; calibration drift after launch.
- The demo runs on **simulated** astronauts; there are no real crew data.

## 10. Roadmap

1. Calibrate the corridors on open NASA data (LSDA, OSDR, Standard Measures).
2. Analog environments: bed rest (NASA bedrest, "puffy-head, bird-legs"), HERA/polar stations.
3. Handle prototype (hydrogel cassette) and a ToF + structured light test rig; testing on parabolic flights.
4. Integration with onboard medical systems and the doctor's format; a multi-person crew.
