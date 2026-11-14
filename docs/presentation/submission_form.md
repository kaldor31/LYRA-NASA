# LYRA — тексты для формы сдачи Space Apps 2026

> Форма и все связанные материалы — **только на английском**. Поля по Project Submission Guide: https://www.spaceappschallenge.org/resources/project-submission-guide/
> Перед вставкой: заменить `<…>` (ссылки, имена). Проверить ссылки в приватном окне браузера.

---

## Project Name
LYRA

## High-Level Project Summary
LYRA is a 90-second daily health scan for astronauts on long-duration missions, delivered as software with a station concept. The astronaut steps into a fold-out frame at the module wall: 3D cameras (structured light for the face, time-of-flight for the body) track facial swelling, leg volume, height and posture, and two smart grips read palm blood flow (ultrasound Doppler), pulse, HRV, SpO₂, skin temperature and grip strength — nothing to wear, no electrodes. LYRA's key idea is to compare each astronaut not only with their own baseline but with the adaptation NASA expects: published NASA/CSA findings (bone loss of 1–1.5% per month, headward fluid shift, >2 L leaving the legs by day 3, up to 3% height gain) form an "expected corridor", and LYRA flags when someone changes faster than expected. Every result is mapped to a NASA Human Research Program risk, explained in plain language with green/yellow/red guidance, and queued to the flight surgeon with ISS, Moon or Mars communication delay. LYRA is a screening tool, not a diagnosis.

## Link to Project Demo
<public link to the 7-slide deck (PDF / Google Slides) — docs/presentation/LYRA_deck.pptx>
*(Демо = колода 7 слайдов, включая титульный. Если делаем видео ≤ 30 с — ссылку на него в Detailed Description.)*

## Link to Final Project
<public GitHub repository / deployed web app link>

## Detailed Project Description
**What it does.** LYRA turns a short daily routine into a health trend for the crew and the flight surgeon. A daily express scan (~90 s): 20 s 3D scan of face and body → 30 s resting with hands on the grips → two maximal squeezes → 15 s voice check-in (sleep, wellbeing, symptoms). A weekly full test (~5 min) adds an isometric handgrip test played as a game ("keep it in the green zone", 2 min at 30% of max) plus 1 min of recovery, to see how pulse and blood flow respond.

**How it works.** Each metric (27 in total) is linked to a NASA HRP risk (bone & muscle loss, headward fluid shift/SANS, cardiovascular adaptations, immune changes, sleep, behavioral health, radiation) and to one of NASA's 5 Hazards of Human Spaceflight. For metrics where NASA publishes an adaptation trend, LYRA builds an expected corridor; the status answers "are you changing faster than NASA expects?". Elsewhere it uses the personal baseline. Green = short summary and a streak; yellow = one concrete onboard action and a re-scan reminder; red = step-by-step instructions and priority in the Earth link queue. Voice prompts guide every step; a training mode runs on first use; "why it matters" cards cite the NASA risk. All data are sent automatically to the flight surgeon via a store-and-forward queue that simulates ISS, lunar and Mars delays (up to 20 min one way). LYRA imports the station dosimeter dose; it does not measure radiation itself.

