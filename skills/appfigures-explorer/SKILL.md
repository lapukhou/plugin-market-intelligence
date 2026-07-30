---
name: appfigures-explorer
description: "Market intelligence for iOS App Store and Google Play apps via the public Appfigures Explorer API (/exs, /exsc). This skill should be used when the user wants revenue or downloads estimates for an app, publisher comparisons, top releases for a period, niche or genre research, a developer's portfolio, MoM dynamics, or revenue geography. Triggers include: App Store / Google Play research, \"how much does this app make\", \"top apps in category X\", \"what's this developer's best app\", \"how is niche Z doing\", keyword / bundle / Apple App Store ID lookups, \"Appfigures\", \"Appfigures Explorer\", \"app intelligence\", \"market intelligence\", \"downloads estimate\", \"revenue estimate\". Not for iOS/Android development, code review of company product code, or App Store Connect developer-account operations."
---

# appfigures-explorer

App Store / Google Play analysis via **Appfigures Explorer**. No auth, two POST endpoints. Revenue and downloads estimates are available anonymously.

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

### 2. Sample size via `/exsc` (optional but recommended)
Before a heavy `/exs`, hit `/exsc?fields=release_date/stats` with the same `q=` to get `count`. If the sample is >5000, narrow the filter or warn the user that results will be truncated.

### 3. Listing via `/exs`
Query with `fields=name,developer,stores_id,product_id,release_date,monetization_strategies,all_rating,all_rating_count,custom_meta` and a suitable `sort=` — usually `-download_estimates_sum_30_days` for top charts, `-release_date` for fresh releases. `count=` goes up to 1000.

If the request is about a specific app, filter with `["match","refno",<APPLE_ID>]`. This works for Apple apps directly, no intermediate steps.

### 4. Parse `custom_meta`
Each record contains a `custom_meta` array — one element per country plus `country=zz` (worldwide rollup).

Key worldwide metrics from the `zz` element:
- `download_estimates_sum_30_days` / `sum_365_days`
- `revenue_estimates_sum_30_days` / `sum_365_days`
- `*_monthly_change` / `*_daily_change` — **ABSOLUTE DELTA in $ or units**, NOT a percentage

### 5. Compute metrics
- **MoM%** = `delta / (current - delta) * 100` (see `references/analysis-patterns.md`)
- **ARPD** = revenue / downloads
- **Monthly baseline** = `(revenue_365 - revenue_30) / 11` — excludes the current window from its own baseline; compare with the 30d sum to spot spikes vs dips (see `references/analysis-patterns.md`)
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

For niche requests add a "Niche dynamics" section counting growing / falling / flat apps by the correct MoM.

### 7. After finishing — ask about saving
At the end offer: "Save the report as a file (~/Desktop/<name>.md) or keep it in chat?". Do not do both automatically.

## Pitfalls (critical!)

1. **Cloudflare filters by UA**. Always send a browser `User-Agent`. WebFetch does not work.
2. **Timestamps are in milliseconds** (13 digits).
3. **`*_change` = absolute delta**, not a percentage. Use the formula above.
4. **`zz` is already the worldwide rollup** — never add it to individual countries (double counting).
5. **`fields=all` does NOT include custom_meta** — for revenue use `*` or an explicit CSV including `custom_meta`.
6. **Future-scheduled releases**: `sort=-release_date` returns dates up to 6 months ahead — Apple allows scheduling.
7. **`all_rating` = stars × 10** (48 = 4.8★), `all_rating_count` = review count.
8. **`stores_id` is the numeric App Store ID for Apple, and the bundle (string) for Google Play**. For Apple, `refno` = same as stores_id, int.

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
