# AgentReady — UI/UX Design Specification

## Design Philosophy

AgentReady is a developer tool for a technical audience. The design must feel like something
engineers actually want to use — not a marketing site, not a startup landing page template.
The reference points are **Vercel**, **Linear**, and **Resend**: dark-first, typographically
sharp, zero decoration that doesn't earn its place, and one clear action at any given moment.

**Three design principles that govern every decision:**

1. **Precision over decoration.** Every pixel either structures information or guides the user.
   No gradients for decoration, no shadows for depth, no rounded corners for friendliness.
2. **The terminal is the aesthetic.** This tool produces code files. The UI should feel like
   it was built by people who live in their editor. Monospaced labels, structured output,
   subtle grid textures. Not playful. Not cozy. Focused.
3. **One thing at a time.** The flow has three moments: Input → Analysis → Results.
   Each moment owns the full screen. Nothing leaks between states.

---

## Color System

All colors are CSS custom properties defined on `:root`. Use only these values — no arbitrary
Tailwind colors, no one-off hex values inline.

```css
:root {
  /* Backgrounds — layered from deepest to surface */
  --bg-base:        #09090b;   /* page background — near-black, not pure black */
  --bg-surface:     #111113;   /* card/panel backgrounds */
  --bg-elevated:    #18181b;   /* hover states, active tabs, input backgrounds */
  --bg-overlay:     #1e1e21;   /* dropdown menus, tooltips */

  /* Borders — very subtle, white with low opacity */
  --border-subtle:  rgba(255, 255, 255, 0.07);
  --border-default: rgba(255, 255, 255, 0.11);
  --border-strong:  rgba(255, 255, 255, 0.18);
  --border-focus:   #06b6d4;   /* cyan — only used for focused input rings */

  /* Text */
  --text-primary:   #f4f4f5;   /* headings, important labels */
  --text-secondary: #a1a1aa;   /* body text, descriptions */
  --text-muted:     #52525b;   /* timestamps, disabled states, placeholders */
  --text-code:      #e4e4e7;   /* monospaced code output */

  /* Accent — ONE accent color, used sparingly */
  --accent:         #06b6d4;   /* cyan-500 — primary CTAs, focus rings, highlights */
  --accent-dim:     rgba(6, 182, 212, 0.12);  /* accent background tint */
  --accent-glow:    rgba(6, 182, 212, 0.25);  /* glow effect on buttons */

  /* Score colors — semantic only, for the audit score breakdown */
  --score-good:     #22c55e;   /* green-500 — checks that pass */
  --score-warn:     #f59e0b;   /* amber-500 — partial credit / present but weak */
  --score-bad:      #ef4444;   /* red-500 — checks that fail */
  --score-good-bg:  rgba(34, 197, 94, 0.10);
  --score-bad-bg:   rgba(239, 68, 68, 0.10);

  /* Dot grid background — used in hero section */
  --grid-dot-color: rgba(255, 255, 255, 0.09);
  --grid-dot-size:  1.5px;
  --grid-spacing:   28px;
}
```

**Color rules:**
- Never use `--accent` on body text. Only on interactive elements (buttons, links, focus states) and the
  score number.
- Never put two accent elements next to each other. Scarcity is what makes cyan feel premium.
- Do not use white (`#ffffff`) anywhere. Use `--text-primary` (`#f4f4f5`) instead.
- Pure black (`#000000`) is also banned. Backgrounds go no darker than `--bg-base` (`#09090b`).

---

## Typography System

Two typefaces only. One for everything UI-related, one for code.

### Fonts

```html
<!-- In index.html <head> -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

```css
:root {
  --font-ui:   'Inter', -apple-system, sans-serif;
  --font-code: 'JetBrains Mono', 'Fira Code', monospace;
}
```

**Inter** handles all UI text: navigation, headings, body copy, buttons, labels.
**JetBrains Mono** handles: generated code output, file names, URL inputs, the score number,
and any pill/badge labels that feel more technical (e.g. `llms.txt`).

### Type Scale

```css
/* Display — hero headline only */
--text-display:   clamp(2.5rem, 5vw, 4rem);
--leading-display: 1.05;
--tracking-display: -0.04em;  /* tight, engineered feel */

/* Heading 1 — section titles */
--text-h1:        1.875rem;   /* 30px */
--leading-h1:     1.2;
--tracking-h1:    -0.025em;

/* Heading 2 — card titles, tab labels */
--text-h2:        1.25rem;    /* 20px */
--leading-h2:     1.3;
--tracking-h2:    -0.015em;

