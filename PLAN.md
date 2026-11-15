# LYRA: plan for NASA Space Apps Challenge 2026 (hackathon in progress)

> **LYRA: Life-signs & Yield-based Readiness Analytics** (Lunar-to-orbit Your Readiness Assessment). "Step in. Scan. Know."
> Team: Alina Dmitriyeva, Daniil Shabalin. Concept source of truth: `docs/research/LYRA_concept_paper_ru.pdf` → `docs/DECISIONS.md` (v2, 2026-11-15).
> Challenge: **Create Health Monitoring Software for Astronauts on Space Missions**: https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/
> Source of decisions: `docs/DECISIONS.md`. Concept: `docs/CONCEPT.md`. NASA data: `data/nasa_reference.json`, `docs/research/nasa_sources.md`.

## 0. Scope (from DECISIONS)

- We are building a **concept**: drawings + presentation + a **web app running on simulation**. No hardware.
- Judging focuses first of all on **software**. Criteria: Impact, Creativity, Validity, Relevance (NASA data), Presentation.
- Everywhere: LYRA "detects change", never "diagnoses"; the medical team decides.
- Core is contactless (touch mirror + 3 camera frames); the vertical Doppler grips are an optional research module.
- All materials, UI and docs are in English (official Space Apps rule).

## 1. Submission deadlines (official)

Source: Project Submission Guide (as of 2026-11-13): https://www.spaceappschallenge.org/resources/project-submission-guide/

