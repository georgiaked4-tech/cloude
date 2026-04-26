---
description: Scan your email inbox for subscription payments and receipts
argument-hint: "[start-date end-date] e.g. 2025-09-01 2026-04-26"
---

Load the `subscription-tracker` skill and scan the connected Gmail inbox for all subscription-related emails.

Default date range: **1 September 2025 → 26 April 2026** (8 months).

If custom dates are provided as arguments use them instead. Otherwise confirm the default range with the user before scanning.

After scanning, present a full subscription list grouped by service name, with amounts and billing frequency, then ask if the user wants to generate the monthly dashboard.
