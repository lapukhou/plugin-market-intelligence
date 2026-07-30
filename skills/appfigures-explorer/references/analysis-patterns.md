# Analysis patterns — formulas and report structures

## Worldwide vs countries

`custom_meta` is an array. `country=zz` is always the worldwide aggregate — **never add it** to individual countries.

```python
def ww(record, key):
    """Extract a worldwide metric from custom_meta."""
    z = next((x for x in (record.get('custom_meta') or [])
              if x.get('country')=='zz'), None)
    return (z or {}).get(key, 0) or 0
```

## MoM% — the most important pattern

`*_monthly_change` and `*_daily_change` are an **absolute delta** (dollars for revenue, units for downloads). NOT a percentage.

**Never display a raw `*_change` value as "% MoM".** This is the single most common mistake when working with Appfigures.

```python
def mom_pct(current, delta):
    """Correct MoM%: delta is the absolute delta of the same field."""
    prev = current - delta
    return (delta / prev * 100) if prev > 0 else 0
```

Example: if `revenue_estimates_sum_30_days = 273955` and `revenue_estimates_monthly_change = 21`, then prev = 273934, MoM = +0.008% — not +21%. Conversely: if `monthly_change = 38070` with `30d = 58093`, then prev = $20K, MoM = +190% — a genuine explosion.

## ARPD (revenue per download)

```python
arpd = revenue_30d / downloads_30d if downloads_30d else 0
```

A rough proxy for unit economics. Typical ranges:
- `< $0.50` — ad-driven / broad audience, weak conversion
- `$0.50 – $3` — average freemium model
- `$3 – $20` — premium subscription model
- `> $20` — narrow niche / high-LTV (professionals, B2B, collector market)

ARPD varies heavily by country — in a single breakdown, US/JP/CH can be 3-5× higher than Brazil/India.

## 365d monthly average as a baseline

To judge "spike or normal", compare `30d` against `(365d - 30d) / 11`:

```python
avg_11mo = (rev_365 - rev_30) / 11 if rev_365 > rev_30 else 0
ratio = rev_30 / avg_11mo if avg_11mo else 0
# ratio > 1.5 = spike
# ratio = 0.8..1.2 = normal
# ratio < 0.7 = dip
```

This is a proxy (there is no direct `prev_30d`), but it gives good trend intuition. Subtracting the current 30d window first keeps it from inflating its own baseline.

## Country breakdown

For a single-app report:

```python
countries = sorted(
    [c for c in record['custom_meta'] if c.get('country') and c['country'] != 'zz'],
    key=lambda x: x.get('revenue_estimates_sum_30_days', 0) or 0,
    reverse=True
)
```

Revenue concentration:
- Top-country share = top1_rev / zz_rev. >40% = "single-country app", <20% = "globally distributed".
- If the top-3 countries produce >70%, the marketing targets are narrow.

Anomalies:
- Low downloads + high revenue in a country = premium segment (CH, IL, NO are often like this)
- High downloads + low revenue = marketing testing without monetization (BR, MX, IN typically)

## Publisher portfolio structure

The Pareto pattern — usually 1 app produces 50-80% of the portfolio:

```python
total_rev = sum(ww(a, 'revenue_estimates_sum_30_days') for a in apps)
top_share = ww(apps[0], 'revenue_estimates_sum_30_days') / total_rev * 100
```

Health markers:
- `top_share > 80%` → cash-cow dependency (risk)
- `top_share 30-50%` → diversified
- Count of apps with rev > $1K ÷ total → portfolio "hit rate"
- Growing vs dead apps released >12 months ago → studio productivity

## Niche dynamics

The correct way to judge whether a niche is "exploding":

```python
growing = [a for a in apps if mom_pct(rev_30, delta_rev) > 10 and rev_30 > 1000]
falling = [a for a in apps if mom_pct(rev_30, delta_rev) < -10 and rev_30 > 1000]
flat = [a for a in apps if -10 <= mom_pct(rev_30, delta_rev) <= 10 and rev_30 > 1000]
```

