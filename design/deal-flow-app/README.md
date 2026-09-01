# Deal Flow App

An iOS design canvas for a live M&A / private equity deal pipeline, built with the
`/design` skill. Each `.dc.html` file is one artboard (iPhone 390×844);
`canvas.json` lays them out and names the two pages.

## Screens (page 1)

| Artboard | Screen |
|---|---|
| `Main.dc.html` | Pipeline — stat strip, live stage filter, mandate cards with stage ticks |
| `Deal.dc.html` | Deal detail — key facts and the nine process milestones |
| `Screening.dc.html` | Inbound screen — verdict, fund criteria pass/fail, bull/bear |
| `Actions.dc.html` | Actions — overdue and this-week items across the book |

## Directions (page 2)

| Artboard | Direction |
|---|---|
| `AltTerminal.dc.html` | A — dark, all-mono, one row per mandate |
| `AltBoard.dc.html` | B — swipeable stage columns, generous cards |

## Visual system

Colour carries status and nothing else. A date or flag is tinted only when it wants
attention, so an on-track due date reads as muted ink, not green.

| Role | Token | | Role | Token |
|---|---|---|---|---|
| Paper | `#f6f2ea` | | Rule | `#e3dccf` |
| Card | `#fffdf8` | | Rule, soft | `#efe9dd` |
| Ink | `#1e1a16` | | Rule, hairline | `#ded6c7` |
| Ink, secondary | `#4a443c` | | Control edge | `#cfc6b6` |
| Ink, muted | `#857c71` | | Separator dot | `#c8bfae` |
| Ink, faint | `#a79d90` | | Text on ink | `#ddd5c8` |

| Status | On paper | Tint | On ink |
|---|---|---|---|
| On track | `#2f6b4a` | `#e7efe9` | — |
| At risk | `#96650f` | — | `#d6a13f` |
| Delayed / fails screen | `#a63c28` | `#fdf6f4` | — |

**Type** — Newsreader (mandate names), IBM Plex Sans (UI), IBM Plex Mono (figures, dates,
small-caps labels). Every stack carries a metric-compatible fallback, since PNG/PDF export
does not embed Google Fonts.

The two artboards on the Directions page run their own palettes by design and are not
bound by the table above.

The book runs to 12 mandates, 8 of them written out across the screens.
Domain content follows the deal stages and screening criteria in
`investment-banking/skills/deal-tracker` and `private-equity/skills/deal-screening`.
All deals, names and dates are fictional sample data.

## Rebuilding the canvas

The published page is generated from these files — it is not checked in.

```
node "<design skill base dir>/seed-canvas.mjs" \
  --template "<design skill base dir>/payload.template.html" \
  --out deal-flow-app.html --title "Deal Flow App" \
  --artboard Main.dc.html --artboard Deal.dc.html \
  --artboard Screening.dc.html --artboard Actions.dc.html \
  --artboard AltTerminal.dc.html --artboard AltBoard.dc.html \
  --canvas canvas.json
```
