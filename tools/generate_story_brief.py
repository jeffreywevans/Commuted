#!/usr/bin/env python3
"""Generate a random story brief as Markdown with YAML front matter."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import secrets
from datetime import date, datetime, timedelta
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml

TITLE_TOKEN_PATTERN = re.compile(r"@(?P<key>protagonist|setting|time_period)\b")
EXPECTED_GENERATED_FIELD_KEYS = {
    "title",
    "protagonist",
    "secondary_character",
    "time_period",
    "setting",
    "central_conflict",
    "inciting_pressure",
    "ending_type",
    "style_guidance",
    "sexual_content_level",
    "word_count_target",
}
WINDOWS_RESERVED_BASENAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}


def _load_json(path: Any) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _data_file(filename: str) -> Any:
    """
    Resolve a story-brief data file.

    Resolution order:
      1) Explicit directory override via COMMUTED_STORY_BRIEF_DATA_DIR.
      2) Installed package resources under data.story_brief.
      3) Repo-relative fallback for source checkout execution.
    """
    override_raw = os.environ.get("COMMUTED_STORY_BRIEF_DATA_DIR")
    if override_raw:
        override = Path(override_raw).expanduser()
        return override / filename

    try:
        return files("data.story_brief").joinpath(filename)
    except (ModuleNotFoundError, FileNotFoundError):
        return Path(__file__).resolve().parent.parent / "data" / "story_brief" / filename


def _require_keys(section_name: str, payload: dict[str, Any], required: set[str]) -> None:
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"{section_name}: missing required keys: {', '.join(missing)}")


def _validate_string_list(section_name: str, key: str, values: Any) -> None:
    if not isinstance(values, list) or not values:
        raise ValueError(f"{section_name}.{key} must be a non-empty list")
    for idx, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{section_name}.{key}[{idx}] must be a non-empty string")


def _validate_availability_rows(section_name: str, key: str, rows: Any) -> None:
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{section_name}.{key} must be a non-empty list")
    for idx, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError(f"{section_name}.{key}[{idx}] must be [name, start_year, end_year]")
        name, start_year, end_year = row
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{section_name}.{key}[{idx}][0] must be a non-empty string")
        if not isinstance(start_year, int) or not isinstance(end_year, int):
            raise ValueError(f"{section_name}.{key}[{idx}] years must be integers")
        if start_year > end_year:
            raise ValueError(
                f"{section_name}.{key}[{idx}] start_year must be <= end_year"
            )


def validate_story_data(
    titles: dict[str, Any],
    entities: dict[str, Any],
    prompts: dict[str, Any],
    config: dict[str, Any],
) -> None:
    _require_keys("titles", titles, {"titles"})
    _validate_string_list("titles", "titles", titles["titles"])

    _require_keys(
        "entities",
        entities,
        {"character_availability", "setting_availability"},
    )
    _validate_availability_rows(
        "entities", "character_availability", entities["character_availability"]
    )
    _validate_availability_rows(
        "entities", "setting_availability", entities["setting_availability"]
    )

    _require_keys(
        "prompts",
        prompts,
        {"central_conflicts", "inciting_pressures", "ending_types", "style_guidance"},
    )
    _validate_string_list("prompts", "central_conflicts", prompts["central_conflicts"])
    _validate_string_list("prompts", "inciting_pressures", prompts["inciting_pressures"])
    _validate_string_list("prompts", "ending_types", prompts["ending_types"])
    _validate_string_list("prompts", "style_guidance", prompts["style_guidance"])

    _require_keys(
        "config",
        config,
        {
            "schema_version",
            "dataset_version",
            "date_start",
            "date_end",
            "sexual_content_options",
            "sexual_content_weights",
            "word_count_targets",
            "ordered_keys",
            "writing_preamble",
        },
    )
    if not isinstance(config["schema_version"], int) or config["schema_version"] < 1:
        raise ValueError("config.schema_version must be an integer >= 1")
    if not isinstance(config["dataset_version"], str) or not config["dataset_version"].strip():
        raise ValueError("config.dataset_version must be a non-empty string")

    try:
        start = date.fromisoformat(str(config["date_start"]))
        end = date.fromisoformat(str(config["date_end"]))
    except ValueError as exc:
        raise ValueError("config date_start/date_end must be ISO dates (YYYY-MM-DD)") from exc
    if start > end:
        raise ValueError("config.date_start must be <= config.date_end")

    _validate_string_list(
        "config", "sexual_content_options", config["sexual_content_options"]
    )
    weights = config["sexual_content_weights"]
    if not isinstance(weights, list) or not weights:
        raise ValueError("config.sexual_content_weights must be a non-empty list")
    if len(weights) != len(config["sexual_content_options"]):
        raise ValueError("config sexual_content_options/weights must be the same length")
    for idx, value in enumerate(weights):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(
                f"config.sexual_content_weights[{idx}] must be a real number"
            )
        if not math.isfinite(value):
            raise ValueError(
                f"config.sexual_content_weights[{idx}] must be finite"
            )
        if value < 0:
            raise ValueError(
                f"config.sexual_content_weights[{idx}] must be non-negative"
            )
    if sum(weights) <= 0:
        raise ValueError("config.sexual_content_weights must sum to > 0")

    targets = config["word_count_targets"]
    if not isinstance(targets, list) or not targets:
        raise ValueError("config.word_count_targets must be a non-empty list")
    for idx, value in enumerate(targets):
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"config.word_count_targets[{idx}] must be a positive integer")

    ordered_keys = config["ordered_keys"]
    if not isinstance(ordered_keys, list) or not ordered_keys:
        raise ValueError("config.ordered_keys must be a non-empty list")
    if len(set(ordered_keys)) != len(ordered_keys):
        raise ValueError("config.ordered_keys must not contain duplicates")
    for idx, key in enumerate(ordered_keys):
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"config.ordered_keys[{idx}] must be a non-empty string")
    ordered_key_set = set(ordered_keys)
    missing = sorted(EXPECTED_GENERATED_FIELD_KEYS - ordered_key_set)
    extra = sorted(ordered_key_set - EXPECTED_GENERATED_FIELD_KEYS)
    if missing or extra:
        problems: list[str] = []
        if missing:
            problems.append(f"missing expected keys: {', '.join(missing)}")
        if extra:
            problems.append(f"unexpected keys: {', '.join(extra)}")
        raise ValueError(f"config.ordered_keys mismatch: {'; '.join(problems)}")

    if not isinstance(config["writing_preamble"], str) or not config["writing_preamble"].strip():
        raise ValueError("config.writing_preamble must be a non-empty string")


def _tupleize_rows(rows: list[list[Any]]) -> list[tuple[str, int, int]]:
    return [(str(name), int(start), int(end)) for name, start, end in rows]


def load_story_data() -> dict[str, Any]:
    titles = _load_json(_data_file("titles.json"))
    entities = _load_json(_data_file("entities.json"))
    prompts = _load_json(_data_file("prompts.json"))
    config = _load_json(_data_file("config.json"))
    validate_story_data(titles, entities, prompts, config)

    return {
        "titles": [str(v) for v in titles["titles"]],
        "character_availability": _tupleize_rows(entities["character_availability"]),
        "setting_availability": _tupleize_rows(entities["setting_availability"]),
        "central_conflicts": [str(v) for v in prompts["central_conflicts"]],
        "inciting_pressures": [str(v) for v in prompts["inciting_pressures"]],
        "ending_types": [str(v) for v in prompts["ending_types"]],
        "style_guidance": [str(v) for v in prompts["style_guidance"]],
        "date_start": date.fromisoformat(str(config["date_start"])),
        "date_end": date.fromisoformat(str(config["date_end"])),
        "sexual_content_options": [str(v) for v in config["sexual_content_options"]],
        "sexual_content_weights": [float(v) for v in config["sexual_content_weights"]],
        "word_count_targets": [int(v) for v in config["word_count_targets"]],
        "ordered_keys": [str(v) for v in config["ordered_keys"]],
        "writing_preamble": str(config["writing_preamble"]),
        "dataset_version": str(config["dataset_version"]),
    }


DATA = load_story_data()

# Compatibility aliases retained during migration from in-file tables.
TITLES = DATA["titles"]
# Legacy alias retained: protagonists and secondary characters are now drawn
# from the same character_availability pool.
PROTAGONIST_AVAILABILITY = DATA["character_availability"]
CHARACTER_AVAILABILITY = DATA["character_availability"]
SETTING_AVAILABILITY = DATA["setting_availability"]
CENTRAL_CONFLICTS = DATA["central_conflicts"]
INCITING_PRESSURES = DATA["inciting_pressures"]
ENDING_TYPES = DATA["ending_types"]
STYLE_GUIDANCE = DATA["style_guidance"]
DATE_START = DATA["date_start"]
DATE_END = DATA["date_end"]
SEXUAL_CONTENT_OPTIONS = DATA["sexual_content_options"]
SEXUAL_CONTENT_WEIGHTS = DATA["sexual_content_weights"]
WORD_COUNT_TARGETS = DATA["word_count_targets"]
ORDERED_KEYS = DATA["ordered_keys"]
WRITING_PREAMBLE = DATA["writing_preamble"]
DATASET_VERSION = DATA["dataset_version"]


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for cross-platform safety while preserving extension.

    Removes control chars and characters invalid on Windows/macOS/Linux,
    strips trailing dots/spaces, and avoids reserved Windows base names.
    """
    name = Path(filename).name
    stem, suffix = Path(name).stem, Path(name).suffix

    # Remove control chars and characters invalid on common filesystems.
    safe_stem = re.sub(r'[\x00-\x1f<>:"/\\\\|?*]+', "-", stem).strip(" .")
    safe_suffix = re.sub(r'[\x00-\x1f<>:"/\\\\|?*]+', "", suffix).strip(" .")

    if not safe_stem:
        safe_stem = "story-brief"

    if safe_stem.casefold() in WINDOWS_RESERVED_BASENAMES:
        safe_stem = f"{safe_stem}-file"

    if safe_suffix and not safe_suffix.startswith("."):
        safe_suffix = f".{safe_suffix}"

    return f"{safe_stem}{safe_suffix}"


