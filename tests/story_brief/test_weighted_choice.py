import random

import pytest

from tools.generate_story_brief import weighted_choice


def test_weighted_choice_returns_option_from_domain() -> None:
    rng = random.Random(1)
    options = ["a", "b", "c"]
    weights = [0.6, 0.3, 0.1]

    value = weighted_choice(rng, options, weights)
    assert value in options


@pytest.mark.parametrize(
    ("options", "weights", "expected_exc"),
    [
        ([], [], ValueError),
        (["a"], [], ValueError),
        (["a", "b"], [1.0], ValueError),
        (["a"], [float("nan")], ValueError),
        (["a"], [float("inf")], ValueError),
        (["a"], [-1.0], ValueError),
        (["a"], [0.0], ValueError),
        (["a"], [True], TypeError),
        (["a"], ["x"], TypeError),
    ],
)
def test_weighted_choice_invalid_inputs(options, weights, expected_exc) -> None:
    rng = random.Random(1)
    with pytest.raises(expected_exc):
        weighted_choice(rng, options, weights)


def test_weighted_choice_does_not_select_zero_weight_at_random_zero() -> None:
    class ZeroRng:
        def random(self) -> float:
            return 0.0

    choice = weighted_choice(ZeroRng(), ["disabled", "enabled"], [0.0, 1.0])
    assert choice == "enabled"
