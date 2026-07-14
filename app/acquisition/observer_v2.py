from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import yaml

from app.acquisition.authority import SourceAuthority
from app.acquisition.observers import ObserverAuthorization


@dataclass(frozen=True)
class MediaPolicy:
    """
    Media types that one observer is permitted to acquire.

    HTML resources may be traversed. Other accepted media types are terminal
    observations: they are acquired but never crawled for additional links.
    """

    follow_html: bool = True
    follow_pdf: bool = True
    follow_docx: bool = False
    follow_xlsx: bool = False
    follow_csv: bool = False
    follow_text: bool = False

    @classmethod
    def from_dict(
        cls,
        payload: Optional[Dict[str, Any]],
    ) -> "MediaPolicy":
        payload = payload or {}

        return cls(
            follow_html=bool(
                payload.get("follow_html", True)
            ),
            follow_pdf=bool(
                payload.get("follow_pdf", True)
            ),
            follow_docx=bool(
                payload.get("follow_docx", False)
            ),
            follow_xlsx=bool(
                payload.get("follow_xlsx", False)
            ),
            follow_csv=bool(
                payload.get("follow_csv", False)
            ),
            follow_text=bool(
                payload.get("follow_text", False)
            ),
        )

    def accepts_url(self, url: str) -> bool:
        path = urlparse(url).path.casefold()

        suffix_map = {
            ".pdf": self.follow_pdf,
            ".doc": self.follow_docx,
            ".docx": self.follow_docx,
            ".xls": self.follow_xlsx,
            ".xlsx": self.follow_xlsx,
            ".csv": self.follow_csv,
            ".txt": self.follow_text,
            ".md": self.follow_text,
        }

        for suffix, accepted in suffix_map.items():
            if path.endswith(suffix):
                return accepted

        return self.follow_html

    def accepts_media_type(
        self,
        media_type: Optional[str],
    ) -> bool:
        normalized = (
            media_type or ""
        ).split(";", 1)[0].casefold()

        if normalized in {
            "text/html",
            "application/xhtml+xml",
        }:
            return self.follow_html

        if normalized == "application/pdf":
            return self.follow_pdf

        if normalized in {
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }:
            return self.follow_docx

        if normalized in {
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }:
            return self.follow_xlsx

        if normalized == "text/csv":
            return self.follow_csv

        if normalized in {
            "text/plain",
            "text/markdown",
        }:
            return self.follow_text

        return False

    @staticmethod
    def is_html(
        media_type: Optional[str],
    ) -> bool:
        normalized = (
            media_type or ""
        ).split(";", 1)[0].casefold()

        return normalized in {
            "text/html",
            "application/xhtml+xml",
        }


