import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlparse
from urllib.request import Request, urlopen

from app.acquisition.authority import SourceAuthority
from app.acquisition.filesystem import FilesystemAcquisitionService
from app.acquisition.method import AcquisitionMethod
from app.acquisition.source_document import SourceDocument


class _HTMLTitleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._inside_title = False
        self._parts = []

    def handle_starttag(self, tag, attrs) -> None:
        if tag.casefold() == "title":
            self._inside_title = True

    def handle_endtag(self, tag) -> None:
        if tag.casefold() == "title":
            self._inside_title = False

    def handle_data(self, data) -> None:
        if self._inside_title:
            self._parts.append(data)

    @property
    def title(self) -> Optional[str]:
        value = " ".join(" ".join(self._parts).split())
        return value or None


class WebAcquisitionService:
    """
    Acquire one public web resource as a SourceDocument.

    Responsibilities:
    - issue one HTTP GET request,
    - preserve the response bytes,
    - derive a deterministic storage-relative path,
    - delegate hashing and MIME handling to FilesystemAcquisitionService,
    - return a SourceDocument.

    This service does not crawl links, parse institutional meaning, chunk,
    embed, or modify the vector database.
    """

    def __init__(
        self,
        storage_root: Path,
        *,
        timeout_seconds: float = 30.0,
        user_agent: str = (
            "InstitutionalSemanticObservatory/0.1 "
            "(institutional research acquisition)"
        ),
    ) -> None:
        self.storage_root = Path(storage_root).resolve()
        self.storage_root.mkdir(parents=True, exist_ok=True)

        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

        self.filesystem_service = FilesystemAcquisitionService(
            self.storage_root
        )

    def acquire(
        self,
        *,
        url: str,
        source_organization: str,
        authority: SourceAuthority,
        title: Optional[str] = None,
    ) -> SourceDocument:
        request = Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/pdf,text/plain,*/*;q=0.8"
                ),
            },
        )

        with urlopen(
            request,
            timeout=self.timeout_seconds,
        ) as response:
            content = response.read()
            final_url = response.geturl()

            content_type_header = (
                response.headers.get_content_type()
                or "application/octet-stream"
            )

            charset = response.headers.get_content_charset()

        relative_path = self.storage_path_for_url(
            final_url,
            media_type=content_type_header,
        )

        destination = self.storage_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)

        resolved_title = (
            title
            or self._extract_title(
                content=content,
                media_type=content_type_header,
                charset=charset,
            )
            or self._fallback_title(final_url)
        )

        return self.filesystem_service.acquire(
            source_file=destination,
            title=resolved_title,
            source_organization=source_organization,
            authority=authority,
            acquisition_method=AcquisitionMethod.WEB_CRAWL,
            source_url=final_url,
            media_type=content_type_header,
        )

    @staticmethod
    def storage_path_for_url(
        url: str,
        *,
        media_type: Optional[str] = None,
    ) -> Path:
        parsed = urlparse(url)

        if parsed.scheme not in {"http", "https"}:
            raise ValueError(
                f"Unsupported web URL scheme: {parsed.scheme!r}"
            )

        if not parsed.netloc:
            raise ValueError("Web URL must contain a hostname.")

        host = parsed.netloc.casefold()
        path = parsed.path or "/"

        if path.endswith("/"):
            path += "index.html"

        path_object = Path(path.lstrip("/"))

        if not path_object.name:
            path_object = path_object / "index.html"

        if "." not in path_object.name:
            suffix = WebAcquisitionService._suffix_for_media_type(
                media_type
            )
            path_object = path_object.with_name(
                path_object.name + suffix
            )

        if parsed.query:
            normalized_query = urlencode(
                sorted(parse_qsl(parsed.query, keep_blank_values=True))
            )
            query_hash = hashlib.sha256(
                normalized_query.encode("utf-8")
            ).hexdigest()[:12]

            path_object = path_object.with_name(
                f"{path_object.stem}__query_{query_hash}"
                f"{path_object.suffix}"
            )

        safe_parts = [
            WebAcquisitionService._safe_path_part(part)
            for part in path_object.parts
            if part not in {"", ".", ".."}
        ]

        return Path(
            WebAcquisitionService._safe_path_part(host),
            *safe_parts,
        )

    @staticmethod
    def _suffix_for_media_type(
        media_type: Optional[str],
    ) -> str:
        mapping = {
            "text/html": ".html",
            "application/xhtml+xml": ".html",
            "application/pdf": ".pdf",
            "text/plain": ".txt",
            "application/json": ".json",
        }

        return mapping.get(
            (media_type or "").casefold(),
            ".bin",
        )

    @staticmethod
    def _safe_path_part(value: str) -> str:
        value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
        value = value.strip("._")
        return value or "index"

    @staticmethod
    def _extract_title(
        *,
        content: bytes,
        media_type: str,
        charset: Optional[str],
    ) -> Optional[str]:
        if media_type.casefold() not in {
            "text/html",
            "application/xhtml+xml",
        }:
            return None

        encoding = charset or "utf-8"
        text = content.decode(encoding, errors="replace")

        parser = _HTMLTitleParser()
        parser.feed(text)
        return parser.title

    @staticmethod
    def _fallback_title(url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")

        if path:
            name = Path(path).name
            if name:
                return name

        return parsed.netloc
