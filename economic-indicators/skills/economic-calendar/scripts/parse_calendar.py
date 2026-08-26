#!/usr/bin/env python3
"""Normalize a pasted or exported economic calendar into structured rows.

Calendar sites (Trading Economics and lookalikes) copy out as a block layout
rather than a real table: a date header, then repeating time / country /
event blocks, with the four value columns tab-separated after the event name.

    01/09/2026<TAB>Actual<TAB>Previous<TAB>Consensus<TAB>Forecast
    02:00 AM
    AU
    Manufacturing PMI Final AUG<TAB><TAB>52.0<TAB>52.0<TAB>52.0

Both English and Russian exports parse, since only the date, time and country
lines are matched structurally; the event text is carried through as-is.

Usage:
    parse_calendar.py raw.txt -o calendar.csv
    parse_calendar.py raw.txt --format json --country US,EA --min-importance high
"""

import argparse
import csv
import json
import re
import sys

# Two-letter codes as used by Trading Economics. Note GE is Georgia and DE is
# Germany; EA is the euro area aggregate while EU is the European Union.
COUNTRIES = {
    "AR": "Argentina", "AU": "Australia", "BR": "Brazil", "CA": "Canada",
    "CH": "Switzerland", "CN": "China", "DE": "Germany", "EA": "Euro Area",
    "ES": "Spain", "EU": "European Union", "FR": "France", "GB": "United Kingdom",
    "GE": "Georgia", "HK": "Hong Kong", "ID": "Indonesia", "IN": "India",
    "IT": "Italy", "JP": "Japan", "KR": "South Korea", "MX": "Mexico",
    "MY": "Malaysia", "NL": "Netherlands", "NO": "Norway", "NZ": "New Zealand",
    "OP": "OPEC", "PL": "Poland", "PT": "Portugal", "RU": "Russia",
    "SA": "Saudi Arabia", "SE": "Sweden", "SG": "Singapore", "TH": "Thailand",
    "TR": "Turkey", "TW": "Taiwan", "US": "United States", "VN": "Vietnam",
    "WL": "World", "ZA": "South Africa",
}

MONTHS = "JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC"

# Reference period trailing the event name: "AUG", "Q2", "AUG/28", "SEP/04".
RE_PERIOD = re.compile(r"\s(Q[1-4]|(?:%s)(?:/\d{1,2})?)\s*$" % MONTHS)
RE_DATE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
RE_TIME = re.compile(r"^(\d{1,2}:\d{2})\s*(AM|PM)?$", re.IGNORECASE)
RE_COUNTRY = re.compile(r"^[A-Z]{2}$")

# Importance is a market-attention heuristic, not a field in the export.
# Auctions are checked first: a bond auction is routine even when the event
# name mentions a rate.
LOW_FIRST = (
    "аукцион", "размещение", "торги по", "вексел", "облигаци", "бонов",
    "auction", "bill", "bond", "t-bill", "btf", "letras", "bubill",
)
HIGH = (
    "решение по процентной ставке", "решение фрс", "решение цб", "процентной ставке",
    "инфляц", "ипц", "ввп", "безработиц", "вне с/х", "занятост", "нерабоч",
    "payroll", "заработная плата", "почасовая", "розничные продажи",
    "пресс-конференц", "протокол", "бежевая книга", "экономические прогнозы",
    "прогноз процентной ставки", "базовая ставка", "ставка по депозитным",
    "деловой активности", "pmi", "ism",
    "interest rate decision", "inflation", "cpi", "gdp", "unemployment",
    "nonfarm", "employment change", "retail sales", "press conference",
    "ваканс", "jolts", "job openings",
    "minutes", "beige book", "rate decision", "core inflation",
)
MEDIUM = (
    "промышленное производство", "обрабатывающая промышленность", "торговый баланс",
    "счет текущих операций", "экспорт", "импорт", "заказы", "доверие", "уверенность",
    "настроени", "заявки на пособие", "цен производителей", "запасы", "ипотеч",
    "жиль", "строительств", "производительность", "денежн", "кредитован",
    "международные резервы", "бюджет", "продажи",
    "industrial production", "trade balance", "current account", "orders",
    "confidence", "sentiment", "jobless claims", "ppi", "inventories",
    "mortgage", "housing", "construction", "money supply", "reserves", "budget",
)
IMPORTANCE_RANK = {"low": 0, "medium": 1, "high": 2}


