# DSL Cookbook — ready-made `q=` values for common tasks

Every example is the value of the **form parameter `q=`** for `/exs` and `/exsc`. Pass it via `--data-urlencode "q=…"`, otherwise the escaping breaks.

## Building blocks

### iOS only
```json
["match","storefronts",["and","apple:ios"]]
```

### Google Play only
```json
["match","storefronts",["and","google_play"]]
```

### One specific app by Apple ID
```json
["match","refno",6751584800]
```

### One app by Google Play bundle
```json
["match","sku","com.whatsapp"]
```
(alternatively `bundle_id`)

### Release date window (timestamps in ms)
```json
["match","release_date",["range",1772323200000,1775001600000]]
```

### Only apps with non-zero downloads over 30d
```json
["match","download_estimates_sum_30_days",["range",1,99999999]]
```

### Subscription apps only
```json
["match","monetization_strategies",["or","subscriptions"]]
```

### Paid apps only
```json
["match","is_paid",true]
```

### Search by name
```json
["match","name","brain"]
```
Full-text contains-search, tokenized.

### Publisher (single token)
```json
["match","developer",["and","AIBY"]]
```

### Publisher (multiple words)
```json
["match","developer",["and","DPM","APPS"]]
```
All tokens must be present in the string. Add more tokens for uniqueness.

## Compositions (and/or/not)

### iOS + date window + subscriptions
```json
["and",
  ["match","storefronts",["and","apple:ios"]],
  ["match","release_date",["range",1772323200000,1775001600000]],
  ["match","monetization_strategies",["or","subscriptions"]]
]
```

### iOS + specific publisher + non-zero downloads
(downloads as a proxy for activity — revenue fields are not filterable at the record root)
```json
["and",
  ["match","storefronts",["and","apple:ios"]],
  ["match","developer",["and","AIBY"]],
  ["match","download_estimates_sum_30_days",["range",1,99999999]]
]
```

### iOS + Education category + brain
```json
["and",
  ["match","storefronts",["and","apple:ios"]],
  ["match","name","brain"],
  ["match","categories.main",6017]
]
```
(6017 = Education primary category; `categories.main` holds a single ID. For full coverage across platform variants prefer `categories.all` — ID lists in `categories.md`)

## Ready-made recipes

### "Top new releases of the month by downloads, iOS, non-zero"
DSL:
```json
["and",
  ["match","storefronts",["and","apple:ios"]],
  ["match","release_date",["range",FROM_MS,TO_MS]],
  ["match","download_estimates_sum_30_days",["range",1,99999999]]
]
```
Sort: `sort=-download_estimates_sum_30_days`
Fields: `fields=name,developer,stores_id,product_id,release_date,custom_meta`

### "All apps of a specific publisher"
DSL:
```json
["and",
  ["match","storefronts",["and","apple:ios"]],
  ["match","developer",["and","<developer_first_token>"]]
]
```
Sort: `sort=-download_estimates_sum_30_days` (top) or `-release_date` (newest)
Fields: `fields=name,developer,stores_id,release_date,monetization_strategies,custom_meta`

⚠️ If the publisher has many near-namesakes (like DPM APPS LP — many "DPM*"), use more tokens: `["and","DPM","APPS"]`. Filter to the exact name client-side afterwards.

### "Subscription apps in a niche"
DSL:
```json
["and",
  ["match","storefronts",["and","apple:ios"]],
  ["match","name","<keyword>"],
  ["match","monetization_strategies",["or","subscriptions"]]
]
```

### "Apps present in a single store only" (not ported)
DSL:
```json
["and",
  ["match","storefronts",["and","apple:ios"]],
  ["match","num_storefronts",1]
]
```

### "Sub-apps with ratings >= 4.0 only (40 on the ×10 scale)"
```json
["and",
  ["match","storefronts",["and","apple:ios"]],
  ["match","monetization_strategies",["or","subscriptions"]],
  ["match","all_rating",["range",40,50]],
  ["match","all_rating_count",["range",100,99999999]]
]
```

### Excluding values with `not`

To **exclude** values, wrap the `match` in a `not`. Inside the `match`, use `or` to list multiple excluded values:

```json
["and", ["not", ["match", "categories.all", ["or", 6021, 16021]]]]
```
→ "categories.all contains neither 6021 nor 16021".

**Rule:** `not` always wraps the whole `["match", field, value]` expression, not the value itself.

#### Exclusion examples

**iOS, without the Games category (6014):**
```json
["and",
  ["match","storefronts",["and","apple:ios"]],
  ["not",["match","categories.all",["or",6014]]]
]
```

**iOS, excluding a specific publisher:**
```json
["and",
  ["match","storefronts",["and","apple:ios"]],
  ["not",["match","developer",["and","AIBY"]]]
]
```

**iOS, excluding several categories at once:**
```json
["and",
  ["match","storefronts",["and","apple:ios"]],
  ["not",["match","categories.all",["or",6014,6018,6021]]]
]
```

**iOS, non-free (paid) only:**
```json
["and",
  ["match","storefronts",["and","apple:ios"]],
  ["not",["match","is_paid",false]]
]
```

## Computing millisecond month boundaries

In Python (canonical — use this for any month not listed below):
```python
from datetime import datetime, timezone
def month_window_ms(year, month):
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = datetime(year + (month==12), (month%12)+1, 1, tzinfo=timezone.utc)
    return int(start.timestamp()*1000), int(end.timestamp()*1000)
```

Precomputed for 2025-12 through 2026-12:
- 2025-12: 1764547200000 — 1767225600000
- 2026-01: 1767225600000 — 1769904000000
- 2026-02: 1769904000000 — 1772323200000
- 2026-03: 1772323200000 — 1775001600000
- 2026-04: 1775001600000 — 1777593600000
- 2026-05: 1777593600000 — 1780272000000
- 2026-06: 1780272000000 — 1782864000000
- 2026-07: 1782864000000 — 1785542400000
- 2026-08: 1785542400000 — 1788220800000
- 2026-09: 1788220800000 — 1790812800000
- 2026-10: 1790812800000 — 1793491200000
- 2026-11: 1793491200000 — 1796083200000
- 2026-12: 1796083200000 — 1798761600000

## Filtering by App Store category

Use `["match","categories.all",["or",ID1,ID2,...]]`. Each category has several ID variants (iPad / Mac / TV / Watch use their own numbering) — all known IDs are collected in **`categories.md`**.

Example: top Health & Fitness iOS apps:
```json
["and",
  ["match","storefronts",["and","apple:ios"]],
  ["match","categories.all",["or",57,1014,6013,12007,16013,86013]]
]
```

## Known limitations

- The `genre` parameter does not work in the DSL; use `categories.all` (see above).
- Sorting works on root-level fields only (not fields inside `custom_meta`). Sort by revenue client-side after the dump.
- Text search `["match","name","X"]` matches whole tokens, case-insensitively. No wildcards.
- There are no `revenue_*` fields at the record root — only inside `custom_meta` (see analysis-patterns).
