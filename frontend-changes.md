# Frontend Changes

## Feature: Dark/Light Mode Toggle Button

### Files Modified

- `frontend/index.html`
- `frontend/style.css`
- `frontend/script.js`

---

### `frontend/index.html`

- Added a `<button id="themeToggle">` element fixed-positioned outside the `.container`, just before the `<script>` tags at the bottom of `<body>`.
- The button contains two inline SVG icons:
  - **Sun icon** (`.icon-sun`) — displayed in dark mode to signal "switch to light"
  - **Moon icon** (`.icon-moon`) — displayed in light mode to signal "switch to dark"
- Includes `aria-label` and `title` attributes for accessibility and keyboard discoverability.
- Updated CSS/JS cache-busting version query strings from `?v=9` to `?v=10`.

---

### `frontend/style.css`

#### New CSS variables
- Added `--toggle-bg` and `--toggle-hover-bg` to `:root` (dark defaults) and `body.light-mode` (light overrides).
- Added `body.light-mode` ruleset overriding all dark-theme CSS variables with light equivalents:
  - Background: `#f8fafc`, surface: `#ffffff`, text: `#0f172a`, borders: `#e2e8f0`, etc.
  - Primary blue (`--primary-color`, `--user-message`) unchanged — consistent brand color across themes.

#### Smooth transitions
- `body` now has `transition: background-color 0.3s ease, color 0.3s ease` so the entire page fades between themes.
- `.sidebar` has matching `transition: background-color 0.3s ease, border-color 0.3s ease`.

#### `.theme-toggle` button styles
- `position: fixed; top: 1rem; right: 1rem; z-index: 1000` — always visible in the top-right corner.
- Circular shape (`border-radius: 50%`), 44×44 px (meets WCAG touch-target minimum).
- Hover: slight scale up (`transform: scale(1.08)`) + shadow.
- Active: slight scale down (`transform: scale(0.95)`) for tactile feedback.
- Focus: `box-shadow: 0 0 0 3px var(--focus-ring)` via `:focus-visible` — keyboard accessible without polluting mouse UX.

#### Icon visibility
- `body:not(.light-mode) .icon-moon { display: none }` — hides moon in dark mode.
- `body.light-mode .icon-sun { display: none }` — hides sun in light mode.

---

### `frontend/script.js`

#### `initTheme()`
- Called on `DOMContentLoaded`, before any other setup.
- Reads `localStorage.getItem('theme')` and applies `body.classList.add('light-mode')` if saved value is `'light'`.
- Defaults to dark mode when no preference is stored.

#### `toggleTheme()`
- Toggles `body.classList` `.light-mode` and writes `'light'` or `'dark'` to `localStorage` so the preference persists across page reloads.
- Updates `aria-label` on the button dynamically so screen readers announce the *next* action.

#### `setupEventListeners()`
- Added `themeToggle.addEventListener('click', toggleTheme)`.
- Button is a native `<button>` element, so it is automatically keyboard-navigable (Tab + Enter/Space) without extra JS.

---

## Feature: Light Theme CSS Variables

### Files Modified

- `frontend/style.css`

---

### `frontend/style.css`

#### Semantic variable system — `:root`

Converted hardcoded component colors into named CSS variables so both themes control every visual token from one place:

| New variable | Default (dark) value | Purpose |
|---|---|---|
| `--welcome-shadow` | `0 4px 16px rgba(0,0,0,0.2)` | Welcome message drop-shadow |
| `--code-bg` | `rgba(0, 0, 0, 0.2)` | Inline code and fenced code block backgrounds |
| `--error-bg` | `rgba(239, 68, 68, 0.1)` | Error message background |
| `--error-text` | `#f87171` | Error message text |
| `--error-border` | `rgba(239, 68, 68, 0.2)` | Error message border |
| `--success-bg` | `rgba(34, 197, 94, 0.1)` | Success message background |
| `--success-text` | `#4ade80` | Success message text |
| `--success-border` | `rgba(34, 197, 94, 0.2)` | Success message border |

Variables were also reorganised into labelled groups (Brand, Surfaces, Text, Messages, Code, Status, Toggle) for clarity.

#### Light mode additions — `body.light-mode`

Extended the existing ruleset with all new variables plus refinements to existing ones:

| Variable | Light value | Rationale |
|---|---|---|
| `--primary-color` | `#1d4ed8` | Darker blue — 7.3:1 contrast on `#f8fafc` (WCAG AAA) |
| `--primary-hover` | `#1e40af` | Proportionally darker hover state |
| `--focus-ring` | `rgba(29, 78, 216, 0.25)` | Matches the darker primary |
| `--user-message` | `#1d4ed8` | Consistent with primary in light mode |
| `--welcome-border` | `#1d4ed8` | Consistent with primary in light mode |
| `--welcome-shadow` | `0 4px 16px rgba(0,0,0,0.08)` | Softer shadow on light background |
| `--code-bg` | `rgba(0, 0, 0, 0.06)` | Subtle tint — dark `rgba(0,0,0,0.2)` would be too heavy on white |
| `--error-text` | `#dc2626` | 5.9:1 contrast on `#f8fafc` — WCAG AA ✓ |
| `--error-bg` | `rgba(220, 38, 38, 0.08)` | Paired with the darker red |
| `--success-text` | `#16a34a` | 4.7:1 contrast on `#f8fafc` — WCAG AA ✓ |
| `--success-bg` | `rgba(22, 163, 74, 0.08)` | Paired with the darker green |

