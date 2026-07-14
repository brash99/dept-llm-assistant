from collections import Counter, deque
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from time import perf_counter, sleep
from typing import Dict, List, Set, Tuple
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from app.acquisition.manifest import (
    AcquisitionManifest,
    AcquisitionStatus,
)
from app.acquisition.observer_v2 import ObserverV2
from app.acquisition.web import WebAcquisitionService


class _LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: List[str] = []

    def handle_starttag(self, tag, attrs) -> None:
        if tag.casefold() not in {"a", "link"}:
            return

        href = dict(attrs).get("href")

        if href:
            self.links.append(href)


@dataclass(frozen=True)
class ObserverV2Failure:
    url: str
    error_type: str
    message: str


@dataclass(frozen=True)
class ObserverV2Report:
    observer_name: str
    budget: int
    observations_attempted: int
    observations_acquired: int
    new_documents: int
    unchanged_documents: int
    changed_documents: int
    duplicate_documents: int
    robots_denied: int
    offsite_links_skipped: int
    outside_scope_links_skipped: int
    unsupported_links_skipped: int
    duplicate_urls_skipped: int
    failed_resources: int
    media_counts: Dict[str, int]
    elapsed_seconds: float
    failures: Tuple[ObserverV2Failure, ...] = ()

    @property
    def completion(self) -> float:
        if not self.budget:
            return 0.0

        return min(
            1.0,
            self.observations_acquired / self.budget,
        )

    def to_dict(self) -> dict:
        return {
            "observer_name": self.observer_name,
            "budget": self.budget,
            "observations_attempted": (
                self.observations_attempted
            ),
            "observations_acquired": (
                self.observations_acquired
            ),
            "completion": self.completion,
            "new_documents": self.new_documents,
            "unchanged_documents": (
                self.unchanged_documents
            ),
            "changed_documents": (
                self.changed_documents
            ),
            "duplicate_documents": (
                self.duplicate_documents
            ),
            "robots_denied": self.robots_denied,
            "offsite_links_skipped": (
                self.offsite_links_skipped
            ),
            "outside_scope_links_skipped": (
                self.outside_scope_links_skipped
            ),
            "unsupported_links_skipped": (
                self.unsupported_links_skipped
            ),
            "duplicate_urls_skipped": (
                self.duplicate_urls_skipped
            ),
            "failed_resources": self.failed_resources,
            "media_counts": dict(self.media_counts),
            "elapsed_seconds": self.elapsed_seconds,
            "failures": [
                {
                    "url": failure.url,
                    "error_type": failure.error_type,
                    "message": failure.message,
                }
                for failure in self.failures
            ],
        }


