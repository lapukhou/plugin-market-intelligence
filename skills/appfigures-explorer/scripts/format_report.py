#!/usr/bin/env python3
"""
format_report.py — render a report from an /exs dump.

Usage:
    python format_report.py <input.json> [--mode app|portfolio|niche|releases]
                            [--top 15] [--limit-countries 10] [-o report.md]

Modes:
    app        — detailed profile of a single app (uses results[0])
    portfolio  — all apps of a single publisher
    niche      — niche dynamics (growing/falling/flat)
    releases   — top releases for a period

If --mode is omitted, the script guesses from the record count and developers:
one record → app; one developer → portfolio; otherwise → releases.
Niche mode is never auto-detected — pass --mode niche explicitly.
"""
import argparse
import json
import sys


def ww(record, key):
    z = next((x for x in (record.get('custom_meta') or []) if x.get('country') == 'zz'), None)
    return (z or {}).get(key, 0) or 0


def mom_pct(current, delta):
    prev = current - delta
    return (delta / prev * 100) if prev > 0 else 0


def fmt_int(n):
    return f'{n:,}' if isinstance(n, (int, float)) else str(n)


def fmt_money(n):
    return f'${n:,.0f}' if n else '$0'


def enrich(rec):
    """Lift worldwide metrics to the top level."""
    rec = dict(rec)
    rev30 = ww(rec, 'revenue_estimates_sum_30_days')
    dl30 = ww(rec, 'download_estimates_sum_30_days')
    delta_r = ww(rec, 'revenue_estimates_monthly_change')
    delta_d = ww(rec, 'download_estimates_monthly_change')
    rec['_rev30'] = rev30
    rec['_dl30'] = dl30
    rec['_rev365'] = ww(rec, 'revenue_estimates_sum_365_days')
    rec['_dl365'] = ww(rec, 'download_estimates_sum_365_days')
    rec['_mom_rev'] = mom_pct(rev30, delta_r)
    rec['_mom_dl'] = mom_pct(dl30, delta_d)
    rec['_arpd'] = (rev30 / dl30) if dl30 else 0
    rec['_prev_rev30'] = rev30 - delta_r
    rec['_prev_dl30'] = dl30 - delta_d
    return rec


def country_table(record, top=10):
    countries = sorted(
        [c for c in (record.get('custom_meta') or [])
         if c.get('country') and c['country'] != 'zz'],
        key=lambda x: x.get('revenue_estimates_sum_30_days', 0) or 0,
        reverse=True,
    )
    out = ['| Country | DL 30d | Rev 30d | ARPD | Rev 365d |',
           '|---|---:|---:|---:|---:|']
    for c in countries[:top]:
        cdl = c.get('download_estimates_sum_30_days', 0) or 0
        crv = c.get('revenue_estimates_sum_30_days', 0) or 0
        cr365 = c.get('revenue_estimates_sum_365_days', 0) or 0
        arpd = f'${crv/cdl:.2f}' if cdl else '—'
        out.append(f'| {c["country"].upper()} | {fmt_int(cdl)} | {fmt_money(crv)} | {arpd} | {fmt_money(cr365)} |')
    return '\n'.join(out)


def store_link(record):
    sid = record.get('stores_id')
    if record.get('store') == 'google_play' or (isinstance(sid, str) and not sid.isdigit()):
        return f'[Google Play](https://play.google.com/store/apps/details?id={sid})'
    return f'[App Store](https://apps.apple.com/us/app/id{sid})'


def render_app(record, limit_countries=10):
    r = enrich(record)
    rt = r.get('all_rating')
    rating = f'{rt/10}★ × {fmt_int(r.get("all_rating_count", 0))}' if rt else '—'
    mon = ', '.join(r.get('monetization_strategies') or [])
    out = [
        f'# 🎯 {r.get("name")}',
        '',
        f'**{r.get("subtitle") or ""}** · {store_link(r)}',
        f'**Developer:** {r.get("developer")} · **Release:** {(r.get("release_date") or "")[:10]} · **Rating:** {rating}',
        f'**Monetization:** {mon}',
        '',
        '## Worldwide 30d',
        '',
        '| Metric | 30d | 365d | MoM% | Prev 30d |',
        '|---|---:|---:|---:|---:|',
        f'| Downloads | {fmt_int(r["_dl30"])} | {fmt_int(r["_dl365"])} | {r["_mom_dl"]:+.1f}% | {fmt_int(r["_prev_dl30"])} |',
        f'| Revenue | {fmt_money(r["_rev30"])} | {fmt_money(r["_rev365"])} | {r["_mom_rev"]:+.1f}% | {fmt_money(r["_prev_rev30"])} |',
        f'| ARPD | ${r["_arpd"]:.2f} | — | — | — |',
        '',
        f'## Top-{limit_countries} countries by revenue 30d',
        '',
        country_table(record, limit_countries),
    ]
    return '\n'.join(out)


def render_releases(records, top=15, limit_countries=10):
    enriched = [enrich(r) for r in records]
    enriched.sort(key=lambda x: x['_rev30'], reverse=True)
    out = [f'# 🏆 Top releases\n\n**Sample:** {len(records)} apps\n',
           '| # | Release | Rev 30d | DL 30d | MoM% | Apple ID | Name · Developer |',
           '|---|---|---:|---:|---:|---|---|']
    for i, r in enumerate(enriched[:top], 1):
        rd = (r.get('release_date') or '')[:10]
        out.append(
            f'| {i} | {rd} | {fmt_money(r["_rev30"])} | {fmt_int(r["_dl30"])} | '
            f'{r["_mom_rev"]:+.0f}% | {r.get("stores_id")} | '
            f'{r.get("name","")[:40]} · {r.get("developer","")[:25]} |'
        )
    if enriched:
        out.append('\n---\n')
        out.append('## 🥇 Leader — deep dive\n')
        out.append(render_app(enriched[0], limit_countries))
    return '\n'.join(out)


