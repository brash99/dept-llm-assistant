#!/usr/bin/env python3

import argparse
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from typing import Dict, Iterable, List, Optional, Set, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import (
    parse_qsl,
    urlencode,
    urljoin,
    urlparse,
    urlunparse,
)
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: List[str] = []
        self.title_parts: List[str] = []
        self._inside_title = False

    def handle_starttag(self, tag, attrs) -> None:
        tag = tag.casefold()
        attributes = dict(attrs)

        if tag == "a":
            href = attributes.get("href")
            if href:
                self.links.append(href)

        if tag == "title":
            self._inside_title = True

    def handle_endtag(self, tag) -> None:
        if tag.casefold() == "title":
            self._inside_title = False

    def handle_data(self, data) -> None:
        if self._inside_title:
            self.title_parts.append(data)

    @property
    def title(self) -> str:
        return " ".join(
            " ".join(self.title_parts).split()
        )


@dataclass(frozen=True)
class PageRecord:
    url: str
    depth: int
    title: str
    status_code: int
    content_type: str
    internal_links: int
    external_links: int


@dataclass(frozen=True)
class FailureRecord:
    url: str
    depth: int
    error_type: str
    message: str


def normalize_url(url: str) -> str:
    parsed = urlparse(url)

    if parsed.scheme.casefold() not in {"http", "https"}:
        raise ValueError(
            f"Unsupported URL scheme: {parsed.scheme!r}"
        )

    scheme = parsed.scheme.casefold()
    netloc = parsed.netloc.casefold()

    path = parsed.path or "/"

    while "//" in path:
        path = path.replace("//", "/")

    if not path.startswith("/"):
        path = "/" + path

    query = urlencode(
        sorted(
            parse_qsl(
                parsed.query,
                keep_blank_values=True,
            )
        )
    )

    return urlunparse(
        (
            scheme,
            netloc,
            path,
            "",
            query,
            "",
        )
    )


def top_level_area(url: str) -> str:
    path = urlparse(url).path.strip("/")

    if not path:
        return "(root)"

    return path.split("/", 1)[0].casefold()


def second_level_area(url: str) -> str:
    parts = [
        part
        for part in urlparse(url).path.split("/")
        if part
    ]

    if not parts:
        return "(root)"

    if len(parts) == 1:
        return parts[0].casefold()

    return "/".join(
        part.casefold()
        for part in parts[:2]
    )


def should_skip_link(url: str) -> bool:
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        return True

    ignored_suffixes = {
        ".7z",
        ".avi",
        ".css",
        ".csv",
        ".doc",
        ".docx",
        ".eot",
        ".gif",
        ".gz",
        ".ico",
        ".jpeg",
        ".jpg",
        ".js",
        ".json",
        ".map",
        ".mov",
        ".mp3",
        ".mp4",
        ".pdf",
        ".png",
        ".ppt",
        ".pptx",
        ".rar",
        ".svg",
        ".tar",
        ".tif",
        ".tiff",
        ".ttf",
        ".wav",
        ".webp",
        ".woff",
        ".woff2",
        ".xls",
        ".xlsx",
        ".xml",
        ".zip",
    }

    return Path(parsed.path).suffix.casefold() in ignored_suffixes


def safe_name(value: str) -> str:
    cleaned = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        value,
    )
    return cleaned.strip("._") or "site"


def load_robots(
    seed_url: str,
) -> RobotFileParser:
    parsed = urlparse(seed_url)
    robots_url = (
        f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    )

    parser = RobotFileParser()
    parser.set_url(robots_url)

    try:
        parser.read()
    except Exception:
        parser.parse(
            [
                "User-agent: *",
                "Allow: /",
            ]
        )

    return parser


def fetch_html(
    *,
    url: str,
    user_agent: str,
    timeout_seconds: float,
) -> Tuple[
    bytes,
    str,
    str,
    int,
]:
    request = Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": (
                "text/html,"
                "application/xhtml+xml;q=0.9,"
                "*/*;q=0.1"
            ),
        },
    )

    with urlopen(
        request,
        timeout=timeout_seconds,
    ) as response:
        body = response.read()
        final_url = response.geturl()
        content_type = (
            response.headers.get_content_type()
            or "application/octet-stream"
        )
        status_code = getattr(
            response,
            "status",
            200,
        )

    return (
        body,
        final_url,
        content_type,
        status_code,
    )