class ObserverV2Runner:
    """
    Execute one policy-driven institutional observer.

    HTML resources may produce additional observations. Permitted non-HTML
    resources are acquired as terminal SourceDocuments.
    """

    IGNORED_SUFFIXES = {
        ".css",
        ".js",
        ".map",
        ".ico",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".webp",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".mp3",
        ".mp4",
        ".mov",
        ".avi",
        ".zip",
        ".tar",
        ".gz",
        ".7z",
        ".rar",
    }

    def __init__(
        self,
        observer: ObserverV2,
    ) -> None:
        self.observer = observer

        self.web_service = WebAcquisitionService(
            observer.storage_root
        )

        self.manifest = AcquisitionManifest(
            observer.manifest_path
        )

    def run(self) -> ObserverV2Report:
        started = perf_counter()

        queue = deque(
            (
                self._normalize_url(seed),
                0,
            )
            for seed in self.observer.seed_urls
        )

        queued_urls = {
            url
            for url, _ in queue
        }

        visited_urls: Set[str] = set()
        robots_by_origin = {}

        status_counts = Counter()
        media_counts = Counter()

        attempted = 0
        acquired = 0
        robots_denied = 0
        offsite_skipped = 0
        outside_scope_skipped = 0
        unsupported_skipped = 0
        duplicate_skipped = 0
        failures = []

        while (
            queue
            and acquired < self.observer.budget
        ):
            current_url, depth = queue.popleft()

            if current_url in visited_urls:
                duplicate_skipped += 1
                continue

            visited_urls.add(current_url)

            if not self._host_allowed(current_url):
                offsite_skipped += 1
                continue

            if not self._scope_allowed(current_url):
                outside_scope_skipped += 1
                continue

            if not self._url_type_allowed(current_url):
                unsupported_skipped += 1
                continue

            if self.observer.respect_robots:
                robots = self._robots_for_url(
                    current_url,
                    robots_by_origin,
                )

                if not robots.can_fetch(
                    self.web_service.user_agent,
                    current_url,
                ):
                    robots_denied += 1
                    continue

            attempted += 1

            try:
                document = self.web_service.acquire(
                    url=current_url,
                    source_organization=(
                        self.observer
                        .source_organization
                    ),
                    authority=self.observer.authority,
                )

                if not (
                    self.observer
                    .media_policy
                    .accepts_media_type(
                        document.media_type
                    )
                ):
                    unsupported_skipped += 1
                    continue

                decision = self.manifest.record(
                    document
                )

                status_counts[
                    decision.status
                ] += 1

                acquired += 1

                media_counts[
                    document.media_type
                    or "application/octet-stream"
                ] += 1

                if (
                    depth < self.observer.max_depth
                    and self.observer.media_policy.is_html(
                        document.media_type
                    )
                ):
                    saved_path = (
                        self.web_service.storage_root
                        / document.relative_path
                    )

                    discovered = self._extract_links(
                        saved_path=saved_path,
                        base_url=(
                            document.source_url
                            or current_url
                        ),
                    )

                    discovered.sort(
                        key=self._priority_key
                    )

                    for discovered_url in discovered:
                        if (
                            discovered_url in queued_urls
                            or discovered_url
                            in visited_urls
                        ):
                            duplicate_skipped += 1
                            continue

                        if not self._host_allowed(
                            discovered_url
                        ):
                            offsite_skipped += 1
                            continue

                        if not self._scope_allowed(
                            discovered_url
                        ):
                            outside_scope_skipped += 1
                            continue

                        if not self._url_type_allowed(
                            discovered_url
                        ):
                            unsupported_skipped += 1
                            continue

                        queue.append(
                            (
                                discovered_url,
                                depth + 1,
                            )
                        )

                        queued_urls.add(
                            discovered_url
                        )

            except Exception as error:
                failures.append(
                    ObserverV2Failure(
                        url=current_url,
                        error_type=type(
                            error
                        ).__name__,
                        message=str(error),
                    )
                )

            if (
                self.observer
                .request_delay_seconds
                > 0
            ):
                sleep(
                    self.observer
                    .request_delay_seconds
                )

        return ObserverV2Report(
            observer_name=self.observer.name,
            budget=self.observer.budget,
            observations_attempted=attempted,
            observations_acquired=acquired,
            new_documents=status_counts[
                AcquisitionStatus.NEW
            ],
            unchanged_documents=status_counts[
                AcquisitionStatus.UNCHANGED
            ],
            changed_documents=status_counts[
                AcquisitionStatus.CHANGED
            ],
            duplicate_documents=status_counts[
                AcquisitionStatus.DUPLICATE_CONTENT
            ],
            robots_denied=robots_denied,
            offsite_links_skipped=offsite_skipped,
            outside_scope_links_skipped=(
                outside_scope_skipped
            ),
            unsupported_links_skipped=(
                unsupported_skipped
            ),
            duplicate_urls_skipped=duplicate_skipped,
            failed_resources=len(failures),
            media_counts=dict(
                media_counts.most_common()
            ),
            elapsed_seconds=(
                perf_counter() - started
            ),
            failures=tuple(failures),
        )

    def _extract_links(
        self,
        *,
        saved_path: Path,
        base_url: str,
    ) -> List[str]:
        text = saved_path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        parser = _LinkExtractor()
        parser.feed(text)

        discovered = set()

        for href in parser.links:
            href = href.strip()

            if not href:
                continue

            if href.casefold().startswith(
                (
                    "#",
                    "mailto:",
                    "tel:",
                    "javascript:",
                    "data:",
                )
            ):
                continue

            absolute = urljoin(
                base_url,
                href,
            )

            parsed = urlparse(absolute)

            if parsed.scheme not in {
                "http",
                "https",
            }:
                continue

            discovered.add(
                self._normalize_url(absolute)
            )

        return list(discovered)

    def _url_type_allowed(
        self,
        url: str,
    ) -> bool:
        suffix = Path(
            urlparse(url).path
        ).suffix.casefold()

        if suffix in self.IGNORED_SUFFIXES:
            return False

        return (
            self.observer
            .media_policy
            .accepts_url(url)
        )

    def _host_allowed(
        self,
        url: str,
    ) -> bool:
        host = (
            urlparse(url)
            .netloc
            .casefold()
        )

        return host in set(
            self.observer.allowed_hosts
        )

    def _scope_allowed(
        self,
        url: str,
    ) -> bool:
        return any(
            url.startswith(prefix)
            for prefix
            in self.observer.allowed_prefixes
        )

    def _priority_key(
        self,
        url: str,
    ) -> Tuple[int, str]:
        normalized = url.casefold()

        hits = sum(
            1
            for term in self.observer.priority_terms
            if term.casefold() in normalized
        )

        return (
            -hits,
            normalized,
        )

    def _robots_for_url(
        self,
        url: str,
        cache: dict,
    ) -> RobotFileParser:
        parsed = urlparse(url)

        origin = (
            f"{parsed.scheme}://"
            f"{parsed.netloc}"
        )

        if origin in cache:
            return cache[origin]

        parser = RobotFileParser()
        parser.set_url(
            f"{origin}/robots.txt"
        )

        try:
            parser.read()
        except Exception:
            parser.parse(
                [
                    "User-agent: *",
                    "Allow: /",
                ]
            )

        cache[origin] = parser
        return parser

    @staticmethod
    def _normalize_url(
        url: str,
    ) -> str:
        parsed = urlparse(url)

        return parsed._replace(
            scheme=parsed.scheme.casefold(),
            netloc=parsed.netloc.casefold(),
            fragment="",
            path=parsed.path or "/",
        ).geturl()