/* Body — descriptions, paragraph text */
--text-body:      0.9375rem;  /* 15px */
--leading-body:   1.6;
--tracking-body:  0;

/* Small — meta labels, timestamps, secondary info */
--text-small:     0.8125rem;  /* 13px */
--leading-small:  1.5;

/* Code — monospace output, file names, URLs */
--text-code:      0.875rem;   /* 14px */
--leading-code:   1.7;

/* Label — uppercase category tags NEVER use these in headings */
/* Only use for functional labels like check names in the audit */
--text-label:     0.75rem;    /* 12px */
--tracking-label: 0.06em;
```

**Typography rules:**
- Display headline uses `font-weight: 700`, tracking `-0.04em`. No other element gets this treatment.
- Never put letter-spacing on body text — only display and monospaced labels.
- Line length cap: `max-width: 62ch` on any paragraph of body text.
- Do not use ALL CAPS for navigation links, button labels, or headings. Only for the tiny
  category label above the hero headline (`DEVELOPER TOOL` style pre-label), and only once on the page.

---

## Spacing System

Use an 8px base unit. All spacing is a multiple of 4px minimum, 8px preferred.

```css
:root {
  --space-1:   4px;
  --space-2:   8px;
  --space-3:   12px;
  --space-4:   16px;
  --space-5:   20px;
  --space-6:   24px;
  --space-8:   32px;
  --space-10:  40px;
  --space-12:  48px;
  --space-16:  64px;
  --space-20:  80px;
  --space-24:  96px;
}
```

**Layout container:**
```css
.container {
  width: 100%;
  max-width: 900px;  /* intentionally narrow — this is a tool, not a marketing site */
  margin: 0 auto;
  padding: 0 var(--space-6);
}
```

---

## Border & Surface System

```css
/* Standard card */
.card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;         /* consistent 8px everywhere — no mixed radii */
}

/* Elevated card (hover state or active panel) */
.card:hover, .card--active {
  background: var(--bg-elevated);
  border-color: var(--border-default);
}

/* Input fields */
.input {
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: 8px;
}
.input:focus {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px var(--accent-dim);
  outline: none;
}
```

**Border rules:**
- 1px borders only. Never 2px.
- Border radius is `8px` everywhere. No `4px`, no `12px`, no `full`. One value, always.
  Exception: the main CTA button uses `8px`. Pills/badges use `9999px`.
- No box-shadows for depth. Layering is done through background color difference.
  The only allowed shadow is the focus ring on the input (`box-shadow: 0 0 0 3px var(--accent-dim)`).

---

## Page Layout Structure

The app has exactly three views. They never coexist on the same screen.

```
┌─────────────────────────────────────────┐
│  HEADER (fixed, 56px tall)              │
├─────────────────────────────────────────┤
│                                         │
│  VIEW A: LANDING + INPUT FORM           │
│  (full-page, centered vertically)       │
│                                         │
│  ↓ on submit                            │
│                                         │
│  VIEW B: LOADING / ANALYSIS STATE       │
│  (full-page, centered vertically)       │
│                                         │
│  ↓ on complete                          │
│                                         │
│  VIEW C: RESULTS PAGE                   │
│  (scrollable, top-aligned)              │
│                                         │
└─────────────────────────────────────────┘
```

---

## Component Specifications

---

### 1. Header (Persistent)

**Height:** 56px  
**Position:** `position: fixed; top: 0; left: 0; right: 0; z-index: 100`  
**Background:** `var(--bg-base)` with `border-bottom: 1px solid var(--border-subtle)`  
**Backdrop blur:** `backdrop-filter: blur(12px)` with `background: rgba(9,9,11,0.85)`

```
┌──────────────────────────────────────────────────────────────┐
│  ◈  AgentReady         ·         [  Try Another URL  ]       │
│  ^                                ^  only shown on           │
│  logo                             │  results page            │
└──────────────────────────────────────────────────────────────┘
```

**Logo:**
- A small icon to the left: a simple `◈` character rendered in `--accent` color, or a minimal SVG of two overlapping squares (representing API + AI)
- Next to it: `AgentReady` in Inter 600, `--text-primary`, tracking `-0.02em`
- No tagline in the header

**Right side:**
- On the landing page: a GitHub link (small icon + `Star on GitHub` in `--text-muted`, 13px)
- On the results page only: a ghost button `← New Analysis` that resets the app back to View A

**CSS for header text:**
```css
.logo-text {
  font-family: var(--font-ui);
  font-weight: 600;
  font-size: 1rem;
  letter-spacing: -0.02em;
  color: var(--text-primary);
}
.logo-icon {
  color: var(--accent);
  font-size: 1.1rem;
  margin-right: 8px;
}
```

---

### 2. Landing View (View A)

This is the first thing the user sees. It occupies the full viewport height (minus the 56px header).

**Layout:** Centered vertically and horizontally within the viewport.

```
┌─────────────────────────────────────────────────────────────┐
│  [dot grid background — fades out at edges]                 │
│                                                             │
│               DEVELOPER TOOL  ← tiny label, cyan           │
│                                                             │
│          Make your product                                  │
│          AI-agent ready.                                    │
│                    ← display headline, 2 lines              │
│                                                             │
│    Paste your website and GitHub repo. We'll generate       │
│    llms.txt, an MCP server, OpenAPI spec, and a full        │
│    agent-readiness audit. Takes ~15 seconds.                │
│                    ← body text, max 52ch                    │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  🌐  https://yoursite.com                           │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ⌥  https://github.com/org/repo                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│              [  Analyze my product  →  ]                    │
│                    ← primary CTA button                     │
│                                                             │
│       At least one URL required · Public repos only         │
│                    ← micro-copy in --text-muted             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2a. Dot Grid Background

