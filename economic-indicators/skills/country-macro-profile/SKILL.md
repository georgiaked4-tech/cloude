---
name: country-macro-profile
description: Build a one-page macro snapshot for a country — growth, inflation, labor, external balance, policy stance, and fiscal position — with the trend on each and what it implies. Use when the user asks about "the economy of [country]", "macro profile", "country snapshot", "how is [country] doing", "макро-профиль", "экономика страны", or needs country context before a cross-border deal, allocation, or research note.
---

# Country Macro Profile

A snapshot that answers: where is this economy in its cycle, where is policy
heading, and what could break.

## Workflow

### Step 1: Assemble the core series

Six blocks. For each, the latest print, the prior, and the direction of travel
over three to four periods — the trend carries more information than the level.

**Growth**
- GDP growth QoQ and YoY; composition (consumption, investment, net exports)
- Composite PMI and its direction relative to 50
- Industrial production and retail sales

**Inflation**
- Headline and core CPI YoY, and the MoM run rate
- PPI as pipeline pressure
- Inflation expectations, where surveyed

**Labor**
- Unemployment rate with the participation rate beside it
- Employment change and wage growth
- Wage growth versus inflation — the real-income line drives consumption

**External**
- Current account, in the currency and as a share of GDP
- Trade balance, with the export/import split
- FX reserves, and their trend as evidence of intervention

**Policy**
- Policy rate, last move, and the implied path
- Real policy rate (policy rate minus core inflation) — the number that says
  whether policy is actually tight
- Balance sheet stance

**Fiscal**
- Budget balance and public debt to GDP
- Sovereign credit rating and outlook
- Debt service cost, which turns a rate cycle into a fiscal problem

### Step 2: Read the cycle

Place the economy: expansion, slowdown, contraction, or recovery. Justify it
with the series above rather than asserting it, and name the disagreement when
blocks conflict — resilient labor with contracting manufacturing is a common
and genuinely ambiguous configuration.

Then the tensions:

- Inflation falling while growth holds = a soft landing path
- Inflation falling because demand is collapsing = a different thing entirely
- Tight labor with weak productivity = persistent unit labor cost pressure
- Wide current account deficit with falling reserves = currency vulnerability

### Step 3: Add the structural layer

Numbers without structure mislead. Where relevant:

- Demographics and the working-age trend
- Energy dependence and terms of trade
- Concentration — one commodity, one sector, one export market
- Institutional factors: central bank independence, capital controls, sanctions,
  FX access, repatriation restrictions

For a cross-border deal or allocation, the institutional layer often dominates
the macro numbers. Convertibility and the ability to get cash out matter more
than a quarter of GDP.

### Step 4: Output

```
# [Country] Macro Profile — [as of date]

**Read.** Two or three sentences: cycle position, policy direction, main risk.

| Block | Latest | Prior | Trend | Note |
|-------|--------|-------|-------|------|
| GDP YoY | | | | |
| CPI YoY / Core | | | | |
| Unemployment | | | | |
| Policy rate (real) | | | | |
| Current account %GDP | | | | |
| Debt %GDP | | | | |

**What's working / what isn't.**
**Policy path.** What the central bank does next and why.
**Risks.** Two or three, with what would confirm each.
```

### Step 5: Source discipline

- Date every figure — a macro snapshot with undated numbers is unusable
- Name the source per block (national statistics office, central bank, IMF,
  calendar export) and keep to one vintage where possible
- Distinguish official statistics from estimates, especially where official
  data is contested or the release schedule has been disrupted
- Note revisions to headline series rather than quietly using the new number

## Related

- Bulk source data by country: `economic-calendar` skill
- Policy detail: `central-bank-watch` skill
