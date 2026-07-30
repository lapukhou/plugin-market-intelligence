---
name: appfigures-explorer
description: "Market intelligence for iOS App Store and Google Play apps via the public Appfigures Explorer API (/exs, /exsc). This skill should be used when the user wants revenue or downloads estimates for an app, publisher comparisons, top releases for a period, niche or genre research, a developer's portfolio, MoM dynamics, or revenue geography. Triggers include: App Store / Google Play research, \"how much does this app make\", \"top apps in category X\", \"what's this developer's best app\", \"how is niche Z doing\", keyword / bundle / Apple App Store ID lookups, \"Appfigures\", \"Appfigures Explorer\", \"app intelligence\", \"market intelligence\", \"downloads estimate\", \"revenue estimate\". Not for iOS/Android development, code review of company product code, or App Store Connect developer-account operations."
---

# appfigures-explorer

App Store / Google Play analysis via **Appfigures Explorer**. No auth, two POST endpoints. Revenue and downloads estimates are available anonymously.

**Two hard limits shape every query** (both are 403s, verified 2026-07-30): `sort=` is rejected outright, and `/exs` returns at most **25 records** (`count × page ≤ 25`). So you cannot sort a market or page through it — you narrow the filter until the apps you want fall inside the 25, using `/exsc` (uncapped) to size the set. Details in `references/api.md`.

## When to use

When the user asks **any** question of the form:

- "How much does [app] make?"
- "Find top apps in niche [X] released in [period]"
- "What performs best for developer [Y]?"
- "How is niche [Z] doing?" / "MoM for the niche"
- "Show apps by keyword / bundle / Apple ID"
- "Compare iOS vs Google Play by [metric]"
- "Build an app intelligence report on [app]"

If the context is ambiguous (e.g. "tell me about X"), silently apply the **default**: iOS App Store, worldwide, 30-day window. After finishing, ask whether Google Play or a saved report file is needed.

## Architecture and tools

Source of truth: **`/market/explorer/_u/data/exs`** (listing with custom_meta) and **`/market/explorer/_u/data/exsc`** (aggregations). Full API reference in `references/api.md`. Ready-made DSL snippets in `references/dsl-cookbook.md`. Analysis algorithms (MoM formula, ARPD, country breakdown) in `references/analysis-patterns.md`. Ready-made DSL filters for App Store categories (Books, Games: Puzzle, Health & Fitness, etc.) in `references/categories.md`.

For typical queries use the wrapper `scripts/query_exs.py` — it takes DSL and parameters, prints clean JSON to stdout (diagnostics go to stderr), and escapes the form body automatically. It is REQUIRED for queries whose DSL contains nested quotes.

To render the final report use `scripts/format_report.py`, which takes an `/exs` dump and formats tables, country breakdown, and the MoM block. Working without it is fine for non-standard tasks.

## Analysis algorithm

Work in this order:

### 1. Understand the task
Expand the user's request into three attributes:
- **subject**: niche / publisher / specific app / category-plus-window
- **storefront**: `apple:ios` (default) or `google_play`
- **time window**: 30d (default), calendar month, year, or a specific release_date range

### 2. Size the set via `/exsc` — mandatory, not optional
`/exs` returns **at most 25 records** anonymously and **rejects `sort=` outright** (both are 403s — see the plan-limits section of `references/api.md`). So `/exsc` is where the real work of scoping happens.

Hit `/exsc?fields=download_estimates_sum_30_days/stats` with the same `q=` to get `count` plus the market's download sum. Then:

- `count ≤ 25` → the whole set fits; pull it in one `/exs` call.
- `count > 25` → **you cannot page to the rest.** Add a `download_estimates_sum_30_days` floor to the DSL and raise it until `count ≤ 25`. That floor is what makes the query a "top" query now that sorting is gone. Report the floor you used and the count it excluded — a niche table built from 25 of 322 apps must say so.

### 3. Listing via `/exs`
Query with `fields=name,developer,stores_id,product_id,release_date,monetization_strategies,all_rating,all_rating_count,custom_meta` and `count=25`. **Never send `sort=`** — it fails the whole request. Sort client-side after parsing `custom_meta` (`scripts/format_report.py` already does).

If the request is about a specific app, filter with `["match","refno",<APPLE_ID>]`. This works for Apple apps directly, no intermediate steps, and single-app queries are unaffected by the 25-record cap.

### 4. Parse `custom_meta`
Each record contains a `custom_meta` array — one element per country plus `country=zz` (worldwide rollup).

