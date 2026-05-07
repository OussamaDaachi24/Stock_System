# Stock Management System — Design System v1

**Status:** Locked
**Last Updated:** 2026-05-07
**Scope:** Visual polish — typography, color, borders, shadows, spacing, component states. No layout changes.
**Source of truth:** [frontend/src/styles.css](frontend/src/styles.css) `:root` block.

---

## Philosophy

Linear / Stripe Dashboard / Vercel feel. Neutral base, single accent, subtle shadows, no gradients, no glassmorphism, no animations beyond 200ms.

---

## Typography

Font stack: `-apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`
Mono: `ui-monospace, SFMono-Regular, "JetBrains Mono", Menlo, Consolas, monospace`

| Token | Size | Weight | Line-height | Color | Use |
|---|---|---|---|---|---|
| `--fs-display` | 24px | 600 | 1.25 | `--c-text` | Page title (`h2`) |
| `--fs-h1` | 18px | 600 | 1.25 | `--c-text` | Section header (`h3`) |
| `--fs-h2` | 14px | 600 | 1.25 | `--c-text` | Card title (`h4`) |
| `--fs-body` | 13px | 400 | 1.5 | `--c-text` | Body, inputs, buttons |
| `--fs-small` | 12px | 400 | 1.5 | `--c-text-2` | Labels, secondary text |
| `--fs-meta` | 11px | 500 | 1.5 | `--c-text-muted` | Stat labels, table headers (uppercase) |

Weights: `400` normal, `500` medium, `600` bold. Letter-spacing `-0.01em` on headings.

