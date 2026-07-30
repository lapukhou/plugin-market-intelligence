# Market Intelligence

A Claude Code plugin for App Store and Google Play market research. It answers what an app actually earns, who else is in the niche, and which keywords are worth ranking for — from live data, not guesses.

Two skills, two data sources: **Appfigures Explorer** for money and traction, **Astro** for keywords and rankings.

## `appfigures-explorer` skill

Market intelligence for iOS App Store and Google Play apps via the public **Appfigures Explorer** API (`/exs`, `/exsc` — no auth required):

- **Revenue and downloads estimates** — 30-day and 365-day, worldwide or per country
- **MoM dynamics** — computed from absolute deltas, with a monthly baseline to separate spikes from trends
- **Niche and genre research** — top apps in a category, fresh releases for a period, growing / falling / flat counts
- **Developer portfolios** — every app a publisher ships and how revenue is distributed across them
- **Revenue geography** — top countries by revenue share
- **Lookups** by keyword, bundle ID, or Apple App Store ID

What anonymous access **cannot** do: the Explorer API rejects `sort=` and caps `/exs` at **25 records per query**, with no deep pagination. Niche work therefore means narrowing the filter (typically a downloads floor, calibrated against the uncapped `/exsc` count) until the apps that matter fall inside that window — the skill does this and reports the floor and the count it excluded. Appfigures also leaves revenue estimates null for a sizeable share of apps; those render as `—` and stay out of the totals rather than being counted as `$0`.

Just say something like:

> How much does this app make, and who else is in this niche?

It defaults to iOS App Store / worldwide / 30-day window when the request is ambiguous, then asks whether you want Google Play or a saved report file.

## `astro-explorer` skill

App Store Optimization through the **Astro** macOS app's MCP server — your own tracked apps, keywords and ranking history, plus live store lookups:

- **Keyword research** — AI suggestions filtered by popularity (> 25) and difficulty (< 75), long-tail hunting
- **Rank tracking** — current position with history, week-over-week losses and gainers, volatility
- **Competitor mining** — extract keywords from apps that outrank you, add rivals as tracked apps
- **App Store search** — who actually ranks for a term
- **Ratings** — rating and review count per store, with history
- **Localization** — clone a keyword set into another country store
- **App Store Connect metadata** — allocate tracked keywords into Title / Subtitle / Keyword Field under Apple's character and indexing rules

Just say something like:

> Which of my keywords lost positions this week?

The skill treats Astro as the user's live working data: writes are batched and confirmed, `remove_keywords` is never called without listing what disappears, and the 60 requests/minute budget is planned up front.

## Requirements

**`appfigures-explorer`** needs only Python 3 (standard library — no third-party packages). The Explorer endpoints need no API key, but they sit behind Cloudflare and require a browser `User-Agent`; the scripts set one.

**`astro-explorer`** needs [Astro](https://tryastro.app) running locally with its MCP server enabled (Astro → Settings → MCP Server). The server starts and stops with the app; `lsof -i :8089` confirms it is listening. The plugin bundles the connection in `.mcp.json`, so installing the plugin is enough — no manual setup. Popularity and difficulty come from Astro's paid tier; without it those fields arrive empty and the skill says so rather than guessing.

To use the Astro server outside this plugin, add it by hand:

```bash
claude mcp add --transport http astro http://127.0.0.1:8089/mcp
```

## Pipeline position

Both skills also serve the [discovery plugin](https://github.com/lapukhou/plugin-discovery): its `opportunity-scoring` skill uses `appfigures-explorer` to calibrate satisfaction scores against what shipping products actually deliver, rather than what the use case author remembered.

```
use-case-map.md   →   job-map.md   →   opportunity-scores.md
(use-case-mapping)    (discovery)      (discovery)
                                        ↑ appfigures-explorer (competitive calibration)
```

## Installation

This repository doubles as its own marketplace:

```
/plugin marketplace add lapukhou/plugin-market-intelligence
/plugin install market-intelligence@plugin-market-intelligence
```

It is also listed in the combined [lapukhou-plugins](https://github.com/lapukhou/lapukhou-plugins) marketplace:

```
/plugin marketplace add lapukhou/lapukhou-plugins
/plugin install market-intelligence@lapukhou-plugins
```

### Local development

To try the plugin from a local checkout:

```bash
claude --plugin-dir /path/to/plugin-market-intelligence
```

## Structure

```
plugin-market-intelligence/
├── .claude-plugin/
│   ├── plugin.json          # Plugin manifest
│   └── marketplace.json     # Marketplace listing (this repo doubles as a marketplace)
├── .mcp.json                # Astro MCP server (http, 127.0.0.1:8089)
└── skills/
    ├── appfigures-explorer/
    │   ├── SKILL.md
    │   ├── references/
    │   │   ├── api.md                  # /exs and /exsc endpoint reference
    │   │   ├── dsl-cookbook.md         # Ready-made query DSL snippets
    │   │   ├── categories.md           # DSL filters for App Store categories
    │   │   └── analysis-patterns.md    # MoM formula, ARPD, country breakdown
    │   └── scripts/
    │       ├── query_exs.py            # Explorer query wrapper (clean JSON to stdout)
    │       └── format_report.py        # Renders an /exs dump into the report format
    └── astro-explorer/
        ├── SKILL.md
        ├── references/
        │   ├── tools.md                # All 13 Astro MCP tools, params and quirks
        │   └── playbooks.md            # Bootstrapping, discovery, rank analysis, ASC metadata
        └── evals/
            └── evals.json              # Eval suite (skill-creator format)
```

## License

MIT
