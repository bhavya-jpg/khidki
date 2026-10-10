# Design references: what thirteen award sites teach Khidki

Collected Sat 10 Oct 2026 with Playwright (Chromium, GPU on, 1440×900 and 390×844, network idle plus 3 s,
up to eight one-viewport scroll steps, hover on the main buttons, computed styles read from the page).
Screenshots are in `docs/design-refs/screens/` and are **gitignored**: they are other people's work.
We borrow principles only. No layouts, images, copy, code or fonts are taken; every font below is
commercial except ours (Anek, SIL OFL).

**What could and could not be seen**

| Site | Live capture | Awwwards (date, score) |
|---|---|---|
| Canairi | No: `canairi.io` now redirects to an unrelated domain; `canairi.com` refused the automated browser | Site of the Day, 10 Jul 2022, 7.38 |
| Air View | No: the URL serves a default Apache page (site retired) | Honorable Mention, 18 Nov 2016 |
| TruAQ | Yes | Honorable Mention, 9 May 2023 |
| Igloo Inc | Yes (needed about 20 s before the scene appeared) | Site of the Day, 23 Jul 2024, 7.92 |
| Messenger | Yes (start screen only; it is a game, scrolling does nothing) | Site of the Day, 10 Nov 2025, 7.92 |
| Summer Afternoon | Yes (opening scene only; no scroll) | Site of the Day, 7 Feb 2023, 7.87 |
| Mont-Blanc | Yes | Nominee, 22 Sep 2022 |
| Climate TRACE | Yes (cookie banner left in place) | Honorable Mention, 11 Mar 2024 |
| AI in Design Report 2026 | Yes | Site of the Day, 26 Aug 2026, 7.40 |
| Every day is a gift | Yes | Honorable Mention, 6 Sep 2026 |
| Ice and Sky | No: the domain is parked | Site of the Day, 23 Jun 2015, 7.89 |
| Weather Kids | Yes | Nominee, 30 Apr 2024 |
| Climate History | No: no response in 60 s, twice | Honorable Mention, 10 May 2021 |

Scores: Awwwards publishes the Design / Usability / Creativity / Content breakdown only for Sites of the
Day. For the others, "votes" below is the mean of the five votes shown on the page (of 15 or more cast), so
treat it as indicative. For sites that did not load, everything said comes from the Awwwards listing and is
marked "listing only".

---

## Per site

### 1. Canairi (listing only)
- Scores: Design 7.39, Usability 7.26, Creativity 7.39, Content 7.64. Palette `#9C9C9C`, `#FFFFFF`,
  `#ECD06F`. Tags: Promotional, Technology, Clean, Scrolling, UI design, Webflow.
- Does well: three colours where yellow is the only colour, and a promise that is one sentence about one
  action: it "will let you know when to ventilate your home in the most simple way".
- Transferable (teacher tablet): the product is the signal. One object changes state and that is the whole
  message, readable without reading. Our window must say "act now" from across the room.
- Do not copy: nothing visual; it could not be observed.
- Usability 7.26 is mid-range for this set. A fair reference for clarity of message, unverified for layout.

### 2. Air View by Blueair (listing only)
- No official breakdown; votes: Design 5.8, Usability 6.2, Creativity 7.0, Content 6.2. Palette `#000`,
  `#2779A7`, `#FFFFFF`. Tags: Culture & Education, Promotional, Fullscreen, WebGL.
- Does well: opens on one sourced statistic (WHO: 92% of people breathe air above its limits), then makes
  it personal: "the air you are breathing right now".
- Transferable (landing): statistic first, then your own room, now. Each landing fact should carry its source.
- Do not copy: a full-screen WebGL campaign site that no longer exists. Our printable timetable is the
  opposite bet: it works with no server at all.
- A weak usability reference (6.2).

### 3. TruAQ
- Votes: Design 7.4, Usability 7.6. Lighthouse: performance 30, accessibility 82, 10.1 MB. Webflow, Lenis,
  a WebGL canvas. Colours `#123A3E` ink and field, `#53696A` secondary, peach `#FFE4CE`.
