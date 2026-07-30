# Astro MCP tool reference

Every tool is namespaced `mcp__astro__*` when the server is configured directly, or
`mcp__plugin_market-intelligence_astro__*` when it comes from this plugin's bundled `.mcp.json`.
The bare tool names below (`list_apps`, `search_rankings`, …) are the stable part; resolve the
full name with `ToolSearch` rather than typing a prefix from memory. Params marked **required**
are enforced
by the server; a missing one is a validation error, not a silent default.

Contents:
- [Identifying an app](#identifying-an-app)
- [Read tools](#read-tools)
- [Write tools](#write-tools)
- [Server, transport, errors](#server-transport-errors)

## Identifying an app

Most tools accept `appId` **or** `appName`:

- `appId` — the **numeric App Store ID** (e.g. `"389801252"`), exact match. Some tool descriptions
  call this a "bundle ID"; that's wrong — Astro's docs are explicit that these fields take the
  numeric store ID. Take the value from `list_apps` rather than typing one from memory.
- `appName` — partial, case-insensitive match. Convenient, but ambiguous when two tracked apps
  share a word. Use it for one-off human-driven requests, prefer `appId` when scripting a
  multi-step flow.

`store` is a lowercase ISO country code — `us`, `it`, `uk`, `de`, `jp`. A keyword is tracked
*per store*, so the same text can exist several times with different metrics. When a keyword
exists in multiple stores and you omit `store`, mutating tools error out asking you to narrow.

`platform` defaults to `iphone`; other values are `ipad`, `mac`, `appletv`, `realityDevice`.

## Read tools

### `list_apps`
No parameters. Returns tracked apps with keyword counts and stores. Your entry point — also the
cheapest health check for the server.

### `get_app_keywords`
| Param | Required | Notes |
|---|---|---|
| `appId` | – | exact match |
| `appName` | – | partial match |
| `store` | – | filter |

All params optional; with none it returns everything tracked. One call for a whole app's keyword
set — far cheaper than looping `search_rankings`.

### `search_rankings`
| Param | Required | Notes |
|---|---|---|
| `keyword` | **yes** | partial, case-insensitive match |
| `store` | **yes** | |
| `appId` / `appName` | – | narrow to one app |
| `includeHistory` | – | `true` adds time-series data points |
| `includeStatistics` | – | average, min, max, volatility, trend (improving/stable/declining). **Requires `includeHistory: true`** |
| `period` | – | `week` \| `month` \| `year` \| `all`; overrides `daysBack` |
| `daysBack` | – | default 30; only used with `includeHistory`, ignored when `period` is set |

`includeStatistics` is the efficient path for trend questions — the server computes volatility and
direction so you don't pull raw points and eyeball them. Because `keyword` is a partial match, a
short query like `"fit"` sweeps in `fitness`, `fit tracker`, etc.; that's occasionally useful as a
cheap group query, and occasionally a surprise.

### `get_app_ratings`
| Param | Required | Notes |
|---|---|---|
| `appId` / `appName` | – | |
| `store` | – | filter; omit to compare across all stores |
| `includeHistory` | – | default `false`; `true` returns all historical points |

Omitting `store` to get every store at once is the basis of "which of my stores is healthiest".

### `search_app_store`
| Param | Required | Notes |
|---|---|---|
| `keyword` | **yes** | search term or app name |
| `store` | **yes** | |
| `appId` | – | your app's ID — adds your ranking position for this keyword to the response |
| `limit` | – | default 50, max 100 |
| `platform` | – | default `iphone` |

Live App Store query, so it works for terms that aren't tracked. Passing your own `appId` is
almost always worth it — same request, and you learn where you actually sit. This is the tool for
"who are my competitors on X".

### `get_keyword_suggestions`
| Param | Required | Notes |
|---|---|---|
| `store` | **yes** | |
| `appId` / `appName` | – | |
| `highPopularity` | – | default `true`; set `false` to surface long-tail/low-volume ideas |

Works for untracked apps too — pass an `appId` straight from `search_app_store` to profile a
competitor that isn't in Astro. `highPopularity: false` is the lever for long-tail research;
leaving it at the default while the user asked for low-competition terms is a common mismatch.

### `extract_competitors_keywords`
| Param | Required | Notes |
|---|---|---|
| `keyword` | **yes** | **must already be tracked in Astro** |
| `store` | **yes** | |

Takes the apps ranking for a tracked keyword, generates word combinations from their metadata,
fetches popularity for each, and returns everything above popularity 5, sorted by score. The
popularity-5 floor means results can still be far below the useful-in-metadata threshold of 25 —
filter again before recommending. If the keyword isn't tracked, `add_keywords` it first (or pick a
tracked keyword instead) rather than retrying.

## Write tools

### `add_app`
| Param | Required | Notes |
|---|---|---|
| `appStoreId` | conditional | numeric ID; required unless `temporary: true` |
| `platform` | – | default `iphone` |
| `temporary` | – | `true` creates a placeholder for an unpublished app |
| `name` | – | name for the temporary app; defaults to `Temporary App N` |

Find the ID with `search_app_store` first. Temporary apps let a user track keywords before their
app ships — always pass a real `name`, since `Temporary App 3` is useless in a later `list_apps`.

### `add_keywords`
| Param | Required | Notes |
|---|---|---|
| `keywords` | **yes** | array, max 100 |
| `store` | **yes** | |
| `appId` / `appName` | – | which app to attach to |
| `platform` | – | default `iphone` |

Fetches ranking, popularity and difficulty for the whole batch in one server-side pass, and skips
keywords already tracked. Batch aggressively: one 80-keyword call instead of 80 calls is the
difference between fine and rate-limited.

### `remove_keywords` — destructive
| Param | Required | Notes |
|---|---|---|
| `keywords` | conditional | array, max 100 |
| `keyword` | conditional | single; either this or `keywords` |
| `appId` / `appName` | – | |
| `store` | – | required if the keyword exists in several stores |

The tool's own description requires the assistant to enumerate what will be deleted and obtain
explicit user confirmation before calling. Deletions commit in one transaction; keywords that
weren't found are reported per item. Not documented on Astro's public MCP page — it exists on the
server, so don't tell the user removal is impossible.

### `set_keyword_note`
| Param | Required | Notes |
|---|---|---|
| `keyword` | **yes** | exact match |
| `note` | – | omit or pass `""` to **delete** the existing note |
| `appId` / `appName` | – | |
| `store` | – | narrows when the keyword exists in several stores |

Notes are free text in the GUI's Notes column. The standard use is stashing a translation next to
a localized keyword. Because an omitted `note` deletes, never call this tool "to check" a note —
it has no read mode. Read keyword metadata with `get_app_keywords` instead.

### `set_keyword_tag`
| Param | Required | Notes |
|---|---|---|
| `keyword` | **yes** | exact match |
| `tag` | **yes** | must already exist |
| `action` | **yes** | `add` \| `remove` |
| `appId` / `appName` | – | |
| `store` | – | |

Errors on adding a tag that's already present or removing one that isn't assigned — so when
re-tagging a set, read current tags first or tolerate the per-item error rather than aborting the
batch.

### `manage_tag`
| Param | Required | Notes |
|---|---|---|
| `action` | **yes** | `list` \| `create` \| `update` |
| `name` | conditional | required for `create` and `update`; unused for `list` |
| `color` | conditional | required for `create`, optional for `update`. One of red, orange, yellow, green, blue, purple, gray |
| `newName` | – | `update` only — renames the tag |

`list` needs nothing else. Run it before creating, so you reuse the user's existing vocabulary
instead of adding a near-duplicate tag.

## Server, transport, errors

- Transport: `POST http://127.0.0.1:8089/mcp`, MCP Streamable HTTP. Port is configurable in
  Astro → Settings → MCP Server; a changed port means the URL changes to `127.0.0.1:PORT/mcp`.
- Bound to localhost only: `127.0.0.1` and `::1`. LAN and external connections are dropped at the
  TCP level. Sends no CORS headers, so browsers can't reach it — MCP clients are unaffected.
- Rate limit: 60 requests/minute per client, then `429 Too Many Requests`. Sliding window — wait
  and retry.
- The server lives and dies with the Astro app and must be enabled manually in Settings.
- Register with Claude Code: `claude mcp add --transport http astro http://127.0.0.1:8089/mcp`,
  verify with `claude mcp list`.
- Claude Desktop can't reach localhost servers; it needs an HTTPS tunnel
  (`cloudflared tunnel --url http://127.0.0.1:8089`) pasted in as a custom connector, with a fresh
  URL after every restart.

| Symptom | Cause | Fix |
|---|---|---|
| Connection refused | Astro closed, or MCP toggle off | Open Astro → Settings → MCP Server; check `lsof -i :8089` |
| `429` | over 60 req/min | Pause, batch harder |
| Tool not found | wrong name (case-sensitive), or stale server | Verify name; restart the server from Astro's settings |
| "App not found" | wrong identifier | `list_apps`, then use the numeric App Store ID |
| Null popularity/difficulty | free tier | Report as unavailable, not as zero |

Astro's own docs: <https://tryastro.app/docs/mcp> and <https://tryastro.app/docs/mcp-prompts>
(the prompts table is client-rendered from `https://tryastro.app/api/mcp-prompts`, which returns
plain JSON if you need it).
