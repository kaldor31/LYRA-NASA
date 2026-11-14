# LYRA dashboard: design decisions

Owner: frontend. Decisions were made without a review round (team away during the hackathon); change them here first, then in code.

## 1. Audit of the previous UI (design-audit, phase findings)

Phase 1, critical
- No visual hierarchy: the eye had nowhere to land. Crew chips, scenario chips, step chips, status pills and tabs all shared the same pill shape and weight.
- The story a judge needs (who, overall status, what changed vs NASA, what to do next) was split across a tab and a card grid of 24 equally loud cards.
- Emoji used as icons and status (🟢 🟡 🔴 🔥 🔊 🎤 📡 ☢ 🎓 💳 ✊). Font-dependent, inconsistent, and they double up with the ✓ ▲ ‼ symbols.
- No visible keyboard focus, icon buttons without labels, modal without focus handling, toast not announced.
- Mirror prompt overlay covered the body labels; 3D labels used neon borders.

Phase 2, refinement
- Gradient logo, gradient buttons, gradient panels, radial page glow, glow text-shadow: decoration with no meaning.
- Five accent hues (cyan, lavender, orange streak, yellow, green) competing with the status colours.
- Every container rounded 12 to 18 px with a border: the "SaaS card kit".
- Numbers not tabular, jumping while live readouts update.

Phase 3, polish
- Chart: thick white line, dashed band outline and dashed centre fight each other; tooltip only on hover; no keyboard access; no summary for screen readers.
- Long em dashes and middle-dot meta strings everywhere.
- Reduced motion ignored (line draw animation, scan, auto-rotate).

## 2. Direction

"Medical instrument on a mirror." The station screen sits behind a half-silvered mirror, so the UI is dark, quiet and readable at arm's length. The memorable element is the 3D point cloud and the "You vs NASA" corridor; everything else is calm, flat and typographic.

Rejected: neon cyan sci-fi HUD (reads as fiction, not as a credible medical device), glassmorphism, glowing outlines, gradient CTAs.

## 3. Tokens

Colour (dark only; the device is a mirror display):

| Token | Hex | Use |
|---|---|---|
| `--bg` | `#0D1114` | page, graphite with a cool cast |
| `--surface` | `#13181D` | panels |
| `--raised` | `#1A2027` | inputs, hovered rows, readouts |
| `--line` | `#252D35` | hairlines, dividers |
| `--line-strong` | `#34404B` | control borders |
| `--text` | `#E7ECF0` | primary text |
| `--text-2` | `#A3AEB8` | secondary text (7:1 on surface) |
| `--text-3` | `#7F8B96` | tertiary, axis labels (4.6:1 on surface) |
| `--accent` | `#8FB2E8` | the only accent: selection, focus ring, NASA corridor, links |
| `--ok` | `#5BC98A` | status Normal only |
| `--warn` | `#E8B04B` | status Recheck only |
| `--bad` | `#F0686A` | status Deviation only |
| `--retry` | `#C9A2E6` | status Remeasure only |

Rules
- Status colours are used only for status, and always with an icon and a word: Normal (circle-check), Recheck (triangle-alert), Deviation (octagon-alert), Remeasure (rotate-ccw). Readable in greyscale.
- The primary action is a light filled button (`--text` on `--bg`), not a coloured one, so it never competes with status colour.
- No gradients, no glows, no shadows except the modal scrim.

Type
- IBM Plex Sans (400, 500, 600) for UI and body: engineering heritage, very legible at distance.
- IBM Plex Sans Condensed (500, 600) for readouts and big numbers, so values fit narrow columns.
- All numbers use `font-variant-numeric: tabular-nums`.
- Scale (1.25): 12, 13, 14, 16 (base), 20, 25, 31, 39 px.
- Sentence case for prompts and body; Title Case for buttons, tabs and section headings (Vercel guideline). No all-caps labels, no tracked eyebrows.

Spacing: 4 px base; 8, 12, 16, 24, 32, 48. Radius: 6 px controls, 10 px panels, 999 px only for the progress track.

