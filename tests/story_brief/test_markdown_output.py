from tools.generate_story_brief import ORDERED_KEYS, to_markdown


def test_markdown_front_matter_delimiters_present() -> None:
    fields = {
        "title": "You Park Like You F*ck and Deserve the Ticket",
        "protagonist": "A",
        "secondary_character": "B",
        "time_period": "2000-01-01",
        "setting": "X",
        "central_conflict": "conflict",
        "inciting_pressure": "pressure",
        "ending_type": "ending",
        "style_guidance": "style",
        "sexual_content_level": "none",
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
        "central_conflict": "conflict",
        "inciting_pressure": "pressure",
        "ending_type": "ending",
        "style_guidance": "style",
        "sexual_content_level": "none",
        "word_count_target": 1500,
    }

    text = to_markdown(fields)
    assert "# You Park Like You F\\*ck and Deserve the Ticket" in text


def test_yaml_keys_appear_in_configured_order() -> None:
    fields = {
        "title": "Title",
        "protagonist": "A",
        "secondary_character": "B",
        "time_period": "2000-01-01",
        "setting": "X",
        "central_conflict": "conflict",
        "inciting_pressure": "pressure",
        "ending_type": "ending",
        "style_guidance": "style",
        "sexual_content_level": "none",
        "word_count_target": 1500,
    }

    text = to_markdown(fields)
    yaml_block = text.split("---\n", 2)[1]

    positions = [yaml_block.find(f"{key}:") for key in ORDERED_KEYS]
    assert all(pos >= 0 for pos in positions)
    assert positions == sorted(positions)
