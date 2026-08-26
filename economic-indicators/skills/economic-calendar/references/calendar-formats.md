# Calendar Formats

## Block layout (Trading Economics and lookalikes)

The dominant paste format. A date header, then repeating blocks of
time / country / event, tab-separated:

```
01/09/2026	Actual	Previous	Consensus	Forecast
02:00 AM
AU
Manufacturing PMI Final AUG		52.0	52.0	52.0
02:01 AM
GB
BRC Shop Price Index AUG		0.9%		1.0%
```

Structural facts the parser relies on:

- Dates are `DD/MM/YYYY`, **not** US order. `01/09/2026` is 1 September.
- The date header repeats for every day, sometimes twice for the same day.
- Times are 12-hour with AM/PM, rendered in the **viewer's** time zone. The
  paste carries no zone marker at all — establish it before publishing times.
- Some events carry no time and appear at the end of a day's block (monthly car
  registrations, budget balances, survey releases with no fixed hour).
- The reference period is glued to the end of the event name: `AUG`, `Q2`,
  `AUG/28` (week ending), `Prel JUL`, `SEP/04`.
- Value cells are frequently empty. Empty `actual` = not yet released. Empty
  `consensus` = no survey published, which is the norm outside the majors.
- Trailing tabs vary row to row; column count is not stable.

## Column semantics

| Column | What it is | Trap |
|--------|-----------|------|
| Actual | The printed number | Blank until release; revisions are not shown |
| Previous | Prior period's print | Often silently revised — the previous shown may not be the previous quoted last month |
| Consensus | Survey median of economists | Missing for most non-G10 releases |
| Forecast | The **vendor's own model** projection | Not a street survey. Markets trade against consensus, not this |

Consensus and forecast disagreeing is signal, not error: it means the vendor
model reads the data differently than the surveyed economists, and the release
has wider two-way risk than usual.

## Country codes

Two-letter codes, with the ones that get misread:

- `EA` = Euro Area aggregate; `EU` = European Union (institutional issuance,
  ECOFIN); the two are different rows and different meanings
- `GE` = **Georgia**, not Germany. Germany is `DE`
- `SA` = Saudi Arabia; South Africa is `ZA`
- `WL` = World aggregates (FAO food price index, supply-chain pressure)
- `OP` = OPEC meetings and monthly reports
- `KR` South Korea, `ID` Indonesia, `IN` India, `SG` Singapore, `TR` Turkey,
  `AR` Argentina, `MX` Mexico, `BR` Brazil, `CN` China, `JP` Japan,
  `AU` Australia, `CA` Canada, `RU` Russia, `US` United States, `GB` UK,
  `FR` France, `IT` Italy, `ES` Spain

## Other sources

**Investing.com** — same block idea, but importance is exported as a
star/bull rating you should keep instead of the heuristic, and the country is a
flag alt-text that may not survive the paste.

**Bloomberg ECO** — exports as a real table with a proper survey column and
standard deviation of estimates. When available, prefer it: the standard
deviation is what makes a surprise scorable (see the `data-surprise` skill).

**Central bank IR pages** — authoritative for policy dates and the only source
to trust for a meeting date more than a quarter out. Calendar sites carry
placeholder dates that move.

## Truncation

Free/guest exports cap out — Trading Economics stops at 1,000 rows and says so
in the footer of the paste. A truncated export silently drops the end of the
date range, so a "nothing scheduled" answer from a truncated file is wrong.
Check the row count against the date span before concluding a week is quiet.
