import random
from datetime import date

import pytest

from tools.generate_story_brief import CHARACTER_AVAILABILITY, pick_story_fields


def test_same_seed_is_deterministic() -> None:
    fields_a = pick_story_fields(random.Random(12345))
    fields_b = pick_story_fields(random.Random(12345))
    assert fields_a == fields_b


def test_different_seeds_typically_differ() -> None:
    fields_a = pick_story_fields(random.Random(100))
    fields_b = pick_story_fields(random.Random(101))
    assert fields_a != fields_b


def test_secondary_character_differs_from_protagonist() -> None:
    for seed in range(50):
        fields = pick_story_fields(random.Random(seed))
        assert fields["secondary_character"] != fields["protagonist"]


def test_explicit_date_overrides_random_date() -> None:
    fields = pick_story_fields(random.Random(999), selected_date=date(2000, 1, 1))
    assert fields["time_period"] == "2000-01-01"


def test_explicit_date_out_of_range_fails() -> None:
    with pytest.raises(ValueError, match="--date must be between"):
        pick_story_fields(random.Random(1), selected_date=date(1900, 1, 1))


def test_selected_characters_are_valid_for_time_period_year() -> None:
    availability = {name: (start, end) for name, start, end in CHARACTER_AVAILABILITY}

    for seed in range(200):
        fields = pick_story_fields(random.Random(seed))
        year = int(str(fields["time_period"])[:4])

        protagonist = str(fields["protagonist"])
        secondary = str(fields["secondary_character"])

        p_start, p_end = availability[protagonist]
        s_start, s_end = availability[secondary]

        assert p_start <= year <= p_end
        assert s_start <= year <= s_end


def test_duplicate_character_rows_require_two_distinct_names(monkeypatch: pytest.MonkeyPatch) -> None:
    from tools import generate_story_brief as story_brief

    data = dict(story_brief.get_data())
    data["character_availability"] = [("Only Name", 2000, 2000), ("Only Name", 2000, 2000)]
    monkeypatch.setattr(story_brief, "get_data", lambda: data)

    with pytest.raises(ValueError, match="two distinct available characters"):
        pick_story_fields(random.Random(7), selected_date=date(2000, 1, 1))


def test_weather_value_is_from_allowed_pool() -> None:
    allowed = {
        "great",
        "good",
        "typical",
        "lousy",
        "the sky is trying to kill everyone",
    }
    for seed in range(25):
        fields = pick_story_fields(random.Random(seed))
        assert fields["weather"] in allowed
