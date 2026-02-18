# Frontend Changes

## Feature: Dark / Light Theme Toggle

### Files Modified

#### `frontend/index.html`
- **FOUC prevention**: Added an inline `<script>` in `<head>` that reads `localStorage.getItem('theme')` and immediately sets `data-theme` on `<html>` before any paint, eliminating flash-of-unstyled-content when the saved theme is light.
- **Toggle button**: Added a fixed-position `<button id="themeToggle" class="theme-toggle">` just before `</body>`. Contains two inline SVGs — `.icon-sun` (visible in dark mode) and `.icon-moon` (visible in light mode) — both present in the DOM at all times so CSS transitions can animate between them.
- **Cache-buster versions**: bumped `style.css?v=10` → `v=11` and `script.js?v=9` → `v=10`.

#### `frontend/style.css`
Four new sections appended after the existing responsive breakpoints:

1. **Light theme variables** (`[data-theme="light"]`)
   Overrides every `:root` CSS custom property with light-appropriate values:
   - `--background: #f1f5f9` — light slate-gray page background
   - `--surface: #ffffff` — white card/sidebar surface
   - `--surface-hover: #e2e8f0`
   - `--text-primary: #0f172a` — near-black for strong contrast
   - `--text-secondary: #64748b`
   - `--border-color: #cbd5e1`
   - `--shadow`, `--focus-ring`, `--welcome-bg`, `--welcome-border` adjusted for light context

2. **Smooth theme transitions**
   Targeted `transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease` added to `body`, `.sidebar`, `.chat-main`, `.chat-container`, `.chat-messages`, `.chat-input-container`, `.message-content`, `.stat-item`, `.course-title-item`. Elements that already have `transition: all` (e.g. `#chatInput`, `.suggested-item`) are intentionally excluded to avoid overriding their existing hover/focus animations.

3. **Theme toggle button styles** (`.theme-toggle`)
   - `position: fixed; top: 1rem; right: 1rem` — top-right corner, always visible
   - 40 × 40 px circle with `border-radius: 50%`
   - Uses `--surface`, `--border-color`, `--text-secondary` CSS variables so it automatically adapts to both themes
   - Hover: scale 1.08, primary-color border/icon tint
   - Focus: `box-shadow: 0 0 0 3px var(--focus-ring)` for keyboard accessibility
   - Active: scale 0.9 for tactile feedback
   - Both SVG icons use `position: absolute` + `opacity` + `transform: rotate()` transitions to create a smooth crossfade-with-rotation swap on theme change:
     - Dark mode → sun fades in at 0°, moon fades out at 90°
     - Light mode → moon fades in at 0°, sun fades out at −90°

4. **Light theme specific overrides**
   - `.sources-content a`: blue pill links re-colored for a light background
   - `.sources-content span`: muted pill adjusted
   - `.message-content code` / `pre`: `rgba(0,0,0,0.06)` tint instead of the darker dark-mode value

#### `frontend/script.js`
- **`initTheme()`**: Called on `DOMContentLoaded`; reads the `data-theme` already set by the inline head script and syncs the toggle button's `aria-label`.
- **`toggleTheme()`**: Reads current `data-theme` from `document.documentElement`, flips it between `'dark'` and `'light'`, writes back to the element and to `localStorage`, then calls `updateToggleLabel()`.
- **`updateToggleLabel(theme)`**: Keeps the button's `aria-label` accurate (`"Switch to light theme"` / `"Switch to dark theme"`).
- **`setupEventListeners()`**: Wired `click` on `#themeToggle` to `toggleTheme()`.
- **`DOMContentLoaded` handler**: Added `initTheme()` call after `setupEventListeners()`.

### Design Decisions
- **`data-theme` on `<html>`** (not `<body>`) so the inline head script can set it before the body renders, preventing any flicker.
- **Dual SVG / opacity approach** instead of `display:none/block` so CSS transitions can animate the icon swap.
- **`localStorage` persistence** — the chosen theme survives page refresh and future visits.
- **Dark as default** — matches the existing stylesheet's `:root` variables; no additional selector needed for dark mode.
- **No `transition: all` override** — existing hover/interactive animations are preserved by only adding transitions to elements that didn't already have them.
