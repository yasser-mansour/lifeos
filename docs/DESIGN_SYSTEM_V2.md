# LIFEOS Design System v2

Source of truth: `backend/static/css/{tokens,base,layout,components,charts}.css` (desktop) and `android/.../ui/theme/{Color,Type,Theme}.kt` (Android — same token values ported to Compose). This document explains the *decisions*, not just the values — read it before touching either.

## Why v2, and what actually changed

v1 (`docs/UI_DESIGN.md`) got the tokens right: a restrained neutral palette, one accent, semantic color used sparingly, a real (non-inverted) dark palette, tabular numerals, one hand-authored icon set, no charting library. None of that is being thrown away — it's extended.

What v1 didn't have, and what was actually wrong: **every module rendered through the same generic template** — `page-header` (title + primary button, top right) followed by a `.list` of rows. Tasks, Study, and Journal were structurally identical pages with different words on them. A restrained token system applied uniformly to a undifferentiated layout still reads as "one dashboard," because hierarchy and atmosphere live in composition, not just in color.

v2's actual addition is **per-module atmosphere as a first-class design decision** — not a new color, a new decision about layout density, chrome, and rhythm made once per module and applied deliberately.

## Principles (extends v1, doesn't replace it)

1. **Hierarchy through typography and space, not boxes.** A card is for genuine containment — a stat surface, a modal — not the default wrapper for a list row.
2. **Three text tiers, every screen.** Primary (what you're looking at), secondary (what it belongs to), tertiary (when/how/where). See v1's example; unchanged.
3. **Not everything deserves attention.** A page has one Level 1 element. Everything else recedes until it's needed.
4. **Per-module atmosphere.** Every module gets an explicit answer to: *what should this feel like, and what does that rule out?* See the table below. This is decided once, in this document, and every screen in that module inherits it — not re-decided per page.
5. **Navigation recedes once you've arrived.** The sidebar orients; it shouldn't compete with the content once you're three levels deep into Northstar.

## Module atmosphere table

| Module | Feels like | Chrome level | Primary action placement | Explicitly avoid |
|---|---|---|---|---|
| Home | Orientation, a status check | Low — no boxed sections, separator-driven flow | Two buttons, top right, quiet | Turning it into a report with a card per metric |
| Focus | Concentration; a *mode*, not a page | Minimal while active — sidebar recedes | One primary action ("Start Focus") | Cards competing with the timer; notifications during a session |
| Study | Academic progress, deliberately calmer-formal than Focus | Low-medium | "Start Study" | Mixing project/business focus time into any study number |
| Tasks | Momentum, speed | Low — dense list, thin tab bar | "+ New Task", top right | Giant task cards; anything that slows scanning |
| Projects | A workspace, control | Medium — header strip + tabs | Contextual per tab | Treating a project like a settings form |
| Finance | Trust, precision | Low-medium — text-forward, numbers aligned right | "Add Transaction" | Gradient KPI cards; red for ordinary expenses |
| Journal | Reflection, privacy | **Near-zero** — no page-header button row, generous margins, serif-leaning body | Inline "Write" prompt, not a button | Anything that makes it resemble Tasks or Finance |
| Writing | Creation, focus | Near-zero in the editor itself; distraction-free toggle | Inline, in the editor | A toolbar-heavy CMS feel |
| Security/Devices/Lock | Restraint, precision, nothing playful | Low, deliberately plain | — | Any color that isn't neutral/accent; icons that feel decorative |

Everything else (People, Calendar, Goals, Notes, Settings) inherits the **Tasks-like "organize" register** (low chrome, dense lists) unless a later pass gives it a specific reason not to.

## Tokens (extended from v1 — see `tokens.css`)

Unchanged from v1: `--bg-*`, `--surface-*`, `--border-*`, `--text-*`, `--accent*`, semantic colors + `-soft` variants, `--chart-*`, spacing (`--space-1..16`), radii (`--radius-sm..full`), shadows.

**New in v2:**

```css
/* Elevation ladder — named, not just "surface-primary vs secondary".
   Every raised element picks a rung; nothing invents a one-off shadow. */
--elevation-0   /* bg-primary — the page itself */
--elevation-1   /* surface-primary — a list row on hover, a subtle panel */
--elevation-2   /* surface-overlay — modal, drawer, popover */
--elevation-3   /* command palette, the one thing above everything else */

/* Motion — named durations, not ad hoc ms in every transition rule */
--motion-micro:  120ms;  /* hover, focus ring, checkbox */
--motion-panel:  200ms;  /* drawer slide, modal, popover open */
--motion-page:   140ms;  /* route/tab content swap — kept subtle, never a slide-the-whole-page effect */
--motion-ease: cubic-bezier(0.4, 0, 0.2, 1);

@media (prefers-reduced-motion: reduce) {
  /* all --motion-* effectively 0 — see base.css */
}
```

Reduced-motion handling: a single rule in `base.css` collapses all `--motion-*` custom properties to `0ms` under `prefers-reduced-motion: reduce`, so components never need their own reduced-motion branch — they just use the variable.

## Typography

System stack unchanged (`-apple-system, "SF Pro Text", ...`). Roles, now named consistently instead of ad hoc `text-3xl`/`text-4xl` mixing:

| Role | Token | Use |
|---|---|---|
| Display | `--text-4xl`, weight 600 | The one number/timer that *is* the screen (active Focus timer, a balance) |
| Page title | `--text-2xl`, weight 600 | `page-title` |
| Section title | `--text-xs`, uppercase, `--text-muted`, letter-spacing | `eyebrow` |
| Item title | `--text-md`/`--text-base`, weight 500 | list-row-title |
| Body | `--text-base` | paragraphs, journal/writing body |
| Secondary | `--text-sm`, `--text-secondary` | list-row-meta |
| Metadata | `--text-xs`, `--text-muted` | timestamps, device names, tags |
| Numeric | `--font-mono`, `font-variant-numeric: tabular-nums` | money, durations, timers, counts |

Journal/Writing body text gets one deliberate exception: `max-width: 640px` reading column and `line-height: 1.7` (vs. the app default `1.5`) — set in `.prose` (new utility class), not by cloning the whole typography scale.

## Component architecture

New/formalized reusable pieces this pass (desktop, `templates/components/` partials + matching CSS):

- **Location bar** (`_location_bar.html`) — the `←` + breadcrumb-ish context layer described below. Replaces ad hoc "back to X" links.
- **Entity picker** (`_entity_picker.html` + `entity-picker.js`) — searchable popover for Project/Person/Account/Course selection, replacing plain `<select>` for any relationship with more than ~5 realistic options. Recent-first, create-new inline.
- **Confirm dialog** (`_confirm_dialog.html`) — the integrated modal pattern already used for account archive/transaction delete this pass, formalized as a partial so every destructive action uses one call site instead of copy-pasted modal HTML.
- **Journal/Writing prose shell** — the near-zero-chrome layout described above.

Android equivalents tracked separately in `android/README` once the Compose pass starts (Phase 5 of this rebuild — not yet started as of this document).

## Back navigation

`window.history.back()` when real LIFEOS history exists (tracked via a `sessionStorage` breadcrumb stack pushed on every full page load — see `app.js::NavHistory`), falling back to a server-known parent URL (e.g. an account's context, a task's project) when the tab was opened fresh (a bookmark, a new tab, a reload). Never navigates outside LIFEOS — the JS only ever calls `history.back()` after confirming the previous history entry's origin matches, otherwise it uses the fallback.

## What v2 explicitly keeps from v1 unchanged

Icon system, chart-without-a-library approach, drawer/modal/page selection rule, command palette mechanism (`Cmd/Ctrl+K` → `/search/api/`). These were already right.
