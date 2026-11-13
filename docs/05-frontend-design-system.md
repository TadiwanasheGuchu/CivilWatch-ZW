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
| `SiteHeader` | `components/site-header.tsx` | Navy header with wordmark |

The resident bottom navigation (Home, Explore, Report, My Reports, Profile) is added in Milestone 2, together with the routes it links to, so no navigation item points at a page that does not exist.

Icons: Lucide only, `size-4`/`size-5`, stroke 2, `aria-hidden` when a text label is present.