def crawl_site(
    *,
    seed_url: str,
    allowed_hosts: Iterable[str],
    max_pages: int,
    max_depth: int,
    delay_seconds: float,
    timeout_seconds: float,
    user_agent: str,
    respect_robots: bool,
    authorization_note: Optional[str],
) -> dict:
    if max_pages < 1:
        raise ValueError(
            "max_pages must be at least 1."
        )

    if max_depth < 0:
        raise ValueError(
            "max_depth must be non-negative."
        )

    if not respect_robots and not authorization_note:
        raise ValueError(
            "Disabling robots enforcement requires "
            "--authorization-note."
        )

    normalized_seed = normalize_url(seed_url)

    allowed_host_set = {
        host.casefold()
        for host in allowed_hosts
    }

    if (
        urlparse(normalized_seed)
        .netloc.casefold()
        not in allowed_host_set
    ):
        raise ValueError(
            "Seed URL host is not in allowed_hosts."
        )

    robots = (
        load_robots(normalized_seed)
        if respect_robots
        else None
    )

    queue = deque(
        [
            (
                normalized_seed,
                0,
            )
        ]
    )

    queued: Set[str] = {
        normalized_seed
    }

    visited: Set[str] = set()
    pages: List[PageRecord] = []
    failures: List[FailureRecord] = []

    edges: Set[Tuple[str, str]] = set()
    external_hosts = Counter()
    skipped_non_html = 0
    skipped_duplicates = 0
    robots_denied = 0

    while (
        queue
        and len(pages) < max_pages
    ):
        current_url, depth = queue.popleft()

        if current_url in visited:
            skipped_duplicates += 1
            continue

        visited.add(current_url)

        if (
            respect_robots
            and robots is not None
            and not robots.can_fetch(
                user_agent,
                current_url,
            )
        ):
            robots_denied += 1
            continue

        try:
            (
                body,
                final_url,
                content_type,
                status_code,
            ) = fetch_html(
                url=current_url,
                user_agent=user_agent,
                timeout_seconds=timeout_seconds,
            )

            normalized_final_url = normalize_url(
                final_url
            )

            if content_type not in {
                "text/html",
                "application/xhtml+xml",
            }:
                skipped_non_html += 1
                continue

            text = body.decode(
                "utf-8",
                errors="replace",
            )

            parser = LinkExtractor()
            parser.feed(text)

            internal_urls: Set[str] = set()
            external_urls: Set[str] = set()

            for href in parser.links:
                href = href.strip()

                if not href or href.startswith(
                    (
                        "#",
                        "mailto:",
                        "tel:",
                        "javascript:",
                        "data:",
                    )
                ):
                    continue

                discovered = urljoin(
                    normalized_final_url,
                    href,
                )

                parsed = urlparse(discovered)

                if parsed.scheme not in {
                    "http",
                    "https",
                }:
                    continue

                if (
                    parsed.netloc.casefold()
                    not in allowed_host_set
                ):
                    external_urls.add(discovered)
                    external_hosts[
                        parsed.netloc.casefold()
                    ] += 1
                    continue

                if should_skip_link(discovered):
                    skipped_non_html += 1
                    continue

                try:
                    normalized_discovered = (
                        normalize_url(discovered)
                    )
                except ValueError:
                    continue

                internal_urls.add(
                    normalized_discovered
                )

                edges.add(
                    (
                        normalized_final_url,
                        normalized_discovered,
                    )
                )

            pages.append(
                PageRecord(
                    url=normalized_final_url,
                    depth=depth,
                    title=parser.title,
                    status_code=status_code,
                    content_type=content_type,
                    internal_links=len(
                        internal_urls
                    ),
                    external_links=len(
                        external_urls
                    ),
                )
            )

            if depth < max_depth:
                for discovered in sorted(
                    internal_urls
                ):
                    if (
                        discovered in visited
                        or discovered in queued
                    ):
                        skipped_duplicates += 1
                        continue

                    queue.append(
                        (
                            discovered,
                            depth + 1,
                        )
                    )
                    queued.add(discovered)

        except (
            HTTPError,
            URLError,
            TimeoutError,
            OSError,
            ValueError,
        ) as error:
            failures.append(
                FailureRecord(
                    url=current_url,
                    depth=depth,
                    error_type=type(
                        error
                    ).__name__,
                    message=str(error),
                )
            )

        if delay_seconds > 0:
            time.sleep(delay_seconds)

    top_level_counts = Counter(
        top_level_area(
            page.url
        )
        for page in pages
    )

    second_level_counts = Counter(
        second_level_area(
            page.url
        )
        for page in pages
    )

    inbound_counts = Counter(
        destination
        for _, destination in edges
    )

    outbound_counts = Counter(
        source
        for source, _ in edges
    )

    return {
        "generated_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "seed_url": normalized_seed,
        "allowed_hosts": sorted(
            allowed_host_set
        ),
        "max_pages": max_pages,
        "max_depth": max_depth,
        "respect_robots": respect_robots,
        "authorization_note": (
            authorization_note
        ),
        "summary": {
            "pages_visited": len(pages),
            "unique_internal_edges": len(edges),
            "external_link_occurrences": (
                sum(
                    external_hosts.values()
                )
            ),
            "external_hosts": len(
                external_hosts
            ),
            "failures": len(failures),
            "robots_denied": robots_denied,
            "queued_but_not_visited": len(
                queue
            ),
            "skipped_non_html": (
                skipped_non_html
            ),
            "skipped_duplicates": (
                skipped_duplicates
            ),
        },
        "top_level_areas": dict(
            top_level_counts.most_common()
        ),
        "second_level_areas": dict(
            second_level_counts.most_common()
        ),
        "external_hosts": dict(
            external_hosts.most_common()
        ),
        "most_linked_pages": [
            {
                "url": url,
                "inbound_links": count,
            }
            for url, count in (
                inbound_counts.most_common(50)
            )
        ],
        "highest_outbound_pages": [
            {
                "url": url,
                "outbound_links": count,
            }
            for url, count in (
                outbound_counts.most_common(50)
            )
        ],
        "pages": [
            asdict(page)
            for page in pages
        ],
        "edges": [
            {
                "source": source,
                "destination": destination,
            }
            for source, destination in sorted(
                edges
            )
        ],
        "failures": [
            asdict(failure)
            for failure in failures
        ],
    }


