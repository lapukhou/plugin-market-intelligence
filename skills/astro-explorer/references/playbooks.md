# Astro MCP playbooks

Recipes for the jobs that actually come up. Each is a call sequence, not a script — adapt it, and
skip steps whose answers you already have from earlier in the conversation.

Contents:
- [Bootstrapping an empty Astro](#bootstrapping-an-empty-astro)
- [Keyword discovery](#keyword-discovery)
- [Long-tail / low-competition hunting](#long-tail--low-competition-hunting)
- [Competitor mining](#competitor-mining)
- [Rank movement analysis](#rank-movement-analysis)
- [Localizing into another store](#localizing-into-another-store)
- [App Store Connect metadata allocation](#app-store-connect-metadata-allocation)
- [Tagging and notes as a working memory](#tagging-and-notes-as-a-working-memory)

## Bootstrapping an empty Astro

When `list_apps` returns `[]`:

1. Ask which app — a name, a store URL, or a numeric ID. If they give a URL, the ID is the digits
   after `/id`.
2. `search_app_store` with the app's name and the user's home store to confirm you have the right
   app, and to read off the numeric ID.
3. `add_app` with that `appStoreId`.
4. `get_keyword_suggestions` for a starting set, then `add_keywords` in one batch.

**Unpublished app:** `add_app` with `temporary: true` and a real `name`. Keyword popularity and
difficulty work fine without a live listing — only the app's own rank is meaningless, since there's
nothing to rank. Say that plainly instead of reporting rank `0` or `null` as a position.

Rankings need history before trend questions mean anything: roughly a week for "did this move",
a month for anything about volatility. If a user asks for trends on a set they added yesterday,
tell them the tracking is too young rather than reading noise as signal.

## Keyword discovery

The default flow behind *"find keywords for my app"*:

1. `get_keyword_suggestions` — `store` required, `appId`/`appName` for the app.
2. Filter to **popularity > 25 and difficulty < 75**. State the filter in your answer so the user
   can move the thresholds.
3. Drop anything already tracked (`get_app_keywords`) so your proposal is genuinely new — though
   `add_keywords` would skip duplicates anyway, a list padded with keywords they already have
   reads as sloppy.
4. Present the survivors with their numbers, recommend a subset, confirm, then `add_keywords` in
   one batch.

Don't add everything the suggestion engine returns. A tracked keyword the app has no chance on is
a row the user maintains forever for no information.

## Long-tail / low-competition hunting

For *"low competition but relevant"*:

- `get_keyword_suggestions` with `highPopularity: false` — the default `true` filters out exactly
  what's being asked for.
- Invert the thresholds: **difficulty well under 75**, and accept popularity below 25 as the point
  of the exercise. Be explicit that these terms trade volume for winnability, so the user isn't
  surprised when a #1 rank produces few downloads.
- Multi-word phrases dominate here. Keep them intact — a phrase that ranks is one unit.

## Competitor mining

**Mining keywords from apps that outrank you** — needs a keyword *already tracked*:

1. `search_rankings` for the tracked keyword to see the ranking landscape, or work from keywords
   where the app already places top-10 (those are where the app is credible).
2. `extract_competitors_keywords` on each such keyword. Its floor is popularity 5, so re-filter to
   the > 25 / < 75 band before proposing anything.
3. Dedupe across keywords — the same combination surfaces repeatedly — and `add_keywords` the
   survivors in one batch.

Cap this at a handful of source keywords. Each call is a live NLP pass, and 20 of them will both
rate-limit you and drown the user.

**Adding a rival to tracking:**

1. `search_app_store` on the contested keyword, passing your own `appId` so you also get your
   position.
2. Pick the genuine competitors — direct rivals, market leaders, niche leaders, fast risers — not
   just rows 1 and 2, which are often unrelated big-brand apps.
3. `add_app` for each, then optionally `add_keywords` with the *same* keyword set as your app, so
   the two are comparable head-to-head in the GUI.

**Profiling a competitor without tracking it:** `get_keyword_suggestions` accepts an `appId` for an
untracked app. Cheap way to read a rival's keyword surface with no writes at all.

## Rank movement analysis

For *"which keywords lost positions"*:

1. `get_app_keywords` for the tracked set.
2. `search_rankings` with `includeHistory: true`, `includeStatistics: true`, and `period: "week"`
   (or `month`). The statistics block returns average, min, max, volatility and a trend direction,
   which answers the question without you diffing raw points.
3. Group the output into **declining**, **improving**, **stable/volatile**. Volatile-but-flat is
   its own category and matters: it usually means the app sits at a rank boundary, not that
   anything changed.

Before concluding, check data freshness. Astro only refreshes while it's open, so a user who had
it closed for five days has a "week-over-week" window that is really two days of data. Rank drops
across *every* keyword at once usually means a stale or partial refresh rather than an algorithm
hit — check that before alarming anyone.

`search_rankings` is per-keyword, so a 60-keyword set is 60 calls and brushes the rate limit. For
large sets, either work through the keywords that matter (tagged, or top-ranked) or warn the user
what the full sweep costs before starting it.

## Localizing into another store

Cloning a keyword set into a new country store, e.g. `us` → `it`:

1. `get_app_keywords` for the source store; pick the keywords worth translating — the ones that
   already rank or have real popularity, not the whole set.
2. Translate into the target language. Translate *intent*, not words: the Italian term users
   actually search is rarely a literal rendering, and compound English phrases often collapse into
   one local word.
3. `add_keywords` with the target `store` — one batch.
4. `set_keyword_note` on each new keyword with the English original. This is the trick that makes a
   localized set maintainable months later, when the user can't read their own keyword list.
5. Optionally `get_keyword_suggestions` against the target store afterward. Native suggestions
   catch high-volume local terms translation never would.

Then verify: translated keywords come with their own popularity and difficulty in the target store,
and some will be dead on arrival. Report those instead of leaving them tracked silently.

**Choosing which store to expand into:** `get_app_ratings` with no `store` returns every store, so
rating quality can rank the candidates — Astro's own prompt library suggests copying the keyword
set from the highest-rated store into the second-highest.

## App Store Connect metadata allocation

Turning tracked keywords into the three fields Apple indexes. The rules below come from Apple's
indexing behavior, and each one exists because breaking it wastes characters:

- **Title — 30 characters.** Highest-weight field.
- **Subtitle — 30 characters.** Second highest.
- **Keyword Field — 100 characters.** Comma-separated, **no spaces after commas** — a space costs
  a character and buys nothing.

Allocation rules:

- **No repetition across fields.** Apple combines words across Title, Subtitle and Keyword Field
  when matching, so a word appearing twice buys nothing the second time. Each word lands in exactly
  one field.
- **Don't split multi-word keywords.** "habit" in the Title and "tracker" in the Subtitle is weaker
  than "habit tracker" whole in one field.
- **Singular only.** Apple auto-indexes plurals, so "tracker" already covers "trackers". Adding the
  plural spends characters on nothing.
- **No stop words** — a, and, the, for, with, to, "app". Ignored by the algorithm.
- **No company or category name.** The developer name and the App Store category are already
  indexed; repeating "InnerGrow" or "Health & Fitness" is wasted space.
- **Order by importance, strongest first.** Position within a field carries weight.
- **`&`, `:` and `-` count as 2 characters in the Title.** Budget for it inside the 30.

Procedure:

1. `get_app_keywords` for the store you're writing metadata for.
2. Rank by value — popularity weighted against difficulty and current position. A keyword already
   at rank 3 needs less help than a high-popularity keyword at rank 60.
3. Fill Title first with the best keywords that fit 30 characters, then Subtitle from what's left,
   then the Keyword Field to 100. Count characters explicitly and show the counts; "roughly fits"
   is a rejected binary.
4. Record the allocation in Astro so it survives the conversation: `manage_tag` to create `title`,
   `subtitle`, `keyword field`, then `set_keyword_tag` per keyword. The user can then see the plan
   in their GUI while typing it into App Store Connect.
5. Present the three final strings verbatim with character counts, plus which keywords didn't make
   the cut and why.

## Tagging and notes as a working memory

Tags survive the conversation; your analysis doesn't. When you've done real work — identified top
performers, flagged decliners, allocated metadata — persist it:

1. `manage_tag` with `action: "list"` first, to reuse the user's existing vocabulary rather than
   inventing a parallel one.
2. `manage_tag` `create` for anything genuinely new (colors: red, orange, yellow, green, blue,
   purple, gray). Conventional mapping that reads well in the GUI: red = declining, green =
   improving or top performer, blue/purple = metadata field assignments, gray = parked ideas.
3. `set_keyword_tag` per keyword — one call each, so for large sets confirm the batch first.
4. `set_keyword_note` for anything a tag can't carry: a translation, a rank at the time of review,
   why a keyword was rejected.

Remember `set_keyword_note` deletes when `note` is omitted or empty, and that it overwrites rather
than appends. Check the existing note before replacing something the user wrote by hand — and when
you can't see it, ask rather than clobber.
