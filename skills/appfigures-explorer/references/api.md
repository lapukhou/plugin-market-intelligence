# Appfigures — working reference

Reverse-engineered `appfigures.com/market/explorer`. A **single** endpoint (`/exs`) covers practically every task, plus `/exsc` for quick recon.

- Public, no auth — only a browser `User-Agent` is required (Cloudflare filters by fingerprint; `python-requests` and WebFetch are blocked).
- Revenue, downloads, and trend data are available anonymously via the `custom_meta` array inside `/exs`.

### ⚠️ Anonymous plan limits (verified 2026-07-30)

Two hard caps shape every query. Both return **HTTP 403** with a `message` field, not an empty result:

| Limit | Behaviour |
|---|---|
| `sort` unavailable | Any `sort=` value → `{"message":"Cannot use custom sort with the current account plan"}`. Tested with `-download_estimates_sum_30_days`, `-release_date`, `release_date`, `-importance`, `-all_rating_count` — all rejected. |
| 25-record window | `count × page` must be **≤ 25** → `{"message":"Cannot request more than 25 results with the current account plan"}`. `count=25&page=1` ✅, `count=12&page=2` ✅, `count=13&page=2` ❌, `count=50` ❌. |

So `/exs` shows only the **first 25 records** of a result set, in the index's default relevance order (roughly by `importance`, but not strictly sorted). Consequences:

- **Never send `sort=`** — it fails the whole request. Sort client-side within the 25 records.
- **Deep pagination is impossible.** You cannot walk a 322-app niche; you get 25 records total.
- **To reach the top of a market, narrow the filter instead of sorting.** Add a `download_estimates_sum_30_days` floor and calibrate it with `/exsc` until `count ≤ 25` (recipe below).
- `/exsc` is **not** capped — its `count` and stats work over the full result set. Use it for market sizing.

## Endpoints

| # | URL | Method | Purpose |
|---|---|---|---|
| 1 | `/market/explorer/_u/data/exs` | POST | **Main**: listing + DSL filter + `custom_meta` with per-country revenue |
| 2 | `/market/explorer/_u/data/exsc` | POST | **Recon**: aggregations (count/min/max/avg/sum) over the same index |

Host: `appfigures.com` (not `app.appfigures.com`).

---

## 1. `/exs` — the main tool ⭐⭐⭐

```bash
curl -X POST 'https://appfigures.com/market/explorer/_u/data/exs?fields=name,stores_id,product_id,custom_meta&count=25' \
  -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36' \
  -H 'content-type: application/x-www-form-urlencoded' \
  --data-urlencode 'q=["and",["match","storefronts",["and","apple:ios"]]]'
```

### Query parameters

| Parameter | Value |
|---|---|
| `fields` | CSV of field names. `*` = all 96 (includes `custom_meta`). `all` = curated 48 (WITHOUT `custom_meta`!). |
| `sort` | ❌ **Unusable anonymously** — any value returns 403. Documented for completeness (`-<field>` = desc, on root-level fields only); omit it entirely and sort client-side. |
| `count` | Records per page. **Max 25** anonymously, and `count × page ≤ 25`. |
| `page` | Pagination (1..N), but bounded by the same `count × page ≤ 25` window. |

### Filter DSL (form-body `q=`)

Nested JSON arrays `[op, ...args]`.

- **Operators:** `and`, `or`, `not`, `match`
- **`match` value:** literal / `["and", ...]` / `["or", ...]` / `["range", from, to]`

```json
["and", ["match", "storefronts", ["and", "apple:ios"]]]                       // iOS only
["and", ["match", "refno", 6751584800]]                                       // by Apple ID (replaces /products/apple/<id>)
["match", "release_date", ["range", 1774915200000, 1777593600000]]            // date window (ms)
["match", "download_estimates_sum_30_days", ["range", 1, 99999999]]           // drop zeros
["match", "num_storefronts", 1]                                               // single-store apps only
["match", "monetization_strategies", ["or", "subscriptions"]]                 // sub-apps only
["match", "developer", ["and", "AIBY"]]                                       // publisher (single token)
["match", "developer", ["and", "DPM", "APPS"]]                                // two-word publisher
["match", "name", "brain"]                                                    // name contains "brain"
```