Rules:
- Headings always `--c-text` (#18181B), never gray.
- Body uses `--c-text` or `--c-text-2`; metadata uses `--c-text-muted`.
- No italics for hints; use `--c-text-muted` instead.

---

## Color Palette

### Neutral
| Token | Hex | Use |
|---|---|---|
| `--c-bg` | `#FAFAFA` | App background |
| `--c-surface` | `#FFFFFF` | Cards, modals, nav, inputs |
| `--c-surface-2` | `#F4F4F5` | Hover bg, code bg |
| `--c-border` | `#E4E4E7` | Dividers, card borders |
| `--c-border-strong` | `#D4D4D8` | Input borders, secondary buttons |
| `--c-text` | `#18181B` | Primary text, headings |
| `--c-text-2` | `#3F3F46` | Body secondary, paragraph |
| `--c-text-muted` | `#71717A` | Metadata, placeholders, helper |
| `--c-text-faint` | `#A1A1AA` | Input placeholder, disabled |

### Accent (locked — single accent only)
| Token | Hex | Use |
|---|---|---|
| `--c-accent` | `#2563EB` | Primary action, links, focus border |
| `--c-accent-hover` | `#1D4ED8` | Primary hover |
| `--c-accent-soft` | `#EFF6FF` | Subtle accent bg |
| `--c-accent-text` | `#FFFFFF` | Text on accent |

### Status
| Token | Hex | Soft variant |
|---|---|---|
| `--c-success` | `#16A34A` | `--c-success-soft` `#F0FDF4` |
| `--c-warning` | `#D97706` | `--c-warning-soft` `#FFFBEB` |
| `--c-danger` | `#DC2626` | `--c-danger-soft` `#FEF2F2` |

Rules: no random colors per page, no gradients, status colors only via pills/inline status text.

---

## Spacing — 4px grid

| Token | Value |
|---|---|
| `--s-1` | 4px |
| `--s-2` | 8px |
| `--s-3` | 12px |
| `--s-4` | 16px |
| `--s-5` | 20px |
| `--s-6` | 24px |
| `--s-8` | 32px |

Component padding (locked):
- Card: `--s-5` (20px)
- Modal: `--s-6` (24px)
- Container: `--s-6` (24px)
- Button: `0 --s-3` (height 32px)
- Input: `0 10px` (height 32px)
- Table cell: `10px 12px`
- Toolbar bottom margin: `--s-4`

---

## Borders & Shadows

### Radius
- `--r-sm` 4px — buttons, inputs, pills (`999px` exception for pill chips)
- `--r-md` 6px — cards
- `--r-lg` 8px — modals

Border width: `--bw` 1px. Border color: `--c-border` (default), `--c-border-strong` (inputs/secondary buttons), `--c-accent` (focus).

### Shadows (3 levels only)
```css
--sh-1: 0 1px 2px rgba(15,23,42,.04), 0 1px 1px rgba(15,23,42,.03);  /* cards */
--sh-2: 0 4px 8px -2px rgba(15,23,42,.08), 0 2px 4px -2px rgba(15,23,42,.04);  /* dropdowns, toast */
--sh-3: 0 16px 32px -12px rgba(15,23,42,.18), 0 4px 8px -4px rgba(15,23,42,.08);  /* modals */
```
No shadows on buttons. No colored shadows.

### Focus
`--focus-ring: 0 0 0 3px rgba(37,99,235,.18)` — paired with `border-color: --c-accent` on inputs.

---

## Motion
- `--t-fast` 120ms ease — bg, border-color
- `--t-base` 160ms ease — broader transitions
- No animation > 200ms. No fade/blur on hover.

---

## Components

### Button (`.btn`)
Height 32px · padding `0 --s-3` · radius `--r-sm` · font-size `--fs-body` · weight 500.
Variants: primary (filled accent), `.secondary` (white bg, `--c-border-strong`), `.danger` (white bg + red text → fills red on hover).
Hover: bg shift only, no shadow. Focus: `--focus-ring`. Disabled: opacity 0.5.

### Input (`.input`)
Height 32px · padding `0 10px` · 1px `--c-border-strong` · radius `--r-sm`.
Hover: border `--c-text-faint`. Focus: border `--c-accent` + `--focus-ring`. Disabled: bg `--c-surface-2`.
Placeholder: `--c-text-faint`.

### Table
`border-collapse: separate` · cell padding `10px 12px` · `th` uppercase, `--fs-meta`, `--c-text-muted`.
Row hover: bg `--c-surface-2`. Last row: no bottom border.

### Card (`.card`)
Bg `--c-surface` · border 1px `--c-border` · radius `--r-md` · padding `--s-5` · shadow `--sh-1`.
Stacked cards: `margin-top: --s-3`.

### Modal (`.modal`)
Bg `--c-surface` · border 1px `--c-border` · radius `--r-lg` · padding `--s-6` · width 520px · shadow `--sh-3`.
Backdrop: `rgba(15,23,42,.45)` + `backdrop-filter: blur(2px)`.

### Toast (`.toast`)
Fixed bottom-right `--s-6` · padding `10px 14px` · radius `--r-sm` · shadow `--sh-2`.
Default: dark bg + white text. `.error`: bg `--c-danger`.

### Pill (`.pill`)
Height 20px · padding `0 8px` · radius 999px · `--fs-meta` · weight 500.
Variants: default (neutral), `.success`, `.warning`, `.danger` — all use soft bg + status text color, no border.

### Stat (Dashboard)
`.stat-label` 11px uppercase muted · `.stat-value` 24px weight 600 `-0.02em` letter-spacing.

---

## Interaction States

| State | Treatment |
|---|---|
| Hover (button) | Background-color shift only, no shadow |
| Hover (row) | Bg `--c-surface-2` |
| Hover (link) | Underline, no color change |
| Focus (input) | Border `--c-accent` + `--focus-ring` (no glow halo) |
| Focus (button) | `--focus-ring` only |
| Disabled | Opacity 0.5, `cursor: not-allowed` |
| Loading | Spinner only — disable element, no blur/fade |

---

## Audit Checklist (Verified)

- [x] All heading colors `--c-text` (#18181B)
- [x] Body uses `--c-text-2` / `--c-text-muted` hierarchy
- [x] All borders 1px `--c-border` or `--c-border-strong`
- [x] All radii from {`--r-sm` 4, `--r-md` 6, `--r-lg` 8}
- [x] Box-shadows from 3-level system only
- [x] No shadows on buttons
- [x] Buttons consistent padding (32px height, `0 --s-3`)
- [x] Inputs consistent border + focus
- [x] Table cells uniform `10px 12px`
- [x] Cards consistent `--s-5` padding
- [x] Single accent (`--c-accent` indigo-blue)
- [x] No gradients
- [x] No glassmorphism (modal backdrop blur 2px is the only blur)
- [x] All hover transitions ≤ 160ms
- [x] No striped rows — borders only
- [x] Focus visible on every interactive element
- [x] No hardcoded hex/rgb in `.tsx` files (verified via grep)

---

## Token Reference (CSS)

All tokens live in `:root` of [frontend/src/styles.css](frontend/src/styles.css#L6-L78). Pages consume them via class names (`.btn`, `.card`, `.input`, `.pill`, `.toast`, `.stat-label`, `.stat-value`) and inline `var(--token)` for layout-only style props (margin, gap, color of dynamic status text).

Screens redesigned & tokenized:
- [DashboardPage.tsx](frontend/src/pages/DashboardPage.tsx)
- [ReceivingPage.tsx](frontend/src/pages/ReceivingPage.tsx)
- [ReturnsPage.tsx](frontend/src/pages/ReturnsPage.tsx)
- [ReservationsPage.tsx](frontend/src/pages/ReservationsPage.tsx)
- [ReportsPage.tsx](frontend/src/pages/ReportsPage.tsx)
- [AdminPage.tsx](frontend/src/pages/AdminPage.tsx)
- [ProductsPage.tsx](frontend/src/pages/ProductsPage.tsx) · [SuppliersPage.tsx](frontend/src/pages/SuppliersPage.tsx) · [PurchaseOrdersPage.tsx](frontend/src/pages/PurchaseOrdersPage.tsx) · [LoginPage.tsx](frontend/src/pages/LoginPage.tsx)
- Global chrome: [App.tsx](frontend/src/App.tsx) (`.nav`)
