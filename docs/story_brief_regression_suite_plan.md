# Story Brief Generator: Automated Regression Suite Proposal

## What is a regression suite?

A regression suite is a set of automated tests that re-check previously working behavior whenever code or data changes.

For this project, it means:
- every edit to `tools/generate_story_brief.py`
- every edit to `data/story_brief/*.json`

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

## Minimal first milestone (high ROI)

If you only do 5 tests first, do these:
1. schema validates baseline files,
2. duplicate ordered keys fails,
3. weighted all-zero fails,
4. same seed deterministic,
5. `--print-only` writes nothing.

These give strong protection for very little effort.

## Suggested rollout plan

1. Add `pytest` to dev dependencies.
2. Add baseline tests for schema + weighted choice.
3. Add deterministic generation tests.
4. Add CLI file-behavior tests with temporary directories.
5. Wire into CI so every PR runs tests automatically.

## Definition of done

- `pytest -q` passes locally.
- CI runs suite on every PR.
- New bug fixes include a regression test.