def escape_markdown_heading_text(value: str) -> str:
    """Escape Markdown-significant characters for safe heading rendering."""
    return re.sub(r"([\\`*_{}\[\]()#+\-.!])", r"\\\1", value)


def random_date_in_range(
    rng: random.Random | secrets.SystemRandom, start: date, end: date
) -> date:
    """Return a random date between start and end (inclusive)."""
    day_span = (end - start).days
    return start + timedelta(days=rng.randint(0, day_span))


def available_characters(selected_date: date) -> list[str]:
    """Return characters available for the selected date's year."""
    year = selected_date.year
    return [
        name
        for name, start_year, end_year in CHARACTER_AVAILABILITY
        if start_year <= year <= end_year
    ]


def available_settings(selected_date: date) -> list[str]:
    """Return settings available for the selected date's year."""
    year = selected_date.year
    return [
        setting
        for setting, start_year, end_year in SETTING_AVAILABILITY
        if start_year <= year <= end_year
    ]


def weighted_choice(
    rng: random.Random | secrets.SystemRandom,
    options: list[str],
    weights: list[float],
) -> str:
    """Pick one option using relative weights."""
    if not options:
        raise ValueError("options must not be empty")
    if not weights:
        raise ValueError("weights must not be empty")
    if len(options) != len(weights):
        raise ValueError("options and weights must be the same length")

    for index, weight in enumerate(weights):
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            raise TypeError(f"weight at index {index} must be a real number")
        if not math.isfinite(weight):
            raise ValueError(f"weight at index {index} must be finite")
        if weight < 0:
            raise ValueError(f"weight at index {index} must be non-negative")

    total = sum(weights)
    if total <= 0:
        raise ValueError("at least one weight must be greater than zero")

    threshold = rng.random() * total
    cumulative = 0.0

    for option, weight in zip(options, weights):
        cumulative += weight
        if threshold < cumulative:
            return option

    return options[-1]


