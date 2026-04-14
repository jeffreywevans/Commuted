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
    combine_rc = 0
    if glob.glob(covfile + ".*"):
        combine_rc = subprocess.run(
            [
                sys.executable,
                "-m",
                "coverage",
                "--config-file=tox.ini",
                "combine",
                combine_dir,
            ],
            check=True,
        ).returncode

    xml_rc = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "--config-file=tox.ini",
            "xml",
            "-o",
            "coverage.xml",
        ],
        check=True,
    ).returncode
    report_rc = subprocess.run(
        [sys.executable, "-m", "coverage", "--config-file=tox.ini", "report"],
        check=True
    ).returncode

    if pytest_rc != 0:
        return pytest_rc
    if combine_rc != 0:
        return combine_rc
    if xml_rc != 0:
        return xml_rc
    return report_rc


if __name__ == "__main__":
    raise SystemExit(main())
