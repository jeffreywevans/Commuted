# Story Brief Data Versioning Guidance

## Short answer

- **Per-file version numbers:** usually overkill for this project.
- **Structured version tracking:** yes, good idea.

## Current implementation

- `schema_version` is present in `data/story_brief/config.json`.
- `dataset_version` is now present in `data/story_brief/config.json` and validated at load time.

## Why per-file versions are usually too much

Git already tracks each file revision and history.
Adding separate `version` values to every JSON file often creates:
- extra bookkeeping,
- more merge churn,
- and potential inconsistency across files.

## Recommended approach

Use a **single top-level data version strategy** in `data/story_brief/config.json`:

1. Keep `schema_version` for structure compatibility (already present).
2. Add `dataset_version` (semantic-style, e.g. `2026.04.10` or `1.3.0`) for content snapshots.
3. Update `dataset_version` only when prompt pools/config materially change.
4. Keep human-readable notes in a small changelog file (e.g., `data/story_brief/CHANGELOG.md`).

## When per-file versions make sense

Use per-file versions only if files are released independently or consumed by different external systems on separate cadences.
That does not appear to be the case here.

## Practical policy proposal

- Keep **one schema version** + **one dataset version** in `config.json`.
- Enforce compatibility checks in loader logic.
- Treat Git commit history as the source of per-file change history.
- Optionally tag releases in Git for stable checkpoints.

## Verdict

For this project: **versioning is good; per-file version counters are excessive**.
