import random
from datetime import date

import pytest

from commuted_calligraphy.story_brief.generate_story_brief import get_data, pick_story_fields


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
    with pytest.raises(ValueError, match="outside available range"):
        pick_story_fields(random.Random(1), selected_date=date(1900, 1, 1))


def test_selected_characters_are_valid_for_time_period_year() -> None:
    availability = {
        name: (start, end)
        for name, start, end in get_data()["character_availability"]
    }

    for seed in range(200):
        fields = pick_story_fields(random.Random(seed))
        selected = date.fromisoformat(str(fields["time_period"]))

        protagonist = str(fields["protagonist"])
        secondary = str(fields["secondary_character"])

        p_start, p_end = availability[protagonist]
        s_start, s_end = availability[secondary]

        assert p_start <= selected <= p_end
        assert s_start <= selected <= s_end


def test_duplicate_character_rows_require_two_distinct_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from commuted_calligraphy.story_brief import generate_story_brief as story_brief

    data = dict(story_brief.get_data())
    data["character_availability"] = [
        ("Only Name", date(2000, 1, 1), date(2000, 12, 31)),
        ("Only Name", date(2000, 1, 1), date(2000, 12, 31)),
    ]
    monkeypatch.setattr(story_brief, "get_data", lambda: data)

    with pytest.raises(ValueError, match="two distinct available characters"):
        pick_story_fields(random.Random(7), selected_date=date(2000, 1, 1))


def test_weather_value_is_from_allowed_pool() -> None:
    allowed = {
        "great",
        "good",
        "typical",
        "lousy",
        "the sky is trying to kill someone",
    }
    for seed in range(25):
        fields = pick_story_fields(random.Random(seed))
        assert fields["weather"] in allowed


def test_sexual_scene_tags_follow_count_and_group_rules() -> None:
    tag_groups = get_data()["sexual_scene_tag_groups"]
    tag_to_group = {
        tag: group_name
        for group_name, tags in tag_groups.items()
        for tag in tags
    }

    for seed in range(200):
        fields = pick_story_fields(random.Random(seed))
        selected_tags = fields["sexual_scene_tags"]

        assert isinstance(selected_tags, list)
        assert 2 <= len(selected_tags) <= 5
        assert len(selected_tags) == len(set(selected_tags))

        selected_groups = {tag_to_group[tag] for tag in selected_tags}
        assert len(selected_groups) == len(selected_tags)
