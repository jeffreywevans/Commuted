# Story Brief Data Strategy

## Recommendation

Use a **small set of domain-based JSON files** (not one giant file, and not one file per key).

### Suggested layout

- `commuted_calligraphy/story_brief/data/titles.json`
- `commuted_calligraphy/story_brief/data/entities.json` (characters, settings, availability windows)
- `commuted_calligraphy/story_brief/data/prompts.json` (conflicts, pressures, endings, style)
- `commuted_calligraphy/story_brief/data/config.json` (ordered keys, weights, date range, word-count targets)
- `commuted_calligraphy/story_brief/data/partner_distributions.json` (date-aware weighted `sexual_partner` pools; `[]` indicates celibacy, while omitted era data indicates absent data)

## Why this approach

### Versus one giant JSON file

Pros of giant file:
- Easy single-load startup.
- Single file to track.

Cons of giant file:
- Merge conflicts grow quickly.
- Harder review diffs for unrelated edits.
- Harder ownership/delegation across collaborators.

### Versus one file per key

Pros of per-key files:
- Very granular edits.
- Tiny diffs.

Cons of per-key files:
- File sprawl and navigation overhead.
- Harder to reason about related content together.
- More loader/plumbing complexity.

## Why domain-based split is the sweet spot

- Keeps related concepts together.
- Keeps diffs manageable.
- Limits file count while avoiding a mega-file.
- Scales naturally when adding new ordered keys.

## Future-proofing for new ordered keys

1. Keep `ordered_keys` and key metadata in `config.json`.
2. Add a lightweight schema validator (required keys, types, ranges).
3. Support defaults/fallbacks so adding a new key does not break old datasets.
4. Version the data format with `schema_version` in `config.json`.

## Practical migration plan

1. Move constants to `commuted_calligraphy/story_brief/data/*.json`.
2. Add a loader module that validates and returns typed structures.
3. Keep existing Python names as compatibility aliases during transition.
4. Add smoke tests for data loading + generation with `--seed`.
5. Remove in-file tables once parity is confirmed.
