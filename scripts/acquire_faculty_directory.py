#!/usr/bin/env python3
"""Capture a raw snapshot of CNU's faculty directory and profile pages.

This is an ISO Evidence Layer acquisition tool. It uses HTML parsing only to
discover profile URLs; downloaded response bodies are written without content
transformation. Normalization and semantic extraction belong to later stages.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import time
from typing import Iterable, Optional
from urllib.parse import unquote, urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup
import requests


# ---------------------------------------------------------------------------
# Crawler configuration
# ---------------------------------------------------------------------------

BASE_URL = "https://cnu.edu/faculty/"
OUTPUT_DIRECTORY = Path("data/acquisition/faculty/raw")
REQUEST_DELAY_SECONDS = 0.5
RETRY_COUNT = 3
REQUEST_TIMEOUT_SECONDS = 30.0
USER_AGENT = "InstitutionalSemanticObservatory/0.1"

TRANSIENT_HTTP_STATUSES = {408, 425, 429, 500, 502, 503, 504}


@dataclass(frozen=True)
class FetchResult:
    """One HTTP acquisition attempt after any configured retries."""

    url: str
    status: Optional[int]
    content: Optional[bytes]
    error: Optional[str] = None

    @property
    def succeeded(self) -> bool:
        return (
            self.status is not None
            and 200 <= self.status < 300
            and self.content is not None
        )


class PoliteFetcher:
    """Issue sequential requests with a fixed delay and bounded retries."""

    def __init__(
        self,
        *,
        session: Optional[requests.Session] = None,
        request_delay: float = REQUEST_DELAY_SECONDS,
        retry_count: int = RETRY_COUNT,
        timeout: float = REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self.session = session or requests.Session()
        self.request_delay = request_delay
        self.retry_count = retry_count
        self.timeout = timeout
        self._has_requested = False

        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1",
                # Ask the server for an uncompressed entity body so the bytes
                # written to the .html file are the received HTML bytes.
                "Accept-Encoding": "identity",
            }
        )

    def fetch(self, url: str) -> FetchResult:
        """Fetch one URL, retrying only network and transient HTTP failures."""
        last_error: Optional[str] = None
        last_status: Optional[int] = None

        for attempt in range(self.retry_count + 1):
            if self._has_requested:
                time.sleep(self.request_delay)
            self._has_requested = True

            try:
                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    allow_redirects=True,
                )
                last_status = response.status_code

                if 200 <= response.status_code < 300:
                    return FetchResult(
                        url=url,
                        status=response.status_code,
                        content=response.content,
                    )

                last_error = f"HTTP {response.status_code}"
                if (
                    response.status_code not in TRANSIENT_HTTP_STATUSES
                    or attempt == self.retry_count
                ):
                    break
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.SSLError,
            ) as error:
                last_error = f"{type(error).__name__}: {error}"
                if attempt == self.retry_count:
                    break
            except requests.exceptions.RequestException as error:
                # Other requests failures (for example an invalid redirect)
                # are recorded but are not assumed to be transient.
                last_error = f"{type(error).__name__}: {error}"
                break

        return FetchResult(
            url=url,
            status=last_status,
            content=None,
            error=last_error or "Unknown acquisition failure",
        )


def discover_profile_urls(index_html: bytes) -> list[str]:
    """Return sorted, unique faculty profile URLs linked from the index."""
    soup = BeautifulSoup(index_html, "html.parser")
    directory = urlparse(BASE_URL)
    directory_path = directory.path.rstrip("/") + "/"
    urls = set()

    for link in soup.find_all("a", href=True):
        absolute_url, _fragment = urldefrag(
            urljoin(BASE_URL, str(link["href"]))
        )
        parsed = urlparse(absolute_url)

        if parsed.scheme not in {"http", "https"}:
            continue
        if parsed.netloc.casefold() != directory.netloc.casefold():
            continue
        if not parsed.path.startswith(directory_path):
            continue

        filename = PurePosixPath(parsed.path).name.casefold()
        if filename in {"", "index", "index.html"}:
            continue
        if not filename.endswith((".html", ".htm")):
            continue

        urls.add(absolute_url)

    return sorted(urls)


def filename_for_url(url: str) -> str:
    """Create a readable, deterministic, nonnumeric filename from a URL."""
    parsed = urlparse(url)
    path = unquote(parsed.path).strip("/")
    path_without_suffix = re.sub(r"\.html?$", "", path, flags=re.IGNORECASE)
    slug = re.sub(r"[^a-z0-9]+", "_", path_without_suffix.casefold()).strip("_")

    if not slug:
        slug = "page_" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]

    # A textual prefix keeps even an unusual numeric URL from producing a
    # numeric filename. A query suffix prevents deterministic collisions.
    filename = f"{slug}.html"
    if parsed.query:
        query_hash = hashlib.sha256(parsed.query.encode("utf-8")).hexdigest()[:10]
        filename = f"{slug}_{query_hash}.html"
    if filename[0].isdigit():
        filename = "faculty_" + filename

    return filename


def _unique_filenames(urls: Iterable[str]) -> dict[str, str]:
    """Resolve the unlikely case where distinct URLs produce one filename."""
    result: dict[str, str] = {}
    used: dict[str, str] = {}

    for url in sorted(urls):
        filename = filename_for_url(url)
        previous_url = used.get(filename)

        if previous_url is not None and previous_url != url:
            stem = Path(filename).stem
            suffix = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
            filename = f"{stem}_{suffix}.html"

        used[filename] = url
        result[url] = filename

    return result


def _manifest_record(
    *,
    crawl_timestamp: str,
    result: FetchResult,
    saved_filename: str,
) -> dict[str, object]:
    content = result.content
    record: dict[str, object] = {
        "crawl_timestamp": crawl_timestamp,
        "original_url": result.url,
        "saved_filename": saved_filename,
        "http_status": result.status,
        "content_length": len(content) if content is not None else None,
        "sha256_hash": (
            hashlib.sha256(content).hexdigest()
            if content is not None
            else None
        ),
    }
    if result.error:
        record["error"] = result.error
    return record


def _write_manifest(snapshot_directory: Path, records: list[dict[str, object]]) -> None:
    manifest_path = snapshot_directory / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def acquire_faculty_directory(
    *,
    output_directory: Path = OUTPUT_DIRECTORY,
    fetcher: Optional[PoliteFetcher] = None,
    now: Optional[datetime] = None,
) -> int:
    """Acquire the index and all discovered profiles; return a process code."""
    crawl_time = now or datetime.now(timezone.utc)
    crawl_timestamp = crawl_time.isoformat()
    snapshot_directory = Path(output_directory) / crawl_time.date().isoformat()
    snapshot_directory.mkdir(parents=True, exist_ok=True)

    fetcher = fetcher or PoliteFetcher()
    records: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []

    print(f"Downloading faculty directory index: {BASE_URL}")
    index_result = fetcher.fetch(BASE_URL)
    index_record = _manifest_record(
        crawl_timestamp=crawl_timestamp,
        result=index_result,
        saved_filename="faculty_index.html",
    )
    records.append(index_record)

    if not index_result.succeeded:
        failures.append(index_record)
        _write_manifest(snapshot_directory, records)
        print(f"Faculty index failed: {index_result.error}")
        print(f"Manifest: {snapshot_directory / 'manifest.json'}")
        return 1

    assert index_result.content is not None
    (snapshot_directory / "faculty_index.html").write_bytes(index_result.content)

    profile_urls = discover_profile_urls(index_result.content)
    filenames = _unique_filenames(profile_urls)
    total = len(profile_urls)
    downloaded = 0

    print(f"Discovered {total} faculty profile URLs.")

    for position, url in enumerate(profile_urls, start=1):
        filename = filenames[url]
        result = fetcher.fetch(url)
        record = _manifest_record(
            crawl_timestamp=crawl_timestamp,
            result=result,
            saved_filename=filename,
        )
        records.append(record)

        if result.succeeded:
            assert result.content is not None
            (snapshot_directory / filename).write_bytes(result.content)
            downloaded += 1
            print(f"Downloaded {position} / {total}: {filename}")
        else:
            failures.append(record)
            print(
                f"Failed {position} / {total}: {url} "
                f"({result.error})"
            )

    _write_manifest(snapshot_directory, records)

    print()
    print("Faculty directory acquisition complete")
    print(f"Snapshot: {snapshot_directory}")
    print(f"Profiles discovered: {total}")
    print(f"Profiles downloaded: {downloaded}")
    print(f"Failures: {len(failures)}")

    if failures:
        print("Failure summary:")
        for failure in failures:
            print(
                f"- {failure['original_url']}: "
                f"{failure.get('error', 'Unknown acquisition failure')}"
            )

    return 1 if failures else 0


def main() -> int:
    return acquire_faculty_directory()


if __name__ == "__main__":
    raise SystemExit(main())
