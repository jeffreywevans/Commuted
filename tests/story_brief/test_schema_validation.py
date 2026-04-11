from copy import deepcopy
import json
from pathlib import Path

import pytest

from tools.generate_story_brief import validate_story_data


def load_all():
    data_dir = Path(__file__).resolve().parents[2] / "data" / "story_brief"
    titles = json.loads((data_dir / "titles.json").read_text(encoding="utf-8"))
    entities = json.loads((data_dir / "entities.json").read_text(encoding="utf-8"))
    prompts = json.loads((data_dir / "prompts.json").read_text(encoding="utf-8"))
    config = json.loads((data_dir / "config.json").read_text(encoding="utf-8"))
    return titles, entities, prompts, config


def test_schema_validation_accepts_current_data() -> None:
    titles, entities, prompts, config = load_all()
    validate_story_data(titles, entities, prompts, config)


@pytest.mark.parametrize(
    ("mutator", "expected_msg"),
    [
        (lambda t, e, p, c: c.pop("ordered_keys"), "missing required keys"),
        (lambda t, e, p, c: c.update({"dataset_version": ""}), "dataset_version"),
        (lambda t, e, p, c: c.update({"date_start": "not-a-date"}), "ISO dates"),
        (
            lambda t, e, p, c: c.update({"sexual_content_weights": [0, 0, 0, 0, 0]}),
            "must sum to > 0",
        ),
        (
            lambda t, e, p, c: c.update({"ordered_keys": c["ordered_keys"] + ["title"]}),
            "must not contain duplicates",
        ),
        (
            lambda t, e, p, c: c.update(
                {"ordered_keys": ["titel" if k == "title" else k for k in c["ordered_keys"]]}
            ),
            "ordered_keys mismatch",
        ),
        (lambda t, e, p, c: p.pop("weather"), "missing required keys"),
        (
            lambda t, e, p, c: e["setting_availability"].append(["Bad Row", 2020]),
            r"must be \[name, start_year, end_year\]",
        ),
        (
            lambda t, e, p, c: e["character_availability"].append(["Bool Year", True, 2000]),
            "boundary values must not be booleans",
        ),
        (
            lambda t, e, p, c: c.update({"word_count_targets": [True, 1200]}),
            "must be a positive integer",
        ),
        (
            lambda t, e, p, c: t.update({"titles": t["titles"] + [t["titles"][0]]}),
            "titles.titles contains duplicate value",
        ),
        (
            lambda t, e, p, c: p.update(
                {"weather": p["weather"] + [p["weather"][0]]}
            ),
            "prompts.weather contains duplicate value",
        ),
        (
            lambda t, e, p, c: e.update(
                {
                    "character_availability": e["character_availability"]
                    + [e["character_availability"][0]]
                }
            ),
            "entities.character_availability contains duplicate value",
        ),
        (
            lambda t, e, p, c: t.update({"titles": ["A Tale of @protagnoist"]}),
            "unsupported token",
        ),
    ],
)
def test_schema_validation_rejects_bad_data(mutator, expected_msg: str) -> None:
    titles, entities, prompts, config = load_all()
    titles = deepcopy(titles)
    entities = deepcopy(entities)
    prompts = deepcopy(prompts)
    config = deepcopy(config)

    mutator(titles, entities, prompts, config)

    with pytest.raises(ValueError, match=expected_msg):
        validate_story_data(titles, entities, prompts, config)
