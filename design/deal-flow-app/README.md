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

- **Ground** `#f6f2ea` paper, `#fffdf8` cards, `#1e1a16` ink, `#e3dccf` rules
- **Colour is status only** — on track `#2f6b4a`, at risk `#96650f`, delayed `#a63c28`
- **Type** — Newsreader (mandate names), IBM Plex Sans (UI), IBM Plex Mono (figures, dates)

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
