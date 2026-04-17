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
from typing import AbstractSet, Any, Iterable, NamedTuple, TypeVar

import yaml

PoolValue = TypeVar("PoolValue", str, int)

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
    "sexual_partner",
    "sexual_scene_tags",
    "word_count_target",
}
SEXUAL_SCENE_TAG_COUNT_OPTIONS = (2, 3, 4, 5)
SEXUAL_SCENE_TAG_COUNT_WEIGHTS = (0.7, 0.1, 0.1, 0.1)
PROMPT_LIST_KEYS = (
    "central_conflicts",
    "inciting_pressures",
    "ending_types",
    "style_guidance",
    "weather",
)
PROMPT_LIST_KEYS_SET = frozenset(PROMPT_LIST_KEYS)
CHARACTER_AVAILABILITY_KEY = "character_availability"
SETTING_AVAILABILITY_KEY = "setting_availability"
PARTNER_DISTRIBUTIONS_KEY = "partner_distributions"
ENTITY_AVAILABILITY_KEYS = frozenset(
    {
        CHARACTER_AVAILABILITY_KEY,
        SETTING_AVAILABILITY_KEY,
    }
)
WINDOWS_RESERVED_BASENAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}


class ValidatedStoryData(NamedTuple):
    character_availability: list[tuple[str, date, date]]
    setting_availability: list[tuple[str, date, date]]
    date_start: date
    date_end: date
    partner_distributions: dict[str, list[dict[str, Any]]]


class DatasetLintReport(NamedTuple):
    errors: list[str]
    warnings: list[str]

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


def _load_json(path: Any) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _data_file(filename: str) -> Any:
    """
    Resolve a story-brief data file.

    Resolution order:
      1) COMMUTED_STORY_BRIEF_DATA_DIR env var (custom/system deployments).
      2) Direct-script source checkout fallback (repo-relative `data/`).
      3) Installed package resources under
         commuted_calligraphy.story_brief.data (packaged installs).

    Why this chain exists:
      - Allows testing against alternate datasets without code changes.
      - Supports container/ops setups that mount data at runtime.
      - Keeps editable local data working during development.
    """
    override_raw = os.environ.get("COMMUTED_STORY_BRIEF_DATA_DIR")
    if override_raw:
        override = Path(override_raw).expanduser()
        return override / filename

    repo_relative = Path(__file__).resolve().parent / "data" / filename
    if __package__ in (None, "") and repo_relative.exists():
        return repo_relative

    try:
        return files("commuted_calligraphy.story_brief.data").joinpath(filename)
    except (ModuleNotFoundError, FileNotFoundError):
        return repo_relative


def _require_keys(
    section_name: str, payload: dict[str, Any], required: AbstractSet[str]
) -> None:
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
            raise ValueError(f"{section_name}.{key}[{idx}] must be [name, start, end]")
        name, start_boundary, end_boundary = row
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{section_name}.{key}[{idx}][0] must be a non-empty string")
        name = name.strip()
        try:
            start = _parse_availability_boundary(start_boundary)
            end = _parse_availability_boundary(end_boundary)
        except ValueError as exc:
            raise ValueError(f"{section_name}.{key}[{idx}] {exc}") from exc
        if start > end:
            raise ValueError(
                f"{section_name}.{key}[{idx}] start must be <= end"
            )
        parsed_rows.append((name, start, end))

    _validate_availability_name_windows(section_name, key, parsed_rows)
    return parsed_rows


def _validate_availability_name_windows(
    section_name: str, key: str, rows: list[tuple[str, date, date]]
) -> None:
    windows_by_name: dict[str, list[tuple[date, date, int]]] = {}
    for idx, row in enumerate(rows):
        name, start, end = row
        name_norm = name.casefold()
        windows_by_name.setdefault(name_norm, []).append((start, end, idx))

    for name_windows in windows_by_name.values():
        name_windows.sort(key=lambda item: item[0])
        for prev, curr in zip(name_windows, name_windows[1:]):
            _, prev_end, prev_idx = prev
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


