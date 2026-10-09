# Design plan and decisions

The binding art direction is `docs/SPEC.md` §14. This file restates the plan and logs the decisions
made while building, with reasons.

## The plan, restated
- **Concept: the window is the interface.** Every screen is seen through a classroom window. The frame is
  the layout, the panes hold the data, and whether the panes are open is the product's answer.
- **One bold thing per screen:** the `AirWindow`, and the Anek width axis on the instruction verb. Everything
  else stays quiet.
- **Palette from the classroom:** chalk (whitewashed wall), blackboard, haze (Delhi smog), breath (sky
  through an open window), haldi (turmeric, "action due"), sindoor (severe air and errors only).
- **Generic looks avoided:** no cream-and-terracotta, no black-and-acid-green, no identical card grids, no
  all-caps eyebrow labels, no monospace data labels, no "→" on buttons, no middle-dot meta strings, no
  dual-axis charts.

## Decisions log

### The AirWindow encoding: one dot = 2 µg/m³ in that window, at any size
The spec's legend reads "Each dot ≈ 2 µg/m³ of PM2.5". To make that literally true, the dot count is
`PM2.5 ÷ 2` per window, regardless of pixel size: 250 µg/m³ outside means 125 dots behind the glass. The
constant is shared through React context, and if a slow device has to drop dots, it doubles for every window
on the page together, and every legend updates with it. The breath haze uses one mapping everywhere
(0 at 400 ppm, full at 2,400 ppm).

### Panes show the window the air says, not the window the instruction wants
The spec's orchestrated moment swings the illustrated panes to the *target* state when an instruction
arrives. We show the state *inferred from the CO₂ curve* instead, and the instruction text carries the
target. When the teacher taps "I've opened them", the panes swing open only once the air confirms it. That
makes the partial-open moment visible (one pane swings, the other stays shut) instead of hiding it behind a
cheerful illustration, and keeps the window honest.

### Plain CSS with tokens instead of Tailwind
The venue network is ~43 KB/s and every extra dependency costs minutes. The tokens are CSS custom
properties (`web/src/design/tokens.css`), and the teacher route stays small (≈91 KB gzipped JS, budget 170).

### Window frame paint is a theme token
The first dark-mode screenshot drew the frame in blackboard green on a blackboard background, so it
vanished. Frame paints are now tokens (`--window-paint-green`, `--window-paint-blue`) with a light value for
dark mode. The window *scene* (sky, smog, dots) is the same in both themes.

### Primary button text uses `--on-fill`
`--breath-ink` turns light blue in dark mode; chalk text on it failed contrast. Text on filled buttons uses
`--on-fill` (chalk in light mode, blackboard in dark mode).

### Bilingual text: the second language is never smaller than 0.85 rem
The English line under a Hindi instruction (and vice versa) scaled to 0.55 em, which put the follow-up
banner's English at ~9 px. It now has a floor of 0.85 rem.

### Screenshots use Playwright, not Chrome's `--screenshot`
Headless Chrome's one-shot screenshot captured the canvas before it painted, which looked like a bug in
the AirWindow. The design-QA loop uses Playwright, as the spec says.

## Redesign, Fri 9 Oct (night)

Feedback: the first UI was "too basic". Direction after looking at current Awwwards winners and trend surveys
(bento layouts, tactile grain, editorial numerals, one strong metaphor per screen), without WebGL or GSAP:

### The window became a scene, and every new element is data
Behind the glass there is now a Delhi skyline (two layers of rooftops with water tanks) and a sun. Both fade
as outdoor PM2.5 rises, under a smog veil whose density follows the same value. On a clean day you see the
city; at PM2.5 250 it is gone. The frame is painted with a bevel and a sill; the glass has reflections. The dot
encoding and the CO₂ haze are unchanged.

### Teacher screen as a calm instrument panel
The window sits on a lit "wall" card; three readouts (CO₂, PM2.5 inside, AQI outside) use big tabular
numerals with a status word and dot (colour is never the only signal); the instruction has a countdown ring;
and an **air ribbon** shows the whole day's plan (one stripe per 5 minutes, darker = more open, a "now"
marker, period labels). The ribbon stitches together every plan version of the day (each version owns the
steps from when it was made), so the past shows what was planned at the time.

### Landing page
A blackboard hero whose headline widens (Anek's width axis) as the window opens, cycling Shut, Open and
Khidki with numbers from the physics model; a strip of four facts; a bento "four steps"; results read live
from `benchmark.json` (including the honest "+4 points PM2.5" tile); a "built on AWS" list; footer with
attribution and the not-a-medical-device line. Sections reveal on scroll, off under reduced motion.

### New roles and rules
- Panels use a 24 px radius (`--r-panel`), a new role between buttons (14 px) and the window frame (2 px).
- Grain: a fixed SVG-noise overlay at 5–7% opacity, multiply in light mode, screen in dark.
- Devanagari display text uses line-height 1.28; the 1.75 body rule was leaking into headings.
- The landing page defaults to English (its readers are judges and principals); teacher and parent pages
  default to Hindi. A saved choice wins.
- The 2025 classroom study is quoted only for what we verified (CO₂ down ~19%, PM up as windows opened).