def render_title(
    template: str, *, protagonist: str, setting: str, time_period: str
) -> str:
    """Render @token placeholders in title templates."""
    values = {
        "protagonist": protagonist,
        "setting": setting,
        "time_period": time_period,
    }
    return TITLE_TOKEN_PATTERN.sub(lambda match: values[match.group("key")], template)


def pick_story_fields(
    rng: random.Random | secrets.SystemRandom, selected_date: date | None = None
) -> dict[str, str | int]:
    if selected_date is None:
        selected_date = random_date_in_range(rng, DATE_START, DATE_END)
    elif not (DATE_START <= selected_date <= DATE_END):
        raise ValueError(
            f"--date must be between {DATE_START.isoformat()} and {DATE_END.isoformat()}"
        )
    time_period = selected_date.isoformat()

    characters_for_date = available_characters(selected_date)
    if len(characters_for_date) < 2:
        raise ValueError(
            f"Need at least two available characters for year {selected_date.year}."
        )

    settings_for_date = available_settings(selected_date)
    if not settings_for_date:
        raise ValueError(
            f"No settings are available for year {selected_date.year}. "
            "Check setting availability data."
        )

    protagonist = rng.choice(characters_for_date)
    eligible_secondary = [name for name in characters_for_date if name != protagonist]
    secondary_character = rng.choice(eligible_secondary)
    setting = rng.choice(settings_for_date)
    title_template = rng.choice(TITLES)

    return {
        "title": render_title(
            title_template,
            protagonist=protagonist,
            setting=setting,
            time_period=time_period,
        ),
        "protagonist": protagonist,
        "secondary_character": secondary_character,
        "time_period": time_period,
        "setting": setting,
        "central_conflict": rng.choice(CENTRAL_CONFLICTS),
        "inciting_pressure": rng.choice(INCITING_PRESSURES),
        "ending_type": rng.choice(ENDING_TYPES),
        "style_guidance": rng.choice(STYLE_GUIDANCE),
        "sexual_content_level": weighted_choice(
            rng, SEXUAL_CONTENT_OPTIONS, SEXUAL_CONTENT_WEIGHTS
        ),
        "word_count_target": rng.choice(WORD_COUNT_TARGETS),
    }


