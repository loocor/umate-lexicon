# Source policy

Operational rules for what may enter the Lemma store. `CLEANROOM.md` says
which *recipe trees* must never be copied; this file says which *sources*
may be pinned, and how they are recorded.

The machine-readable list lives in
[`data/sources.lock.json`](../data/sources.lock.json). The gate runs in
`umate_lexicon.sources` on every `verify-sources` and locked `pipeline`.

## Admission gate

A source may be pinned only if all of the following hold:

1. It carries an explicit, published license, or is a government /
   standards body publication with a stated public-use term.
2. The license string is recorded verbatim in the lock entry.
3. The license is not GPL or AGPL in any spelling.
4. The artifact is a stable, hashable file (a dated dump or a pinned
   commit), not a rolling page that changes under us.
5. The content is bulk-published public material — no user corpora, no
   private or logged-in content.

## Hard exclusions

- **GPL / AGPL, any variant.** `gpl-*`, `gplv2`, `gplv3`, `agpl-*`,
  "GPL-3.0-only" and similar all fail the lock parser. This is a
  product decision: the emitted tables are embedded in a commercial
  app, so copyleft source code licenses are out of scope entirely.
  `is_blocked_license()` implements the check; LGPL is deliberately
  allowed and is the license of official Rime luna / essay / emoji.
- Recipe trees: `iDvel/rime-ice`, `rime-wanxiang`, `melt_eng`, or any
  community schema / Lua / OpenCC tree. See `CLEANROOM.md`.
- Commercial IME cell dictionaries: Sogou / QQ / Baidu `.scel` exports.
- Content behind a login, a paywall, or a site whose terms forbid
  crawling.
- Content that may not be redistributed or that is legally restricted
  in the target markets.
- Personal data of any kind: private messages, comment histories with
  identifiers, contact lists, transcripts, user-typed corpora.

## Privacy

Sources are public bulk dumps only. The pipeline never ingests anything
that identifies a person, and never ingests material the user produced.
When a candidate source mixes public text with user-generated content,
either restrict the ingest to the public portion or drop the source.

## robots.txt and terms of service

Prefer an official bulk dump or export over crawling HTML. When a source
has no dump and must be fetched over HTTP:

- check `robots.txt` and the site terms first, and record the outcome;
- fetch at a low rate with a stable user agent;
- never authenticate, and never work around a block;
- if the terms are unclear, treat the source as not admitted until the
  question is answered.

The lock stores `homepage` so the license and terms can be re-checked
later.

## License recording

Every lock entry records:

| Field | Meaning |
| --- | --- |
| `id` | stable source id, used as `lemma_sources.source_id` |
| `license` | license string, verbatim, e.g. `cc-by-sa-cedict` |
| `homepage` | where the license and terms can be re-read |
| `url` | exact pinned artifact URL |
| `sha256` | content hash; a mismatch is a hard failure |
| `filename` / `extract` | artifact name and how it unpacks |

Per-lemma provenance lands in the `lemma_sources` table, and the emitter
writes one `NOTICE` fragment per output directory listing every source
id, license, and row count.

## Share-alike

CC BY-SA sources (CC-CEDICT, Wikimedia titles) are tagged per lemma and
kept in `NOTICE`. Share-alike and coverage-only material stays in the
`bulk` layer and is not silently folded into a default keyboard SKU.
Changing that requires a recorded decision, not an emitter tweak.

## Adding a source

1. Confirm the license and the terms, and note the decision.
2. Pin a dated dump or a commit; compute the sha256.
3. Add the lock entry with `license`, `homepage`, `url`, `sha256`,
   `filename`, `ingest`.
4. Run `verify-sources` and the locked `pipeline`. No unlicensed source
   may reach the store, and no fixture fallback is allowed in the
   locked path.
