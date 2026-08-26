---
description: Score a data release against consensus and read the market implication
argument-hint: "[release, e.g. 'US CPI August' or 'actual 3.4 vs cons 3.2']"
---

Load the `data-surprise` skill to score a release against expectations.

Compute the surprise against consensus (not the vendor forecast), standardize it
where a surprise history is available, check whether the prior period was
revised, look inside the print at the components that matter, and give the read
for rates, FX and equities.

If actual and consensus were provided in the arguments, use them. Otherwise
retrieve the release first, and say so if consensus is unavailable.
