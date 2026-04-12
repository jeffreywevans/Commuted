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
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml

TITLE_TOKEN_PATTERN = re.compile(r"@(?P<key>protagonist|setting|time_period)\b")
ANY_TITLE_TOKEN_PATTERN = re.compile(r"@(?P<key>[A-Za-z_]\w*)\b")
EXPECTED_GENERATED_FIELD_KEYS = {
    "title",
    "protagonist",
    "secondary_character",
    "time_period",
    "setting",
    "weather",
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
      1) COMMUTED_STORY_BRIEF_DATA_DIR env var (custom/system deployments).
      2) Installed package resources under data.story_brief (packaged installs).
      3) Repo-relative fallback for source checkout execution (local development).

    Why this chain exists:
      - Allows testing against alternate datasets without code changes.
      - Supports container/ops setups that mount data at runtime.
      - Keeps editable local data working during development.
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


def _validate_no_duplicate_strings(section_name: str, key: str, values: list[str]) -> None:
    seen: dict[str, int] = {}
    for idx, value in enumerate(values):
        normalized = value.strip().casefold()
        if normalized in seen:
            first_idx = seen[normalized]
            raise ValueError(
                f"{section_name}.{key} contains duplicate value at index {idx} "
                f"(first seen at index {first_idx})"
            )
        seen[normalized] = idx


def _validate_title_tokens(values: list[str]) -> None:
    allowed = {"protagonist", "setting", "time_period"}
    for idx, value in enumerate(values):
        for token in ANY_TITLE_TOKEN_PATTERN.findall(value):
            if token not in allowed:
                raise ValueError(
                    f"titles.titles[{idx}] contains unsupported token '@{token}'"
                )


def _parse_availability_boundary(value: Any) -> date:
    if isinstance(value, bool):
        raise ValueError("boundary values must not be booleans")
    if isinstance(value, int):
        return date(value, 1, 1)
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("boundary string values must be ISO dates (YYYY-MM-DD)") from exc
    raise ValueError("boundary values must be an integer year or ISO date string")


def _validate_availability_rows(
    section_name: str, key: str, rows: Any
) -> list[tuple[str, date, date]]:
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{section_name}.{key} must be a non-empty list")
    parsed_rows: list[tuple[str, date, date]] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError(f"{section_name}.{key}[{idx}] must be [name, start_year, end_year]")
        name, start_year, end_year = row
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{section_name}.{key}[{idx}][0] must be a non-empty string")
        try:
            start = _parse_availability_boundary(start_year)
            end = _parse_availability_boundary(end_year)
        except ValueError as exc:
            raise ValueError(f"{section_name}.{key}[{idx}] {exc}") from exc
        if start > end:
            raise ValueError(
                f"{section_name}.{key}[{idx}] start must be <= end"
            )
        parsed_rows.append((name, start, end))

    _validate_availability_name_windows(section_name, key, rows)
    return parsed_rows


def _validate_availability_name_windows(section_name: str, key: str, rows: list[list[Any]]) -> None:
    windows_by_name: dict[str, list[tuple[date, date, int]]] = {}
    for idx, row in enumerate(rows):
        name, start_boundary, end_boundary = row
        name_norm = str(name).strip().casefold()
        start = _parse_availability_boundary(start_boundary)
        end = _parse_availability_boundary(end_boundary)
        windows_by_name.setdefault(name_norm, []).append((start, end, idx))

    for name_windows in windows_by_name.values():
        name_windows.sort(key=lambda item: item[0])
        for prev, curr in zip(name_windows, name_windows[1:]):
            prev_start, prev_end, prev_idx = prev
            curr_start, _, curr_idx = curr
            if curr_start <= prev_end:
                raise ValueError(
                    f"{section_name}.{key} has overlapping availability windows "
                    f"for the same name at indices {prev_idx} and {curr_idx}"
                )


def _has_date_overlap(
    rows: list[tuple[str, date, date]], range_start: date, range_end: date
) -> bool:
    for _, start, end in rows:
        if start <= range_end and end >= range_start:
            return True
    return False