def classify(event):
    """Return low / medium / high market attention for an event name."""
    text = event.lower()
    if any(k in text for k in LOW_FIRST):
        return "low"
    if any(k in text for k in HIGH):
        return "high"
    if any(k in text for k in MEDIUM):
        return "medium"
    return "low"


def split_period(event):
    """Peel the reference period off the end of an event name."""
    match = RE_PERIOD.search(event)
    if not match:
        return event.strip(), ""
    return event[: match.start()].strip(), match.group(1)


def normalize_time(raw):
    """Render a 12h or 24h clock string as HH:MM, keeping the source order."""
    match = RE_TIME.match(raw)
    if not match:
        return ""
    hour, minute = (int(p) for p in match.group(1).split(":"))
    meridiem = (match.group(2) or "").upper()
    if meridiem == "PM" and hour != 12:
        hour += 12
    elif meridiem == "AM" and hour == 12:
        hour = 0
    return "%02d:%02d" % (hour, minute)


def parse(lines):
    """Walk the block layout and yield one dict per calendar event."""
    rows = []
    date = time = country = ""
    for raw in lines:
        cells = raw.rstrip("\n").split("\t")
        first = cells[0].strip()
        if not first:
            continue

        date_match = RE_DATE.match(first)
        if date_match:
            day, month, year = date_match.groups()
            date = "%s-%s-%s" % (year, month, day)
            time = country = ""
            continue

        if RE_TIME.match(first) and len(first) <= 8:
            time = normalize_time(first)
            continue

        if RE_COUNTRY.match(first) and len(cells) == 1:
            country = first
            continue

        if not country:
            # Page furniture (headers, footers, chat widgets) before any block.
            continue

        event, period = split_period(first)
        values = [c.strip() for c in cells[1:5]]
        values += [""] * (4 - len(values))
        rows.append({
            "date": date,
            "time": time,
            "country_code": country,
            "country": COUNTRIES.get(country, country),
            "event": event,
            "period": period,
            "actual": values[0],
            "previous": values[1],
            "consensus": values[2],
            "forecast": values[3],
            "importance": classify(first),
        })
        country = ""
        time = ""
    return rows


def in_date_range(row, start, end):
    if not row["date"]:
        return not (start or end)
    if start and row["date"] < start:
        return False
    if end and row["date"] > end:
        return False
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?", help="calendar text file (default: stdin)")
    ap.add_argument("-o", "--output", help="output file (default: stdout)")
    ap.add_argument("--format", choices=["csv", "json"], default="csv")
    ap.add_argument("--country", help="comma-separated country codes to keep, e.g. US,EA,GB")
    ap.add_argument("--min-importance", choices=["low", "medium", "high"], default="low")
    ap.add_argument("--from", dest="start", help="earliest date, YYYY-MM-DD")
    ap.add_argument("--to", dest="end", help="latest date, YYYY-MM-DD")
    ap.add_argument("--released", action="store_true",
                    help="keep only events that already have an actual value")
    args = ap.parse_args()

    if args.input:
        with open(args.input, encoding="utf-8") as handle:
            rows = parse(handle)
    else:
        rows = parse(sys.stdin)

    if args.country:
        wanted = {c.strip().upper() for c in args.country.split(",")}
        rows = [r for r in rows if r["country_code"] in wanted]
    floor = IMPORTANCE_RANK[args.min_importance]
    rows = [r for r in rows if IMPORTANCE_RANK[r["importance"]] >= floor]
    rows = [r for r in rows if in_date_range(r, args.start, args.end)]
    if args.released:
        rows = [r for r in rows if r["actual"]]

    out = open(args.output, "w", encoding="utf-8", newline="") if args.output else sys.stdout
    try:
        if args.format == "json":
            json.dump(rows, out, ensure_ascii=False, indent=2)
            out.write("\n")
        else:
            fields = ["date", "time", "country_code", "country", "event", "period",
                      "actual", "previous", "consensus", "forecast", "importance"]
            writer = csv.DictWriter(out, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    finally:
        if args.output:
            out.close()

    print("parsed %d events" % len(rows), file=sys.stderr)


if __name__ == "__main__":
    main()