def _validate_prompt_lists(prompts: dict[str, Any]) -> None:
    _require_keys("prompts", prompts, PROMPT_LIST_KEYS_SET)
    for key in PROMPT_LIST_KEYS:
        _validate_string_list("prompts", key, prompts[key])
        _validate_no_duplicate_strings("prompts", key, prompts[key])


def _validate_titles(titles: dict[str, Any]) -> None:
    _require_keys("titles", titles, {"titles"})
    _validate_string_list("titles", "titles", titles["titles"])
    _validate_no_duplicate_strings("titles", "titles", titles["titles"])
    _validate_title_tokens(titles["titles"])


def _validate_entities(
    entities: dict[str, Any],
) -> tuple[list[tuple[str, date, date]], list[tuple[str, date, date]]]:
    _require_keys("entities", entities, ENTITY_AVAILABILITY_KEYS)
    character_rows = _validate_availability_rows(
        "entities", CHARACTER_AVAILABILITY_KEY, entities[CHARACTER_AVAILABILITY_KEY]
    )
    setting_rows = _validate_availability_rows(
        "entities", SETTING_AVAILABILITY_KEY, entities[SETTING_AVAILABILITY_KEY]
    )
    return character_rows, setting_rows


def _validate_config_versions(config: dict[str, Any]) -> None:
    if not isinstance(config["schema_version"], int) or config["schema_version"] < 1:
        raise ValueError("config.schema_version must be an integer >= 1")
    if not isinstance(config["dataset_version"], str) or not config["dataset_version"].strip():
        raise ValueError("config.dataset_version must be a non-empty string")


def _parse_and_validate_config_dates(config: dict[str, Any]) -> tuple[date, date]:
    try:
        start = date.fromisoformat(str(config["date_start"]))
        end = date.fromisoformat(str(config["date_end"]))
    except ValueError as exc:
        raise ValueError("config date_start/date_end must be ISO dates (YYYY-MM-DD)") from exc
    if start > end:
        raise ValueError("config.date_start must be <= config.date_end")
    return start, end


def _validate_config_date_overlap(
    character_rows: list[tuple[str, date, date]],
    setting_rows: list[tuple[str, date, date]],
    start: date,
    end: date,
) -> None:
    if not _has_date_overlap(character_rows, start, end):
        raise ValueError(
            f"config date range has no overlap with entities.{CHARACTER_AVAILABILITY_KEY}"
        )
    if not _has_date_overlap(setting_rows, start, end):
        raise ValueError(
            f"config date range has no overlap with entities.{SETTING_AVAILABILITY_KEY}"
        )


def _validate_sexual_content_weights(config: dict[str, Any]) -> None:
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


def _validate_word_count_targets(config: dict[str, Any]) -> None:
    targets = config["word_count_targets"]
    if not isinstance(targets, list) or not targets:
        raise ValueError("config.word_count_targets must be a non-empty list")
    for idx, value in enumerate(targets):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"config.word_count_targets[{idx}] must be a positive integer")


def _validate_sexual_scene_tag_groups(config: dict[str, Any]) -> None:
    groups = config["sexual_scene_tag_groups"]
    if not isinstance(groups, dict) or not groups:
        raise ValueError("config.sexual_scene_tag_groups must be a non-empty object")
    if len(groups) < 2:
        raise ValueError("config.sexual_scene_tag_groups must contain at least 2 groups")
    if len(groups) > 5:
        raise ValueError("config.sexual_scene_tag_groups must contain at most 5 groups")

    for group_name, tags in groups.items():
        if not isinstance(group_name, str) or not group_name.strip():
            raise ValueError("config.sexual_scene_tag_groups keys must be non-empty strings")
        _validate_string_list("config", f"sexual_scene_tag_groups.{group_name}", tags)
        _validate_no_duplicate_strings(
            "config", f"sexual_scene_tag_groups.{group_name}", tags
        )


def _validate_ordered_keys(config: dict[str, Any]) -> None:
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


def _validate_writing_preamble(config: dict[str, Any]) -> None:
    if not isinstance(config["writing_preamble"], str) or not config["writing_preamble"].strip():
        raise ValueError("config.writing_preamble must be a non-empty string")


