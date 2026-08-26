---
description: Parse and filter an economic calendar
argument-hint: "[countries and/or date range, e.g. 'US EA this week']"
---

Load the `economic-calendar` skill to normalize an economic calendar into a
filterable table of releases.

If the user has pasted or attached calendar data, parse that. If not, ask which
countries and date range they want, then pull it from an available data source.

Apply any filters in the arguments. With no arguments, default to high-importance
releases for the next five business days.
