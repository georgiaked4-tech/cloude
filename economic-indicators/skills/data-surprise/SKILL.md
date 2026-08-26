---
name: data-surprise
description: Score an economic release against expectations and explain what it means for rates, FX, and equities. Computes the surprise versus consensus, standardizes it so releases of different units are comparable, checks whether revisions changed the story, and translates the result into a market read. Use when a data point has just printed, or when the user asks "beat or miss", "vs consensus", "what does this print mean", "data surprise", "сюрприз", or pastes actual/consensus numbers.
---

# Data Surprise

A release is not "good" or "bad" — it is above or below what was already
priced. This skill turns a print into a surprise, then into a market read.

## Workflow

### Step 1: Establish the bar

Three numbers get confused constantly. Separate them before anything else:

- **Consensus** — the median of a survey of economists. This is the bar.
- **Vendor forecast** — a calendar site's own model. Not the bar.
- **Whisper** — where the market is actually positioned, which can sit away
  from consensus after a run of same-direction prints or a strong leading
  indicator. When it exists, the whisper explains price action that consensus
  cannot.

If only a vendor forecast is available, say so and label the comparison
accordingly. Do not present it as a beat or miss against consensus.

### Step 2: Compute the surprise

```
surprise = actual - consensus
```

Report the raw gap in the release's own units, always. Then standardize so
prints in different units can be ranked:

```
z = (actual - consensus) / stdev(historical surprises)
```

Use the standard deviation of past surprises for that same series — Bloomberg
publishes the dispersion of estimates, which is a serviceable proxy. Without a
history, fall back to the percentage gap and say the score is unstandardized.

Rules of thumb for a standardized surprise:

| \|z\| | Reading |
|-------|---------|
| < 0.5 | In line. The market ignores it |
| 0.5–1.0 | Modest surprise. Moves the asset, not the narrative |
| 1.0–2.0 | Real surprise. Re-prices the front end |
| > 2.0 | Large. Expect follow-through and forecast revisions |

### Step 3: Check the revision

The headline surprise is frequently the smaller story. Always check:

- Was the **previous** period revised, and by how much? A beat against
  consensus that comes with a downward revision to last month can be net
  negative — US payrolls does this routinely.
- Does the revision change the **trend**? Two months revised down turns an
  acceleration into a plateau.
- For quarterly data, does the level or the composition drive it? GDP carried
  by inventories is weaker than the headline, and inventory builds reverse.

### Step 4: Look inside the print

Headline vs. the components that actually inform the next move:

| Release | Look at |
|---------|---------|
| CPI | Core MoM, services ex-shelter, the 3m annualized run rate |
| Payrolls | Household vs establishment survey, participation, hours, revisions |
| PMI | New orders, employment, prices paid; new orders less inventories |
| GDP | Final domestic demand ex-inventories and ex-net-trade |
| Retail sales | Control group |
| Trade balance | Volume vs price effects |

A headline miss with strong internals and a headline beat with weak internals
both happen often enough that leading with the headline alone is a mistake.

### Step 5: Translate to a market read

State the direction and the mechanism, not just the direction:

- **Rates** — does this move the policy path? Cite the front end (2y, or the
  relevant OIS/futures-implied path) rather than asserting a hike or cut.
- **FX** — rate differential is the usual channel; for commodity currencies and
  EM, terms of trade and risk appetite can dominate it.
- **Equities** — good-news-is-good-news or good-news-is-bad-news depends on the
  regime. In an inflation-anxious regime, strong data sells bonds and stocks
  together; in a growth-anxious regime, strong data lifts equities. Name which
  regime you are assuming.

Be honest about attribution. On a day with several releases, a central bank
speaker, or a month-end flow, do not pin the whole move on one print.

### Step 6: Output

Short form, for one release:

> **[Country] [Indicator] [Period]: [actual] vs [consensus] cons ([previous] prior)**
> [Beat/miss/in line] by [gap] ([z] sd). [Revision note.] [Key internal.]
> Read: [what it does to the policy path and the asset the user cares about.]

Table form, for a batch:

| Release | Actual | Cons | Prev | Surprise | z | Read |
|---------|--------|------|------|----------|---|------|

## Related

- Getting the consensus and previous from a calendar: `economic-calendar` skill
- Framing the release before it lands: `week-ahead-macro` skill