Rendered as an SVG pattern using a CSS background-image. It must:
- Cover the full landing section
- Be masked by a radial gradient so it fades out 30% from center toward edges (dots are visible only near the center)
- NOT animate unless the user has an interaction (mouse move)
- Respect `prefers-reduced-motion: reduce` — static if the user prefers

```css
.dot-grid-bg {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle, var(--grid-dot-color) var(--grid-dot-size), transparent var(--grid-dot-size));
  background-size: var(--grid-spacing) var(--grid-spacing);
  /* Radial mask — fade toward edges */
  -webkit-mask-image: radial-gradient(ellipse 70% 60% at 50% 50%, black 40%, transparent 100%);
  mask-image: radial-gradient(ellipse 70% 60% at 50% 50%, black 40%, transparent 100%);
  z-index: 0;
  pointer-events: none;
}
.landing-content {
  position: relative;
  z-index: 1;
}
```

#### 2b. Category Pre-Label

```
DEVELOPER TOOL
```
- Font: `var(--font-code)`, 11px, `letter-spacing: 0.1em`
- Color: `var(--accent)` — `#06b6d4`
- No background, no border — just the text
- Small horizontal rule on each side: `──  DEVELOPER TOOL  ──`
  rendered using CSS pseudo-elements or actual `<hr>` siblings

#### 2c. Display Headline

```
Make your product
AI-agent ready.
```
- Font: Inter 700
- Size: `clamp(2.5rem, 5vw, 4rem)` — scales with viewport
- Tracking: `-0.04em`
- Color: `var(--text-primary)` — no gradient on the text, no mixed colors
- Line height: `1.05`
- The period at the end of "ready." is the only punctuation. No exclamation marks.
- Two lines, naturally broken. Do not use `<br>` — use `max-width` to control wrapping.
- `text-align: center`

#### 2d. Body Copy

```
Paste your website and GitHub repo. We'll generate
llms.txt, an MCP server, OpenAPI spec, and a full
agent-readiness audit. Takes ~15 seconds.
```
- Font: Inter 400
- Size: `var(--text-body)` — 15px
- Color: `var(--text-secondary)` — `#a1a1aa`
- `max-width: 50ch`
- `text-align: center`
- Line height: `1.6`
- Note: "llms.txt", "MCP server", "OpenAPI spec" can be in `<code>` tags styled with
  `font-family: var(--font-code); color: var(--text-primary); font-size: 0.85em`

#### 2e. Input Fields

Both inputs are the same width as the CTA button below them. Max width `520px`.

```
┌──────────────────────────────────────────────────┐
│  [globe icon]  https://yoursite.com              │
└──────────────────────────────────────────────────┘
```

**Visual spec:**
- Height: `48px`
- Background: `var(--bg-elevated)` — `#18181b`
- Border: `1px solid var(--border-default)` — `rgba(255,255,255,0.11)`
- Border radius: `8px`
- Left icon: 16px, color `var(--text-muted)`, `margin-left: 14px`
- Text: `var(--font-code)`, 14px, color `var(--text-secondary)`
- Placeholder text: `var(--text-muted)`
- Focus state: `border-color: var(--accent)`, `box-shadow: 0 0 0 3px var(--accent-dim)`
- The transition: `border-color 150ms ease, box-shadow 150ms ease`
- Spacing between the two inputs: `var(--space-3)` — 12px
- The two inputs are stacked, not side-by-side