def validate_story_data(
    titles: dict[str, Any],
    entities: dict[str, Any],
    prompts: dict[str, Any],
    config: dict[str, Any],
) -> None:
    _require_keys("titles", titles, {"titles"})
    _validate_string_list("titles", "titles", titles["titles"])
    _validate_no_duplicate_strings("titles", "titles", titles["titles"])
    _validate_title_tokens(titles["titles"])

    _require_keys(
        "entities",
        entities,
        {"character_availability", "setting_availability"},
    )
    character_rows = _validate_availability_rows(
        "entities", "character_availability", entities["character_availability"]
    )
    setting_rows = _validate_availability_rows(
        "entities", "setting_availability", entities["setting_availability"]
    )

    _require_keys(
        "prompts",
        prompts,
        {
            "central_conflicts",
            "inciting_pressures",
            "ending_types",
            "style_guidance",
            "weather",
        },
    )
    _validate_string_list("prompts", "central_conflicts", prompts["central_conflicts"])
    _validate_no_duplicate_strings("prompts", "central_conflicts", prompts["central_conflicts"])
    _validate_string_list("prompts", "inciting_pressures", prompts["inciting_pressures"])
    _validate_no_duplicate_strings("prompts", "inciting_pressures", prompts["inciting_pressures"])
    _validate_string_list("prompts", "ending_types", prompts["ending_types"])
    _validate_no_duplicate_strings("prompts", "ending_types", prompts["ending_types"])
    _validate_string_list("prompts", "style_guidance", prompts["style_guidance"])
    _validate_no_duplicate_strings("prompts", "style_guidance", prompts["style_guidance"])
    _validate_string_list("prompts", "weather", prompts["weather"])
    _validate_no_duplicate_strings("prompts", "weather", prompts["weather"])

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

    if not _has_date_overlap(character_rows, start, end):
        raise ValueError(
            "config date range has no overlap with entities.character_availability"
        )
    if not _has_date_overlap(setting_rows, start, end):
        raise ValueError(
            "config date range has no overlap with entities.setting_availability"
        )

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
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
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


def _tupleize_availability_rows(rows: list[list[Any]]) -> list[tuple[str, date, date]]:
    return [
        (str(name), _parse_availability_boundary(start), _parse_availability_boundary(end))
        for name, start, end in rows
    ]


def load_story_data() -> dict[str, Any]:
    titles = _load_json(_data_file("titles.json"))
    entities = _load_json(_data_file("entities.json"))
    prompts = _load_json(_data_file("prompts.json"))
    config = _load_json(_data_file("config.json"))
    validate_story_data(titles, entities, prompts, config)

    return {
        "titles": [str(v) for v in titles["titles"]],
        "character_availability": _tupleize_availability_rows(entities["character_availability"]),
        "setting_availability": _tupleize_availability_rows(entities["setting_availability"]),
        "central_conflicts": [str(v) for v in prompts["central_conflicts"]],
        "inciting_pressures": [str(v) for v in prompts["inciting_pressures"]],
        "ending_types": [str(v) for v in prompts["ending_types"]],
        "style_guidance": [str(v) for v in prompts["style_guidance"]],
        "weather": [str(v) for v in prompts["weather"]],
        "date_start": date.fromisoformat(str(config["date_start"])),
        "date_end": date.fromisoformat(str(config["date_end"])),
        "sexual_content_options": [str(v) for v in config["sexual_content_options"]],
        "sexual_content_weights": [float(v) for v in config["sexual_content_weights"]],
        "word_count_targets": [int(v) for v in config["word_count_targets"]],
        "ordered_keys": [str(v) for v in config["ordered_keys"]],
        "writing_preamble": str(config["writing_preamble"]),
        "dataset_version": str(config["dataset_version"]),
    }


@lru_cache(maxsize=1)
def get_data() -> dict[str, Any]:
    """Load and cache story-brief data on first use."""
    return load_story_data()


_COMPAT_ALIASES: dict[str, str] = {
    "TITLES": "titles",
    "PROTAGONIST_AVAILABILITY": "character_availability",
    "CHARACTER_AVAILABILITY": "character_availability",
    "SETTING_AVAILABILITY": "setting_availability",
    "CENTRAL_CONFLICTS": "central_conflicts",
    "INCITING_PRESSURES": "inciting_pressures",
    "ENDING_TYPES": "ending_types",
    "STYLE_GUIDANCE": "style_guidance",
    "WEATHER": "weather",
    "DATE_START": "date_start",
    "DATE_END": "date_end",
    "SEXUAL_CONTENT_OPTIONS": "sexual_content_options",
    "SEXUAL_CONTENT_WEIGHTS": "sexual_content_weights",
    "WORD_COUNT_TARGETS": "word_count_targets",
    "ORDERED_KEYS": "ordered_keys",
    "WRITING_PREAMBLE": "writing_preamble",
    "DATASET_VERSION": "dataset_version",
}


def __getattr__(name: str) -> Any:
    """Compatibility layer for legacy module-level constants."""
    if name in _COMPAT_ALIASES:
        return get_data()[_COMPAT_ALIASES[name]]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
    """Return characters available for the selected date."""
    return [
        name
        for name, start_date, end_date in get_data()["character_availability"]
        if start_date <= selected_date <= end_date
    ]


