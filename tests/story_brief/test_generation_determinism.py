import random

from tools.generate_story_brief import pick_story_fields


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