**Validation error state:**
- If the user clicks Analyze with both fields empty:
  - Both inputs get `border-color: var(--score-bad)` — `#ef4444`
  - A single inline error below both inputs (not a toast, not a modal):
    `At least one URL is required.` — 13px, `var(--score-bad)`, fade in over 150ms

#### 2f. CTA Button

```
[  Analyze my product  →  ]
```

**Visual spec:**
- Height: `48px`
- Width: same as inputs — fills the same `520px` column
- Background: `var(--accent)` — `#06b6d4`
- Text color: `#09090b` (dark text on cyan — strong contrast)
- Font: Inter 600, 15px, `letter-spacing: -0.01em`
- Border radius: `8px`
- Border: none
- Arrow `→` is part of the text, separated by a space. It shifts `4px` right on hover.
- Hover: `filter: brightness(1.08)` — no color change, just brightens slightly
- Active: `filter: brightness(0.92)` — depresses
- Transition: `filter 100ms ease, transform 100ms ease`
- Cursor: `pointer`
- Disabled state (while loading): `opacity: 0.4`, `cursor: not-allowed`
- The button never shows a spinner — the loading view replaces it entirely

#### 2g. Micro-copy Below Button

```
At least one URL required · Public repos only
```
- Font: Inter 400, 13px
- Color: `var(--text-muted)`
- `text-align: center`
- Dot separator: `·` — a middle dot, not a slash or pipe

---

### 3. Loading View (View B)

This replaces View A when the user clicks Analyze. It must feel like something is actually
happening — not a spinner in a void. Users wait ~15 seconds on average; the UI must hold attention
and manage expectation for that full duration.

**Layout:** Full-page, centered vertically and horizontally (same layout as View A).

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                    ┌──────────────┐                         │
│                    │  [pulse orb] │                         │
│                    └──────────────┘                         │
│                                                             │
│               Crawling website...              ← stage msg  │
│               Reading GitHub repo...           ← crossfades │
│               Analyzing with AI...                          │
│               Generating artifacts...                       │
│                                                             │
│       ────────────────────────────────────                  │
│       [████████████████░░░░░░░░░░░░░░░░]  58%              │
│                                                             │
│       yourwebsite.com · github.com/org/repo                 │
│                    ← reminder of what's being analyzed      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 3a. Pulse Orb

A centered animated element. NOT a spinner. NOT a loading bar alone.

```css
/* A glowing cyan pulse orb */
.pulse-orb {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow:
    0 0 0 0 var(--accent-glow),
    0 0 24px 4px var(--accent-dim);
  animation: orb-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes orb-pulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 var(--accent-glow), 0 0 24px 4px var(--accent-dim);
  }
  50% {
    transform: scale(1.1);
    box-shadow: 0 0 0 16px rgba(6,182,212,0), 0 0 40px 12px var(--accent-dim);
  }
}

@media (prefers-reduced-motion: reduce) {
  .pulse-orb { animation: none; }
}
```

#### 3b. Stage Messages

Four distinct stages, each with its own message. They auto-advance on a timer, but also
respond to real backend events if you wire up a server-sent event stream:

| Stage | Message | Duration |
|---|---|---|
| 1 | `Crawling website...` | 3s |
| 2 | `Reading GitHub repo...` | 3s |
| 3 | `Analyzing with AI...` | 6s |
| 4 | `Generating artifacts...` | 3s |

**Visual spec:**
- Font: `var(--font-code)`, 14px, `var(--text-secondary)`
- Only ONE message visible at a time
- Transition: the outgoing message fades out (`opacity: 0`) and the incoming fades in
  (`opacity: 1`) over `300ms ease`. No slide, no bounce — just opacity.
- A blinking cursor `_` at the end of each message, in `var(--accent)`:
  ```
  Analyzing with AI..._
  ```
  The cursor blinks at `1s` interval (CSS `animation: blink 1s step-end infinite`)

#### 3c. Progress Bar

```css
.progress-bar-track {
  height: 2px;                   /* very thin — not chunky */
  background: var(--border-subtle);
  border-radius: 9999px;
  width: 320px;
  max-width: 90%;
}
.progress-bar-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 9999px;
  box-shadow: 0 0 8px 1px var(--accent-glow);  /* subtle glow on the fill */
  transition: width 600ms ease-out;
}
```