If the top-5 leaders are **flat or falling** while a couple of small apps grow, the niche is **mature and rotating** — not explosive growth.

If the top-5 grow in sync at >50% MoM — a real seasonal/viral spike.

## Report templates

### Single app — deep dive
```markdown
# 🎯 [Name]

**[Subtitle]** · [URL]
**Developer:** [name] (country) · **Release:** [date] · **Rating:** [stars]★ × [count]
**Monetization:** [strategies]

## Worldwide 30d
| | 30d | 365d | MoM% | Prev 30d |
|---|---:|---:|---:|---:|
| Downloads | … | … | … | … |
| Revenue | … | … | … | … |
| ARPD | … | — | — | — |

## Top-N countries by revenue
[table]

## Observations
- [What is UNUSUAL — not a restatement of the numbers]
- [What an analyst would notice at a glance]
```

### Top releases for a period
```markdown
# 🏆 Top iOS releases [period]

**Sample:** [N] apps (with non-zero downloads)

| # | Release | Rev 30d | DL 30d | Apple ID | Name · Developer |
|---|---|---:|---:|---|---|
[top 15-20]

## Winner — [Name]
[deep dive from the template above]

## Patterns
- [What stands out: genres, countries, team sizes]
```

### Publisher portfolio
```markdown
# 🏭 [Publisher] — iOS Portfolio

**Apps:** [N] · **Run rate:** ~$[Xm]/yr
| | 30d | 365d |
|---|---:|---:|
| Revenue | … | … |
| Downloads | … | — |

## Top performers
[table]

## Structure
- Cash cow: [%] of revenue from a single app
- Hit rate: [Y of N] apps make >$1K/mo

## Where the momentum is
[1-2 apps with genuine MoM growth]
```

### Niche analysis
```markdown
# 🔍 [Niche] — state of play

**In the index:** [N] iOS subscription apps with "[keyword]" in the name
**Combined:** $[X]M/mo, $[Y]M/yr

## Top-15
[table with MoM%]

## Dynamics
- Growing >10% MoM: [N] apps
- Falling >10% MoM: [N] apps
- Flat: [N] apps

## Gaining momentum
[1-3 apps with a genuine breakout]

## Losing ground
[1-3 apps with a dip]
```

## MoM in a single pass

```python
import json, urllib.request, urllib.parse

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36'

def fetch_exs(q, fields, sort=None, count=100):
    body = urllib.parse.urlencode({'q': q}).encode()
    qs = f'fields={urllib.parse.quote(fields, safe=",*")}&count={count}'
    if sort: qs += f'&sort={urllib.parse.quote(sort)}'
    url = f'https://appfigures.com/market/explorer/_u/data/exs?{qs}'
    req = urllib.request.Request(url, data=body,
        headers={'User-Agent': UA, 'Content-Type': 'application/x-www-form-urlencoded'})
    return json.load(urllib.request.urlopen(req))

def enrich(record):
    """Lift worldwide metrics to the top level."""
    z = next((x for x in (record.get('custom_meta') or []) if x.get('country')=='zz'), {})
    rec = dict(record)
    rec['rev_30d'] = z.get('revenue_estimates_sum_30_days', 0) or 0
    rec['rev_365d'] = z.get('revenue_estimates_sum_365_days', 0) or 0
    rec['dl_30d'] = z.get('download_estimates_sum_30_days', 0) or 0
    delta_r = z.get('revenue_estimates_monthly_change', 0) or 0
    delta_d = z.get('download_estimates_monthly_change', 0) or 0
    prev_r = rec['rev_30d'] - delta_r
    prev_d = rec['dl_30d'] - delta_d
    rec['mom_rev'] = (delta_r / prev_r * 100) if prev_r > 0 else 0
    rec['mom_dl']  = (delta_d / prev_d * 100) if prev_d > 0 else 0
    rec['arpd']    = (rec['rev_30d'] / rec['dl_30d']) if rec['dl_30d'] else 0
    return rec
```
