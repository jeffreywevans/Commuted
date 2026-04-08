#!/usr/bin/env python3
"""Generate a random story brief as Markdown with YAML front matter."""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import secrets
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "story_brief"
TITLE_TOKEN_PATTERN = re.compile(r"@(?P<key>protagonist|setting|time_period)\b")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _tupleize_rows(rows: list[list[Any]]) -> list[tuple[str, int, int]]:
    return [(str(name), int(start), int(end)) for name, start, end in rows]


def load_story_data() -> dict[str, Any]:
    titles = _load_json(DATA_DIR / "titles.json")
    entities = _load_json(DATA_DIR / "entities.json")
    prompts = _load_json(DATA_DIR / "prompts.json")
    config = _load_json(DATA_DIR / "config.json")

    return {
        "titles": [str(v) for v in titles["titles"]],
        "protagonist_availability": _tupleize_rows(entities["protagonist_availability"]),
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
    }


DATA = load_story_data()

# Compatibility aliases retained during migration from in-file tables.
TITLES = DATA["titles"]
PROTAGONIST_AVAILABILITY = DATA["protagonist_availability"]
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


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def escape_markdown_heading_text(value: str) -> str:
    """Escape Markdown-significant characters for safe heading rendering."""
    return re.sub(r"([\\\\`*_{}\[\]()#+\-.!])", r"\\\1", value)


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
    if len(options) != len(weights):
        raise ValueError("options and weights must be the same length")
    if not weights:
        raise ValueError("weights must not be empty")

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
        if threshold <= cumulative:
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


def pick_story_fields(rng: random.Random | secrets.SystemRandom) -> dict[str, str | int]:
    selected_date = random_date_in_range(rng, DATE_START, DATE_END)
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
        default="8. Story Seeds",
        help="Directory where the markdown file will be written.",
    )
    parser.add_argument(
        "--filename", help="Optional explicit filename for the markdown file."
    )
    parser.add_argument(
        "--seed", type=int, help="Optional random seed for reproducible output."
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

    fields = pick_story_fields(rng)
    markdown = to_markdown(fields)

    if args.print_only:
        print(markdown)
        return

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.filename:
        filename = Path(args.filename).name
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
