# Subscription Expense Tracker

description: Scan a Gmail inbox for subscription payment emails across a date range and produce a monthly expense dashboard. Triggers on "scan subscriptions", "subscription dashboard", "monthly expenses", "track subscriptions", "how much do I spend on subscriptions", "subscription costs".

## Overview

This skill connects to Gmail via MCP, searches for all subscription-related emails in the specified date range, extracts payment data, deduplicates recurring charges, and renders a structured monthly dashboard.

---

## Step 1 — Confirm Scope

Before scanning, confirm with the user:
- **Date range** (default: 2025-09-01 → 2026-04-26, covering 8 calendar months)
- **Currency** (default: detect from emails; ask if mixed currencies are found)
- **Email provider**: Gmail is pre-configured via MCP. If the user has Outlook/other, note that they need to update `.mcp.json`.

---

## Step 2 — Gmail Search Queries

Use the Gmail MCP tool to run the following searches in sequence. For each query, limit results to the date range using Gmail's `after:` / `before:` operators.

```
after:2025/09/01 before:2026/04/27 (subject:receipt OR subject:invoice OR subject:payment OR subject:subscription OR subject:renewed OR subject:charged OR subject:"your order" OR subject:billing)
```

Also run targeted queries for the most common subscription services:

```
after:2025/09/01 before:2026/04/27 from:(noreply@netflix.com OR accounts@netflix.com)
after:2025/09/01 before:2026/04/27 from:(no-reply@spotify.com OR receipt@spotify.com)
after:2025/09/01 before:2026/04/27 from:(appleid@id.apple.com OR no_reply@email.apple.com)
after:2025/09/01 before:2026/04/27 from:(noreply@google.com OR payments-noreply@google.com OR receipts@google.com)
after:2025/09/01 before:2026/04/27 from:(auto-confirm@amazon.com OR payments@amazon.com OR digital-no-reply@amazon.com)
after:2025/09/01 before:2026/04/27 from:(microsoft@email.microsoft.com OR msa@notification.microsoft.com OR noreply@microsoft.com)
after:2025/09/01 before:2026/04/27 from:(billing@openai.com OR receipts@openai.com)
after:2025/09/01 before:2026/04/27 from:(billing@anthropic.com OR receipts@anthropic.com)
after:2025/09/01 before:2026/04/27 from:(noreply@dropbox.com OR billing@dropbox.com)
after:2025/09/01 before:2026/04/27 from:(billing@notion.so OR team@mail.notion.so)
after:2025/09/01 before:2026/04/27 from:(billing@figma.com)
after:2025/09/01 before:2026/04/27 from:(billing@github.com OR noreply@github.com)
after:2025/09/01 before:2026/04/27 from:(billing@slack.com OR receipts@slack.com)
after:2025/09/01 before:2026/04/27 from:(billing@zoom.us OR no-reply@zoom.us)
after:2025/09/01 before:2026/04/27 from:(billing@adobe.com OR adobeid@adobe.com)
after:2025/09/01 before:2026/04/27 from:(noreply@canva.com OR billing@canva.com)
after:2025/09/01 before:2026/04/27 from:(billing@1password.com OR receipts@1password.com)
after:2025/09/01 before:2026/04/27 from:(billing@nordvpn.com)
after:2025/09/01 before:2026/04/27 from:(billing@grammarly.com)
after:2025/09/01 before:2026/04/27 from:(noreply@hulu.com OR billing@hulu.com)
after:2025/09/01 before:2026/04/27 from:(noreply@disneyplus.com OR help@disneyplus.com)
after:2025/09/01 before:2026/04/27 from:(info@telegram.org OR premium@telegram.org)
after:2025/09/01 before:2026/04/27 from:(noreply@twitter.com OR billing@twitter.com OR receipts@x.com)
after:2025/09/01 before:2026/04/27 from:(billing@youtube.com OR noreply@youtube.com)
after:2025/09/01 before:2026/04/27 from:(noreply@patreon.com OR billing@patreon.com)
after:2025/09/01 before:2026/04/27 from:(noreply@substack.com)
after:2025/09/01 before:2026/04/27 from:(billing@linear.app)
after:2025/09/01 before:2026/04/27 from:(billing@vercel.com OR team@vercel.com)
after:2025/09/01 before:2026/04/27 from:(billing@render.com)
after:2025/09/01 before:2026/04/27 from:(billing@heroku.com)
after:2025/09/01 before:2026/04/27 from:(aws-receipts@amazon.com)
after:2025/09/01 before:2026/04/27 from:(billing@digitalocean.com)
```

---

## Step 3 — Extract Payment Data

For each email found, extract:

| Field | How to find it |
|---|---|
| `service` | Sender domain or brand name in subject/body |
| `amount` | Regex: currency symbol + digits (e.g. `\$[\d,]+\.?\d*`, `€[\d]+`, `£[\d]+`, `[\d]+[,.]?\d*\s?(USD\|EUR\|GBP\|RUB\|₽)`) |
| `currency` | Symbol or ISO code next to amount |
| `date` | Email date header (normalize to YYYY-MM-DD) |
| `month` | Derived from date: YYYY-MM |
| `frequency` | Monthly / Annual / Weekly (infer from subject or body keywords: "monthly", "annual", "yearly", "per year") |
| `plan` | Plan name if mentioned (e.g. "Premium", "Pro", "Business") |

