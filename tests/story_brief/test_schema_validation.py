from copy import deepcopy

import pytest

from tools.generate_story_brief import DATA_DIR, _load_json, validate_story_data


def load_all():
    titles = _load_json(DATA_DIR / "titles.json")
    entities = _load_json(DATA_DIR / "entities.json")
    prompts = _load_json(DATA_DIR / "prompts.json")
    config = _load_json(DATA_DIR / "config.json")
    return titles, entities, prompts, config


def test_schema_validation_accepts_current_data() -> None:
    titles, entities, prompts, config = load_all()
    validate_story_data(titles, entities, prompts, config)


@pytest.mark.parametrize(
    ("mutator", "expected_msg"),
    [
        (lambda t, e, p, c: c.pop("ordered_keys"), "missing required keys"),
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
            lambda t, e, p, c: e["setting_availability"].append(["Bad Row", 2020]),
            r"must be \[name, start_year, end_year\]",
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