### Full catalog of Explorer index fields (96 via `fields=*`)

**Identifiers (10):**
| Field | Description |
|---|---|
| `product_id` | Internal Appfigures ID (int) |
| `stores_id` | Apple App Store ID / Google Play bundle |
| `refno` | Alias for stores_id on Apple (int) |
| `sku` | Bundle ID (often null) |
| `bundle_id` | Explicit bundle (`com.openai.chat`) |
| `store` | `"apple"`, `"google_play"` |
| `storefronts` | `["apple:ios"]`, `["google_play"]`, etc. |
| `type` | `"app"`, `"in-app"` |
| `entity_type` | Usually `"product"` |
| `active` | `true`/`false` |

**Metadata (21):** `name`, `subtitle`, `developer`, `developer_id`, `developer_country`, `developer_email`, `developer_site`, `publisher_id`, `icon`, `screenshots`, `video_url`, `version`, `version_required`, `view_url`, `support_url`, `copyright`, `primary_description`, `release_notes`, `release_date`, `added_date`, `updated_date`

**Classification (9):** `categories` (`{main, all[]}`), `num_categories`, `iab_categories_v1`, `num_iab_categories_v1`, `content_rating` (`"4+"`, `"12+"`, `"17+"`), `recommended_age`, `top_developer`, `editors_choice`, `rank_join`

**Technical (20):** `sdks`, `all_sdks`, `num_sdks`, `num_all_sdks`, `all_permissions`, `num_all_permissions`, `permission_groups`, `num_permission_groups`, `download_size`, `devices`, `num_devices`, `langs`, `localized_langs`, `num_langs`, `num_localized_langs`, `countries`, `num_countries`, `watch_compatible`, `has_voice_control`, `num_storefronts`

**Monetization (11):** `prices` (`[{country, currency, price}]`), `num_prices`, `us_price`, `is_paid`, `has_inapps`, `has_ads`, `has_subscriptions`, `monetization_strategies` (`["inapps","ads","subscriptions"]`), `monetization_slug`, `num_monetization_strategies`, `ad_observed`

**Ratings (4):** `all_rating` (stars × 10, 48 = 4.8★), `all_rating_count`, `version_rating`, `version_rating_count`

**Root-level aggregates (5):** `downloads` (usually null), `download_estimates_sum_30_days`, `download_estimates_average_30_days`, `importance` (Appfigures popularity score 0–2293), `num_screenshots`. **There are NO revenue fields at the root — only inside `custom_meta`.**

**Demographics (8):** `inferred_female_percent`, `inferred_gender_classification` (`"leans_male"`, `"leans_female"`, `"even_demographic"`), `inferred_age_classification` (dominant group), `inferred_age_18_to_24_percent`, `inferred_age_25_to_34_percent`, `inferred_age_35_to_49_percent`, `inferred_age_50_to_64_percent`, `inferred_age_65_and_older_percent`

**Relations (6):** `similar` (`[{related_id, storefronts, score, ratings_score}]`), `num_similar`, `exact` (same app in other stores), `num_exact`, `other_storefronts`, `num_other_storefronts`

**Localization:** `meta` (`[{primary_description, release_notes, …}]` per language)

**Special:** `custom_meta` ⬇️

### 🎯 `custom_meta` — revenue and downloads PER COUNTRY

Array of objects. Each element = one country. `country=zz` is the worldwide rollup.

