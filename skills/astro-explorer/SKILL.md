---
name: astro-explorer
description: App Store Optimization (ASO) work through the Astro MCP server — a local desktop app (127.0.0.1:8089) holding the user's tracked apps, keyword rankings and history, popularity/difficulty scores, ratings, tags and notes. Use this whenever the user wants keyword research, rank tracking, keyword suggestions, competitor keyword extraction, App Store search, localization into other country stores, or App Store Connect title/subtitle/keyword-field metadata. Trigger on mentions of Astro, tryastro, ASO, keyword popularity or difficulty, "which keywords lost positions", "find keywords for my app", "who ranks for X", "track these keywords", app ratings by store, or any `mcp__astro__*` tool. Also read this BEFORE calling any mcp__astro__ tool directly, even for a task that looks like one call — the server rate-limits at 60 requests/minute, several tools mutate the user's real tracking database, and popularity/difficulty have specific thresholds that make or break a recommendation.
---

# Astro MCP

Astro is a macOS ASO app. Its MCP server exposes the user's local Astro database — tracked
apps, tracked keywords, ranking history, ratings — plus live App Store lookups. You read and
write real data the user looks at in a GUI, so treat writes as edits to their working file.

## Before anything else

Call `list_apps` first. It is free of arguments, confirms the server is alive, and returns the
exact `appId` + `store` values every other tool needs. Guessing an app identifier is the single
most common failure.

Three outcomes:

- **Apps returned** → note their numeric IDs and stores; use those verbatim downstream.
- **Empty array `[]`** → nothing is tracked yet. Don't error out; offer to bootstrap (see
  *Bootstrapping* below). An empty Astro is a normal state for a fresh install.
- **Connection refused / tool missing** → Astro isn't running or the MCP server is off. Tell the
  user to open Astro → Settings → MCP Server and enable the toggle; the server starts and stops
  with the app. `lsof -i :8089` confirms whether anything is listening.

In Claude Code the Astro tools are deferred, so load the ones you need with `ToolSearch` before
calling. Search by keyword rather than by exact name — the prefix depends on how the server was
added: `mcp__astro__list_apps` when configured directly, but
`mcp__plugin_market-intelligence_astro__list_apps` when it comes from this plugin's bundled
`.mcp.json`. A query like `+astro list apps` resolves either.

## The 13 tools at a glance

| Read | Write |
|---|---|
| `list_apps` — tracked apps, keyword counts, stores | `add_app` — track an app by numeric App Store ID, or create a temporary placeholder |
| `get_app_keywords` — keywords tracked for one app | `add_keywords` — batch up to 100 keywords |
| `search_rankings` — current rank + optional history/statistics | `remove_keywords` — **destructive**, confirm first |
| `get_app_ratings` — rating + review count, optional history | `set_keyword_note` — note on a keyword |
| `search_app_store` — live store search, who ranks for a term | `set_keyword_tag` — add/remove a tag |
| `get_keyword_suggestions` — AI suggestions, tracked or untracked apps | `manage_tag` — list/create/rename/recolor tags |
| `extract_competitors_keywords` — mine keywords from apps ranking for a tracked keyword | |

Full parameter tables, defaults and per-tool quirks: `references/tools.md`. Read it before
composing a non-obvious call — several tools have required params that aren't guessable
(`search_rankings` requires both `keyword` and `store`) and identifier fields whose docs
disagree with reality.

## Reading the metrics correctly

Recommendations live or die on these three numbers, so get them right:

- **Popularity** — Apple Ads search volume for the term. Higher means more potential traffic.
  A keyword worth putting in metadata is generally **> 25**; below that you may rank #1 and see
  nothing. Long-tail plays are the deliberate exception, and you should say so when proposing one.
- **Difficulty** — Astro's proprietary estimate of how hard ranking is. Target **< 75**. Above
  that, a new or small app realistically won't break in.
- **Position** — the app's current rank for the keyword. Only meaningful against history: a rank
  of 40 is good news if it was 90 last week.

Popularity and difficulty come from Astro's paid tier. If they arrive null or absent, say the
data isn't available rather than reasoning as if the numbers were zero — a keyword with unknown
popularity is not a bad keyword.

Astro refreshes rankings roughly every 24 hours while the app is open. "Last update" ages
matter: if a user has had Astro closed for a week, the ranks are a week old, and week-over-week
comparisons will be misleading. Check before drawing trend conclusions.

## Budget: 60 requests per minute

The server returns `429 Too Many Requests` past 60 calls/minute, and Astro's own docs warn that
MCP sessions burn a lot of tokens. Both problems have the same cause — per-item loops. Plan the
call graph before you start:

- `add_keywords` takes an array of up to 100. One call, not 40.
- `get_app_keywords` returns the whole tracked set at once. Prefer it over per-keyword lookups
  when you need a broad view.
- `search_rankings` is per-keyword by design. Before looping it over 50 keywords, ask whether the
  answer needs all 50 or just the top/bottom slice, and tell the user what you're about to spend.
- `search_app_store` and `extract_competitors_keywords` are the expensive ones (live network +
  NLP). Cap them at the handful of keywords that actually matter and say which you chose.

If you do hit a 429, pause briefly and resume — it's a sliding window, not a ban.

## Writing to the user's data

`add_keywords`, `add_app`, tags and notes all mutate the database backing the user's GUI. For
anything beyond one or two items, state the plan and get a yes: *"I'll add these 12 keywords to
InnerGrow in the `us` store — go ahead?"* This isn't ceremony; the user's alternative to your
bulk write is undoing it by hand, row by row.

`remove_keywords` is destructive and its own tool description mandates it: list every keyword
that will be deleted and get explicit confirmation before calling. Never fold a removal into a
larger "cleanup" the user only approved in the abstract.

`add_keywords` silently skips keywords already tracked, so re-running it is safe and its result
tells you what was genuinely new — useful for reporting instead of a second verification pass.

Tags must exist before assignment: `manage_tag` with `action: "create"` (colors are limited to
red, orange, yellow, green, blue, purple, gray), then `set_keyword_tag` per keyword.

## Workflows

`references/playbooks.md` has step-by-step recipes for the recurring jobs, drawn from Astro's
own prompt library:

- **Bootstrapping** an empty Astro, including temporary apps for unreleased products
- **Keyword discovery** — suggestions filtered by popularity/difficulty, long-tail hunting
- **Competitor mining** — extracting keywords from apps that outrank you, adding rivals as tracked apps
- **Rank movement analysis** — week-over-week losses and gainers, volatility and trend
- **Localization** — cloning a keyword set into another country store with translations in notes
- **App Store Connect metadata** — allocating tracked keywords into Title / Subtitle / Keyword
  Field under Apple's character limits and indexing rules. Read this section before writing any
  metadata; the rules (no repeated words across fields, singulars only, `&` costs 2 characters)
  are non-obvious and getting them wrong wastes the user's 160 characters.

## Presenting results

The user is making spend and release decisions from your output, so:

- Lead with the decision, then the table. "Three keywords are worth adding, four aren't" beats a
  raw dump of 40 rows.
- Always carry `store` alongside a keyword. The same term has different rank, popularity and
  difficulty in `us` and `it`, and a table that omits the store is ambiguous.
- Show popularity and difficulty next to any keyword you recommend — the recommendation isn't
  checkable without them.
- Astro's MCP is beta and its data is estimated. When a conclusion rests on a single data point
  or a stale refresh, say so. The user was told by Astro's own docs to verify before acting on
  strategy, and a flagged uncertainty is worth more to them than false confidence.
