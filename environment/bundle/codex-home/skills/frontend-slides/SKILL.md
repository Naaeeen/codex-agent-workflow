---
name: frontend-slides
description: Create or improve browser-based HTML slide decks, or convert a supplied PPT/PPTX to HTML. Use when HTML is the chosen deliverable; ordinary PowerPoint or Google Slides work belongs to the available presentation workflow.
---

# Frontend Slides

Create zero-dependency, animation-rich HTML presentations that run entirely in the browser.

Inspired by the visual exploration approach showcased in work by [zarazhangrui](https://github.com/zarazhangrui).

## When to Activate

- Creating a talk, pitch, workshop or internal deck specifically for delivery as HTML
- Converting `.ppt` or `.pptx` slides into an HTML presentation
- Improving an existing HTML presentation's layout, motion, or typography
- Exploring presentation styles with a user who does not know their design preference yet

## Non-Negotiables

1. **Zero dependencies**: default to one self-contained HTML file with inline CSS and JS.
2. **Viewport fit is mandatory**: every slide must fit inside one viewport with no internal scrolling.
3. **Show, don't tell**: use visual previews instead of abstract style questionnaires.
4. **Distinctive design**: avoid generic purple-gradient, Inter-on-white, template-looking decks.
5. **Production quality**: keep code commented, accessible, responsive, and performant.

Before generating, read `STYLE_PRESETS.md` for the viewport-safe CSS base, density limits, preset catalog, and CSS gotchas.

## Workflow

### 1. Detect Mode

Choose one path:
- **New presentation**: user has a topic, notes, or full draft
- **PPT conversion**: user has `.ppt` or `.pptx`
- **Enhancement**: user already has HTML slides and wants improvements

### 2. Discover Content

Ask only the minimum needed:
- purpose: pitch, teaching, conference talk, internal update
- length: short (5-10), medium (10-20), long (20+)
- content state: finished copy, rough notes, topic only

Use supplied content and accessible task files directly. Ask only for missing information that materially changes the deck; do not ask the user to paste content already available.

### 3. Discover Style

Preserve the requested brand, existing deck design and user constraints. Visual exploration is useful when the style is unresolved and the user wants alternatives; it is not a required approval gate for every deck.

If the user supplied a template, style, brand or asked you to choose, use that direction and continue. Do not replace it with a preset or force a separate selection round.

When exploration is useful:
1. Establish what feeling the deck should create: impressed, energized, focused, inspired.
2. Generate **3 single-slide preview files** in `.ecc-design/slide-previews/`.
3. Each preview must be self-contained, show typography/color/motion clearly, and stay under roughly 100 lines of slide content.
4. Ask the user which preview to keep or what elements to mix.

Use the preset guide in `STYLE_PRESETS.md` when mapping mood to style.

### 4. Build the Presentation

Output either:
- `presentation.html`
- `[presentation-name].html`

Use an `assets/` folder only when the deck contains extracted or user-supplied images.

Required structure:
- semantic slide sections
- a viewport-safe CSS base from `STYLE_PRESETS.md`
- CSS custom properties for theme values
- a presentation controller class for keyboard, wheel, and touch navigation
- Intersection Observer for reveal animations
- reduced-motion support

### 5. Enforce Viewport Fit

Treat this as a hard gate.

Rules:
- every `.slide` must use `height: 100vh; height: 100dvh; overflow: hidden;`
- all type and spacing must scale with `clamp()`
- when content does not fit, split into multiple slides
- never solve overflow by shrinking text below readable sizes
- never allow scrollbars inside a slide

Use the density limits and mandatory CSS block in `STYLE_PRESETS.md`.

### 6. Validate

Check the finished deck at these sizes:
- 1920x1080
- 1280x720
- 768x1024
- 375x667
- 667x375

If browser automation is available, use it to verify no slide overflows and that keyboard navigation works.

### 7. Deliver

At handoff:
- keep task-owned previews in the scratch area; do not remove user-supplied files
- open the deck with the platform-appropriate opener when useful
- summarize file path, preset used, slide count, and easy theme customization points

Prefer the host's file/browser preview when available, using the actual saved path. On Windows use native PowerShell operations if an external opener is needed, rather than a command from another shell.

## PPT / PPTX Conversion

For PowerPoint conversion:
1. For `.pptx`, use an available `python-pptx` runtime or the host presentation tools to extract text, images and notes. The legacy binary `.ppt` format is not supported by `python-pptx`; use an already available converter to create a separate `.pptx` copy, or use an export-based workflow. Preserve the original file and check conversion fidelity.
2. If `python-pptx` is unavailable, ask whether to install it or fall back to a manual/export-based workflow.
3. Preserve slide order, speaker notes, and extracted assets.
4. After extraction, run the same style-selection workflow as a new presentation.

Keep conversion cross-platform. Do not rely on macOS-only tools when Python can do the job.

## Implementation Requirements

### HTML / CSS

- Use inline CSS and JS unless the user explicitly wants a multi-file project.
- Use the supplied brand fonts or suitable local fallbacks. Remote font loading is optional; a required offline/self-contained deck must not depend on fetching them.
- Prefer atmospheric backgrounds, strong type hierarchy, and a clear visual direction.
- Use abstract shapes, gradients, grids, noise, and geometry rather than illustrations.

### JavaScript

Include:
- keyboard navigation
- touch / swipe navigation
- mouse wheel navigation
- progress indicator or slide index
- reveal-on-enter animation triggers

### Accessibility

- use semantic structure (`main`, `section`, `nav`)
- keep contrast readable
- support keyboard-only navigation
- respect `prefers-reduced-motion`

## Content Density Limits

Use these maxima unless the user explicitly asks for denser slides and readability still holds:

| Slide type | Limit |
|------------|-------|
| Title | 1 heading + 1 subtitle + optional tagline |
| Content | 1 heading + 4-6 bullets or 2 short paragraphs |
| Feature grid | 6 cards max |
| Code | 8-10 lines max |
| Quote | 1 quote + attribution |
| Image | 1 image constrained by viewport |

## Anti-Patterns

- generic startup gradients with no visual identity
- arbitrary font replacement that conflicts with the brand, accessibility or offline requirements
- long bullet walls
- code blocks that need scrolling
- fixed-height content boxes that break on short screens
- invalid negated CSS functions like `-clamp(...)`

## Related ECC Skills

- `frontend-patterns` for component and interaction patterns around the deck
- `liquid-glass-design` when a presentation intentionally borrows Apple glass aesthetics
- `e2e-testing` if you need automated browser verification for the final deck

## Deliverable Checklist

- presentation runs from a local file in a browser
- every slide fits the viewport without scrolling
- style is distinctive and intentional
- animation is meaningful, not noisy
- reduced motion is respected
- file paths and customization points are explained at handoff
