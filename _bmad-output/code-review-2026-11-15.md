# LYRA code review (BMad `bmad-code-review`), 2026-11-15

- **Target:** uncommitted changes vs HEAD `7176f16` in `lyra/`, `tests/`, `README.md`, `lyra/ARCHITECTURE.md`,
  `requirements.txt`, `.gitignore`, `.claude/launch.json` (22 files, about 3.8k diff lines).
  Excluded: `docs/**`, `PLAN.md`, `data/nasa_reference.json`, `docs/presentation/**`.
- **Mode:** `no-spec`. No story or spec file exists, so the Acceptance Auditor layer was skipped.
- **Layers run in parallel:** Blind Hunter (BH), Edge Case Hunter (ECH), Verification Gap (VG). None failed.
- **Run:** non-interactive (the user was away). Every `patch` finding was applied.

## Summary

| Verdict | Count |
|---|---|
| high | 1 |
| medium | 12 |
| low | 15 |
| rejected (false, or low and not worth the complexity) | 5 |
| out of scope (forwarded) | 1 |

Triage result: 28 `patch`, all applied (2 had a part deferred), 0 `decision-needed` (no-spec mode),
2 `defer`, 5 rejected.

## Findings and fixes

### High

1. **No-WebGL path crashes every session** (BH). `stubApi` had no `setSkeleton`, but `stepTurn`,
   `finishFlow` and the error handler call it. Fixed at `lyra/dashboard/body3d.js:151`.

### Medium

2. **Correlated posture yellows escalate the overall result to red** (BH). One posture change moves
   several angles, and "2 yellows = red" then defeats the "a single posture change is not escalated" rule.
   Fixed: un-escalated posture yellows count as one (`lyra/core/assess.py:332`). Test:
   `test_single_posture_change_counts_once_in_overall`.
3. **"Repeated" posture check used a baseline that already contained the recent values** (BH, VG). Fixed:
   the recent values are now judged against the earlier history (`lyra/core/assess.py:260`).
4. **"Why flagged" listed only retries** (BH, ECH). Fixed: it now shows the reason for every core flag
   (`lyra/dashboard/app.js:377`).
5. **The posture reference text said "microgravity" on the Moon and Mars** (BH). Fixed: a new `postureRef()`
   (`app.js:798`) drives the wording in `stepTurn` and on the Scan tab (`app.js:1051`).
6. **"Skip Research Module" skipped only the animation** (BH, ECH). Doppler, grip, PPG and SpO2 values were
   still simulated, stored and downlinked. Fixed in three places:
   - The flow skips the grip, handgrip and recovery steps (`app.js:606`, `app.js:860`).
   - The UI sends a new optional `skip_research` field (`lyra/server.py:62`).
   - The service drops every research key (`lyra/service.py:190`).

   This only adds a field, so the API contract is unchanged. Tests: `test_skipped_back_pain_and_research_are_not_recorded`
   and `test_session_skip_research_flag`.
7. **The report Change column showed a number for unconfirmed values** (BH, ECH). Fixed at `app.js:1126`.
8. **History downlink packets were always "green" and had no report** (BH). Fixed: they now use the real
   status of the last session and attach its medical report (`lyra/service.py:54`). Test:
   `test_history_packets_carry_real_status_and_report`.
9. **The 3D and stick-figure posture deformation was always 0 in flight** (BH, ECH). In space `preflight` is
   None, so the delta was 0. Fixed: it falls back to the in-mission baseline and ignores unconfirmed values
   (`lyra/core/engine.py:83`).
10. **The Scan tab showed rejected rPPG, face and tension values as valid** (ECH). Fixed: only confirmed values
    are shown, and the signal quality is still displayed (`app.js:1052`).
11. **A skipped optional back-pain question was recorded and downlinked as "No back pain"** (ECH). The simulator
    filled it with 0. Fixed at `lyra/service.py:182`.
12. **Verification gap: the back-pain and fatigue to posture escalation path through `evaluate` was untested**
    (VG). Mutation testing showed that forcing it on or off left the suite green. Added
    `test_evaluate_wires_back_pain_into_posture_escalation`.
13. **Verification gap: `previous_value` and `change_vs_previous` were only checked for presence, and
    `_latest` env_mode was not checked at all** (VG). Added `test_previous_value_and_change_are_correct` and
    `test_latest_history_result_uses_stored_env_mode`.

### Low

