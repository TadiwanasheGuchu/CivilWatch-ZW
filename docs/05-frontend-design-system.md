# 05 — Frontend Design System

Tokens live in `frontend/app/globals.css` (Tailwind v4 `@theme`). Use the token utilities (`bg-navy`, `text-teal`, …) — never raw hex values in components.

## Colour

| Token | Hex | Use |
|---|---|---|
| `navy` | #172B3A | Brand, header, primary text |
| `navy-soft` | #24394A | Body copy on light surfaces |
| `teal` | #267C72 | Primary actions, positive status, focus ring (5.0:1 on white) |
| `teal-hover` | #1F665E | Hover state of primary actions |
| `mist` | #F5F7F8 | App background, skeletons |
| `surface` | #FFFFFF | Panels and cards |
| `amber` | #E7B45A | Warning accents (borders, fills) — not for text |
| `amber-text` | #7A5412 | Warning text (6.8:1 on white) |
| `red` | #C65B58 | Error accents (borders, fills) — not for small text |
| `red-text` | #A84744 | Error text (5.7:1 on white) |
| `slate` | #64748B | Secondary text **on white surfaces only** (4.8:1; drops to 4.4:1 on mist) |
| `line` | #DFE4E8 | Borders and dividers |

`amber-text`, `red-text`, `navy-soft`, `teal-hover` and `line` are derived shades of the brand palette, added because the brand Amber, Muted Red and Slate do not meet WCAG AA for small text in every context.

## Typography

- Headings: Manrope 600/700 (`--font-heading`), loaded with `next/font` (self-hosted, `display: swap`).
- Body: Inter (`--font-sans`). Numbers in tables/metrics: `tabular` utility.
- Mobile H1 `text-2xl`, desktop `text-3xl`; body 16px minimum for paragraphs, 14px for dense UI.

## Layout and interaction

- Mobile-first; content max width `max-w-5xl`; 16px side gutter on mobile, 24px from `sm`.
- Touch targets ≥ 44×44 px (`min-h-11` on every `Button` size) — verified by Playwright.
- Visible focus: 3px teal outline on `:focus-visible`. Skip link to `#main` in the root layout.
- Motion is minimal and disabled under `prefers-reduced-motion`.
- Radii: `--radius-control` 8px, `--radius-panel` 12px. Borders over shadows.

## Components

| Component | Location | Notes |
|---|---|---|
| `Button` | `components/ui/button.tsx` | Variants `primary`, `secondary`, `ghost`; sizes `md`, `lg`; `asChild` for links |
| `Input` | `components/ui/input.tsx` | 16px text (prevents iOS zoom), 44px min height, red border when `aria-invalid` |
| `PasswordInput` | `components/ui/password-input.tsx` | Show/hide toggle (`aria-pressed`), 44px tap target |
| `Select` | `components/ui/select.tsx` | **Native** `<select>`: the phone's own picker, accessible by default, no extra JavaScript |
| `Field` | `components/ui/field.tsx` | Label + hint + error; wires `id`, `aria-invalid`, `aria-describedby` onto its control |
| `Alert` | `components/ui/alert.tsx` | `error` (announced via `role="alert"`), `success`, `info` |
| `Panel` | `components/ui/panel.tsx` | Bordered surface with heading, description and actions; a labelled `region` |
| `Badge` | `components/ui/badge.tsx` | `neutral`, `brand` (roles), `navy` (platform admin) |
| `Pagination` | `components/ui/pagination.tsx` | Previous/next with "Page x of y"; hidden for a single page |
| `LoadingRows`, `LoadError`, `EmptyState` | `components/ui/page-states.tsx` | Skeleton, error-with-retry and empty states |
| `Textarea` | `components/ui/textarea.tsx` | Same styling and states as `Input` |
| `ChoiceCard` | `components/ui/choice-card.tsx` | A native radio input presented as a large card (categories, visibility); keyboard and screen-reader friendly |
| `StatusBadge` | `features/reporting/status-badge.tsx` | Report status as text; tone reinforces it (neutral, progress, done, stopped, attention) |
| `ReportListItem` | `features/reporting/report-list-item.tsx` | Thumbnail, status, title, category, council, reference and date |
| `LazyLocationMap` | `features/maps/lazy-location-map.tsx` | MapLibre map, loaded on demand; tap or drag to set a pin; read-only on report pages |
| `BottomNav`, `HeaderNav` | `features/navigation/` | Resident navigation (see below) |
| `SiteHeader` | `components/site-header.tsx` | Navy header with wordmark, `HeaderNav` (tablet and up) and the account link |

### Form conventions

- React Hook Form + Zod. Client schemas mirror the API's rules (`features/authentication/schemas.ts`) for instant feedback; the API remains the authority, and its 422 field errors are shown on the matching field (`lib/form-errors.ts`).
- Errors appear under the field in `red-text`, and the field gets a red border and `aria-invalid`. General failures appear in an `Alert` above the form.
- Submit buttons say what is happening ("Signing in…") and are disabled while pending.
- Destructive actions use an inline confirmation step (e.g. "Remove this person? Remove / Keep") rather than a modal: it keeps context on small screens and needs no focus trapping.

### Navigation

- **Phones (<768 px)**: a fixed bottom bar with Home, Explore, **Report** (a raised teal button), My reports and Profile. It respects the safe-area inset and is hidden on the report form, which has its own Back/Next bar.
- **Tablet and up**: the same destinations sit in the header, with "Report a problem" as a teal button.
- Council workspaces use underline tabs (Staff, Audit log); a tab only appears when the user's permissions allow it.

### Report form

Six steps, one screen each: category → description → photos → location → visibility → review. A progress bar shows "Step n of 6", focus moves to each step's heading, and Back/Next sit in a bar fixed to the bottom of the screen so they stay within thumb reach. Each step is checked before moving on, with messages next to the fields. The review step lists every answer with a "Change" link.

Photos: "Take a photo" (opens the camera where supported) and "Choose from gallery", previews with remove buttons, up to five. Location: "Use my current location" first (most reliable on phones), the map second; the pin's coordinates are always shown as text. If the device cannot run the map, the step says so and location sharing still works; if map images fail to load, the map stays usable with a short note.

### Maps

Raster tiles (OpenStreetMap by default) with attribution, no rotation or tilt, zoom buttons, and cooperative gestures on read-only maps so page scrolling is not hijacked. The map library is only downloaded when a map is shown.

Icons: Lucide only, `size-4`/`size-5`, stroke 2, `aria-hidden` when a text label is present.