def _validate_partner_distributions(
    partner_payload: dict[str, Any],
    *,
    config_start: date,
    config_end: date,
    character_rows: list[tuple[str, date, date]],
) -> dict[str, list[dict[str, Any]]]:
    _require_keys(
        "partner_distributions",
        partner_payload,
        {
            "schema_version",
            "dataset_version",
            "date_start",
            "date_end",
            PARTNER_DISTRIBUTIONS_KEY,
        },
    )
    if (
        not isinstance(partner_payload["schema_version"], int)
        or partner_payload["schema_version"] < 1
    ):
        raise ValueError("partner_distributions.schema_version must be an integer >= 1")
    if (
        not isinstance(partner_payload["dataset_version"], str)
        or not partner_payload["dataset_version"].strip()
    ):
        raise ValueError("partner_distributions.dataset_version must be a non-empty string")

    try:
        payload_start = date.fromisoformat(str(partner_payload["date_start"]))
        payload_end = date.fromisoformat(str(partner_payload["date_end"]))
    except ValueError as exc:
        raise ValueError(
            "partner_distributions date_start/date_end must be ISO dates (YYYY-MM-DD)"
        ) from exc
    if payload_start > payload_end:
        raise ValueError("partner_distributions.date_start must be <= date_end")
    if payload_end < config_start or payload_start > config_end:
        raise ValueError(
            "partner_distributions date range must overlap config.date_start/date_end"
        )

    entries = partner_payload[PARTNER_DISTRIBUTIONS_KEY]
    if not isinstance(entries, list) or not entries:
        raise ValueError("partner_distributions.partner_distributions must be a non-empty list")

    known_characters = {name for name, _, _ in character_rows}
    seen_characters: set[str] = set()
    index: dict[str, list[dict[str, Any]]] = {}
    for idx, character_entry in enumerate(entries):
        section = f"partner_distributions.partner_distributions[{idx}]"
        if not isinstance(character_entry, dict):
            raise ValueError(f"{section} must be an object")
        _require_keys(section, character_entry, {"character", "date_start", "date_end", "eras"})
        character = str(character_entry["character"]).strip()
        if not character:
            raise ValueError(f"{section}.character must be a non-empty string")
        if character not in known_characters:
            raise ValueError(f"partner_distributions includes unknown character '{character}'")
        if character in seen_characters:
            raise ValueError(f"partner_distributions includes duplicate character '{character}'")
        seen_characters.add(character)

        try:
            char_start = date.fromisoformat(str(character_entry["date_start"]))
            char_end = date.fromisoformat(str(character_entry["date_end"]))
        except ValueError as exc:
            raise ValueError(
                f"{section} date_start/date_end must be ISO dates (YYYY-MM-DD)"
            ) from exc
        if char_start > char_end:
            raise ValueError(f"{section} date_start must be <= date_end")

        eras = character_entry["eras"]
        if not isinstance(eras, list) or not eras:
            raise ValueError(f"{section}.eras must be a non-empty list")
        parsed_eras: list[dict[str, Any]] = []
        last_era_end: date | None = None
        for era_idx, era in enumerate(eras):
            era_section = f"{section}.eras[{era_idx}]"
            if not isinstance(era, dict):
                raise ValueError(f"{era_section} must be an object")
            _require_keys(era_section, era, {"date_start", "date_end", "partners"})
            try:
                era_start = date.fromisoformat(str(era["date_start"]))
                era_end = date.fromisoformat(str(era["date_end"]))
            except ValueError as exc:
                raise ValueError(
                    f"{era_section} date_start/date_end must be ISO dates (YYYY-MM-DD)"
                ) from exc
            if era_start > era_end:
                raise ValueError(f"{era_section} date_start must be <= date_end")
            if era_start < char_start or era_end > char_end:
                raise ValueError(f"{era_section} must be within parent character date range")
            if last_era_end is not None and era_start <= last_era_end:
                raise ValueError(f"{section}.eras has overlapping or unsorted ranges")
            last_era_end = era_end

            partners = era["partners"]
            if not isinstance(partners, list):
                raise ValueError(f"{era_section}.partners must be a list")
            parsed_partners: list[tuple[str, float]] = []
            seen_partners: dict[str, int] = {}
            for partner_idx, partner_item in enumerate(partners):
                partner_section = f"{era_section}.partners[{partner_idx}]"
                if not isinstance(partner_item, dict):
                    raise ValueError(f"{partner_section} must be an object")
                _require_keys(partner_section, partner_item, {"partner", "weight"})
                partner_name = str(partner_item["partner"]).strip()
                weight = partner_item["weight"]
                if not partner_name:
                    raise ValueError(f"{partner_section}.partner must be a non-empty string")
                partner_key = partner_name.casefold()
                if partner_key in seen_partners:
                    first_idx = seen_partners[partner_key]
                    raise ValueError(
                        f"{era_section}.partners contains duplicate partner "
                        f"'{partner_name}' at index {partner_idx} "
                        f"(first seen at index {first_idx})"
                    )
                seen_partners[partner_key] = partner_idx
                if isinstance(weight, bool) or not isinstance(weight, (int, float)):
                    raise ValueError(f"{partner_section}.weight must be a real number")
                if not math.isfinite(weight) or weight < 0:
                    raise ValueError(f"{partner_section}.weight must be finite and non-negative")
                parsed_partners.append((partner_name, float(weight)))
            if parsed_partners and sum(weight for _, weight in parsed_partners) <= 0:
                raise ValueError(f"{era_section}.partners must sum to > 0")
            parsed_eras.append(
                {"date_start": era_start, "date_end": era_end, "partners": parsed_partners}
            )

        index[character] = parsed_eras

    missing_characters = sorted(known_characters - seen_characters)
    if missing_characters:
        raise ValueError(
            "partner_distributions is missing characters: " + ", ".join(missing_characters)
        )
    return index