Icons: Lucide 0.469.0 (pinned, jsDelivr), rendered as inline SVG from the icon nodes so they work in innerHTML templates. Stroke 1.75, sizes 16 / 20 / 24. Decorative icons are `aria-hidden`; icon-only buttons have `aria-label`.

Motion: 150 to 250 ms ease-out for state changes, transform and opacity only. One orchestrated moment: the chart line drawing in once. `prefers-reduced-motion` turns off the line draw, the scan sweep pulse and auto-rotate.

## 4. Information architecture

Desktop 1440x810, no page scroll; the right panel scrolls internally.

```
+------------------------------------------------------------------------------+
| LYRA  3D health scan   [Day 1 ISS][Day 40 ISS][Day 180 Mars][Anomaly Moon]   |
|                                     Moon / Gateway, 0.17 g, day 60  Sim  Vox |
+---------------+----------------------+---------------------------------------+
| Crew          |   3D point cloud     | Today | You vs NASA | Downlink | Why   |
|  AR Alex  OK  |                      |---------------------------------------|
|  MS Mira  DEV |    labels per zone   | Mira Sato, Flight Engineer            |
|  IK Ivan  OK  |                      | (!) Possible deviation                |
|  LO Leia  OK  |   mirror prompt      | Faster than NASA expects: face, grip  |
|               |                      | What to do now: 1. 2. 3.              |
| Scenario note |  [Front Side Top 360]| [Start Daily Scan] [Weekly] [Training]|
|               |                      | Measurements: rows with corridor gauge|
+---------------+----------------------+---------------------------------------+
| Screening, not a diagnosis. Data goes to the flight surgeon.   Keys: Space...|
+------------------------------------------------------------------------------+
```

- 10-second story: name, overall status, "Faster than NASA expects" list, next steps, primary button. All above the fold in the Today tab.
- Measurements are rows, not cards: name, value, change since preflight, a small corridor gauge (where the value sits inside NASA's expected band), status. Rows expand (native `<details>`) to show the explanation, actions, "Why it matters" and "Chart". Recheck and Deviation rows open by default.
- Session flow replaces the Today tab content: numbered stepper (a real sequence, so numbers are justified), large prompt, thin progress bar, live readouts, Repeat Prompt and Stop. The same prompt appears on the mirror overlay under the body.
- Below 1280 px the crew rail becomes a 4-column strip; below 900 px everything stacks; at 375 px crew is 2x2 and the scenario switch is a 2x2 grid. No horizontal scroll.

## 5. Chart: "You vs NASA expectation"

- Corridor as a flat accent band at 12 % opacity, no outline. Expected centre as a thin dashed accent line. You as a 1.75 px `--text` line. Grid lines at `--line`.
- Direct labels at the right edge ("NASA corridor", "You") instead of relying on the legend alone; legend kept for line-style description.
- Points outside the corridor in the dangerous direction are drawn larger in the status colour; tooltip states the status in words.
- Keyboard: the chart is focusable; Left/Right move the cursor day by day, Home/End jump. A visually hidden summary describes the latest value vs the corridor.
- Basis tag "Cited" or "Estimated" next to the NASA expectation, sources listed below.

## 6. Copy rules

- English only. Backend strings that still contain Cyrillic are replaced client-side by English fallbacks keyed by id (scenario, crew, environment, metric names, units, status words, packet titles) or regenerated from numeric fields (metric explanation line).
- No emoji anywhere: `clean()` strips pictographs and variation selectors from every backend string.
- No em dashes: `clean()` turns " — " into ", " and " · " into ", ". Ranges are written "1 to 1.5%".
- Voice prompts and commands in English (en-US): "start", "repeat", "stop", numbers one to five, "yes" / "no", "card".

## 7. Accessibility checklist

Skip link, landmarks, one h1, `aria-live` toast, native `<dialog>` for "Why it matters" (Esc closes, focus returns), `:focus-visible` 2 px accent ring with offset, 44 px touch targets for primary controls, `touch-action: manipulation`, `color-scheme: dark`, `theme-color` meta, labelled inputs, tabular numbers, reduced motion honoured.
