# LYRA: NASA/CSA sources and how we use them

> Checked 2026-11-14 (Agent B). Machine-readable version: `data/nasa_reference.json` (36 sources; every number has `source_ids` and `basis`).
> Rule: we mark a number `cited` only if it appears directly in the source. Everything else is `estimated`, with an explanation in `note_ru`. LYRA is screening, not a diagnosis.

## 1. Challenge resources (Resources tab)

Page: https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/?tab=resources

The tab has **5 links**: 3 from NASA HRP and 2 from CSA. **There are no ready-made datasets there (OSDR, LSDA, tables, APIs).** These are overview texts, so "NASA data" in LYRA means published numbers, adaptation trajectories and the HRP risk taxonomy. From them we build the expected adaptation corridor, the risk map and the "why it matters" cards. A link to NASA open repositories (OSDR https://osdr.nasa.gov, LSDA https://nlsp.nasa.gov/explore/lsdahome) is on the roadmap: the LYRA export format can be aligned with Standard Measures. We do not use the data from these repositories themselves.

| id | Title | URL | What we took | Where in LYRA |
|---|---|---|---|---|
| hrp-hazards | 5 Hazards of Human Spaceflight | https://www.nasa.gov/hrp/hazards/ | 5 hazards; Mars on average 140 million miles, about 3 years, up to 2 years at 3/8 g | "Hazard" layer of the risk map |
| hrp-gravity | Hazard: Gravity Fields | https://www.nasa.gov/hrp/hazard-gravity-fields/ | Bone -1 to 1.5%/month; fluids toward the head → pressure on the eyes; kidney stones; 3 gravity fields | Adaptation corridor (face, legs, strength), risks bone_muscle and fluid_shift_eyes |
| hrp-distance | Hazard: Distance From Earth | https://www.nasa.gov/hrp/hazard-distance-from-earth/ | 140 million miles; communication delay **up to 20 min one way**; about 3 years | Transmission queue to the doctor, environment `mars` |
| hrp-isolation | Hazard: Isolation and Confinement | https://www.nasa.gov/hrp/hazard-isolation-and-confinement/ | "sleep loss, circadian desynchronization, and work overload"; NASA is developing methods for monitoring behavioral health | Sleep and fatigue metrics, self-report |
| hrp-hostile | Hazard: Hostile/Closed Environments | https://www.nasa.gov/hrp/hazard-hostile-closed-environments/ | Stress hormones, immune changes, microbe transfer, temperature/pressure/light/noise | Risk immune: temperature, symptoms |
| hrp-radiation | Hazard: Space Radiation | https://www.nasa.gov/hrp/hazard-space-radiation/ | Cancer, CNS, cognitive and motor function, behavior; NSRL (no mSv doses on the page) | Risk radiation_cancer, dose import |
| hrp-risks | Risks of Human Spaceflight | https://www.nasa.gov/hrp/risks/ | 17 HRP risks; SANS is a leading risk; viral reactivation | Risk names and descriptions on screen |
| hrp-ongoing | Ongoing HRP Research in Space | https://www.nasa.gov/hrp/ongoing-hrp-research/ | Catalog of studies (below) | Rationale for the choice of metrics |
| csa-radiation | Monitoring radiation for astronaut health (CSA, 2026-02-26) | https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp | Neutrons about 30% of total radiation on the ISS; CANS (Bubble Technology Industries, $5.5 million); bubble detectors; MOSFET, EVARM, Radi-N, Radi-N2 | `radiation.neutron_share_iss`; slide "LYRA is not a dosimeter: import" |
| csa-why | Why do we conduct science experiments in space? (CSA) | https://www.asc-csa.gc.ca/eng/iss/science/why-do-we-conduct-science-experiments-in-space.asp | Effects of microgravity resemble accelerated aging and a sedentary lifestyle; benefits on Earth | Scalability slide (Earth) |
| csa-why-infographic | Text version of the CSA infographic | https://www.asc-csa.gc.ca/eng/multimedia/search/image/8056 | Bone up to 1.5%/month (people over 50 on Earth about 1%/year); vessels stiffer and aging faster; insulin resistance; muscles; anemia and reduced white blood cells; radiation: cataracts, DNA, cancer | Risk cards, comparison with Earth |

## 2. Related HRP studies (Ongoing HRP Research)

| id | Study | URL | Summary | Link to LYRA metrics |
|---|---|---|---|---|
| hrp-thigh-cuff | Thigh Cuff | https://www.nasa.gov/reference/thigh-cuff/ | Thigh cuffs keep fluid in the legs to counter SANS; ultrasound of leg and neck veins; 2 sessions of 6 h | leg_volume_ml, periorbital_puffiness_mm, doppler_* |
| hrp-venous-haemostasis | Venous Haemostasis (NASA/ESA) | https://www.nasa.gov/reference/venous-haemostasis/ | Changes in venous blood flow and clot risk; jugular vein ultrasound, MRI, blood, blood pressure | doppler_*, flow_asymmetry_pct |
| hrp-spinal-health | Spinal Health | https://www.nasa.gov/missions/station/astronauts-spines-under-scrutiny/ | qCT and MRI of the spine of 9 astronauts (more than 6 months on the ISS) | height_cm, head_forward_deg, shoulder_asym_deg |
| hrp-standard-measures | Standard Measures | https://www.nasa.gov/reference/standard-measures/ | A common set: activity and light, sleep, cognition, sensorimotor, strength, blood, saliva | sleep_score, grip_*; the idea of a "standard daily set" |
| hrp-artemis2-standard-measures | Artemis II Standard Measures | https://www.nasa.gov/reference/artemis-ii-standard-measures/ | Standard set of Artemis II crew data in a shared data bank | Export format for the doctor (roadmap) |
| hrp-cipher | CIPHER | https://www.nasa.gov/reference/cipher/ | 14 studies: bone, muscle, heart/vessels, vision, brain; missions up to 1 year | grip_*, handgrip_*, doppler_* |
| hrp-brain-fluid-pressure | Brain Fluid Pressure | https://www.nasa.gov/reference/brain-fluid-pressure/ | Intracranial pressure ↔ eye/brain changes | periorbital_puffiness_mm (SANS risk) |
| hrp-spinal-fluid-biomarkers | Spinal Fluid Biomarkers | https://www.nasa.gov/reference/spinal-fluid-biomarkers/ | Markers in cerebrospinal fluid associated with SANS | Risk fluid_shift_eyes |
| hrp-b-complex | B-Complex | https://www.nasa.gov/reference/b-complex/ | Vitamin B against eye/brain changes | Risk fluid_shift_eyes |
| hrp-archer | ARCHeR | https://www.nasa.gov/reference/archer/ | Wellbeing, activity, sleep (actigraphy), crew interaction on Artemis II | facial_tension, sleep_score, wellbeing_score |
| hrp-immune-biomarkers | Immune Biomarkers | https://www.nasa.gov/reference/immune-biomarkers/ | Blood and saliva of the Artemis II crew, immunity | Risk immune |
| hrp-zero-t2 | Zero T2 | https://www.nasa.gov/reference/zero-t2/ | Exercise without a treadmill | grip_* (measures on Recheck) |
| hrp-tempus-pro | Tempus Pro | https://www.nasa.gov/reference/tempus-pro/ | Telemedicine device for remote assessment | Analog of the "data → doctor" flow |
| hrp-omics-archive | Omics Archive | https://www.nasa.gov/reference/omics-archive/ | Molecular changes over time | Risk immune (LYRA does not measure this) |
| hrp-space-radiation-element | HRP Space Radiation / NSRL | https://www.nasa.gov/hrp/radiation/ | NSRL (Brookhaven): ground experiments on radiation risks | Risk radiation_cancer |

## 3. Additional sources (numbers for the model)

| id | Source | URL | Number | basis |
|---|---|---|---|---|
| hrp-risk-bone | Risk of Spaceflight-Induced Bone Changes | https://www.nasa.gov/reference/risk-of-spaceflight-induced-bone-changes/ | Bone -1 to 1.5%/month (4-6 month missions); height **up to +3%** | cited |
| nasa-spinal-ultrasound | Spinal Ultrasound Investigation | https://www.nasa.gov/image-article/spinal-ultrasound-investigation/ | "grow up to three percent taller" | cited |
| skylab-anthropometry | Thornton et al., Skylab 4 (NTRS 19750006319) | https://ntrs.nasa.gov/citations/19750006319 | **More than 2 L** of fluid out of the lower legs and thighs by day 3; height increases | cited |
| nasa-bedrest-faq | Bedrest FAQs | https://www.nasa.gov/hrp/bedrest-faqs/ | "puffy-head, bird-legs" | qualitative |
| ntrs-iss-dose | Simonsen, ASCEND draft (NTRS 20250006168) | https://ntrs.nasa.gov/api/citations/20250006168/downloads/ASCEND%20Simonsen%20draft%201.pdf | ISS about 0.2-0.5 mSv/day, about 40-90 mSv over 6 months | range cited (found by search, PDF not rechecked manually); point value 0.35 estimated |
| nasa-std-3001-radiation | NASA-STD-3001 Radiation Protection Tech Brief | https://www.nasa.gov/wp-content/uploads/2023/03/radiation-protection-technical-brief-ochmo.pdf | Career limit 600 mSv | cited (from search) |
| nasa-mars-comm-delay | Mars Communications Disruption and Delay | https://www.nasa.gov/wp-content/uploads/2024/01/mars-communications-disruption-and-delay.pdf | Mars: from about 3 to more than 20 min one way | from search (PDF text not extracted) |
| nssdc-planet-ratio | NASA Planetary Fact Sheet (ratio) | https://nssdc.gsfc.nasa.gov/planetary/factsheet/planet_table_ratio.html | Gravity of the Moon 0.166, Mars 0.380 | cited (from search) |
| astrobee-picoflexx | Astrobee docs: PicoFlexx | https://nasa.github.io/astrobee/v/master/picoflexx_python.html | ToF cameras on the ISS (HazCam/PerchCam) | fact |
| mit-bioadhesive-ultrasound | Wang et al., Science 377:517 (2022); MIT News | https://news.mit.edu/2022/ultrasound-stickers-0728 | Solid hydrogel-elastomer, worn for 48 h or more | fact (not NASA, publisher="MIT") |

## 4. Facts: confirmed / not confirmed

**Confirmed by a source (cited):**
- Weight-bearing bones lose 1 to 1.5% of mineral density per month: NASA Gravity Fields and Risk of Bone Changes. CSA: "up to 1.5%/month" versus about 1%/year for people over 50 on Earth. *Another CSA page gives 1-2%/month; we do not use it.*
- Fluids shift toward the head, press on the eyes and can impair vision; kidney stones; three gravity fields: NASA Gravity Fields.
- Mars: 140 million miles on average, about 3 years, communication delay up to 20 min one way: NASA Distance From Earth and 5 Hazards.
- Isolation: "sleep loss, circadian desynchronization, and work overload"; development of methods for monitoring behavioral health.
- Hostile: increased stress hormones, immune changes, microbe transfer, temperature/pressure/light/noise.
- Radiation: cancer, CNS, cognitive and motor function, behavior; NSRL.
- HRP risks: all 7 risks from the screenshots are on /hrp/risks (17 in total there). SANS is a leading risk.
- Ongoing HRP: all 18 studies from the list are there, URLs above. *The list on the page is longer: Altered Immunity, Food Acceptability and Food Physiology.*
- CSA: neutrons are about 30% of total radiation **on the ISS**; CANS, Bubble Technology Industries, $5.5 million; bubble detectors, MOSFET, EVARM, Radi-N, Radi-N2.
- CSA infographic (text version): vessels stiffer and aging faster, insulin resistance, muscles, anemia and white blood cells, cataracts, DNA, cancer, accelerated aging, benefits on Earth.
- Height in microgravity **up to +3%** (standing): NASA.
- Skylab 4: more than 2 L of fluid leaves the legs by day 3.

**Not confirmed, or team estimate (estimated):**
- Magnitude and rate of facial puffiness (+4%, τ=3 days) and puffiness around the eyes (1 mm): NASA resources give only the mechanism.
- -8% lower leg volume: converted from "more than 2 L for both legs (lower leg + thigh)", τ=2 days.
- Grip strength -1%/month: NASA has no number for the hand (only "muscles lose strength").
- Body volume -0.5%/month.
- Height: the model uses a typical 2% (3% is the upper bound from NASA).
- ISS dose 0.35 mSv/day: midpoint of the 0.2-0.5 range (NASA, NTRS).
- Moon communication delay [1, 2] s: physically about 1.3 s; we did not find an exact NASA quote in the extracted text.
- Pulse, HRV, SpO₂, temperature, blinking, PERCLOS, yawning, facial expression, Doppler, handgrip test: NASA has no expected trajectories, so personal baseline only (`model: none`).
- "Spinal muscles -19%, hernia risk x4" (Spine, 2016): numbers only from secondary media, not added to the JSON.

## 5. Technical checks

**Height in microgravity.** NASA: "crew members grow up to three percent taller" (Spinal Ultrasound; Risk of Bone Changes). Example from NASA: Kate Rubins, 171 → 174.4 cm. An NTRS technical report on sitting height: up to 6% sitting and up to 3% standing, 2-4 cm standing (found by search). Height returns to normal after landing. **Conclusion:** the wording "up to 3%" is cited.

**ToF on the ISS (Astrobee).** NASA Astrobee documentation: HazCam and PerchCam are **pmd PicoFlexx** ToF depth cameras (point cloud + amplitude, factory calibration). Besides them there are NavCam and DockCam (color, fixed focus), SciCam (HD RGB) and SpeedCam. One media article calls HazCam "LIDAR", but the NASA documentation describes a PicoFlexx ToF. **Conclusion:** ToF sensors have already flown on the ISS. We **did not find** structured light (on the Face ID principle) on the ISS; it is our proposal, state this honestly.

**Solid hydrogel for ultrasound (MIT).** Wang C., Chen X., ..., Zhao X. "Bioadhesive ultrasound for long-term continuous imaging of diverse organs", *Science* 377(6605):517-523, 2022-07-29. It is a soft but tough hydrogel (chitosan + polyacrylamide, about 90% water) under an elastomer membrane that keeps it from drying out. The sticker is about 2 cm², about 3 mm thick, and was worn for 48 h or more by 15 volunteers. **Conclusion:** solid hydrogel as an acoustic medium without liquid gel is proven. **The hydrogel tape cassette in the handle is our design; no such device exists.**

## 6. Datasets
- The challenge page has **no datasets**, only 5 article resources (see §1).
- NASA open repositories that can be mentioned (not used in the demo): **OSDR** (Open Science Data Repository, includes GeneLab/ALSDA) https://osdr.nasa.gov and **LSDA** (Life Sciences Data Archive) https://nlsp.nasa.gov/explore/lsdahome. Standard Measures and Artemis II Standard Measures data are available on request through LSDA.
- In the LYRA simulation all trajectories come from `data/nasa_reference.json`. It contains no real individual astronaut data.
