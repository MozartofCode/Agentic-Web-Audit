---
description: Design or review any frontend component for AgentReady. Use when building a new React component, generating Tailwind classes, checking a component against the design spec in UI.md, or debugging visual issues. Always consult this before writing any JSX or CSS.
---

# /ui — UI Design & Component Work

You are a frontend engineer with strong design sensibility working on AgentReady.
Before writing any JSX, you internalize the design system. Your output is production-ready
React — not a prototype, not a sketch.

---

## Step 0: Always Read These First

Before generating any component code, re-read the relevant section of `UI.md`:
- Building a new component? Find its spec in the "Component Specifications" section.
- Fixing a visual bug? Check the token in the "Color System" or "Spacing System" section.
- Not sure which section? Search `UI.md` for the component name.

The UI spec in `UI.md` is the **only** source of truth for visual decisions. If something
isn't in the spec, follow the design principles (dark, minimal, no decoration) and flag
it for the user to review.

---

## Design Token Quick Reference

These are the values from UI.md you'll use most. Never use anything outside this set.

```
BACKGROUNDS
--bg-base:        #09090b   ← page background
--bg-surface:     #111113   ← cards, panels
--bg-elevated:    #18181b   ← hover states, inputs, active tabs

BORDERS
--border-subtle:  rgba(255,255,255,0.07)
--border-default: rgba(255,255,255,0.11)
--border-focus:   #06b6d4   ← input focus ring only

TEXT
--text-primary:   #f4f4f5   ← headings, important values
--text-secondary: #a1a1aa   ← body copy, descriptions
--text-muted:     #52525b   ← placeholders, meta info

ACCENT (use sparingly — one element at a time)
--accent:         #06b6d4   ← cyan, CTAs, focus, score counter
--accent-dim:     rgba(6,182,212,0.12)

SCORE COLORS (audit breakdown only)
--score-good:     #22c55e
--score-warn:     #f59e0b
--score-bad:      #ef4444

FONTS
--font-ui:    'Inter', sans-serif
--font-code:  'JetBrains Mono', monospace

BORDER RADIUS: 8px everywhere (Tailwind: `rounded`)
```

---

## Component Generation Protocol

When asked to build a component, follow this order:

1. **Name and file location** — confirm the component name and where it lives in `src/components/`
2. **Props interface** — list props before writing code: what goes in, what comes out
3. **States** — list all visual states the component can be in (default, hover, active, error, loading, empty)
4. **Write the JSX** — use Tailwind utility classes from the token set above
5. **Write any custom CSS** — only if keyframes or pseudo-elements are needed (use a `.css` file, not inline styles)
6. **Self-review** — before outputting, check each item in the review checklist below

---

## Component Review Checklist

Run this before presenting any component. Fix all failures before outputting.

```
[ ] Uses only approved color tokens (no `gray-900`, `blue-500`, etc.)
[ ] Border radius is `rounded` (8px) everywhere — no `rounded-full` on rectangular elements
[ ] No inline styles (style={{...}}) except for CSS custom property values
[ ] All interactive elements have :hover and :focus states
[ ] Focus states use the --border-focus ring: `focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent`
[ ] Typography: headings use Inter 600+, body uses Inter 400, code uses JetBrains Mono
[ ] Error states are handled — component never shows a blank void
[ ] Loading states are handled — component shows a skeleton or the pulse orb, not a blank
[ ] Mobile: works at 380px width (stacks, doesn't overflow)
[ ] No animation except what's specified in UI.md (no hover translateY, no scroll effects)
[ ] prefers-reduced-motion respected: wrap animations in @media check
[ ] Accessibility: interactive elements are keyboard focusable, have aria-label if icon-only
```

---

## Common Patterns (Copy These)

### Standard card
```jsx
<div className="bg-bg-surface border border-border-subtle rounded p-6">
  {children}
</div>
```

### Ghost/outline button (Copy, Download)
```jsx
<button className="
  h-8 px-3
  bg-transparent
  border border-border-default
  rounded
  text-text-secondary text-[13px] font-medium font-ui
  hover:bg-bg-elevated hover:border-border-strong
  transition-colors duration-100
  focus:outline-none focus:ring-2 focus:ring-accent/30
">
  {label}
</button>
```

### Primary CTA button
```jsx
<button className="
  h-12 w-full
  bg-accent
  rounded
  text-bg-base text-[15px] font-semibold font-ui tracking-[-0.01em]
  hover:brightness-108
  active:brightness-92
  transition-all duration-100
  focus:outline-none focus:ring-2 focus:ring-accent/30
  disabled:opacity-40 disabled:cursor-not-allowed
">
  {label} →
</button>
```

### URL input field
```jsx
<div className="relative">
  <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text-muted text-base pointer-events-none">
    {icon}
  </span>
  <input
    className="
      w-full h-12
      bg-bg-elevated
      border border-border-default
      rounded
      pl-10 pr-4
      font-code text-[14px] text-text-secondary
      placeholder:text-text-muted
      focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/20
      transition-all duration-150
    "
    type="url"
    placeholder="https://..."
  />
</div>
```

### Monospaced badge/tag
```jsx
<span className="
  font-code text-[11px] text-text-muted
  border border-border-default
  rounded-full px-2 py-0.5
">
  {label}
</span>
```

---

## Dot Grid Background (Hero Section)

This is a pure CSS pattern — do NOT use a library or image for it.

```css
/* In a dedicated .css file, not Tailwind */
.dot-grid-bg {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(
    circle,
    rgba(255, 255, 255, 0.09) 1.5px,
    transparent 1.5px
  );
  background-size: 28px 28px;
  -webkit-mask-image: radial-gradient(ellipse 70% 60% at 50% 50%, black 40%, transparent 100%);
  mask-image: radial-gradient(ellipse 70% 60% at 50% 50%, black 40%, transparent 100%);
  pointer-events: none;
  z-index: 0;
}
```

---

## Pulse Orb (Loading State)

```css
.pulse-orb {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #06b6d4;
  animation: orb-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
@keyframes orb-pulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(6,182,212,0.25), 0 0 24px 4px rgba(6,182,212,0.12);
  }
  50% {
    transform: scale(1.1);
    box-shadow: 0 0 0 16px rgba(6,182,212,0), 0 0 40px 12px rgba(6,182,212,0.12);
  }
}
@media (prefers-reduced-motion: reduce) {
  .pulse-orb { animation: none; box-shadow: 0 0 12px 4px rgba(6,182,212,0.12); }
}
```

---

## Score Counter Animation

Do not use CSS for the number counter. Use this JS approach in a `useEffect`:

```javascript
useEffect(() => {
  if (score == null) return;
  const el = scoreRef.current;
  const duration = 1200;
  const start = performance.now();
  function frame(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 4); // easeOutQuart
    el.textContent = Math.round(eased * score);
    if (progress < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}, [score]);
```

---

## What NOT to Do

- ❌ No `bg-gray-*`, `text-gray-*`, `border-gray-*` — use custom tokens
- ❌ No gradient text effects on headings
- ❌ No hover `translateY(-2px)` on cards
- ❌ No `shadow-*` Tailwind classes — no box shadows for decoration
- ❌ No `rounded-xl`, `rounded-2xl`, `rounded-3xl` — use plain `rounded` (8px)
- ❌ No `font-bold` on body copy — only on headings and button labels
- ❌ No color-only error indicators — always pair color with icon or text
- ❌ No `transition-all` on elements with many properties — be specific: `transition-colors`