def validate_story_data(
    titles: dict[str, Any],
    entities: dict[str, Any],
    prompts: dict[str, Any],
    config: dict[str, Any],
    partner_distributions: dict[str, Any],
) -> ValidatedStoryData:
    _validate_titles(titles)
    character_rows, setting_rows = _validate_entities(entities)

    _validate_prompt_lists(prompts)

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
            "sexual_scene_tag_groups",
            "word_count_targets",
            "ordered_keys",
            "writing_preamble",
        },
    )
    _validate_config_versions(config)
    start, end = _parse_and_validate_config_dates(config)
    _validate_config_date_overlap(character_rows, setting_rows, start, end)
    _validate_sexual_content_weights(config)
    _validate_sexual_scene_tag_groups(config)
    _validate_word_count_targets(config)
    _validate_ordered_keys(config)
    _validate_writing_preamble(config)
    partner_distribution_index = _validate_partner_distributions(
        partner_distributions,
        config_start=start,
        config_end=end,
        character_rows=character_rows,
    )

    return ValidatedStoryData(
        character_availability=character_rows,
        setting_availability=setting_rows,
        date_start=start,
        date_end=end,
        partner_distributions=partner_distribution_index,
    )


def load_story_data() -> dict[str, Any]:
    titles = _load_json(_data_file("titles.json"))
    entities = _load_json(_data_file("entities.json"))
    prompts = _load_json(_data_file("prompts.json"))
    config = _load_json(_data_file("config.json"))
    partner_distributions = _load_json(_data_file("partner_distributions.json"))
    validated = validate_story_data(titles, entities, prompts, config, partner_distributions)
    prompt_lists = {
        key: [str(value) for value in prompts[key]]
        for key in PROMPT_LIST_KEYS
    }

    return {
        "titles": [str(v) for v in titles["titles"]],
        CHARACTER_AVAILABILITY_KEY: validated.character_availability,
        SETTING_AVAILABILITY_KEY: validated.setting_availability,
        **prompt_lists,
        "date_start": validated.date_start,
        "date_end": validated.date_end,
        "sexual_content_options": [str(v) for v in config["sexual_content_options"]],
        "sexual_content_weights": [float(v) for v in config["sexual_content_weights"]],
        "sexual_scene_tag_groups": {
            str(group_name): [str(tag) for tag in tags]
            for group_name, tags in config["sexual_scene_tag_groups"].items()
        },
        "word_count_targets": [int(v) for v in config["word_count_targets"]],
        "ordered_keys": [str(v) for v in config["ordered_keys"]],
        "writing_preamble": str(config["writing_preamble"]),
        "dataset_version": str(config["dataset_version"]),
        PARTNER_DISTRIBUTIONS_KEY: validated.partner_distributions,
    }