| Element field | Description |
|---|---|
| `country` | ISO-2 or `"zz"` (worldwide) |
| `download_estimates_sum_30_days` | Downloads over 30 days |
| `download_estimates_average_30_days` | Daily average (30d / 30) |
| `download_estimates_sum_365_days` | Downloads over 365 days |
| `download_estimates_daily_change` | ⚠️ **Absolute delta in units** (not %) |
| `download_estimates_monthly_change` | ⚠️ **Absolute delta in units** (not %) |
| `revenue_estimates_sum_30_days` | Revenue $ over 30 days |
| `revenue_estimates_average_30_days` | Daily average |
| `revenue_estimates_sum_365_days` | Revenue $ over 365 days |
| `revenue_estimates_daily_change` | ⚠️ **Absolute delta in $** |
| `revenue_estimates_monthly_change` | ⚠️ **Absolute delta in $** |

### ⚠️ `*_change` is an ABSOLUTE DELTA, NOT A PERCENTAGE

The `*_daily_change` and `*_monthly_change` fields return the **absolute change in metric units** (dollars for revenue, units for downloads). The values are easy to mistake for percentages — don't. Values below −100 and above +1000 are common.

**The correct MoM% formula:**
```python
delta = cm[zz]['revenue_estimates_monthly_change']
current = cm[zz]['revenue_estimates_sum_30_days']
previous = current - delta
mom_pct = (delta / previous * 100) if previous > 0 else 0
```

### Parsing worldwide (jq)

```bash
jq '.results[] | {name,
  rev_30d: (.custom_meta[] | select(.country=="zz") | .revenue_estimates_sum_30_days),
  dl_30d:  (.custom_meta[] | select(.country=="zz") | .download_estimates_sum_30_days)
}'
```

---

## 2. `/exsc` — aggregations (recon)

```bash
curl -X POST 'https://appfigures.com/market/explorer/_u/data/exsc?fields=release_date/stats' \
  -H 'user-agent: Mozilla/5.0 ...' \
  -H 'content-type: application/x-www-form-urlencoded' \
  --data-urlencode 'q=["and",["match","storefronts",["and","apple:ios"]]]'
```

Same DSL in `q=`. `fields=<field>/stats` returns `{count, min, max, avg, sum, min_as_string, max_as_string, avg_as_string, sum_as_string}`.

### When to use

- **Niche size** before `/exs` — `count` is instant and **not** subject to the 25-record cap
- **Date window**: `release_date/stats` → min/max → when the niche emerged, whether future-scheduled releases exist
- **Market volume**: sum over `download_estimates_sum_30_days` — the only way to size a market larger than 25 apps
- **Floor calibration**: the standard replacement for the unavailable `sort=` (recipe below)
- **Segment comparison**: avg `all_rating` in two niches with two curls

### Limitations

- Aggregates root-level fields only. `revenue_estimates_*` live inside `custom_meta` — `/exsc` cannot see them. Segment revenue sums must be computed client-side from `/exs`.
- Only `min/max/avg/sum/count` — no histograms/percentiles/top-N.
- An invalid field name silently returns `count=0` — verify valid names via `/exs?fields=*`.

---

## Pitfalls

1. **Cloudflare filters by UA/TLS:** no `user-agent` → 403. `python-requests` and WebFetch are blocked. Curl with its default UA passes, but explicitly sending a browser UA is safer.
2. **Timestamps are in milliseconds** (13 digits). `date -u -d '2026-03-01' +%s000` (GNU) or `date -ju -f '%Y-%m-%d' '2026-03-01' +%s000` (macOS).
3. **`fields=all` does NOT include `custom_meta`** — for revenue use `fields=*` or an explicit CSV including `custom_meta`.
4. **Future-scheduled releases:** Apple allows scheduling releases ahead of time, so a `release_date` range whose upper bound is "today" silently excludes nothing, while an open-ended range picks up dates up to 6 months out. Clamp the range explicitly if you mean "already shipped".
5. **`zz` vs ISO codes in `custom_meta`:** `zz` is already the worldwide rollup — never add it to individual countries (double counting).
6. **`*_change` is an absolute delta**, not a percentage (see the formula above).
7. **`all_rating` is stars × 10**, i.e. `48` = 4.8★.
8. **`stores_id` is the numeric App Store ID for Apple; the bundle (string) for Google Play.** For Apple, `refno` = same as `stores_id`, int.