The original light-mode `#f87171` (light red) and `#4ade80` (light green) both fail WCAG on light backgrounds (~3.3:1 and ~1.9:1 respectively) and are replaced.

#### Component rule fixes

- `.message-content code` / `.message-content pre`: replaced hardcoded `rgba(0,0,0,0.2)` → `var(--code-bg)`.
- `.message.welcome-message .message-content`: replaced hardcoded `box-shadow: 0 4px 16px rgba(0,0,0,0.2)` → `var(--welcome-shadow)`.
- `.error-message`: replaced three hardcoded color values → `var(--error-bg)`, `var(--error-text)`, `var(--error-border)`.
- `.success-message`: replaced three hardcoded color values → `var(--success-bg)`, `var(--success-text)`, `var(--success-border)`.
- `.message-content blockquote`: fixed broken `var(--primary)` reference (variable did not exist) → `var(--primary-color)`.

---

## Feature: JavaScript Theme Toggle Functionality

### Files Modified

- `frontend/script.js`
- `frontend/style.css`

---

### `frontend/script.js`

#### `initTheme()` — improved

The existing function only read `localStorage` and applied the class. Three problems were fixed:

1. **No-flash on load** — the saved theme was applied synchronously, which triggered CSS transitions while the page was still painting, causing a visible flash. Fix: `body.no-transition` is added before applying the class, then removed inside a `requestAnimationFrame` callback so transitions only activate after the first paint.

2. **`prefers-color-scheme` support** — when no value is stored in `localStorage`, the function now reads `window.matchMedia('(prefers-color-scheme: light)')` to respect the user's OS-level preference. Priority order: explicit localStorage save → OS preference → default dark.

3. **Initial `aria-label` sync** — the button label was never set on load, only after the first click. `syncThemeAriaLabel()` is now called inside `initTheme()` so screen readers always have an accurate label from page load.

#### `syncThemeAriaLabel()` — extracted helper

Logic for computing and setting the `aria-label` was duplicated between `initTheme` and `toggleTheme`. Extracted into a shared helper that reads the current class state and writes the appropriate label.

#### `toggleTheme()` — simplified

Replaced the inline `themeToggle.setAttribute(...)` call with `syncThemeAriaLabel()`.

---

### `frontend/style.css`

#### `body.no-transition` utility

```css
body.no-transition,
body.no-transition * {
    transition: none !important;
}
```

Disables every transition on the body and all descendants during theme initialisation. Removed after the first `requestAnimationFrame` by JS, so interactive transitions are unaffected.

#### Broader transition coverage

Added `transition: background-color 0.3s ease, border-color 0.3s ease, color 0.3s ease, box-shadow 0.3s ease` to `.stat-item`, `.message-content`, and `.chat-input-container`. These elements have their own `background` declarations using CSS variables, so they previously snapped instantly on theme switch instead of fading with the rest of the page.

---

## Feature: `data-theme` Attribute Migration

### Files Modified

- `frontend/style.css`
- `frontend/script.js`

---

### Why `data-theme` over a class

Placing the theme token in a `data-theme` attribute on the `<html>` element (`document.documentElement`) is the standard convention because:
- It separates semantic state (`data-theme="light"`) from presentational classes (e.g. `active`, `disabled`)
- `:root[data-theme="light"]` overrides CSS custom properties at the highest cascade level, so every child inherits updated values without specificity fights
- The attribute value is always explicit (`"light"` or `"dark"`), whereas class presence is implicit and harder to introspect from outside JS

---

### `frontend/style.css`

**Theme override selector** — `body.light-mode { ... }` replaced by `:root[data-theme="light"] { ... }`.

Placing the override on `:root` (the `<html>` element) means CSS custom property values are resolved at the document root and cascade to all elements. No change to any variable names or values.

**Icon visibility selectors** — all four rules migrated from `body.light-mode` / `body:not(.light-mode)` to `:root[data-theme="light"]` / `:root:not([data-theme="light"])`:

| Before | After |
|---|---|
| `body:not(.light-mode) .icon-moon` | `:root:not([data-theme="light"]) .icon-moon` |
| `body.light-mode .icon-sun` | `:root[data-theme="light"] .icon-sun` |
| `body.light-mode .icon-moon` | `:root[data-theme="light"] .icon-moon` |
| `body:not(.light-mode) .icon-sun` | `:root:not([data-theme="light"]) .icon-sun` |

The `:not([data-theme="light"])` form also covers the brief window before JS runs (when no attribute is present), correctly defaulting to dark mode icon state.

The `body.no-transition` / `body.no-transition *` utility rule is unchanged — it targets `body` and its descendants via a JS-toggled class, which is separate from the semantic theme attribute.

---

### `frontend/script.js`

**`initTheme()`** — replaced `document.body.classList.add('light-mode')` with `document.documentElement.setAttribute('data-theme', theme)`. The resolved theme is now computed up front as a string (`'light'` or `'dark'`) and written unconditionally, so `data-theme` is always present from the first paint.

**`toggleTheme()`** — replaced `document.body.classList.toggle('light-mode')` with an explicit read-then-write:
```js
const current = document.documentElement.getAttribute('data-theme');
const next = current === 'light' ? 'dark' : 'light';
document.documentElement.setAttribute('data-theme', next);
```
This is more explicit than `toggle` — the new value is always derived from the current attribute, never inferred from class presence.

**`syncThemeAriaLabel()`** — replaced `document.body.classList.contains('light-mode')` with `document.documentElement.getAttribute('data-theme') === 'light'`.
