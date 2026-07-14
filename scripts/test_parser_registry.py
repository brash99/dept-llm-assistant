from pathlib import Path

from app.normalize import build_default_registry


def test_html_files_use_html_parser():
    registry = build_default_registry()

    parser = registry.get_parser(
        Path("example.html")
    )

    assert parser is not None
    assert parser.name == "HTMLParser"


def test_text_files_still_use_text_parser():
    registry = build_default_registry()

    parser = registry.get_parser(
        Path("example.txt")
    )

    assert parser is not None
    assert parser.name == "TextParser"
