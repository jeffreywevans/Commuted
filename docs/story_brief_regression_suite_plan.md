# Story Brief Generator: Automated Regression Suite Proposal

## Status

✅ Initial regression suite implemented in `tests/story_brief/` with `pytest`.  
✅ Coverage now includes direct availability-boundary tests and config/date overlap validation failures.  
🔄 Next phase: strict dataset-health coverage (date coverage + generation preconditions), not just schema shape.

## What is a regression suite?

A regression suite is a set of automated tests that re-check previously working behavior whenever code or data changes.

For this project, it means:
- every edit to `commuted_calligraphy/story_brief/generate_story_brief.py`
- every edit to `commuted_calligraphy/story_brief/data/*.json`

…gets validated automatically so accidental breakage is caught immediately.

## Why you want one

1. **You edit data frequently**
   - Titles, prompts, and availability windows change often.
   - Manual checks are easy to skip or perform inconsistently.

2. **The generator is data-driven**
   - Small JSON mistakes can cause runtime failures or subtle output drift.
   - A test suite catches schema and behavior problems before they land.

3. **Determinism matters**
   - `--seed` implies reproducibility expectations.
   - Regression tests ensure seed-based output remains stable when intended.

4. **Confidence + speed**
   - You can make bigger edits without fear.
   - Faster iteration because tests answer "did I break anything?" in seconds.

## Why you care (practical impact)

Without regression tests, failures are discovered late:
- during manual generation,
- during review,
- or after content has already been used.

With regression tests, failures are discovered early:
- at commit time,
- in CI,
- with precise failure messages.

That directly reduces:
- debugging time,
- accidental bad data merges,
- and trust erosion in generated outputs.

## Proposed test stack

- **Framework:** `pytest`
- **Test location:** `tests/story_brief/`
- **Optional tooling:** `tox` or `nox` for repeatable local/CI runs
- **CI entry command:** `pytest -q`

## Proposed test modules

1. `test_schema_validation.py`
   - Valid baseline files pass.
   - Missing keys fail.
   - Wrong types fail.
   - Invalid dates fail.
   - Invalid weights fail.
   - Duplicate `ordered_keys` fail.

2. `test_weighted_choice.py`
   - Happy-path weighted selection returns in-domain values.
   - Empty options/weights fail.
   - Length mismatch fails.
   - NaN/inf/negative/all-zero fail.

3. `test_generation_determinism.py`
   - Same seed => same generated field dict.
   - Different seeds usually differ.
   - `secondary_character != protagonist` invariant always holds.

4. `test_markdown_output.py`
   - YAML front matter opens/closes with `---`.
   - Ordered keys are emitted in configured order.
   - Heading escaping works for markdown-significant characters.

5. `test_cli_behavior.py`
   - `--print-only` does not write files.
   - default write creates output path.
   - existing file without `--force` fails.
   - existing file with `--force` overwrites.

## Consolidation guidance

Short answer: keep them **separate by behavior area** (current layout is good), but consolidate shared setup/helpers.

### Keep separate
- `test_schema_validation.py`
- `test_weighted_choice.py`
- `test_generation_determinism.py`
- `test_markdown_output.py`
- `test_cli_behavior.py`

This separation keeps failures easy to diagnose and keeps files small enough to reason about.

### Consolidate only shared plumbing
- Common test data builders/fixtures in `tests/story_brief/_fixtures.py` (or `conftest.py`).
- Reusable CLI invocation helpers in one place.
- Shared assertion helpers for markdown/YAML snippets.

### When to merge files
Only merge if a file becomes trivially tiny (for example, 1–2 tests) or if two files are tightly coupled and always edited together.

## Minimal first milestone (high ROI)

If you only do 5 tests first, do these:
1. schema validates baseline files,
2. duplicate ordered keys fails,
3. weighted all-zero fails,
4. same seed deterministic,
5. `--print-only` writes nothing.

These give strong protection for very little effort.

## Suggested rollout plan

1. Keep `pytest -q` as a required gate for all story-brief data/code changes.
2. Add strict data-health tests to verify:
   - every selectable date has at least one setting,
   - every selectable date has at least two distinct characters.
3. Add diagnostics tests for dead windows/unreachable records in availability data.
4. Wire/confirm CI on every PR with a Python matrix (`3.11`, `3.12`, `3.x`) for compatibility coverage.
5. Add lightweight snapshot/regression checks for representative `--seed` + `--date` combinations.

## Definition of done

- `pytest -q` passes locally.
- CI runs suite on every PR.
- New bug fixes include a regression test.
