from __future__ import annotations

import glob
import os
import subprocess
import sys


def run() -> int:
    pytest_cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--cov=commuted_calligraphy",
        "--cov-config=tox.ini",
        "--cov-branch",
        "--cov-report=",
        "--junitxml=test-results.xml",
    ]
    pytest_rc = subprocess.call(pytest_cmd)

    covfile = os.environ.get("COVERAGE_FILE", ".coverage")
    combine_dir = os.path.dirname(covfile) or "."
    if glob.glob(covfile + ".*"):
        subprocess.call([sys.executable, "-m", "coverage", "combine", combine_dir])

    xml_rc = subprocess.call([sys.executable, "-m", "coverage", "xml", "-o", "coverage.xml"])
    report_rc = subprocess.call([sys.executable, "-m", "coverage", "report", "-m"])

    if pytest_rc != 0:
        return pytest_rc
    if xml_rc != 0:
        return xml_rc
    return report_rc


if __name__ == "__main__":
    raise SystemExit(run())
