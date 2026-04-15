from commuted_calligraphy.story_brief.generate_story_brief import (
    ORDERED_KEYS,
    render_title,
    to_markdown,
)


def test_markdown_front_matter_delimiters_present() -> None:
    fields = {
        "title": "You Park Like You F*ck and Deserve the Ticket",
        "protagonist": "A",
        "secondary_character": "B",
        "time_period": "2000-01-01",
        "setting": "X",
        "weather": "great",
        "central_conflict": "conflict",
        "inciting_pressure": "pressure",
        "ending_type": "ending",
        "style_guidance": "style",
        "sexual_content_level": "none",
        "sexual_scene_tags": ["tender", "backstage"],
        "word_count_target": 1500,
    }

    text = to_markdown(fields)
    lines = text.splitlines()

    assert lines[0] == "---"
    assert "\n---\n" in text


def test_markdown_heading_escapes_special_chars() -> None:
    fields = {
        "title": "You Park Like You F*ck and Deserve the Ticket",
        "protagonist": "A",
        "secondary_character": "B",
        "time_period": "2000-01-01",
        "setting": "X",
        "weather": "great",
        "central_conflict": "conflict",
        "inciting_pressure": "pressure",
        "ending_type": "ending",
        "style_guidance": "style",
        "sexual_content_level": "none",
        "sexual_scene_tags": ["tender", "backstage"],
        "word_count_target": 1500,
    }

    text = to_markdown(fields)
    assert "# You Park Like You F\\*ck and Deserve the Ticket" in text


def test_markdown_heading_escapes_single_backslash() -> None:
    fields = {
        "title": r"Backslash \\ Test",
        "protagonist": "A",
        "secondary_character": "B",
        "time_period": "2000-01-01",
        "setting": "X",
        "weather": "great",
        "central_conflict": "conflict",
        "inciting_pressure": "pressure",
        "ending_type": "ending",
        "style_guidance": "style",
        "sexual_content_level": "none",
        "sexual_scene_tags": ["tender", "backstage"],
        "word_count_target": 1500,
    }

    text = to_markdown(fields)
    assert r"# Backslash \\\\ Test" in text


def test_yaml_keys_appear_in_configured_order() -> None:
    fields = {
        "title": "Title",
        "protagonist": "A",
        "secondary_character": "B",
        "time_period": "2000-01-01",
        "setting": "X",
        "weather": "great",
        "central_conflict": "conflict",
        "inciting_pressure": "pressure",
        "ending_type": "ending",
        "style_guidance": "style",
        "sexual_content_level": "none",
        "sexual_scene_tags": ["tender", "backstage"],
        "word_count_target": 1500,
    }

    text = to_markdown(fields)
    yaml_block = text.split("---\n", 2)[1]

    positions = [yaml_block.find(f"{key}:") for key in ORDERED_KEYS]
    assert all(pos >= 0 for pos in positions)
    assert positions == sorted(positions)


def test_render_title_substitutes_all_supported_tokens() -> None:
    title = render_title(
        "From @setting with @protagonist (@time_period)",
        protagonist="Kathy",
        setting="Portland",
        time_period="2001-03-01",
    )
    assert title == "From Portland with Kathy (2001-03-01)"