- Submission opens: **Sat, November 14, 9:00** team Local Event time.
- **Deadline: Sun, November 15, 23:59** Local Event time (for the Universal Event, the Team Owner's local time of residence). Anything saved/submitted after the deadline is **not judged**.
- You can resubmit as many times as you like; the **last saved** version is judged. Judges look mainly at the **project page**; the demo mostly affects Presentation.

## 2. Remaining time (as of Sun 15 Nov, 02:30 local; deadline 23:59 = about 21.5 h left)

**Done (concept agent, 15 Nov night):** DECISIONS v2 and CONCEPT v2 aligned with the paper; `data/nasa_reference.json` v2 (posture metrics, 11 new sources, research-module notes); one NASA dataset chosen and verified (OSDR OSD-575); 5 new drawings + PNGs; 7-slide deck rebuilt with app screenshots; form texts and video script in English.

| Window (local) | Who | What is left |
|---|---|---|
| 02:30 to 09:00 | Team | Sleep. |
| 09:00 to 11:00 | Alina | Read DECISIONS v2, CONCEPT v2 and the deck; mark wording changes. Check the 5 drawings against the paper. |
| 09:00 to 12:00 | Daniil | Deploy the web app (public link), check it in a private window; README in English; final screenshots if the UI changes (then rebuild the deck: `node docs/presentation/_src/build_deck.js`). |
| 11:00 to 13:00 | Both | Export the deck to PDF (Keynote or PowerPoint: File, Export, PDF) and upload with a public link (Google Drive / GitHub). Check: 7 slides, names on slide 1, "AI (SI) assisted" labels visible. |
| 13:00 to 16:00 | Both (optional) | 30 s video per `docs/presentation/video_script.md`, English subtitles, length 30.0 s or less. Skip if short on time: the deck is the demo. |
| 16:00 to 19:00 | Both | Fill the project page from `docs/presentation/submission_form.md` (replace the `<...>` links), upload the drawing PNGs from `docs/drawings/png/`. |
| 19:00 to 20:00 | Both | Run-through; final checklist below; **Submit for Judging**; screenshot the confirmation banner. |
| 20:00 to 23:59 | Buffer | Do not touch unless needed; resubmit after any edit (the last saved version is judged). |

## 3. Submission checklist (exactly per Project Submission Guide 2026)

Source: https://www.spaceappschallenge.org/resources/project-submission-guide/ · criteria: 2026 Judging & Awards Guide: https://www.spaceappschallenge.org/resources/judging-awards-guide/

**General**
- [ ] All members are confirmed participants of **the same Local Event**.
- [ ] **All form content and all related materials are in English.** Slides in English only. The video may be voiced in another language, but **English subtitles are required**.
- [ ] **All required fields** are filled in (otherwise the button will not work).
- [ ] No images/video/audio of people **under 18**.
- [ ] "Terms and Conditions" and "Confirm All Work is Original" checked → **Submit for Judging** → confirmation banner.

**Form fields** (ready texts: `docs/presentation/submission_form.md`)
- [ ] Project Name
- [ ] High-Level Project Summary (what we built, how it addresses the challenge, why it matters)
- [ ] Link to Project Demo: **7 slides maximum (including the title and intro slides) OR a video of 30 s or less**. Exceeding this → **not eligible for Global Judging**. External hosting (YouTube, Google Drive, GitHub, ...), **public link with no login/password/permissions**; video/slides are not uploaded to the Space Apps site.
- [ ] Link to Final Project: public link (website / repository), check in a private window.
- [ ] Detailed Project Description (what it does, how it works, benefits, goals, tools/languages/hardware/software).
- [ ] **Use of Super Intelligence (SI)**: this is what the site calls AI (ML, chatbots, image generation, LLMs). Allowed as a tool; state where and how. Rules: SI images and video need a **visible watermark**; audio, code and data must be **disclosed in the description and metadata**. Generated content **must not use/modify NASA branding** (logos, flags, mission identifiers). Judges do not see the answer to this question, but they do see the labels in the project. The page also says SI must not be used to come up with the solution idea itself.
- [ ] **NASA Data**: specifically which NASA data and resources. **A Global Award requires at least one NASA resource.**
- [ ] Space Agency Partner Data and Other References: all data, resources, tools, code, texts, images (for us: CSA, a 2026 partner).
- [ ] Images on the page: JPG/PNG/GIF up to 10 MB (drawings → PNG, see `docs/drawings/png/`).

**Demo (if a deck)**: team, member names, chosen challenge; project image; user experience; how NASA/partner data make the solution possible.
**Demo (if a video, 30 s or less)**: 0:00 who you are → 0:02 the challenge → 0:05 name and tagline → 0:10 the idea, how it works, NASA data → 0:20-0:30 the future.

**Team decision:** we submit a **7-slide deck** as the Project Demo (`docs/presentation/LYRA_deck.pptx` → PDF/Google Slides, public link); a 30 s video if possible, with its link in the Detailed Description.

## 4. Where things are

| What | File |
|---|---|
| Decisions | `docs/DECISIONS.md` |
| Concept | `docs/CONCEPT.md` |
| NASA/CSA sources | `docs/research/nasa_sources.md`, `data/nasa_reference.json` |
| Drawings (5 sheets) | `docs/drawings/01_general_view`, `02_front_side_views`, `03_doppler_cassette`, `04_face_pipeline`, `05_system_ai` (.svg); PNG in `docs/drawings/png/`; rebuild: `python3 docs/drawings/_src/gen_drawings.py && python3 docs/drawings/_src/render_png.py`; v1 sheets and the Russian set in `docs/drawings/archive/v1/` |
| Presentation, video, form | `docs/presentation/` (deck: `node docs/presentation/_src/build_deck.js`, one-time `npm install` in `_src`) |
| Concept paper (Russian, source of truth) | `docs/research/LYRA_concept_paper_ru.pdf` |
| Software | `lyra/`, `tests/`, `README.md` (Agent A) |

## 5. Wording rules

| Do not write | Write instead |
|---|---|
| "diagnoses" | "detects change; Within baseline / Repeat measurement / Refer to specialist" |
| "measures bone density" | "the camera sees external geometry and movement, not bone, discs or muscle strength" |
| "measures the heart through the palm" | "optional Doppler research module; unverified until a phantom / ground test" |
| "trained on NASA data" | "NASA data give space context; CameraVitals validates rPPG; team recordings show the mirror" |
| "determines mental state" | "likely signs of fatigue and strain" |
| "medical device" | "prototype that needs validation; the medical team decides" |
| an estimate presented as a citation | `cited` only if the number is directly in the source, otherwise "team estimate" |