---

## Ready-made pipelines

### Single app by Apple ID → per-country revenue
```bash
APPLE='6751584800'
curl -X POST "https://appfigures.com/market/explorer/_u/data/exs?fields=name,developer,custom_meta" \
  -H 'user-agent: Mozilla/5.0 ...' \
  -H 'content-type: application/x-www-form-urlencoded' \
  --data-urlencode "q=[\"and\",[\"match\",\"refno\",${APPLE}]]"
```

### Top iOS releases for a calendar month
Since `sort` is unavailable, the download floor is what selects the top — raise it until `/exsc` reports `count ≤ 25`.
```bash
# ms window for March 2026: 1772323200000 .. 1775001600000
curl -X POST 'https://appfigures.com/market/explorer/_u/data/exs?fields=name,stores_id,product_id,release_date,developer,custom_meta&count=25' \
  -H 'user-agent: Mozilla/5.0 ...' \
  -H 'content-type: application/x-www-form-urlencoded' \
  --data-urlencode 'q=["and",["match","storefronts",["and","apple:ios"]],["match","release_date",["range",1772323200000,1775001600000]],["match","download_estimates_sum_30_days",["range",50000,99999999]]]'
```

### All apps of a specific publisher
Fine as-is for small publishers (AIBY: 53 apps → only the first 25 are reachable; add a download floor to bias toward the ones that matter).
```bash
curl -X POST 'https://appfigures.com/market/explorer/_u/data/exs?fields=name,release_date,monetization_strategies,custom_meta&count=25' \
  -H 'user-agent: Mozilla/5.0 ...' \
  -H 'content-type: application/x-www-form-urlencoded' \
  --data-urlencode 'q=["and",["match","storefronts",["and","apple:ios"]],["match","developer",["and","AIBY"]]]'
```

### Subscription apps in a narrow topic
```bash
curl -X POST 'https://appfigures.com/market/explorer/_u/data/exs?fields=name,developer,custom_meta&count=25' \
  -H 'user-agent: Mozilla/5.0 ...' \
  -H 'content-type: application/x-www-form-urlencoded' \
  --data-urlencode 'q=["and",["match","storefronts",["and","apple:ios"]],["match","name","brain"],["match","monetization_strategies",["or","subscriptions"]]]'
```

### Calibrating a download floor with `/exsc` (the `sort` replacement)
Binary-search the floor until the niche fits the 25-record window. Books, iOS:
```bash
for FLOOR in 1000 10000 50000 100000; do
  curl -s -X POST 'https://appfigures.com/market/explorer/_u/data/exsc?fields=download_estimates_sum_30_days/stats' \
    -H 'user-agent: Mozilla/5.0 ...' \
    -H 'content-type: application/x-www-form-urlencoded' \
    --data-urlencode "q=[\"and\",[\"match\",\"storefronts\",[\"and\",\"apple:ios\"]],[\"match\",\"categories.all\",[\"or\",6018,16018]],[\"match\",\"download_estimates_sum_30_days\",[\"range\",${FLOOR},99999999]]]" \
    | python3 -c 'import sys,json; print(json.load(sys.stdin)["metadata"]["resultset"]["count"])'
done
```
→ `322`, `85`, `15`, `8`. A floor of 50000 yields 15 apps — the whole set fits in one `/exs` call, then sort them client-side by `custom_meta` revenue.

### Niche size in one command (no record dump)
```bash
curl -X POST 'https://appfigures.com/market/explorer/_u/data/exsc?fields=release_date/stats' \
  -H 'user-agent: Mozilla/5.0 ...' \
  -H 'content-type: application/x-www-form-urlencoded' \
  --data-urlencode 'q=["and",["match","storefronts",["and","apple:ios"]],["match","name","brain"],["match","monetization_strategies",["or","subscriptions"]]]'
```
→ `count: 605` instantly.