def render_portfolio(records, top=15):
    enriched = [enrich(r) for r in records]
    enriched.sort(key=lambda x: x['_rev30'], reverse=True)
    total_rev30 = sum(r['_rev30'] for r in enriched)
    total_rev365 = sum(r['_rev365'] for r in enriched)
    total_dl30 = sum(r['_dl30'] for r in enriched)
    dev = enriched[0].get('developer') if enriched else '?'

    top_share = (enriched[0]['_rev30'] / total_rev30 * 100) if total_rev30 else 0
    hits = sum(1 for r in enriched if r['_rev30'] > 1000)

    out = [
        f'# 🏭 {dev} — iOS Portfolio\n',
        f'**Apps:** {len(enriched)} · **Run rate:** ~${total_rev30*12/1e6:.1f}M/yr\n',
        '| | 30d | 365d |',
        '|---|---:|---:|',
        f'| Downloads | {fmt_int(total_dl30)} | — |',
        f'| Revenue | {fmt_money(total_rev30)} | {fmt_money(total_rev365)} |',
        '',
        '## Top performers\n',
        '| # | App | Release | Rev 30d | DL 30d | Rev 365d | MoM% |',
        '|---|---|---|---:|---:|---:|---:|',
    ]
    for i, r in enumerate(enriched[:top], 1):
        rd = (r.get('release_date') or '')[:10]
        out.append(
            f'| {i} | {r.get("name","")[:40]} | {rd} | '
            f'{fmt_money(r["_rev30"])} | {fmt_int(r["_dl30"])} | '
            f'{fmt_money(r["_rev365"])} | {r["_mom_rev"]:+.0f}% |'
        )
    out.extend([
        '',
        '## Structure',
        f'- Cash cow: {top_share:.1f}% of revenue from a single app',
        f'- Hit rate: {hits} of {len(enriched)} apps make >$1K/mo',
    ])
    return '\n'.join(out)


def render_niche(records, top=15):
    enriched = [enrich(r) for r in records]
    enriched.sort(key=lambda x: x['_rev30'], reverse=True)
    total_rev30 = sum(r['_rev30'] for r in enriched)
    total_rev365 = sum(r['_rev365'] for r in enriched)

    growing = [r for r in enriched if r['_mom_rev'] > 10 and r['_rev30'] > 1000]
    falling = [r for r in enriched if r['_mom_rev'] < -10 and r['_rev30'] > 1000]
    flat = [r for r in enriched if -10 <= r['_mom_rev'] <= 10 and r['_rev30'] > 1000]

    out = [
        f'# 🔍 Niche analysis\n',
        f'**Apps in sample:** {len(enriched)}',
        f'**Combined:** {fmt_money(total_rev30)}/mo, {fmt_money(total_rev365)}/yr\n',
        f'## Top-{top} by revenue 30d\n',
        '| # | App · Developer | Rev 30d | DL 30d | MoM% | Release |',
        '|---|---|---:|---:|---:|---|',
    ]
    for i, r in enumerate(enriched[:top], 1):
        rd = (r.get('release_date') or '')[:10]
        out.append(
            f'| {i} | {r.get("name","")[:35]} · {r.get("developer","")[:20]} | '
            f'{fmt_money(r["_rev30"])} | {fmt_int(r["_dl30"])} | '
            f'{r["_mom_rev"]:+.0f}% | {rd} |'
        )
    out.extend([
        '',
        '## Niche dynamics',
        f'- 📈 Growing >10% MoM (rev > $1K): **{len(growing)}**',
        f'- 📉 Falling <-10% MoM (rev > $1K): **{len(falling)}**',
        f'- ➖ Flat: **{len(flat)}**',
    ])
    if growing:
        out.append('\n### Gaining momentum')
        for r in growing[:5]:
            out.append(f'- **{r.get("name")}** · {r.get("developer")} — {fmt_money(r["_rev30"])} ({r["_mom_rev"]:+.0f}% MoM)')
    if falling:
        out.append('\n### Losing ground')
        for r in falling[:5]:
            out.append(f'- **{r.get("name")}** · {r.get("developer")} — {fmt_money(r["_rev30"])} ({r["_mom_rev"]:+.0f}% MoM)')
    return '\n'.join(out)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('input', help='JSON file from query_exs.py')
    p.add_argument('--mode', choices=['app', 'portfolio', 'niche', 'releases'], default=None)
    p.add_argument('--top', type=int, default=15)
    p.add_argument('--limit-countries', type=int, default=10,
                   help='Rows in the country breakdown table (app/releases modes)')
    p.add_argument('-o', '--output', default=None)
    args = p.parse_args()

    with open(args.input) as f:
        data = json.load(f)
    records = data.get('results', [])

    if not records:
        print('❌ Empty results.', file=sys.stderr)
        sys.exit(1)

    mode = args.mode
    if not mode:
        if len(records) == 1:
            mode = 'app'
        else:
            # Single developer → portfolio; otherwise releases
            devs = set(r.get('developer') for r in records)
            mode = 'portfolio' if len(devs) == 1 else 'releases'

    if mode == 'app':
        report = render_app(records[0], args.limit_countries)
    elif mode == 'portfolio':
        report = render_portfolio(records, args.top)
    elif mode == 'niche':
        report = render_niche(records, args.top)
    elif mode == 'releases':
        report = render_releases(records, args.top, args.limit_countries)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f'✓ Saved to {args.output}')
    else:
        print(report)


if __name__ == '__main__':
    main()
