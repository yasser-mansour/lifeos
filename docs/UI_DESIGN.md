# UI Design System

Source: `backend/static/css/{tokens,base,layout,components,charts}.css` (desktop) and `android/.../ui/theme/{Color,Type,Theme}.kt` (Android — the same token values, ported to Compose `Color`/`Typography`).

## Principles

- Hierarchy through typography weight and color, not box-per-item. Cards are used for genuine containment (a stat surface, a modal), not as the default wrapper for every list row — see `components.css`'s `.list-row` (a plain row with a subtle bottom border) versus `.surface` (an actual bordered/padded container), and use the latter sparingly.
- Three text tiers per the spec's own example: primary (the number/title itself), secondary (what it is), tertiary (when/where/how). A study session shows `2h 14m` in `--text-2xl`/`--text-primary`, `Mathematics · Calculus` in `--text-md`/`--text-secondary`, and `09:32–11:46 · Galaxy A25 · Stopwatch` in `--text-xs`/`--text-muted`.
- Dark mode is a deliberate second palette (`DarkPalette` in tokens), not an inverted light mode — backgrounds step through three near-black layers (`--bg-primary` → `--bg-secondary` → `--surface-secondary`) rather than one pure black, and the accent color shifts to a lighter indigo (`#8B93F5` vs `#4954E0`) for contrast against dark surfaces rather than reusing the light-mode accent at reduced opacity.

## Tokens

```css
--bg-primary / --bg-secondary
--surface-primary / --surface-secondary / --surface-hover
--border-subtle / --border-strong
--text-primary / --text-secondary / --text-muted
--accent / --accent-soft
--success / --warning / --danger (+ -soft variants for badge backgrounds)
--chart-1..6 (categorical series) / --chart-grid
```

Spacing (`--space-1` through `--space-16`, 4px base unit), radii (`--radius-sm` 6px through `--radius-full`), and a two-speed transition scale (`--transition-fast` 120ms, `--transition-base` 180ms) round out the token set. Every value used in a template traces back to one of these — there are no ad hoc hex colors or pixel values scattered through the CSS files (a few one-off `style="..."` attributes in templates use `var(--space-*)` tokens directly rather than literal pixel numbers, for the same reason).

## Typography

System font stack (`-apple-system, "SF Pro Text", ...`) — no bundled/CDN webfont, so the app always renders in the OS's native font with zero network dependency, matching the "no internet requirement" constraint. Numbers (money, durations, timers) use `var(--font-mono)` with `font-variant-numeric: tabular-nums`, which is what keeps a column of dollar amounts visually aligned and gives the Study timer's digits a steady, non-jittering width as they change every second.

## Layout

`app-shell` → `sidebar` (232px, collapsible to a 68px icon rail, persisted via `localStorage`) + `main`. Below 980px width, the sidebar becomes an off-canvas panel behind a hamburger toggle in a `mobile-topbar` (spec §105: "Sidebar should collapse sensibly. Do not merely scale everything down.") — verified by hand at narrow widths during this build, since it's exactly the kind of thing that silently breaks without a real render check (see the root README's testing notes for the sidebar-visibility bug this caught).

Three interaction surfaces, used consistently rather than interchangeably (spec §101):
- **Drawer** (`.drawer`, slides from the right) — task detail, person detail, study session quick-view. Fetched as an HTML fragment (`data-drawer-url` + `LifeOS.loadDrawer()` in `app.js`) so opening one doesn't reload the page.
- **Modal** (`.modal-backdrop` + `.modal`) — quick creation (new task/project/account/etc.) and confirmations.
- **Dedicated page** — Project, Course, Writing chapter: enough content that a drawer would feel cramped.

## Command palette

`Cmd/Ctrl+K` (`static/js/app.js::Palette`) opens a centered overlay, debounced-fetches `/search/api/` as you type, and renders grouped, keyboard-navigable results (arrow keys + Enter) using the same icon set as the sidebar.

## Icons

One small hand-authored set (`apps/core/templatetags/icons.py`) — geometric, single stroke-weight (1.75), 24×24 viewBox, round caps — rather than pulling in an icon library or mixing emoji into production navigation (spec §111). Chosen over a third-party set specifically so the whole icon vocabulary is one file, reviewable in one pass, and never dependent on a CDN.

## Charts

No charting library — bars, the study heatmap, and distribution rows are all plain HTML/CSS (`static/css/charts.css`: `.chart-bar`, `.heatmap-cell[data-level]`, `.legend-bar-fill`), sized with inline `style="width:...%"` computed server-side or via the `percent` template filter. This keeps every chart themeable through the same token system as everything else and avoids a JS charting dependency for what are, so far, fairly simple visualizations (bar heights and a 5-level heatmap).

## What deliberately isn't literal drawer/modal/page purity

A few screens compromise for build-time reasons and say so in their own comments rather than pretending otherwise — e.g. `templates/study/active.html`'s Pomodoro break handling reuses pause/resume events rather than a fully separate phase-transition UI. Nothing user-facing is a placeholder; where scope was trimmed, it was trimmed at the level of "simpler mechanism, same real behavior," not "fake it."