Progress is pseudo-animated across the 4 stages (not real-time from backend):
- Stage 1: 0% → 20%
- Stage 2: 20% → 45%
- Stage 3: 45% → 80%
- Stage 4: 80% → 100%

When transitioning to 100%, add a brief `flash` keyframe that brightens the fill bar,
then fade the entire loading view out over `400ms` as the results slide in.

#### 3d. URL Reminder

```
yourwebsite.com · github.com/org/repo
```
- Font: `var(--font-code)`, 12px, `var(--text-muted)`
- Show only the domains, not the full paths
- If only one URL was provided, show only that one

---

### 4. Results View (View C)

This view scrolls. It does not fit in one screen — that is fine and expected.

**Entry animation:** The results view fades in over `300ms` as the loading view fades out.
Use a `translateY(-8px)` + `opacity: 0` → `translateY(0)` + `opacity: 1` — one clean entrance,
then no more animation.

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  RESULTS HEADER BANNER                                      │
│  yourwebsite.com · github.com/org/repo → full analysis done │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  PRODUCT SUMMARY CARD                                       │
│  Product name + one-line description                        │
│                                                             │
│  AUDIT SCORE CARD                                           │
│  Big number + score breakdown grid                          │
│                                                             │
│  ARTIFACT SECTION                                           │
│  Tab bar: [llms.txt] [Audit] [MCP Server] [OpenAPI]         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Code viewer with syntax highlighting                 │   │
│  │  + copy button + download button                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

#### 4a. Results Header Banner

A slim banner above the score card. Not a full-width colored block — just a line of text.

```
✓  Analysis complete for yoursite.com  ·  ~12 seconds
```

- Font: Inter 500, 14px
- `✓` checkmark in `var(--score-good)` — `#22c55e`
- Domain name in `var(--text-primary)`
- Dot separator and timing info in `var(--text-muted)`
- No background color — sits directly on `var(--bg-base)`
- `margin-bottom: var(--space-6)`

---

#### 4b. Product Summary Card

A single card showing what the AI understood about the product.

```
┌──────────────────────────────────────────────────────────┐
│  Acme Invoice API                    [API]  [REST]        │
│  A REST API for managing customer invoices and payments.  │
│                                                           │
│  Auth: API Key    Stack: Node.js, Express, PostgreSQL     │
└──────────────────────────────────────────────────────────┘
```

**Spec:**
- Background: `var(--bg-surface)`
- Border: `1px solid var(--border-subtle)`
- Border radius: `8px`
- Padding: `var(--space-6)` on all sides
- Product name: Inter 600, 18px, `var(--text-primary)`, tracking `-0.02em`
- Badges (`[API]`, `[REST]`): Monospace 11px, `var(--text-muted)`, border `var(--border-default)`, border-radius `9999px`, padding `2px 8px`. No background color.
- Description: Inter 400, 15px, `var(--text-secondary)`, `margin-top: 8px`
- Meta row (`Auth:`, `Stack:`): 13px, `var(--text-muted)`. The label (`Auth:`) in `var(--text-muted)`, the value (`API Key`) in `var(--text-secondary)`.

---

#### 4c. Audit Score Card

This is the **hero component of the results page**. It should command attention without decoration.