@dataclass(frozen=True)
class ObserverV2:
    """
    Policy-driven contract for one governed institutional observer.
    """

    name: str
    enabled: bool
    source_organization: str
    authority: SourceAuthority

    purposes: Tuple[str, ...]
    priority_terms: Tuple[str, ...]

    seed_urls: Tuple[str, ...]
    allowed_hosts: Tuple[str, ...]
    allowed_prefixes: Tuple[str, ...]

    storage_root: Path
    manifest_path: Path

    budget: int
    max_depth: int
    request_delay_seconds: float
    respect_robots: bool

    media_policy: MediaPolicy
    authorization: Optional[
        ObserverAuthorization
    ] = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError(
                "Observer name must not be empty."
            )

        if not self.seed_urls:
            raise ValueError(
                f"Observer {self.name!r} requires "
                "at least one seed URL."
            )

        if not self.allowed_hosts:
            raise ValueError(
                f"Observer {self.name!r} requires "
                "at least one allowed host."
            )

        if not self.allowed_prefixes:
            raise ValueError(
                f"Observer {self.name!r} requires "
                "at least one allowed prefix."
            )

        if self.budget < 1:
            raise ValueError(
                f"Observer {self.name!r} budget "
                "must be at least 1."
            )

        if self.max_depth < 0:
            raise ValueError(
                f"Observer {self.name!r} max_depth "
                "must be non-negative."
            )

        if (
            not self.respect_robots
            and self.authorization is None
        ):
            raise ValueError(
                f"Observer {self.name!r} may disable "
                "robots enforcement only with explicit "
                "authorization metadata."
            )

    @classmethod
    def from_dict(
        cls,
        payload: Dict[str, Any],
        project_root: Path,
    ) -> "ObserverV2":
        if payload.get("type", "web") != "web":
            raise ValueError(
                "Observer v2 currently supports "
                "type='web' only."
            )

        storage_root = Path(
            payload.get(
                "storage_root",
                "storage/raw_web",
            )
        )

        manifest_path = Path(
            payload["manifest"]
        )

        if not storage_root.is_absolute():
            storage_root = (
                project_root / storage_root
            )

        if not manifest_path.is_absolute():
            manifest_path = (
                project_root / manifest_path
            )

        authorization_payload = payload.get(
            "authorization"
        )

        authorization = (
            ObserverAuthorization.from_dict(
                authorization_payload
            )
            if authorization_payload
            else None
        )

        return cls(
            name=str(payload["name"]),
            enabled=bool(
                payload.get("enabled", True)
            ),
            source_organization=str(
                payload["source_organization"]
            ),
            authority=SourceAuthority(
                payload["authority"]
            ),
            purposes=tuple(
                payload.get("purposes", [])
            ),
            priority_terms=tuple(
                payload.get(
                    "priority_terms",
                    [],
                )
            ),
            seed_urls=tuple(
                payload["seed_urls"]
            ),
            allowed_hosts=tuple(
                host.casefold()
                for host in payload[
                    "allowed_hosts"
                ]
            ),
            allowed_prefixes=tuple(
                payload["allowed_prefixes"]
            ),
            storage_root=storage_root,
            manifest_path=manifest_path,
            budget=int(
                payload.get(
                    "budget",
                    payload.get(
                        "max_pages",
                        25,
                    ),
                )
            ),
            max_depth=int(
                payload.get(
                    "max_depth",
                    5,
                )
            ),
            request_delay_seconds=float(
                payload.get(
                    "request_delay_seconds",
                    0.5,
                )
            ),
            respect_robots=bool(
                payload.get(
                    "respect_robots",
                    True,
                )
            ),
            media_policy=MediaPolicy.from_dict(
                payload.get("media_policy")
            ),
            authorization=authorization,
        )


class ObserverV2Catalog:
    def __init__(
        self,
        observers: Tuple[
            ObserverV2,
            ...,
        ],
    ) -> None:
        self._observers = observers
        self._by_name = {}

        for observer in observers:
            if observer.name in self._by_name:
                raise ValueError(
                    "Duplicate observer name: "
                    f"{observer.name}"
                )

            self._by_name[
                observer.name
            ] = observer

    @classmethod
    def from_yaml(
        cls,
        path: Path,
        *,
        project_root: Optional[Path] = None,
    ) -> "ObserverV2Catalog":
        path = Path(path)

        if project_root is None:
            project_root = Path.cwd()

        payload = yaml.safe_load(
            path.read_text(
                encoding="utf-8"
            )
        ) or {}

        observers = tuple(
            ObserverV2.from_dict(
                record,
                project_root,
            )
            for record in payload.get(
                "observers",
                [],
            )
        )

        return cls(observers)

    def all(
        self,
        *,
        enabled_only: bool = True,
    ) -> Tuple[ObserverV2, ...]:
        if not enabled_only:
            return self._observers

        return tuple(
            observer
            for observer in self._observers
            if observer.enabled
        )

    def get(
        self,
        name: str,
    ) -> ObserverV2:
        try:
            return self._by_name[name]
        except KeyError as error:
            raise KeyError(
                f"Unknown observer: {name}"
            ) from error