def markdown_report(report: dict) -> str:
    summary = report["summary"]

    lines = [
        "# Institutional Website Topology",
        "",
        f"**Seed URL:** {report['seed_url']}",
        "",
        f"**Generated:** {report['generated_at']}",
        "",
        "## Governance",
        "",
        f"- Robots policy enforced: "
        f"`{report['respect_robots']}`",
        f"- Authorization note: "
        f"{report.get('authorization_note') or 'None'}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| HTML pages visited | "
        f"{summary['pages_visited']:,} |",
        f"| Unique internal links | "
        f"{summary['unique_internal_edges']:,} |",
        f"| External link occurrences | "
        f"{summary['external_link_occurrences']:,} |",
        f"| External hosts | "
        f"{summary['external_hosts']:,} |",
        f"| Failures | "
        f"{summary['failures']:,} |",
        f"| Robots-denied URLs | "
        f"{summary['robots_denied']:,} |",
        f"| Queued but not visited | "
        f"{summary['queued_but_not_visited']:,} |",
        "",
        "## Top-Level Institutional Areas",
        "",
        "| Area | HTML Pages Observed |",
        "|---|---:|",
    ]

    for area, count in (
        report["top_level_areas"].items()
    ):
        lines.append(
            f"| `{area}` | {count:,} |"
        )

    lines.extend(
        [
            "",
            "## Second-Level Areas",
            "",
            "| Area | HTML Pages Observed |",
            "|---|---:|",
        ]
    )

    for area, count in list(
        report["second_level_areas"].items()
    )[:100]:
        lines.append(
            f"| `{area}` | {count:,} |"
        )

    lines.extend(
        [
            "",
            "## Most Linked Internal Pages",
            "",
            "| Inbound Links | URL |",
            "|---:|---|",
        ]
    )

    for item in report[
        "most_linked_pages"
    ][:25]:
        lines.append(
            f"| {item['inbound_links']:,} | "
            f"{item['url']} |"
        )

    lines.extend(
        [
            "",
            "## Most Common External Hosts",
            "",
            "| Host | Link Occurrences |",
            "|---|---:|",
        ]
    )

    for host, count in list(
        report["external_hosts"].items()
    )[:25]:
        lines.append(
            f"| `{host}` | {count:,} |"
        )

    lines.extend(
        [
            "",
            "## Recommended Observer Design",
            "",
            "Use the top-level and second-level "
            "area counts to define observer scopes "
            "and page budgets.",
            "",
            "Prioritize areas that:",
            "",
            "- represent major institutional functions",
            "- contain authoritative institutional evidence",
            "- are currently weak in the Semantic Ecosystem",
            "- have sufficient pages to justify an independent observer",
            "",
        ]
    )

    if report["failures"]:
        lines.extend(
            [
                "## Failures",
                "",
                "| URL | Error |",
                "|---|---|",
            ]
        )

        for failure in report[
            "failures"
        ][:100]:
            lines.append(
                f"| {failure['url']} | "
                f"{failure['error_type']}: "
                f"{failure['message']} |"
            )

        lines.append("")

    return "\n".join(lines)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Survey the topology of an institutional "
            "website without adding pages to "
            "Institutional Memory."
        )
    )

    parser.add_argument(
        "seed_url",
    )

    parser.add_argument(
        "--allowed-host",
        action="append",
        default=None,
        help=(
            "Allowed hostname. May be supplied more "
            "than once. Defaults to the seed host."
        ),
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=250,
    )

    parser.add_argument(
        "--max-depth",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=0.25,
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
    )

    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=Path(
            "storage/site_maps/cnu"
        ),
    )

    parser.add_argument(
        "--authorized",
        action="store_true",
        help=(
            "Use documented institutional "
            "authorization rather than public "
            "robots policy."
        ),
    )

    parser.add_argument(
        "--authorization-note",
        default=None,
        help=(
            "Required when --authorized is used."
        ),
    )

    parser.add_argument(
        "--user-agent",
        default=(
            "InstitutionalSemanticObservatory/0.1 "
            "(authorized institutional topology survey)"
        ),
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if (
        args.authorized
        and not args.authorization_note
    ):
        raise SystemExit(
            "--authorized requires "
            "--authorization-note."
        )

    parsed_seed = urlparse(
        args.seed_url
    )

    allowed_hosts = (
        args.allowed_host
        or [parsed_seed.netloc]
    )

    report = crawl_site(
        seed_url=args.seed_url,
        allowed_hosts=allowed_hosts,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        delay_seconds=args.delay,
        timeout_seconds=args.timeout,
        user_agent=args.user_agent,
        respect_robots=not args.authorized,
        authorization_note=(
            args.authorization_note
        ),
    )

    output_prefix = args.output_prefix
    output_prefix.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    json_path = output_prefix.with_suffix(
        ".json"
    )

    markdown_path = output_prefix.with_suffix(
        ".md"
    )

    json_path.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    markdown_path.write_text(
        markdown_report(report),
        encoding="utf-8",
    )

    summary = report["summary"]

    print()
    print("ISO Institutional Website Topology")
    print("=" * 68)
    print(
        f"Seed URL:              "
        f"{report['seed_url']}"
    )
    print(
        f"Pages visited:         "
        f"{summary['pages_visited']}"
    )
    print(
        f"Internal edges:        "
        f"{summary['unique_internal_edges']}"
    )
    print(
        f"External hosts:        "
        f"{summary['external_hosts']}"
    )
    print(
        f"Failures:              "
        f"{summary['failures']}"
    )
    print(
        f"Queued, not visited:   "
        f"{summary['queued_but_not_visited']}"
    )
    print(
        f"JSON report:           "
        f"{json_path}"
    )
    print(
        f"Markdown report:       "
        f"{markdown_path}"
    )
    print()
    print("Top-Level Areas")
    print("-" * 68)

    for area, count in list(
        report["top_level_areas"].items()
    )[:30]:
        print(
            f"{area:35} "
            f"{count:8,d}"
        )


if __name__ == "__main__":
    main()
