---
name: central-bank-watch
description: Track central bank policy across countries — meeting calendar, current policy rate, the implied path, and how the stance has shifted. Covers the Fed, ECB, BoE, BoJ, BoC, and EM central banks. Use when the user asks about "rate decision", "central bank", "FOMC", "ECB meeting", "policy path", "who's cutting", "решение по ставке", "ЦБ", or wants a rates-decision calendar.
---

# Central Bank Watch

## Workflow

### Step 1: Build the meeting grid

For each bank in scope: next meeting date, current policy rate, direction and
size of the last move, and how long the rate has been at this level.

| Bank | Country | Next meeting | Current rate | Last move | Priced for next |
|------|---------|--------------|--------------|-----------|-----------------|

Take meeting dates from the bank's own IR page. Calendar sites carry
placeholders for meetings more than a quarter out, and they move.

Note which meetings carry projections and a press conference — those have
materially more scope to move markets than the interim ones.

### Step 2: Record the stance

For each bank, the current position in its own words:

- The policy statement's forward guidance sentence, quoted rather than paraphrased
- The vote split, where published — a 6-3 hold is a different signal from 9-0
- Projections: the rate path, plus the growth and inflation forecasts that
  justify it
- What leadership has said since the last meeting

The vote split and the dissent direction are the earliest reliable evidence of
a turn.

### Step 3: Read the market-implied path

Distinguish three things and never merge them:

1. **What the bank says** it will do (guidance)
2. **What the market prices** (OIS/futures-implied path)
3. **What economists forecast** (survey)

A gap between (1) and (2) is the tradable observation. Report the implied
probability of a move at the next meeting and the cumulative pricing over the
next twelve months, and cite the instrument.

### Step 4: Track the divergence

Across banks, the useful frame is relative:

- Who is cutting, who is holding, who is hiking, and how those groups shifted
- Rate differentials versus the currency pair they drive
- EM banks constrained by their currency rather than domestic inflation —
  Turkey, Brazil, South Africa, Russia can hold rates far from what domestic
  data alone implies
- Balance sheet policy alongside the rate: QT pace, reinvestment rules, yield
  curve control

### Step 5: Output

**Decision preview** — what is expected, what the statement needs to say to be
hawkish or dovish relative to that, and the thresholds.

**Decision reaction** — what happened, how the statement changed word for word
against the prior one, the vote, the projections, the press conference tone,
and how the implied path moved.

**Grid** — the maintained table across banks for standing reference.

## What to watch

- **Statement diffs.** Compare against the previous statement literally.
  Dropped, added and reordered sentences are the message.
- **Projections vs statement.** When the dot plot and the language disagree,
  the press conference resolves it.
- **The dissenters.** Named dissents are the leading edge of a majority.
- **Meeting types.** Projection meetings ≠ interim meetings.
- **Inter-meeting speakers.** Guidance moves between meetings, and the first
  speaker after a big data surprise is the most informative.

## Related

- Meeting dates within the broader calendar: `economic-calendar` skill
- Data that feeds the decision: `data-surprise` skill
- Framing the meeting in the weekly note: `week-ahead-macro` skill
