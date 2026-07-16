#!/usr/bin/env python3

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs) -> None:
        if tag.casefold() != "a":
            return

        attributes = dict(attrs)
        self._href = attributes.get("href")
        self._text = []

    def handle_data(self, data) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag) -> None:
        if tag.casefold() != "a":
            return

        if self._href:
            title = " ".join(
                " ".join(self._text).split()
            ).strip()

            self.links.append(
                (self._href, title)
            )

        self._href = None
        self._text = []


def extract_candidates(
    *,
    path: Path,
    base_url: str,
) -> list[dict[str, str]]:
    parser = LinkParser()

    parser.feed(
        path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    )

    candidates = []

    for href, title in parser.links:
        url = urljoin(base_url, href)
        lowered = url.casefold()

        if (
            ".pdf" not in lowered
            and "showpublisheddocument" not in lowered
        ):
            continue

        candidates.append(
            {
                "title": title or Path(url).name,
                "url": url,
                "index_file": str(path),
                "index_url": base_url,
            }
        )

    return candidates


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Preview document candidates from a "
            "locally saved authoritative HTML index."
        )
    )

    parser.add_argument(
        "--index",
        action="append",
        nargs=2,
        metavar=("FILE", "BASE_URL"),
        required=True,
        help=(
            "Saved HTML file and its original authoritative URL. "
            "May be supplied multiple times."
        ),
    )

    args = parser.parse_args()

    unique_by_url: dict[str, dict[str, str]] = {}

    for file_value, base_url in args.index:
        path = Path(file_value)

        if not path.exists():
            raise SystemExit(
                f"Index file does not exist: {path}"
            )

        candidates = extract_candidates(
            path=path,
            base_url=base_url,
        )

        print()
        print("=" * 80)
        print(path)
        print("=" * 80)
        print(
            f"Document links found: {len(candidates)}"
        )

        for candidate in candidates:
            unique_by_url.setdefault(
                candidate["url"],
                candidate,
            )

    unique = list(unique_by_url.values())

    print()
    print("=" * 80)
    print("Combined Discovery Preview")
    print("=" * 80)
    print(
        f"Unique document URLs: {len(unique)}"
    )

    for index, candidate in enumerate(
        unique,
        start=1,
    ):
        print()
        print(f"{index:3d}. {candidate['title']}")
        print(f"     {candidate['url']}")


if __name__ == "__main__":
    main()
