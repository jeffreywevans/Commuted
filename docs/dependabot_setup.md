# Dependabot setup recommendations

This repository is a good fit for two Dependabot ecosystems:

1. **`pip`** for Python dependencies defined in `pyproject.toml`, `requirements.txt`, and `requirements-dev.txt`.
2. **`github-actions`** for GitHub Actions workflow dependencies (for example, `actions/checkout` and `actions/setup-python`).

## Proposed defaults

- **Weekly updates** on Monday mornings (UTC) to avoid excessive PR churn.
- **Focused pip groups** for this repo's current dependencies:
  - `runtime-pyyaml`
  - `build-setuptools`
  - `dev-pytest`
- **Labels** so dependency PRs are easy to filter and triage.
- **PR limits** to avoid backlog growth during busy weeks.

## Where this is configured

- `.github/dependabot.yml`

## Optional next steps

- Turn on **auto-merge** for patch-level updates once CI has proven stable.
- Add a `CODEOWNERS` entry for `.github/dependabot.yml` so dependency automation changes always get review.
- If this repo adds new ecosystems later (e.g., Docker, npm), add additional `updates` entries.