def to_markdown(fields: dict[str, str | int]) -> str:
    ordered_fields = {key: fields[key] for key in ORDERED_KEYS}
    yaml_text = yaml.safe_dump(
        ordered_fields,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).strip()

    body = [
        "---",
        yaml_text,
        "---",
        "",
        WRITING_PREAMBLE,
        "",
        f"# {escape_markdown_heading_text(str(fields['title']))}",
        "",
        "## Story Draft",
        "",
        (
            f"*Write a story of approximately {fields['word_count_target']} words "
            "using the YAML brief above.*"
        ),
        "",
    ]
    return "\n".join(body)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a random story brief Markdown file with YAML front matter."
        )
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="output/story-seeds",
        help="Directory where the markdown file will be written.",
    )
    parser.add_argument(
        "--filename", help="Optional explicit filename for the markdown file."
    )
    parser.add_argument(
        "--seed", type=int, help="Optional random seed for reproducible output."
    )
    parser.add_argument(
        "--date",
        help="Optional explicit date in YYYY-MM-DD for reproducible scenario testing.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting an existing output file.",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Print the generated markdown to the terminal and do not write a file.",
    )
    args = parser.parse_args()

    rng: random.Random | secrets.SystemRandom
    if args.seed is None:
        rng = secrets.SystemRandom()
    else:
        rng = random.Random(args.seed)

    selected_date: date | None = None
    if args.date:
        try:
            selected_date = date.fromisoformat(args.date)
        except ValueError as exc:
            raise SystemExit("--date must be in YYYY-MM-DD format") from exc

    fields = pick_story_fields(rng, selected_date=selected_date)
    markdown = to_markdown(fields)

    if args.print_only:
        print(markdown)
        return

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.filename:
        filename = sanitize_filename(args.filename)
    else:
        today_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{today_str} {slugify(str(fields['title']))}.md"

    output_path = output_dir / filename
    if output_path.exists() and not args.force:
        raise SystemExit(
            f"Refusing to overwrite existing file: {output_path}. "
            "Use --force to overwrite."
        )

    output_path.write_text(markdown, encoding="utf-8")
    print(f"Generated {output_path}")


if __name__ == "__main__":
    main()
