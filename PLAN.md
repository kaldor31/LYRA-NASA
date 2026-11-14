# LYRA: plan for NASA Space Apps Challenge 2026 (hackathon in progress)

> **LYRA: 3D health scan for long-duration missions.** "Step in. Grip. Know."
> Challenge: **Create Health Monitoring Software for Astronauts on Space Missions**: https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/
> Source of decisions: `docs/DECISIONS.md`. Concept: `docs/CONCEPT.md`. NASA data: `data/nasa_reference.json`, `docs/research/nasa_sources.md`.

## 0. Scope (from DECISIONS)

- We are building a **concept**: drawings + presentation + a **web app running on simulation**. No hardware.
- Judging focuses first of all on **software**. Criteria: Impact, Creativity, Validity, Relevance (NASA data), Presentation.
- Everywhere: "screening, not a diagnosis".
- All materials, UI and docs are in English (official Space Apps rule).

## 1. Submission deadlines (official)

Source: Project Submission Guide (as of 2026-11-13): https://www.spaceappschallenge.org/resources/project-submission-guide/

- Submission opens: **Sat, November 14, 9:00** team Local Event time.
- **Deadline: Sun, November 15, 23:59** Local Event time (for the Universal Event, the Team Owner's local time of residence). Anything saved/submitted after the deadline is **not judged**.
- You can resubmit as many times as you like; the **last saved** version is judged. Judges look mainly at the **project page**; the demo mostly affects Presentation.

## 2. Timeline (H+0 = now, Sat 11/14; deadline about H+30 to H+38, check against local time)

| When | A: software (`lyra/`, `tests/`, `README.md`) | B: concept (`docs/`, `PLAN.md`, `data/nasa_reference.json`) |
|---|---|---|
| H+0 to H+2 | Reads `nasa_reference.json` v1; "expected adaptation" model, day 1/40/180 scenarios | Done: NASA data checked, 5 drawings, CONCEPT.md, this plan |
| H+2 to H+8 | 3D point cloud (Three.js), express scan + weekly test with voice, "you vs NASA" chart | Done: draft deck (7 slides), 30 s video script, form texts |
| H+8 to H+12 | Normal/Recheck/Deviation statuses, HRP risk cards, queue to the doctor (ISS/Moon/Mars) | App screenshots → into the deck; text edits based on the actual demo |
| H+12 to H+20 | Sleep / buffer. Deployment (GitHub Pages or similar, **public link**), README in English | Screen recording for the video (30 s), editing, **English subtitles** |
| H+20 to H+26 | Fixes, tests, check the link in a private window | Fill in the project page (all fields, English), upload images |
| H+26 to H+28 | **Together:** run-through, final checklist pass, **Submit for Judging** | |
| Buffer | 4 h or more before the deadline: do not touch unless needed; resubmit after any edits | |

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
| Drawings (5 sheets) | `docs/drawings/01...05_*.svg` (English, primary); PNG exports in `docs/drawings/png/`; Russian originals in `docs/drawings/ru/`; old ones in `docs/drawings/archive/` |
| Presentation, video, form | `docs/presentation/` |
| Software | `lyra/`, `tests/`, `README.md` (Agent A) |

## 5. Wording rules

| Do not write | Write instead |
|---|---|
| "diagnoses" | "flags deviations for a recheck and for the doctor" |
| "measures bone density" | "functional markers (grip strength, posture, leg volume) associated with bone and muscle loss" |
| "determines mental state" | "likely signs of fatigue and strain" |
| "medical device" | "screening and self-monitoring; the result is not a diagnosis" |
| an estimate presented as a citation | `cited` only if the number is directly in the source, otherwise "team estimate" |