@lru_cache(maxsize=1)
def get_data() -> dict[str, Any]:
    """Load and cache story-brief data on first use."""
    return load_story_data()


_COMPAT_ALIASES: dict[str, str] = {
    "TITLES": "titles",
    "PROTAGONIST_AVAILABILITY": CHARACTER_AVAILABILITY_KEY,
    "CHARACTER_AVAILABILITY": CHARACTER_AVAILABILITY_KEY,
    "SETTING_AVAILABILITY": SETTING_AVAILABILITY_KEY,
    "CENTRAL_CONFLICTS": "central_conflicts",
    "INCITING_PRESSURES": "inciting_pressures",
    "ENDING_TYPES": "ending_types",
    "STYLE_GUIDANCE": "style_guidance",
    "WEATHER": "weather",
    "DATE_START": "date_start",
    "DATE_END": "date_end",
    "SEXUAL_CONTENT_OPTIONS": "sexual_content_options",
    "SEXUAL_CONTENT_WEIGHTS": "sexual_content_weights",
    "SEXUAL_SCENE_TAG_GROUPS": "sexual_scene_tag_groups",
    "WORD_COUNT_TARGETS": "word_count_targets",
    "ORDERED_KEYS": "ordered_keys",
    "WRITING_PREAMBLE": "writing_preamble",
    "DATASET_VERSION": "dataset_version",
    "PARTNER_DISTRIBUTIONS": PARTNER_DISTRIBUTIONS_KEY,
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
    safe_stem = re.sub(r'[\x00-\x1f<>:"/\\|?*]+', "-", stem).rstrip(" .")
    safe_suffix = re.sub(r'[\x00-\x1f<>:"/\\|?*]+', "", suffix).rstrip(" .")

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
        for name, start_date, end_date in get_data()[CHARACTER_AVAILABILITY_KEY]
        if start_date <= selected_date <= end_date
    ]


def stable_sorted_pool(values: Iterable[PoolValue]) -> list[PoolValue]:
    """Return a consistently sorted copy for seed-stable random selection."""
    return sorted(values)