```
┌──────────────────────────────────────────────────────────┐
│                                                           │
│   Agent Readiness Score                                   │
│                                                           │
│              42                                           │
│          ──────────── /100                                │
│                                                           │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│   │ ✓ Has API    │  │ ✗ llms.txt   │  │ ✓ API Key    │  │
│   │   20 pts     │  │    0 pts     │  │   auth       │  │
│   └──────────────┘  └──────────────┘  └──────────────┘  │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│   │ ✗ OpenAPI   │  │ ✓ Docs found │  │ ✗ Webhooks  │  │
│   │   0 pts      │  │   15 pts     │  │   0 pts      │  │
│   └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

**Score number spec:**
- Font: `var(--font-code)` — JetBrains Mono
- Size: `5rem` (80px)
- Weight: 500
- Color: determined by score:
  - 0–39: `var(--score-bad)` — red
  - 40–69: `var(--score-warn)` — amber
  - 70–100: `var(--score-good)` — green
- **Animated counter:** The number counts up from `0` to the final score over `1200ms`
  using a custom easeOut counter (not CSS — a JS `requestAnimationFrame` loop).
  This is the ONE animation moment. It earns attention and immediately communicates
  that something real was calculated.

```javascript
// Counter animation — use this exact approach
function animateCounter(target, duration, element) {
  const start = performance.now();
  function frame(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    // easeOutQuart
    const eased = 1 - Math.pow(1 - progress, 4);
    element.textContent = Math.round(eased * target);
    if (progress < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}
```

**Score breakdown grid:**
- 6 cells in a 3×2 grid
- Each cell is a small card: `background: var(--bg-surface)`, `border: 1px solid var(--border-subtle)`, `border-radius: 8px`, `padding: 12px 16px`
- Passing cells: `border-left: 2px solid var(--score-good)`, icon `✓` in green
- Failing cells: `border-left: 2px solid var(--score-bad)`, icon `✗` in red
- Label: 13px Inter 500, `var(--text-primary)`
- Points: 12px `var(--font-code)`, `var(--text-muted)`
- The 6 checks (in order):
  1. Has public API
  2. Has llms.txt
  3. Has OpenAPI spec
  4. Has structured docs
  5. API key auth available
  6. Webhook support

---

#### 4d. Artifact Tabs + Viewer

The tabs section is the largest and most interactive part of the results page.

**Tab Bar:**
```
[ llms.txt ]  [ Audit Report ]  [ MCP Server ]  [ OpenAPI Spec ]
```

**Tab bar spec:**
- Background: `var(--bg-surface)`
- Border: `1px solid var(--border-subtle)` — on all sides, wrapping the whole tab+panel unit
- Border radius: `8px` on the outer container
- The tab bar itself has a `border-bottom: 1px solid var(--border-subtle)` separating it from the panel
- Tabs: `padding: 10px 16px`, font Inter 500, 14px
  - Inactive: `var(--text-muted)`, background `transparent`
  - Active: `var(--text-primary)`, background `var(--bg-elevated)`, `border-bottom: 2px solid var(--accent)` (accent underline, not a background color)
  - Hover: `var(--text-secondary)`, background `var(--bg-elevated)` at 50% opacity
  - Transition: `color 120ms ease, background 120ms ease`
- File name badges next to each tab label, monospaced 11px, `var(--text-muted)`:
  - `llms.txt` → label: `llms.txt`
  - `Audit Report` → label: `audit.md`
  - `MCP Server` → label: `mcp_server.ts`
  - `OpenAPI Spec` → label: `openapi.yaml`
- On mobile (< 640px): tabs scroll horizontally with `overflow-x: auto`, `white-space: nowrap`

**Code Viewer Panel:**

```
┌─────────────────────────────────────────────────────────────┐
│  llms.txt                        [Copy]  [Download ↓]       │
├─────────────────────────────────────────────────────────────┤
│  1  # Acme Invoice API                                      │
│  2                                                          │
│  3  > A REST API for managing customer invoices...          │
│  4                                                          │
│  5  ## Key Actions                                          │
│  6  - Create invoice: POST /invoices                        │
│  ...                                                        │
└─────────────────────────────────────────────────────────────┘
```

**Panel spec:**
- Background: `#0d0d0f` — slightly darker than `--bg-base` for contrast
- No additional border (it's inside the outer card's border)
- Padding: `0` — the code goes edge to edge inside the panel
- Min-height: `480px`
- Max-height: `640px`
- `overflow-y: auto`
- `overflow-x: auto`

**Code viewer header (above the code):**
- Height: `44px`
- Background: `var(--bg-surface)`
- Border-bottom: `1px solid var(--border-subtle)`
- Left: file name in `var(--font-code)`, 13px, `var(--text-secondary)`
- Right: two buttons — `Copy` and `Download`
- Padding: `0 var(--space-4)`

**Syntax highlighting colors:**
Use a custom dark theme for `react-syntax-highlighter` that matches the design system.
```javascript
// Custom syntax theme for react-syntax-highlighter
const agentReadyTheme = {
  'code[class*="language-"]': {
    color: '#e4e4e7',           // --text-code: default text
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '13px',
    lineHeight: '1.7',
    background: 'transparent',
  },
  'comment': { color: '#52525b' },   // muted — comments are quiet
  'keyword': { color: '#06b6d4' },   // accent cyan — keywords pop
  'string':  { color: '#86efac' },   // soft green — strings
  'number':  { color: '#fca5a5' },   // soft red — numbers
  'function':{ color: '#c4b5fd' },   // soft purple — function names
  'operator':{ color: '#94a3b8' },   // slate — operators
  'property':{ color: '#7dd3fc' },   // light blue — object keys
  'punctuation': { color: '#52525b' },
};
```

**Line numbers:**
- Show line numbers on all tabs
- Color: `var(--text-muted)`, `user-select: none`
- Width: `44px`, right-aligned, `border-right: 1px solid var(--border-subtle)`, `margin-right: 16px`

**Scrollbar (custom styling for Webkit):**
```css
.code-viewer::-webkit-scrollbar { width: 6px; height: 6px; }
.code-viewer::-webkit-scrollbar-track { background: transparent; }
.code-viewer::-webkit-scrollbar-thumb {
  background: var(--border-default);
  border-radius: 9999px;
}
.code-viewer::-webkit-scrollbar-thumb:hover {
  background: var(--border-strong);
}
```

---

#### 4e. Copy and Download Buttons

These are ghost/outline buttons. Small. Never primary-styled.

**Copy button:**
```
[  Copy  ]
```
- Height: `32px`, padding: `0 12px`
- Background: `transparent`
- Border: `1px solid var(--border-default)`
- Border radius: `8px`
- Font: Inter 500, 13px, `var(--text-secondary)`
- Hover: `background: var(--bg-elevated)`, border `var(--border-strong)`
- On click: icon changes from `Copy` to `✓ Copied` for `2000ms`, then reverts
- No toast, no modal — just the button label change

**Download button:**
```
[  Download ↓  ]
```
- Same size and style as Copy button
- On click: triggers a JS `Blob` download with the correct filename and extension:
  - Tab 1: `llms.txt`
  - Tab 2: `audit-report.md`
  - Tab 3: `mcp_server.ts`
  - Tab 4: `openapi.yaml`
- The file is downloaded immediately — no confirmation, no progress.

---

### 5. Error State

If the backend returns an error (website unreachable, repo not found, etc.):

```
┌──────────────────────────────────────────────────────────┐
│  ⚠  Could not reach https://yoursite.com                 │
│     The site returned a 403. Try the GitHub URL alone.   │
└──────────────────────────────────────────────────────────┘
```

**Spec:**
- This appears below the input fields in View A (the user is taken back to the input view)
- Background: `var(--score-bad-bg)` — `rgba(239, 68, 68, 0.10)`
- Border: `1px solid rgba(239, 68, 68, 0.25)`
- Border-radius: `8px`
- Border-left: `3px solid var(--score-bad)` — accent left border, not full
- Icon `⚠`: `var(--score-bad)`, 14px
- Title text: Inter 500, 14px, `var(--text-primary)` — the error in plain English
- Sub-text: Inter 400, 13px, `var(--text-secondary)` — what to do about it
- Padding: `12px 16px`
- Fade in: `opacity: 0` → `1` over `200ms`
- The inputs are restored with the previous values so the user can edit without re-typing

---

## Motion & Animation Summary

**Do:**
- Score counter animation (one-time, on results reveal)
- Progress bar fill transition (driven by stage advancement)
- Pulse orb breathing animation during loading
- Cursor blink on loading status text
- Focus ring fade-in on inputs (`150ms ease`)
- Results view entrance: `translateY(-8px) opacity(0)` → `translateY(0) opacity(1)`, `300ms ease-out`
- Tab switch: cross-fade between panels, `150ms ease`
- Button hover: `filter: brightness` change, `100ms`
- "Copied" label swap on copy button

**Do not:**
- Scroll-triggered fade-ins on any section (no `IntersectionObserver` animations)
- Hover lift (`translateY(-2px)`) on cards
- Gradient color animations
- Spinning logos or loading icons (the pulse orb is the only exception)
- Stagger animations on the score breakdown grid items
- Page transitions between views (just opacity cross-fade)

**Reduced motion:**
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
  .pulse-orb { animation: none; box-shadow: 0 0 12px 4px var(--accent-dim); }
}
```

---

## Mobile Responsiveness

Breakpoints:
- `sm`: 640px — inputs go full width, tabs scroll horizontally
- `md`: 768px — code viewer shrinks to `min-height: 320px`

**At < 640px:**
- Landing copy reduces to `text-align: left` (centered headings look awkward on narrow screens)
  — Exception: the display headline stays centered
- Input fields and button go full width (`100%`)
- Score breakdown grid becomes 2×3 (2 columns instead of 3)
- Tab labels lose the file name badge — just the human label (`llms.txt`, `Audit`, `MCP`, `API`)
- Header drops the GitHub link
- Code font size reduces to `12px`

**At < 400px:**
- Display headline font size floors at `2rem`
- Tab bar shows abbreviated labels: `txt`, `Audit`, `MCP`, `YAML`

---

## Accessibility

- All inputs have visible `<label>` elements (not just placeholders)
  — position the labels visually above the input
- Tab order: Header → Inputs → Submit button → (Results: tabs, then download buttons)
- Focus styles: always visible, using the `--accent` focus ring (never removed)
- Error messages are announced via `role="alert"` on the error container
- The score number has `aria-label="Agent readiness score: 42 out of 100"`
- Code panels have `role="region"` and `aria-label="[tab name] output"`
- Loading state has `role="status"` and `aria-live="polite"` so screen readers announce stage changes
- Color is never the sole indicator of meaning — passing/failing checks show `✓`/`✗` icons in addition to color

---

## Tailwind Configuration

Add these to `tailwind.config.js` so custom colors are available as utility classes:

```javascript
// tailwind.config.js
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'bg-base':     '#09090b',
        'bg-surface':  '#111113',
        'bg-elevated': '#18181b',
        'accent':      '#06b6d4',
        'accent-dim':  'rgba(6,182,212,0.12)',
        'text-primary':'#f4f4f5',
        'text-secondary':'#a1a1aa',
        'text-muted':  '#52525b',
        'border-subtle': 'rgba(255,255,255,0.07)',
        'border-default':'rgba(255,255,255,0.11)',
        'score-good':  '#22c55e',
        'score-warn':  '#f59e0b',
        'score-bad':   '#ef4444',
      },
      fontFamily: {
        ui:   ['Inter', 'system-ui', 'sans-serif'],
        code: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      fontSize: {
        'display': ['clamp(2.5rem, 5vw, 4rem)', { lineHeight: '1.05', letterSpacing: '-0.04em' }],
      },
      borderRadius: {
        DEFAULT: '8px',   /* override tailwind's default so `rounded` = 8px */
      },
    },
  },
  plugins: [],
};
```

---

## React Component Map

```
App
├── Header
├── LandingView (shown when state === 'idle')
│   ├── DotGridBackground
│   ├── CategoryLabel
│   ├── Headline
│   ├── SubCopy
│   └── InputForm
│       ├── UrlInput (x2)
│       ├── SubmitButton
│       ├── MicroCopy
│       └── ErrorBanner (conditional)
├── LoadingView (shown when state === 'loading')
│   ├── PulseOrb
│   ├── StageMessage
│   ├── ProgressBar
│   └── UrlReminder
└── ResultsView (shown when state === 'done')
    ├── ResultsBanner
    ├── ProductSummaryCard
    ├── AuditScoreCard
    │   ├── ScoreCounter
    │   └── ScoreBreakdownGrid
    └── ArtifactSection
        ├── TabBar
        └── ArtifactPanel
            ├── PanelHeader (filename + Copy + Download buttons)
            └── CodeViewer (syntax-highlighted, scrollable)