**De-duplication rules:**
- If the same service+amount appears more than once in a single calendar month, keep only one entry (it's a duplicate delivery)
- If frequency is `annual`, divide the amount by 12 to get a monthly equivalent and mark it `(annual, prorated)`

---

## Step 4 — Build the Subscription Registry

Compile all extracted records into a structured registry:

```
SERVICE              | PLAN      | AMOUNT  | CURRENCY | FREQ    | MONTHS SEEN
---------------------|-----------|---------|----------|---------|------------
Netflix              | Standard  | 15.49   | USD      | Monthly | Sep–Apr (8)
Spotify              | Individual| 9.99    | USD      | Monthly | Sep–Apr (8)
Apple iCloud+        | 200GB     | 2.99    | USD      | Monthly | Sep–Apr (8)
GitHub Copilot       | Individual| 10.00   | USD      | Monthly | Sep–Apr (8)
...
```

After showing the registry, ask the user to:
1. Confirm or correct any misidentified services
2. Flag any subscriptions they want to cancel
3. Add any missing subscriptions they know about (e.g. auto-pay from bank card not captured in email)

---

## Step 5 — Monthly Dashboard

Render the dashboard in three sections:

### Section A — Month-by-Month Breakdown

For each calendar month in the range, list all active subscriptions and their cost:

```
═══════════════════════════════════════════════════════════
  SUBSCRIPTION EXPENSE DASHBOARD  |  Sep 2025 – Apr 2026
═══════════════════════════════════════════════════════════

📅 SEPTEMBER 2025
─────────────────────────────────────────────────────────
  Netflix (Standard)          $15.49
  Spotify (Individual)         $9.99
  Apple iCloud+ (200GB)        $2.99
  GitHub Copilot              $10.00
  Notion (Personal Pro)        $8.00
  OpenAI ChatGPT Plus         $20.00
  Adobe CC (Photography)      $19.99
  ─────────────────────────────────
  TOTAL SEPTEMBER             $86.46

📅 OCTOBER 2025
─────────────────────────────────────────────────────────
  ...
  TOTAL OCTOBER               $XX.XX

[... repeat for all months ...]
```

### Section B — Summary Statistics

```
═══════════════════════════════════════════════════════════
  SUMMARY  |  Sep 2025 – Apr 2026  (8 months)
═══════════════════════════════════════════════════════════

  Total spent (8 months):          $XXX.XX
  Average monthly spend:           $XXX.XX
  Highest month:                   [Month] — $XXX.XX
  Lowest month:                    [Month] — $XXX.XX

  Monthly subscriptions:           X services
  Annual subscriptions (prorated): X services
  Total unique services:           X

═══════════════════════════════════════════════════════════
  TOP SUBSCRIPTIONS BY COST (monthly equivalent)
═══════════════════════════════════════════════════════════

  1. [Service]    $XX.XX/mo   XX% of total
  2. [Service]    $XX.XX/mo   XX% of total
  3. [Service]    $XX.XX/mo   XX% of total
  ...
```

### Section C — Category Breakdown

Group services into categories and show percentage of total spend:

| Category | Services | Monthly avg | % of spend |
|---|---|---|---|
| 🎬 Entertainment | Netflix, Hulu, Disney+ | $XX.XX | XX% |
| 🎵 Music & Audio | Spotify | $XX.XX | XX% |
| 💼 Productivity | Notion, Slack, Zoom | $XX.XX | XX% |
| ☁️ Cloud & Storage | Dropbox, iCloud, Google One | $XX.XX | XX% |
| 🛠 Dev Tools | GitHub, Vercel, Linear | $XX.XX | XX% |
| 🤖 AI Tools | ChatGPT, Claude, Copilot | $XX.XX | XX% |
| 🎨 Design | Figma, Adobe CC, Canva | $XX.XX | XX% |
| 🔐 Security & VPN | 1Password, NordVPN | $XX.XX | XX% |
| 📦 Other | ... | $XX.XX | XX% |

---

## Step 6 — Actionable Insights

After the dashboard, provide:

1. **Unused / Forgotten subscriptions** — flag any service the user might not be actively using (e.g. duplicate streaming services, overlapping tools)
2. **Annual savings opportunity** — for monthly subs that offer annual plans, calculate how much they'd save switching to annual billing
3. **Cancellation candidates** — list subscriptions under $5/mo that might be easy wins, and subscriptions with similar alternatives
4. **Currency exposure** — if subscriptions are billed in foreign currencies, note any FX risk

---

## Error Handling

- **No emails found for a service**: Skip silently; don't fabricate data
- **Ambiguous amount** (multiple currencies in one email): Flag for user confirmation
- **Gmail auth failure**: Prompt the user to run `npx @gongrzhe/server-gmail-autoauth-mcp` in their terminal to authenticate
- **Rate limits**: Batch queries with a small delay; process up to 500 emails total