def available_settings(selected_date: date) -> list[str]:
    """Return settings available for the selected date."""
    return [
        setting
        for setting, start_date, end_date in get_data()[SETTING_AVAILABILITY_KEY]
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


@lru_cache(maxsize=16)
def symmetric_peak_weights(length: int) -> list[float]:
    """Build symmetric bell-curve-like weights with a center peak."""
    if length <= 0:
        raise ValueError("length must be greater than zero")
    return [float(min(index, length - 1 - index) + 1) for index in range(length)]


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
    for source in (data[CHARACTER_AVAILABILITY_KEY], data[SETTING_AVAILABILITY_KEY]):
        for _, row_start, row_end in source:
            clipped_start = max(range_start, row_start)
            clipped_end = min(range_end, row_end)
            if clipped_start <= clipped_end:
                checkpoints.add(clipped_start)
                if clipped_end < range_end:
                    checkpoints.add(clipped_end + one_day)

    for selected_date in sorted(checkpoints):
        characters = [
            name
            for name, start_date, end_date_for_row in data[CHARACTER_AVAILABILITY_KEY]
            if start_date <= selected_date <= end_date_for_row
        ]
        if len(characters) < 2:
            raise ValueError(
                "Strict validation failed: fewer than two distinct available characters on "
                f"{selected_date.isoformat()}."
            )

        if not any(
            start_date <= selected_date <= end_date_for_row
            for _, start_date, end_date_for_row in data[SETTING_AVAILABILITY_KEY]
        ):
            raise ValueError(
                "Strict validation failed: no available settings on "
                f"{selected_date.isoformat()}."
            )


def _format_date_ranges(ranges: list[tuple[date, date]]) -> str:
    if not ranges:
        return "none"
    rendered = []
    for start, end in ranges:
        if start == end:
            rendered.append(start.isoformat())
        else:
            rendered.append(f"{start.isoformat()}..{end.isoformat()}")
    return ", ".join(rendered)


def _coalesce_ranges(ranges: list[tuple[date, date]]) -> list[tuple[date, date]]:
    if not ranges:
        return []
    sorted_ranges = sorted(ranges, key=lambda item: item[0])
    merged: list[tuple[date, date]] = [sorted_ranges[0]]
    one_day = timedelta(days=1)
    for current_start, current_end in sorted_ranges[1:]:
        last_start, last_end = merged[-1]
        if current_start <= last_end + one_day:
            merged[-1] = (last_start, max(last_end, current_end))
            continue
        merged.append((current_start, current_end))
    return merged


def lint_story_data(data: dict[str, Any]) -> DatasetLintReport:
    """Report actionable dataset diagnostics and coverage gaps."""
    range_start = data["date_start"]
    range_end = data["date_end"]

    one_day = timedelta(days=1)
    checkpoints: set[date] = {range_start}
    if range_end < date.max:
        checkpoints.add(range_end + one_day)
    else:
        checkpoints.add(range_end)
    for source in (data[CHARACTER_AVAILABILITY_KEY], data[SETTING_AVAILABILITY_KEY]):
        for _, row_start, row_end in source:
            clipped_start = max(range_start, row_start)
            clipped_end = min(range_end, row_end)
            if clipped_start <= clipped_end:
                checkpoints.add(clipped_start)
                if clipped_end < range_end:
                    checkpoints.add(clipped_end + one_day)

    missing_character_ranges: list[tuple[date, date]] = []
    thin_character_ranges: list[tuple[date, date]] = []
    missing_setting_ranges: list[tuple[date, date]] = []
    thin_setting_ranges: list[tuple[date, date]] = []

    sorted_checkpoints = sorted(checkpoints)
    for current_start, next_start in zip(sorted_checkpoints, sorted_checkpoints[1:]):
        interval_end = min(range_end, next_start - one_day)
        if interval_end < current_start:
            continue
        characters = [
            name
            for name, start_date, end_date in data[CHARACTER_AVAILABILITY_KEY]
            if start_date <= current_start <= end_date
        ]
        settings = [
            name
            for name, start_date, end_date in data[SETTING_AVAILABILITY_KEY]
            if start_date <= current_start <= end_date
        ]
        if len(characters) < 2:
            missing_character_ranges.append((current_start, interval_end))
        elif len(characters) == 2:
            thin_character_ranges.append((current_start, interval_end))

        if not settings:
            missing_setting_ranges.append((current_start, interval_end))
        elif len(settings) == 1:
            thin_setting_ranges.append((current_start, interval_end))

    errors: list[str] = []
    if missing_character_ranges:
        errors.append(
            "Coverage gap: fewer than two distinct characters on "
            f"{_format_date_ranges(_coalesce_ranges(missing_character_ranges))}."
        )
    if missing_setting_ranges:
        errors.append(
            "Coverage gap: no available settings on "
            f"{_format_date_ranges(_coalesce_ranges(missing_setting_ranges))}."
        )

    warnings: list[str] = []
    if thin_character_ranges:
        warnings.append(
            "Fragile coverage: exactly two characters available on "
            f"{_format_date_ranges(_coalesce_ranges(thin_character_ranges))}."
        )
    if thin_setting_ranges:
        warnings.append(
            "Fragile coverage: exactly one setting available on "
            f"{_format_date_ranges(_coalesce_ranges(thin_setting_ranges))}."
        )

    tokens_seen: set[str] = set()
    for template in data["titles"]:
        tokens_seen.update(TITLE_TOKEN_PATTERN.findall(template))
    missing_title_tokens = sorted({"protagonist", "setting", "time_period"} - tokens_seen)
    if missing_title_tokens:
        warnings.append(
            "Title coverage gap: token(s) never used in templates: "
            f"{', '.join(f'@{token}' for token in missing_title_tokens)}."
        )

    for key in PROMPT_LIST_KEYS:
        options = data[key]
        if len(options) < 3:
            warnings.append(
                f"Prompt depth warning: {key} has only {len(options)} option(s); "
                "consider adding at least 3 for variety."
            )

    if len(data["word_count_targets"]) < 3:
        warnings.append(
            "Prompt depth warning: word_count_targets has fewer than 3 options; "
            "consider adding more range variety."
        )

    return DatasetLintReport(errors=errors, warnings=warnings)


def _emit_lint_report(report: DatasetLintReport) -> None:
    if report.errors:
        print("Dataset lint: errors")
        for message in report.errors:
            print(f"  - {message}")
    else:
        print("Dataset lint: no blocking coverage gaps found.")

    if report.warnings:
        print("Dataset lint: warnings")
        for message in report.warnings:
            print(f"  - {message}")
    else:
        print("Dataset lint: no warnings.")


def pick_story_fields(
    rng: random.Random | secrets.SystemRandom, selected_date: date | None = None
) -> dict[str, str | int | list[str] | None]:
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

    characters_for_date = stable_sorted_pool(available_characters(selected_date))
    if len(characters_for_date) < 2:
        raise ValueError(
            "Need at least two distinct available characters for year "
            f"{selected_date.year}."
        )

    settings_for_date = stable_sorted_pool(available_settings(selected_date))
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
    title_template = rng.choice(stable_sorted_pool(data["titles"]))
    sexual_content_level = weighted_choice(
        rng, data["sexual_content_options"], data["sexual_content_weights"]
    )
    sexual_scene_tags: list[str] = []
    if sexual_content_level != "none":
        tag_group_names = stable_sorted_pool(list(data["sexual_scene_tag_groups"]))
        tag_count_options = [
            count
            for count in SEXUAL_SCENE_TAG_COUNT_OPTIONS
            if count <= len(tag_group_names)
        ]
        tag_count_weights = list(SEXUAL_SCENE_TAG_COUNT_WEIGHTS[: len(tag_count_options)])
        selected_tag_count = int(
            weighted_choice(
                rng,
                [str(value) for value in tag_count_options],
                tag_count_weights,
            )
        )
        selected_tag_groups = rng.sample(tag_group_names, selected_tag_count)
        sexual_scene_tags = [
            rng.choice(stable_sorted_pool(data["sexual_scene_tag_groups"][group_name]))
            for group_name in selected_tag_groups
        ]

    sexual_partner: str | None = None
    if sexual_content_level != "none":
        for era in data[PARTNER_DISTRIBUTIONS_KEY][protagonist]:
            if era["date_start"] <= selected_date <= era["date_end"]:
                if era["partners"]:
                    sorted_partner_pairs = stable_sorted_pool(era["partners"])
                    partner_options = [partner for partner, _ in sorted_partner_pairs]
                    partner_weights = [weight for _, weight in sorted_partner_pairs]
                    sexual_partner = weighted_choice(
                        rng,
                        partner_options,
                        partner_weights,
                    )
                break

    result: dict[str, str | int | list[str] | None] = {
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
        "weather": weighted_choice(
            rng,
            data["weather"],
            symmetric_peak_weights(len(data["weather"])),
        ),
        "central_conflict": rng.choice(stable_sorted_pool(data["central_conflicts"])),
        "inciting_pressure": rng.choice(stable_sorted_pool(data["inciting_pressures"])),
        "ending_type": rng.choice(stable_sorted_pool(data["ending_types"])),
        "style_guidance": rng.choice(stable_sorted_pool(data["style_guidance"])),
        "sexual_content_level": sexual_content_level,
        "sexual_partner": sexual_partner,
        "sexual_scene_tags": sexual_scene_tags,
        "word_count_target": rng.choice(stable_sorted_pool(data["word_count_targets"])),
    }
    return result


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
    parser.add_argument(
        "--lint-dataset",
        action="store_true",
        help=(
            "Run dataset lint diagnostics (coverage gaps + fragile spots) and exit "
            "without generating output."
        ),
    )
    args = parser.parse_args()

    rng: random.Random | secrets.SystemRandom
    if args.seed is None:
        rng = secrets.SystemRandom()
    else:
        rng = random.Random(args.seed)

    if args.lint_dataset:
        try:
            report = lint_story_data(get_data())
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        _emit_lint_report(report)
        if report.has_errors:
            raise SystemExit(1)
        return
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
