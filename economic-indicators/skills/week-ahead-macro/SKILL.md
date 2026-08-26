---
name: week-ahead-macro
description: Write the forward-looking macro note — what data and central bank events land this week, what the market expects, what would count as a surprise, and what each one means for positioning. Use when the user asks for a "week ahead", "macro preview", "what to watch", "look ahead", "неделя впереди", "макро-прогноз на неделю", or wants a recurring Monday macro brief.
---

# Week Ahead Macro

The value of a week-ahead note is not the list of releases — anyone can pull
that. It is saying which two or three matter, what is already priced, and what
would have to print for the week to change anyone's mind.

## Workflow

### Step 1: Scope

Establish before writing:

- **Audience** — a rates desk, an equity PM, a corporate treasurer and a
  private client all need different notes from the same calendar
- **Geography** — global, or a specific bloc
- **Horizon** — the coming week is standard; month-ahead for planning notes
- **Existing positioning** — a note that ignores the book is generic commentary

### Step 2: Pull and rank the calendar

Use the `economic-calendar` skill to get the week's releases, filtered to high
importance. Then rank by **potential to move prices**, not by importance
category. A second-tier release lands hard when:

- The prior print was a large surprise and the market is unsure it was signal
- Consensus is unusually tight (little dispersion = big reaction if wrong)
- The central bank has explicitly said it is data-dependent on this series
- It is the last read before a policy meeting

Three to five events, ranked. A list of twenty is a calendar, not a note.

### Step 3: Frame each event

For each ranked event:

**What lands** — country, release, period, day and time (with zone).

**Consensus** — the number, and the dispersion around it if available.

**What is priced** — the market-implied path, not your opinion of it. For a
policy meeting, the OIS-implied probability. For data, what the front end and
the relevant asset already reflect.

**What would surprise** — the specific thresholds. "Core CPI at 0.4% MoM or
above re-opens the hike debate; 0.1% or below prices a cut for [meeting]" is
useful. "A hot print would be hawkish" is not.

**So what** — the asset-level implication, in one sentence.

### Step 4: Add the non-calendar layer

Scheduled data is only part of the week. Also cover:

- Central bank speakers, especially the ones who move markets
- Auctions large enough to matter (long-end supply in a fragile market)
- Earnings with macro read-through (rails, freight, staffing, banks, retailers)
- Political and fiscal deadlines
- Month-end and quarter-end rebalancing flows
- What is happening in Asia overnight before the domestic session

### Step 5: Structure the note

```
## Week Ahead: [dates]

**The setup.** Two or three sentences: where the market ended last week,
what the open question is, and what this week can resolve.

**Top three.**
1. [Day] — [Release]. Cons [x] vs [prev]. Priced: [what]. Surprise if: [threshold]. So what: [implication].
2. ...
3. ...

**Also on the tape.** Compact table of the rest.

**Risks to the view.** What would break the framing above — including the
unscheduled kind.
```

Keep it to a page. Length is the enemy of a note read before the open.

### Step 6: Recurring delivery

For a standing Monday note, fix the format so week-to-week comparison is easy,
and open with what changed since the last one — the previous week's surprises
are the context for this week's expectations.

## Quality checks

- Every claim about what is "priced" traces to a market instrument, not a view
- Thresholds are specific numbers
- The note would read differently if the calendar were different — a
  week-ahead that could be published any week says nothing
- Where consensus is missing, that is stated rather than filled with a guess

## Related

- Source data: `economic-calendar` skill
- Scoring the prints once they land: `data-surprise` skill
- Policy meetings in the week: `central-bank-watch` skill
