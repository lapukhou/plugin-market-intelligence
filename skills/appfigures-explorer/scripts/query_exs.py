#!/usr/bin/env python3
"""
query_exs.py — wrapper for Appfigures Explorer queries.

Usage:
    python query_exs.py --q '<DSL JSON>' [--fields F1,F2,…] [--sort -release_date]
                        [--count 100] [--page 1] [--endpoint exs|exsc] [-o file.json]

The DSL is passed as a JSON string. The script url-encodes the form body and
adds a browser User-Agent. Stdout is pure JSON (pipeable to jq); all
diagnostics go to stderr.

Example:
    python query_exs.py \\
      --q '["and",["match","storefronts",["and","apple:ios"]],["match","refno",6751584800]]' \\
      --fields name,developer,custom_meta \\
      --count 1
"""
import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36')

DEFAULT_FIELDS = (
    'name,developer,stores_id,product_id,release_date,'
    'monetization_strategies,all_rating,all_rating_count,custom_meta'
)


def fetch(q, fields=DEFAULT_FIELDS, sort=None, count=100, page=1, endpoint='exs'):
    """POST to the Explorer endpoint and return parsed JSON."""
    base = f'https://appfigures.com/market/explorer/_u/data/{endpoint}'
    qs = {'fields': fields, 'count': str(count), 'page': str(page)}
    if sort:
        qs['sort'] = sort
    url = f'{base}?{urllib.parse.urlencode(qs)}'

    body = urllib.parse.urlencode({'q': q}).encode()
    req = urllib.request.Request(url, data=body, headers={
        'User-Agent': UA,
        'Content-Type': 'application/x-www-form-urlencoded',
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        return {'__error': True, 'status': e.code, 'body': body}
    except urllib.error.URLError as e:
        return {'__error': True, 'status': 'network', 'body': str(e.reason)}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--q', required=True, help='DSL filter as JSON string')
    p.add_argument('--fields', default=DEFAULT_FIELDS,
                   help=f'CSV of fields. Default: {DEFAULT_FIELDS}. Use "*" for all.')
    p.add_argument('--sort', default=None, help='e.g. -download_estimates_sum_30_days')
    p.add_argument('--count', type=int, default=100, help='Records per page (max 1000)')
    p.add_argument('--page', type=int, default=1)
    p.add_argument('--endpoint', choices=['exs', 'exsc'], default='exs')
    p.add_argument('-o', '--output', default=None, help='Save JSON to file')
    p.add_argument('--summary', action='store_true', help='Also print a short summary line to stderr')
    args = p.parse_args()

    # Sanity-check: q must parse as JSON
    try:
        json.loads(args.q)
    except json.JSONDecodeError as e:
        print(f'❌ Invalid JSON in --q: {e}', file=sys.stderr)
        sys.exit(2)

    data = fetch(args.q, args.fields, args.sort, args.count, args.page, args.endpoint)

    if data.get('__error'):
        print(f'❌ {data["status"]}: {data["body"][:300]}', file=sys.stderr)
        sys.exit(1)

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f'✓ Saved to {args.output} ({len(data.get("results", []))} records)', file=sys.stderr)

    if args.summary or not args.output:
        meta = data.get('metadata', {}).get('resultset', {})
        n = len(data.get('results', []))
        print(f'total={meta.get("total_count","?")} returned={n} '
              f'page={meta.get("page",1)}/{meta.get("total_pages","?")}', file=sys.stderr)

    if not args.output:
        json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
        print()


if __name__ == '__main__':
    main()
