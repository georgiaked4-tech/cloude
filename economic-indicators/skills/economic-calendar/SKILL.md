---
name: economic-calendar
description: Turn a pasted or exported economic calendar (Trading Economics, Investing.com, Bloomberg ECO, in English or Russian) into a clean, filterable table of macro releases — date, time, country, indicator, reference period, actual, previous, consensus, forecast — and produce the day/week view an analyst actually reads. Use when the user pastes a calendar dump, asks "what's on the calendar", "economic calendar", "macro calendar", "what data is out this week", "экономический календарь", or wants calendar data as CSV/Excel.
---

# Economic Calendar

Calendar sites copy out as an unusable block of text: a date header, then a
repeating time / country / event pattern with four unlabeled value columns. This
skill normalizes that into one row per release, then filters it down to what
matters for the question being asked.

## Workflow

### Step 1: Get the raw calendar

Accept whatever the user has:

- Pasted text from a calendar site (most common — it will look like noise)
- A CSV/Excel export
- A screenshot (read the values out; do not guess ones you cannot read)
- No data at all — then ask which countries and date range, and pull from an
  available MCP data provider or the web

Save pasted text to a file before parsing. Page furniture (nav menus, cookie
banners, chat widgets, footers) is common in pastes and is skipped
automatically — do not spend time cleaning it by hand.

### Step 2: Parse to structured rows

```bash
python3 scripts/parse_calendar.py raw.txt -o calendar.csv
python3 scripts/parse_calendar.py raw.txt --format json --country US,EA,GB
python3 scripts/parse_calendar.py raw.txt --min-importance high --from 2026-09-01 --to 2026-09-07
python3 scripts/parse_calendar.py raw.txt --released          # only events with an actual print
```

Output columns: `date, time, country_code, country, event, period, actual,
previous, consensus, forecast, importance`.

Two things to check before using the output:

- **Column order.** Most sites order the value columns Actual / Previous /
  Consensus / Forecast, which is what the parser assumes. Some order them
  Actual / Forecast / Previous. Spot-check two or three rows whose values you
  can sanity-check (a policy rate, a known CPI print) and say so if the source
  differs — the fix is to relabel the columns, not to re-parse.
- **`importance` is a heuristic**, computed from the event name, not a field in
  the export. It is there to sort a 1,000-row dump quickly. Bond and bill
  auctions are always `low`; policy decisions, CPI, GDP, labor and PMI are
  `high`. Override it when the user's mandate differs — an EM rates desk cares
  about auctions.

Also worth flagging to the user: exports from guest/free accounts are commonly
truncated (Trading Economics caps at 1,000 rows), and an empty `actual` means
the release has not happened yet, not that it printed zero.

### Step 3: Answer at the right altitude

Do not dump the whole table back. Match the output to the question:

**"What's this week?"** — a compact table, high importance only, ordered by
date/time, with the local time zone stated explicitly:

| Date | Time | Country | Release | Period | Previous | Consensus | Why it matters |
|------|------|---------|---------|--------|----------|-----------|----------------|

**"What matters for [asset / portfolio]?"** — filter to releases that plausibly
move it, and say what the market is positioned for. Nothing about a Korean bill
auction belongs in a US equity note.

**"Give me the data"** — write the CSV, or an Excel workbook with one sheet per
country or a filterable single sheet, and hand back the file.

### Step 4: Note the gaps

Say explicitly when:

- Consensus is missing for a release the user is asking about (common outside
  US/EA — the column is simply empty, and "no consensus" is not "consensus of
  zero")
- The calendar's own forecast column is a vendor model, not a street survey —
  these differ, sometimes materially, and only the survey number is the bar the
  print gets judged against
- The export is truncated or the date range is incomplete
- Times are ambiguous: calendars render in the viewer's time zone, so a pasted
  dump carries no zone at all. Ask, or state the assumption in the output.

## Reference

- [references/calendar-formats.md](references/calendar-formats.md) — source layouts, column
  semantics, country codes, and the traps in each
- [references/indicator-glossary.md](references/indicator-glossary.md) — Russian ↔ English
  indicator names and what each one is read for

## Related

- Scoring a print that has landed: use the `data-surprise` skill
- Building the forward-looking note: use the `week-ahead-macro` skill
- Policy meetings specifically: use the `central-bank-watch` skill
