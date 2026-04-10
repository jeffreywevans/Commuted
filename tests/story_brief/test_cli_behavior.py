from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tools.generate_story_brief import sanitize_filename


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tools" / "generate_story_brief.py"


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_print_only_writes_nothing(tmp_path: Path) -> None:
    result = run_cli("--seed", "42", "--print-only", cwd=tmp_path)
    assert result.returncode == 0
    assert result.stdout.startswith("---\n")
    assert list(tmp_path.iterdir()) == []


def test_print_only_with_explicit_date_sets_time_period(tmp_path: Path) -> None:
    result = run_cli("--seed", "42", "--date", "2000-01-01", "--print-only", cwd=tmp_path)
    assert result.returncode == 0
    assert "time_period: '2000-01-01'" in result.stdout


def test_write_and_force_overwrite_behavior(tmp_path: Path) -> None:
    outdir = tmp_path / "out"
    filename = "brief.md"

    first = run_cli("--seed", "42", "-o", str(outdir), "--filename", filename, cwd=tmp_path)
    assert first.returncode == 0
    output_file = outdir / filename
    assert output_file.exists()

    second = run_cli("--seed", "42", "-o", str(outdir), "--filename", filename, cwd=tmp_path)
    assert second.returncode != 0
    assert "Refusing to overwrite existing file" in (second.stdout + second.stderr)

    third = run_cli(
        "--seed",
        "42",
        "-o",
        str(outdir),
        "--filename",
        filename,
        "--force",
        cwd=tmp_path,
    )
    assert third.returncode == 0


def test_default_output_dir_is_relative(tmp_path: Path) -> None:
    filename = "relative-default.md"
    result = run_cli("--seed", "42", "--filename", filename, "--force", cwd=tmp_path)
    assert result.returncode == 0
    assert (tmp_path / "output" / "story-seeds" / filename).exists()


def test_sanitize_filename_handles_invalid_chars_and_reserved_names() -> None:
    assert sanitize_filename("../bad:name?.md") == "bad-name-.md"
    assert sanitize_filename("CON") == "CON-file"
    assert sanitize_filename("   .md") == "story-brief.md"


def test_cli_rejects_invalid_date_format(tmp_path: Path) -> None:
    result = run_cli("--date", "01-01-2000", "--print-only", cwd=tmp_path)
    assert result.returncode != 0
    assert "--date must be in YYYY-MM-DD format" in (result.stdout + result.stderr)


def test_cli_rejects_out_of_range_date_without_traceback(tmp_path: Path) -> None:
    result = run_cli("--date", "1900-01-01", "--print-only", cwd=tmp_path)
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "--date must be between" in combined
    assert "Traceback" not in combined
