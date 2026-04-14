#!/usr/bin/env python3
"""Run pytest and produce combined coverage outputs."""

from __future__ import annotations

import glob
import os
import subprocess
import sys


def main() -> int:
    pytest_rc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--cov=commuted_calligraphy",
            "--cov-config=tox.ini",
            "--cov-branch",
            "--cov-report=",
            "--junitxml=test-results.xml",
        ]
    ).returncode

    covfile = os.environ.get("COVERAGE_FILE", ".coverage")
    combine_dir = os.path.dirname(covfile) or "."
    if glob.glob(covfile + ".*"):
        subprocess.run(
            [
                sys.executable,
                "-m",
                "coverage",
                "--rcfile=tox.ini",
                "combine",
                combine_dir,
            ],
            check=True,
        )

    subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "--rcfile=tox.ini",
            "xml",
            "-o",
            "coverage.xml",
        ],
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "coverage", "--rcfile=tox.ini", "report"],
        check=True,
    )

    if pytest_rc != 0:
        return pytest_rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