def unique_preserving_order(values: list[str]) -> list[str]:
    """Return unique items in first-seen order."""
    return list(dict.fromkeys(values))


def available_settings(selected_date: date) -> list[str]:
    """Return settings available for the selected date."""
    return [
        setting
        for setting, start_date, end_date in get_data()["setting_availability"]
        if start_date <= selected_date <= end_date
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


def validate_story_data_strict(data: dict[str, Any]) -> None:
    """Validate per-date generation preconditions across the configured date range."""
    range_start = data["date_start"]
    range_end = data["date_end"]
    one_day = timedelta(days=1)

    checkpoints: set[date] = {range_start, range_end}
    for _, row_start, row_end in data["character_availability"] + data["setting_availability"]:
        clipped_start = max(range_start, row_start)
        clipped_end = min(range_end, row_end)
        if clipped_start <= clipped_end:
            checkpoints.add(clipped_start)
            if clipped_end < range_end:
                checkpoints.add(clipped_end + one_day)

    for selected_date in sorted(checkpoints):
        characters = [
            name
            for name, start_date, end_date_for_row in data["character_availability"]
            if start_date <= selected_date <= end_date_for_row
        ]
        if len(characters) < 2:
            raise ValueError(
                "Strict validation failed: fewer than two distinct available characters on "
                f"{selected_date.isoformat()}."
            )

        if not any(
            start_date <= selected_date <= end_date_for_row
            for _, start_date, end_date_for_row in data["setting_availability"]
        ):
            raise ValueError(
                "Strict validation failed: no available settings on "
                f"{selected_date.isoformat()}."
            )


def pick_story_fields(
    rng: random.Random | secrets.SystemRandom, selected_date: date | None = None
) -> dict[str, str | int]:
    data = get_data()
    if selected_date is None:
        selected_date = random_date_in_range(rng, data["date_start"], data["date_end"])
    elif not (data["date_start"] <= selected_date <= data["date_end"]):
        raise ValueError(
            f"Date {selected_date.isoformat()} is outside available range "
            f"({data['date_start'].isoformat()} to {data['date_end'].isoformat()}). "
            "Try a date within the Commuted archive timeline."
        )
    time_period = selected_date.isoformat()

    characters_for_date = unique_preserving_order(available_characters(selected_date))
    if len(characters_for_date) < 2:
        raise ValueError(
            "Need at least two distinct available characters for year "
            f"{selected_date.year}."
        )

    settings_for_date = available_settings(selected_date)
    if not settings_for_date:
        raise ValueError(
            f"No settings are available for year {selected_date.year}. "
            "Check setting availability data."
        )

    protagonist = rng.choice(characters_for_date)
    eligible_secondary = [name for name in characters_for_date if name != protagonist]
    if not eligible_secondary:
        raise ValueError(
            "Need at least two distinct available characters for year "
            f"{selected_date.year}."
        )
    secondary_character = rng.choice(eligible_secondary)
    setting = rng.choice(settings_for_date)
    title_template = rng.choice(data["titles"])

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
        "weather": rng.choice(data["weather"]),
        "central_conflict": rng.choice(data["central_conflicts"]),
        "inciting_pressure": rng.choice(data["inciting_pressures"]),
        "ending_type": rng.choice(data["ending_types"]),
        "style_guidance": rng.choice(data["style_guidance"]),
        "sexual_content_level": weighted_choice(
            rng, data["sexual_content_options"], data["sexual_content_weights"]
        ),
        "word_count_target": rng.choice(data["word_count_targets"]),
    }


def to_markdown(fields: dict[str, str | int]) -> str:
    ordered_fields = {key: fields[key] for key in get_data()["ordered_keys"]}
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
        get_data()["writing_preamble"],
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
    parser.add_argument(
        "--validate-strict",
        action="store_true",
        help=(
            "Run strict per-date validation across the configured date range before generating "
            "output."
        ),
    )
    args = parser.parse_args()

    rng: random.Random | secrets.SystemRandom
    if args.seed is None:
        rng = secrets.SystemRandom()
    else:
        rng = random.Random(args.seed)

    if args.validate_strict:
        try:
            validate_story_data_strict(get_data())
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc

    selected_date: date | None = None
    if args.date:
        try:
            selected_date = date.fromisoformat(args.date)
        except ValueError as exc:
            raise SystemExit("--date must be in YYYY-MM-DD format") from exc

    try:
        fields = pick_story_fields(rng, selected_date=selected_date)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
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