14. The front-end `RESEARCH_KEYS` fallback listed only 3 of the 11 research keys. Fixed at `app.js:86`.
15. The body-views counter said "0 of 15", but the backend model has 10 keypoints. Fixed at `app.js:810`.
    *Deferred part:* the 3D overlay in `body3d.js` uses its own 15-joint upright skeleton and does not read
    `body.skeleton`.
16. `CORE_REPORT` contained the research grips. They were replaced by `trunk_tilt_deg` (`app.js:1093`).
17. `spark()` had dead corridor code and a wrong `|| 1`. Both were cleaned up (`app.js:1107`).
    *Deferred part:* drawing the NASA corridor in the sparkline.
18. Packet reports could be opened while still in transit, against DESIGN.md §8. They now open only once
    delivered (`app.js:1380`). The on-board report above the queue is unchanged.
19. Scan tab posture features showed absolute angles with a "+" sign and had stale "next release" captions.
    Fixed with the `feat()` `abs` flag (`app.js:1052` onward).
20. The README tagline still said "Step in. Grip. Know.". Changed to "Step in. Scan. Know." (`README.md:3`).
21. `_pain_or_fatigue` hard-coded 0.5. It now uses `MIN_QUALITY` (`engine.py:99`).
22. The survey flag reason read "Self-report: back pain (self-report, optional) yes.". It is now
    "Self-report: back pain, yes." (`assess.py:235`).
23. The voice prompt said "handles" and the stage label said "Grip handles". Both now say "grips" or
    "Vertical grips" (`app.js:844`, `app.js:122`).
24. A dated "added 2026-11-15" comment in `MetricResult` was removed. `_low` was also hardened for empty
    strings (`assess.py:325`).
25. `loadReport` race: if the user switched astronaut mid-fetch, the old report was stored under the new
    astronaut. Fixed at `app.js:1100`.
26. The back view stick figure was drawn identical to the front view. The backend already mirrors it, so the
    frontend no longer double-flips (`app.js:1011`).
27. Skeleton `features` exposed unconfirmed posture values. Fixed at `engine.py:65`.
28. `stepTurn` called `querySelector("svg").outerHTML` with no null guard, which fails when icons are missing.
    Fixed at `app.js:821`.

## Deferred

- The 3D keypoint overlay is not driven by the backend skeleton (15 vs 10 joints, always upright). Low.
- Draw the NASA corridor band in the report sparkline. Low, enhancement.

## Rejected

- *Live quality checks are scripted with no "simulated" label* (BH). Low. The page already carries a
  Simulation provenance tag and a "Simulated data" header badge. A per-check label adds UI for little value.
- *`test_reference_loads_canonical_keys` subtracts `LOCAL_ONLY`* (BH). False. This is intentional: local-only
  posture metrics are, by design, not in the NASA reference.
- *`ENV_MODE_LABELS[env_mode]` KeyError* (ECH). False. `env_mode` only ever comes from `env_mode_for()` or a
  stored session.
- *`_low("")` IndexError* (ECH). False. Names fall back to the non-empty `spec.name`. It was hardened anyway
  (item 24).
- *Removed "мес" unit alias in `expected.py`* (ECH). False. `data/nasa_reference.json` uses only "%/month".

## Out of scope (forwarded)

- `docs/presentation/_src/build_deck.js` `DRAWING_FILES` still names PNGs that were moved to
  `docs/drawings/archive/v1/` (ECH). This belongs to the agent editing `docs/**`.

## Style nits (not fixed)

- `DESIGN.md` §8 "15 joints" describes the 3D overlay. It is accurate for that overlay, so it was left alone.
- The "Why flagged" lines repeat the metric name ("Sleep (self-rated): Self-report: sleep, 1 of 5.").

## Verification

- `.venv/bin/python -m pytest -q`: **45 passed** (38 before, plus 7 new regression tests).
- Browser check on the `lyra-sim-fast` preview, port 8766, with the server restarted to load the backend
  changes:
  - Ran all 4 scenarios: Day 1 ISS daily, Day 40 ISS daily and weekly with research skipped, Mars day 180
    weekly, Anomaly Moon day 60 daily.
  - The partial-gravity wording is correct on the Moon and Mars.
  - "Why flagged" now lists the reasons.
  - With Skip, no research or back-pain rows appear.
  - The You vs NASA chart, the Report table with sparklines, and the packet report dialog all work.
  - The in-transit Mars packet has no Report button.
  - Zero console errors and zero server errors.
  - At 375 px width there is no horizontal page scroll on any tab (scrollWidth is 375; the report table
    scrolls inside its own wrapper). The viewport was then reset to desktop.