Key worldwide metrics from the `zz` element:
- `download_estimates_sum_30_days` / `sum_365_days`
- `revenue_estimates_sum_30_days` / `sum_365_days`
- `*_monthly_change` / `*_daily_change` — **ABSOLUTE DELTA in $ or units**, NOT a percentage

**These fields are often `null`, and null means "no estimate", not zero.** Roughly a third of a typical sample has no revenue estimate at all. Never write `$0` or `0% MoM` for a null — render `—`, exclude it from totals, state how many apps you excluded, and never count an unknown as "flat".

### 5. Compute metrics
- **MoM%** = `delta / (current - delta) * 100` (see `references/analysis-patterns.md`) — but treat a sub-1% result on a high-volume app as "no change detected", not as a measured flat month. The delta fields are too coarse for that claim: Audible's $20.1M/30d carries a monthly change of $760.
- **ARPD** = revenue / downloads
- **Monthly baseline** = `(revenue_365 - revenue_30) / 11` — excludes the current window from its own baseline; compare with the 30d sum to spot spikes vs dips (see `references/analysis-patterns.md`). **Prefer this over MoM% for trend claims** — it comes from two reported sums rather than a delta field of uncertain scale.
- **Country share** = country_30d_revenue / zz_30d_revenue

### 6. Report
Use `scripts/format_report.py` or build it by hand. **Structure** (stick to it; don't invent new sections without need):

```markdown
# 🎯 [Report title]

## Overview
- App / Developer / Apple ID + URL / Release / Rating / Monetization

## Worldwide 30d
| Metric | 30d | 365d | MoM | Prev 30d |
|---|---|---|---|---|
| Downloads | … | … | … | … |
| Revenue | … | … | … | … |
| ARPD | … | — | — | — |

## Top-N countries by revenue 30d
[table]

## Takeaways
- 2-4 short bullets with NON-OBVIOUS observations (not a restatement of the numbers)
```

For portfolio requests add a "Portfolio structure" section with revenue distribution across apps.

For niche requests add a "Niche dynamics" section counting growing / falling / flat apps by the correct MoM, plus a fourth count for apps with **no estimate** — those are unclassifiable, not flat.

Any report built from a filtered window must state its own limits: the download floor used, how many apps the niche actually contains (`/exsc` count) versus the ≤25 shown, and how many rows carry no revenue estimate. A table of 25 rows presented as "the niche" when `/exsc` reported 322 is the failure mode to avoid.

### 7. After finishing — ask about saving
At the end offer: "Save the report as a file (~/Desktop/<name>.md) or keep it in chat?". Do not do both automatically.

## Pitfalls (critical!)

1. **`sort=` is a 403.** The anonymous plan rejects every sort value. Omit the parameter and sort client-side.
2. **Only the first 25 records are reachable** (`count × page ≤ 25`). Deep pagination is impossible; narrow the filter instead. `/exsc` counts are *not* capped.
3. **Cloudflare filters by UA**. Always send a browser `User-Agent`. WebFetch does not work.
4. **Timestamps are in milliseconds** (13 digits).
5. **`*_change` = absolute delta**, not a percentage. Use the formula above.
6. **`zz` is already the worldwide rollup** — never add it to individual countries (double counting).
7. **`fields=all` does NOT include custom_meta** — for revenue use `*` or an explicit CSV including `custom_meta`.
8. **Future-scheduled releases**: a `release_date` range left open at the top picks up dates up to 6 months ahead — Apple allows scheduling. Clamp it if you mean "already shipped".
9. **`all_rating` = stars × 10** (48 = 4.8★), `all_rating_count` = review count.
10. **`stores_id` is the numeric App Store ID for Apple, and the bundle (string) for Google Play**. For Apple, `refno` = same as stores_id, int.

## For Google Play

If the user explicitly asks for Google Play, replace `apple:ios` with `google_play` in the DSL `storefronts` filter. Reverse lookup by bundle: `["match","sku","com.example.app"]` or `["match","bundle_id","com.example.app"]`.

All other fields (custom_meta, revenue, downloads) work identically.

## When NOT to use this skill

- iOS/Android app development (different tooling).
- App Store Connect developer-account operations.
- Marketing strategy / creatives (that's not data).
- Legal questions about content.

## Clarifying questions

Ask them **only** if the request is genuinely ambiguous (e.g. a niche has hundreds of apps — narrow the genre; or a publisher name has multiple spellings — ask for the Apple ID of one of their apps). Otherwise make the default assumptions and execute.