**Hardware concept (not built).** Mirror panel ~500×900 mm with a display, three thin posts mounted floor-to-ceiling on module rails (fold to the wall), sensor modules at head/torso/leg height, face recognition with an NFC card fallback. Grips use ultrasound gel; our proposed solid-hydrogel tape cassette (our design, inspired by MIT's bioadhesive ultrasound, Science 2022) advances a fresh patch each session, with a liquid-gel dispenser as backup. A compact folding kit targets ships and rovers. Five concept drawings are included (dimensions approximate).

**Benefits.** Fast, near-contactless, daily and self-guided; makes NASA research visible in every result; helps the crew act when Earth is far away. On Earth the same metrics fit polar stations, submarines, remote clinics and older adults (CSA: spaceflight effects resemble accelerated aging).

**Honest limits.** Screening, not diagnosis. LYRA does not measure bone density, eye pressure, vision, radiation or mental state. Most corridors are team estimates tagged "estimated" and must be calibrated on NASA data (LSDA/OSDR, Standard Measures); only numbers stated directly by NASA/CSA are tagged "cited". The demo runs on simulated astronauts.

**Tools.** <Агент A: язык/фреймворки веб-приложения — Python backend, Three.js 3D point cloud, Web Speech API, …>, SVG for drawings, PowerPoint deck. All references in `data/nasa_reference.json` (36 sources, each number tagged cited/estimated).

## Use of Super Intelligence (SI)
Yes. We used an AI coding/writing assistant (Claude, Anthropic, via Claude Code) to: speed up research (finding and reading NASA/CSA pages; every number was checked against the linked source and tagged "cited" or "estimated"), draft documentation and slide text, write the SVG concept drawings as code, and write parts of the web-app code and tests. The project idea, station concept and all design decisions were made by the team (recorded in docs/DECISIONS.md). AI-assisted drawings carry a visible "drawn with AI (SI) assistance" label on the slides; code and data files are acknowledged in the README and here. No NASA logos, flags or mission identifiers were generated or modified. No AI-generated images of people.

## NASA Data
- **NASA HRP — 5 Hazards of Human Spaceflight** (https://www.nasa.gov/hrp/hazards/) and the individual hazard pages: Gravity Fields (bone −1–1.5%/month, headward fluid shift, vision, three gravity fields), Distance from Earth (140 million miles, ~3 years, up to 20-min one-way delay), Isolation & Confinement, Hostile/Closed Environments, Space Radiation → hazard layer of our risk map, environment model, comm-delay queue.
- **NASA HRP — Risks of Human Spaceflight** (https://www.nasa.gov/hrp/risks/) → each metric maps to an HRP risk; "why it matters" cards.
- **NASA — Risk of Spaceflight-Induced Bone Changes; Spinal Ultrasound** (up to 3% taller) → bone/muscle and height corridors.
- **NASA Skylab 4 anthropometry (NTRS 19750006319)** (>2 L of fluid leaves the legs by day 3) → leg-volume corridor.
- **Ongoing HRP Research** (https://www.nasa.gov/hrp/ongoing-hrp-research/): Thigh Cuff, Venous Haemostasis, Spinal Health, Standard Measures, Artemis II Standard Measures, CIPHER, Brain Fluid Pressure, Spinal Fluid Biomarkers, ARCHeR, Immune Biomarkers, Zero T2, Tempus Pro, Omics Archive → justify metric choice, countermeasures and the doctor data flow.
- **NASA ISS dose data (NTRS), NASA-STD-3001 radiation brief, NASA Planetary Fact Sheet** → dose import model, lunar/Mars gravity.
- **NASA Astrobee documentation** (ToF cameras pmd PicoFlexx on ISS) → feasibility of ToF sensing in orbit.
Full list with URLs: `docs/research/nasa_sources.md`.

## Space Agency Partner Data and Other References
- **CSA — Monitoring radiation for astronaut health** (https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp): neutrons ≈30% of total ISS radiation; CANS neutron spectrometer → dosimeter import.
- **CSA — Why do we conduct science experiments in space?** and its infographic (https://www.asc-csa.gc.ca/eng/iss/science/why-do-we-conduct-science-experiments-in-space.asp, https://www.asc-csa.gc.ca/eng/multimedia/search/image/8056): bone up to 1.5%/month vs ~1%/year on Earth after 50; stiffer vessels; accelerated-aging analogy → Earth applications.
- **Wang C. et al., "Bioadhesive ultrasound for long-term continuous imaging of diverse organs", Science 377:517 (2022)**; MIT News (https://news.mit.edu/2022/ultrasound-stickers-0728) → solid hydrogel coupling.
- Software: <Агент A: библиотеки и лицензии — Three.js, MediaPipe, …>.
- No copyrighted images used; all drawings are our own.