- Does well: a centred 53 px light serif headline over a peach gradient with one dark pill button
  (222×60). The second screen is a full-bleed dark teal field with two short sentences ("…9000x smaller
  than a grain of sand") and a scale legend that stays in the corner: "1 micron is equal to 1 millionth of
  a metre". A ball of sand grains slides in as the comparison object; the same particles later turn grey
  at "Say goodbye to 99.99%".
- Transferable (landing, how-it-works): explain the invisible by comparing it with something physical, and
  keep the unit legend on screen the whole time.
- Do not copy: a newsletter pop-up covers the story in 7 of our 9 captures; 14 px body text; hijacked
  scrolling; 10 MB.
- A medium usability reference: clear story, poor performance.

### 4. Igloo Inc
- Scores: Design 8.05, Usability 7.5, Creativity 8.31, Content 7.91; developer award: animations 9.6,
  accessibility 6.6. Three.js r165, 4.1 MB. Palette `#B6BAC5`, `#383E4E`.
- Does well: one object in a one-hue landscape. All interface text sits small in the corners. Scrolling
  dissolves the igloo through fog into an ice crystal, and labels hang off the object on thin leader lines.
- Transferable (landing hero only): label the object itself. Put "outside" and "inside" readings on the
  window with a hairline, not in a row underneath.
- Do not copy: every word is drawn in the canvas (no text for a screen reader in our capture), about 20 s
  before anything appears, tiny low-contrast monospace labels.
- Usability 7.5 is high for this set, but for exploring, not for doing a task. Weak for the tablet.

### 5. Messenger
- Scores: Design 8.04, Usability 7.46, Creativity 8.23, Content 8.15; developer award: animations 9.0,
  accessibility 7.6. Three.js r180, 5.7 MB, 111 requests. Palette `#81BFBC`, `#C9D5C3`.
- Does well: a tiny world in two colours, the title built into the scene, and exactly one button on the
  first screen, the only yellow thing there ("Begin").
- Transferable (teacher tablet, principal page): one filled button per screen, in the one colour nothing
  else uses. Everything else is outline or text.
- Do not copy: game navigation, a loading screen before any content, WebGL.
- Usability 7.46: good for "what do I press first", not for information.

### 6. Summer Afternoon
- Scores: Design 7.78, Usability 7.76, Creativity 8.42, Content 7.47. Three.js r148, 8 MB. Palette
  `#F6ECD9`, `#79AD81`.
- Does well: the scene is the interface. The whole chrome is three small icons and a "0 / 5" counter in
  one corner, in flat poster colours.
- Transferable (teacher tablet): when nothing is due, show the window and one line. And show progress as a
  plain count: "2 of 6 requests used today" makes our attention budget visible and reassuring.
- Do not copy: unlabelled 20 px icon buttons, 8 MB of WebGL.
- The highest official usability here (7.76), but there is no task to complete. A partial reference.

### 7. Mont-Blanc climate change
- Nominee; votes: Design 6.8, Usability 7.0. Three.js r140, 15 MB, no headings in the DOM.
- Does well: a 400 px black serif title at 0.75 line-height on white fades to grey as a grey 3D mountain
  appears. Place names arrive in large italic serif. The only colour on the page is one green dot: the
  thing you can press.
- Transferable (principal page): colour means "press here" and nothing else. Rooms that need action get
  the accent; rooms that are fine get none.
- Do not copy: marquee headline you cannot read whole, numbered hotspots with no labels, 15 MB.
- A weak usability reference.

### 8. Climate TRACE
- Votes: Design 7.8, Usability 7.4. Lighthouse: performance 35, accessibility 77, 6.9 MB. Next.js and a
  WebGL map. Respects `prefers-reduced-motion`. Warm grey `#EBE6E6`, slate `#40494B`, one orange `#FF6F42`.
- Does well: three stacked rows over the globe, each a plain verb phrase with one line under it ("See
  pollution plumes, and how they travel into communities"). Orange marks only the active row and the
  numbers inside sentences. The stat card is complete in itself: "4.9B", unit, period, a hairline bar
  chart, one button.
- Transferable (principal page, landing results): a number never stands alone. Value, unit, period, a tiny
  trend and what to do next sit in one card.
- Do not copy: a cookie banner over the lower third of every frame; 11 px body text on the phone.
- A medium usability reference; the best one here for presenting data.

### 9. AI in Design Report 2026
- Scores: Design 7.66, Usability 7.21, Creativity 7.14, Content 7.38; developer award: accessibility 6.8.
  Lighthouse: performance 51, accessibility 84. Framer, 6 videos.
- Does well: h1 at 120 px / 0.95 line-height, weight 500, tracking −0.06 em. Chapters "01 Tools", "02
  Craft", "03 Teams", each on its own flat field, each listing five things it covers and ending in one
  full-width black bar that opens the chapter. Figures like "900+" sit beside one line of meaning.
- Transferable (landing): every section ends in one door. Ours should end in the live screen it describes.
- Do not copy: small all-caps monospace labels and arrows on buttons (both refused in SPEC §14.2), four
  accent colours.
- Usability 7.21 is the lowest official score here. Use it for content structure only.

### 10. Every day is a gift
- Votes: Design 8.6, Usability 8.0 (one 10 among five). Lighthouse: performance 31, accessibility 95,
  over 20 MB. Three.js r182, Lenis, 19,643 px of scroll. Respects `prefers-reduced-motion`. Lemon `#F2FCA7`, periwinkle `#A8AFFF`, near-black `#212529`.
- Does well: the data has a body. One wrapped matchstick is one day, 365 of them fan out, and the same
  matchstick is the cursor and the menu mark. The headline is 420 px condensed capitals at 0.75 line-height.
- Transferable (landing, teacher ribbon, how-it-works): name the unit in words where it first appears and
  reuse it everywhere. Ours are "one dot ≈ 2 µg/m³" and "one stripe = 5 minutes".
- Do not copy: the weight, all-caps display, a custom cursor (our users touch a tablet).
- Treat the usability votes with care; the page is long and heavy.

### 11. Ice and Sky (listing only)
- Scores: Design 8, Usability 7.43, Creativity 8.29, Content 8; developer award: accessibility 4.67.
  Palette `#2779A7`, `#DF6C4F`, `#FFFFFF`. Tags: Culture & Education, Animation, Big Background Images,
  Navigation Menu, Parallax, Video.
- Does well: a teaching site organised as chapters behind a persistent navigation menu, in blue with one
  warm accent.
- Transferable (landing): a menu that names every destination, so a teacher or judge can jump straight to
  their part.
- Do not copy: accessibility scored 4.67 out of 10; big background video.
- A 2015 usability score. Weak.

### 12. Weather Kids
- Nominee; votes: 6.8 on every criterion. Lighthouse: performance 52, accessibility 100, 45 MB with its
  videos. GSAP, Swiper, jQuery. `#305061`, `#213743`, yellow `#FEE17B`.
- Does well: a 72 px / 0.9 wide grotesque headline over sky; on scroll, one sentence per screen; the
  pledge form is itself a sentence with two blanks ("___ pledge to take climate action for ___"); eight
  languages in the corner.
- Transferable (principal page): a form that reads as the sentence it will log. Our override becomes
  "Hold PE (6B) outdoors because ___."
- Do not copy: half the headline in a second colour (refused in §14.2), white text over clouds, 10 px
  body on the phone, a cursor ring, a child presenter on video (we show no children).
- A weak usability reference on votes, though its markup scores 100 for accessibility.

### 13. Climate History (listing only)
- No official breakdown; votes: Design 8.0, Usability 7.8, Creativity 8.0, Content 9.2. Palette `#000`,
  `#D14836`, `#FFFFFF`. Tags: Culture & Education, Clean, Storytelling, Content architecture, Parallax.
- Does well: described as "a modern educational tool intended for use in South East Asian schools", with
  the strongest content votes of the set.
- Transferable (print page, how-it-works): write for the classroom first; structure follows the lesson.
- Do not copy: nothing visual; it could not be observed.
- Unverified.

---

## Synthesis

**The headline finding.** On the things Khidki is judged on, the references are not better than us; they
are better at one moment. On the five we measured with Lighthouse, performance runs 30 to 52 and page
weight 6 to 45 MB; ours is 67 to 91 at about 1 MB (`docs/AUDIT.md`). Accessibility is closer: theirs 77 to
100, ours 93 to 100. What they do that we do not: one object, one accent, one sentence, one door per
section. Our gaps are discipline, not spectacle.

### Principles, ranked by effect on Design and usability, then the demo video

| # | Principle | Seen in | Exact change | Hours |
|---|---|---|---|---|
| 1 | **The instruction is one sentence, and the reason agrees with it.** | Canairi, Weather Kids, Climate TRACE | Teacher: the "why" line must come from the instruction's own reason, never "All fine" under "Open…" (`services/khidki_services/engine.py`, where the card is built; also the 07:50 row in `web/src/routes/Print.tsx`). Raise `.action__verb` in `web/src/routes/Teacher.css` from `clamp(2rem, 3.6vw, 3.1rem)` to `clamp(2.441rem, 4.4vw, 3.4rem)`: at 1024 px it is 36.9 px today, under the 2.441 rem that §14.6 requires. | 0.4 |
| 2 | **The state reads from across the room, without reading.** | Canairi, Summer Afternoon | Teacher: when an instruction is due, give the window itself the signal: a 4 px `--haldi` outline on `.wall` in `Teacher.css` (set a `data-due` attribute on `.teacher__stage` in `Teacher.tsx`). No outline when nothing is due. | 0.3 |
| 3 | **One accent, and it only ever means "act now".** | Mont-Blanc, Messenger, Climate TRACE, Canairi | `--haldi` is defined that way in §14.3 but we also use it for information. Change `.hero__kicker` (`Landing.css:86`) and `.tile--nudge .tile__n` (`Landing.css:338`) to `--chalk` at 75%; change `.grap__aqi` (`School.css:78`) to `--chalk`. Keep haldi on the landing call-to-action, the teacher's primary button and ring, and "needs action" rooms. | 0.2 |
| 4 | **A number never stands alone.** | Climate TRACE, AI in Design Report, TruAQ | Principal `RoomRow` in `web/src/routes/School.tsx`: replace the "All fine" badge with the CO₂ status word beside the value ("1,714 ppm CO₂, stuffy"), using the same wording as the teacher's `Readout`. Landing `.stat` blocks: add the period and label to each ("a day, simulated on 48 real days") under `stat__label`. | 0.4 |
| 5 | **Name the unit where it first appears.** | Every day is a gift, TruAQ | `web/src/components/ui/AirRibbon.tsx`: start the legend with "One stripe = 5 minutes" / "एक पट्टी = 5 मिनट". The window legend "Each dot ≈ 2 µg/m³" already exists; keep it at `--ink-2`. | 0.2 |
| 6 | **Every section ends in one door.** | AI in Design Report, Ice and Sky | `web/src/routes/Landing.tsx`: end "How it works" with a button to `/teacher/6B`, "Results" with one to `/school/dsv`, and add "Print today's timetable" (`/print/6B`). Add "Principal" to `.nav__links`. Add a catch-all 404 route in `web/src/App.tsx`. (This is audit fix 17.) | 0.5 |
| 7 | **Nothing sits on top of the story, and no text is too small to read.** | TruAQ and Climate TRACE (as warnings), Weather Kids (10 px) | We have no pop-ups: keep it that way. Raise the floor for caption text on phones: in `web/src/design/tokens.css` set `--step--1` to `0.875rem` (14 px) from `0.8rem`, then re-shoot 1024×600 to confirm the teacher screen still fits without scrolling. | 0.3 |
| 8 | **Content first, weight second.** | Igloo (20 s blank), Every day (22.6 MB), Mont-Blanc (15 MB) | Our one heavy asset is the 709 KB Anek Devanagari file. In `web/index.html`, request Devanagari with the weight axis only and keep both axes for Anek Latin; measure before and after. See the conflict note below. (This is audit fix 16.) | 0.4 |
| 9 | **Show the budget as a count.** | Summer Afternoon ("0 / 5") | Teacher: a quiet line in `.teacher__bar`, "आज 6 में से 2 अनुरोध / 2 of 6 requests used today". Needs one field from `engine.room_now` (`requests: {used, max}`, already tracked in `counts`). | 0.5 |
| 10 | **Label the object, not the space beside it.** | Igloo, Mont-Blanc | Landing hero only: move the two hero numbers (`.hero__numbers` in `Landing.tsx`) onto the window as HTML labels with a hairline, "inside" on the room side and "outside" on the sky side. Add an optional `annotations` prop to `AirWindow.tsx`; never used in the `calm` variant. | 1.0 |
| 11 | **A form reads as the sentence it will log.** | Weather Kids | Principal `DecisionRow` in `School.tsx`: the override form becomes one line, "Hold PE (6B) **outdoors** because ___", and the audit log shows the same sentence. Do it together with the passcode fix (audit fix 12). | 0.4 |
| 12 | **For the video: one object, one continuous move.** | Igloo, Mont-Blanc, Summer Afternoon | No code. In `docs/demo-script.md`, film the teacher tablet as a single unbroken shot from instruction to "Air is changing ✓", with the Step Functions graph beside it, instead of cutting between pages. The window swing (`--dur-pane`, 750 ms) is our one orchestrated moment. | 0 |

Principles 1, 6 and 8 are already in the audit's fix list; doing them serves both documents.

### Where a reference conflicts with SPEC §14, and what to keep

| Reference habit | §14 says | Keep |
|---|---|---|
| Display type at 0.75 to 0.95 line-height (Every day, Mont-Blanc, AI report, Weather Kids) | Devanagari needs room for matras (1.28 on display, 1.75 on body) | **Ours** for Hindi. Tighten only Latin display lines: `.section__title` and `.stat__num` to line-height 0.95 and tracking −0.02 em under `:lang(en)` in `Landing.css` |
| All-caps headlines and small caps labels (Every day, AI report, Igloo) | Sentence case everywhere, no all-caps labels | **Ours** |
| Monospace data labels (AI report, Igloo) | No monospace data labels; tabular figures in Anek | **Ours** |
| Half a headline in a second colour (Weather Kids) | No single highlighted word | **Ours** |
| Pill buttons at 50 to 100 px radius, arrows inside (TruAQ, Weather Kids, AI report) | Buttons 14 px, no "→" | **Ours** |
| Full-screen WebGL, smooth-scroll hijack, custom cursors (Igloo, Messenger, Summer Afternoon, Mont-Blanc, TruAQ, Every day) | Refused on the tablet in §14.1; `SCOPE.md` then cut WebGL, GSAP and Lenis everywhere | **Ours**: Canvas2D, native scroll, no custom cursor |
| Four or five accent colours (AI report) | Six tokens, haldi only for action | **Ours** |
| Dropping the font's width axis to save weight (principle 8) | "Width as meaning": the headline and the instruction verb widen as the window opens | **A real trade-off.** Dropping the width axis for Devanagari removes that effect from Hindi text, which is most of the teacher screen. Measure first; if the saving is under 300 KB, keep the axis and preload the font instead |

### Calm screens stay calm
Nothing from Igloo, Messenger, Summer Afternoon, Mont-Blanc or Every day is a gift goes onto the teacher
screen or the print page. Those two get principles 1, 2, 5 and 9 only: fewer words, one signal, one count.
Principle 10 is for the landing page hero. The Lab and parent pages are cut (`docs/SCOPE.md`), so nothing
is proposed for them.

### Order to apply, if time is short
1, 2, 3, 5 (about one hour together, all on the screens the video films), then 6 and 4, then 7 and 8 with
a full re-shoot, then 9 to 11. After each change: re-run the Playwright design-QA screenshots of our own
app at 1024×600, 390×844 and 1440×900 in light and dark, and commit that change by itself.
