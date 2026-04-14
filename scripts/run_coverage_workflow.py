#!/usr/bin/env python3
"""Run pytest and produce combined coverage outputs."""

from __future__ import annotations

import glob
import os
import subprocess
import sys


def main() -> int:
    pytest_rc = subprocess.call(
        [
            "pytest",
            "--cov=commuted_calligraphy",
            "--cov-config=tox.ini",
            "--cov-branch",
            "--cov-report=",
            "--junitxml=test-results.xml",
        ]
    )

    covfile = os.environ.get("COVERAGE_FILE", ".coverage")
    combine_dir = os.path.dirname(covfile) or "."
    combine_rc = 0
    if glob.glob(covfile + ".*"):
        combine_rc = subprocess.call(
            [sys.executable, "-m", "coverage", "combine", combine_dir]
        )

    xml_rc = subprocess.call([sys.executable, "-m", "coverage", "xml", "-o", "coverage.xml"])
    report_rc = subprocess.call([sys.executable, "-m", "coverage", "report", "-m"])

    if pytest_rc != 0:
        return pytest_rc
    if combine_rc != 0:
        return combine_rc
    if xml_rc != 0:
        return xml_rc
    return report_rc


if __name__ == "__main__":
    raise SystemExit(main())