```

**State management:** Use `useState` for `appState: 'idle' | 'loading' | 'done' | 'error'`
and `results: ResultsData | null`. No external state library needed for MVP.

---

## Copy Guidelines

Every word in this UI is a design decision. Follow these rules:

- **Button:** `Analyze my product` — not "Analyze", not "Submit", not "Generate"
- **Loading messages:** End in `...` — conveys ongoing work without false precision
- **Error messages:** State what failed in plain English, then tell the user what to try next.
  Example: `The GitHub repo wasn't found. Check the URL or make sure it's public.`
  Never: `Error 404` alone.
- **Score header:** `Agent Readiness Score` — not "Your Score" or "AI Score"
- **Tab labels:** `llms.txt`, `Audit Report`, `MCP Server`, `OpenAPI Spec`
  — match the deliverable names exactly, not technical jargon like "Artifacts"
- **Download button:** `Download` + filename — `Download llms.txt` on hover/tooltip
- **Empty states:** If for some reason a tab has no content (parse failure): `Nothing to show here.
  The analysis didn't detect enough [routes/docs/API surface] to generate this file.`

---

## What This UI Should Feel Like

Open Vercel's dashboard. Open Linear. Open Resend. These tools feel like they were built
by one person who cared a great deal about every detail, and then enforced those details across
the whole product. That is the tone to match.

The user lands on the page and immediately understands the one thing it does. They type two
URLs. They wait 15 seconds while the tool visibly does work. The results arrive and they can
immediately tell if their product is agent-ready or not. They download the files and leave.

Nothing about this experience apologizes for itself. It does not have an animated hero illustration.
It does not have a testimonials section. It does not have an elaborate onboarding flow.
It is a tool. It works. It gets out of the way.
