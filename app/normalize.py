from collections import Counter
import hashlib
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from app.config import load_config
from app.corpus_policy import CorpusPolicy
from app.knowledge import (
    make_document_id,
    save_knowledge_object,
)
from app.parser_registry import ParserRegistry
from app.parsers.docx_parser import DOCXParser
from app.parsers.html_parser import HTMLParser
from app.parsers.legacy_office_parser import LegacyOfficeParser
from app.parsers.pdf_parser import PDFParser
from app.parsers.pptx_parser import PPTXParser
from app.parsers.text_parser import TextParser
from app.parsers.xlsx_parser import XLSXParser


def build_default_registry():
    registry = ParserRegistry()
    registry.register(PDFParser())
    registry.register(TextParser())
    registry.register(HTMLParser())
    registry.register(DOCXParser())
    registry.register(PPTXParser())
    registry.register(XLSXParser())
    registry.register(LegacyOfficeParser())
    return registry


def normalized_output_path(document, normalized_dir):
    """
    Derive the output filename from the source-qualified relative path.

    This prevents collisions between independent observers that happen to
    contain files with the same local path.
    """
    safe_hash = hashlib.sha256(
        document.relative_path.encode("utf-8")
    ).hexdigest()

    return Path(normalized_dir) / f"{safe_hash}.json"


def qualify_document_source(
    document,
    *,
    source_key: str,
    source_root: Path,
):
    """
    Add observer identity to a parser-produced Document.

    Parsers continue to operate relative to their own physical source root.
    This function then converts that local path into an institution-wide,
    source-qualified path.
    """
    local_relative_path = Path(
        document.relative_path
    ).as_posix()

    qualified_relative_path = (
        Path(source_key) / local_relative_path
    ).as_posix()

    document.relative_path = qualified_relative_path

    document.id = make_document_id(
        qualified_relative_path,
        document.content_hash,
    )

    source_metadata = dict(document.source or {})

    source_metadata.update(
        {
            "kind": source_metadata.get(
                "kind",
                "filesystem",
            ),
            "source_key": source_key,
            "source_root": str(
                Path(source_root).resolve()
            ),
            "local_relative_path": local_relative_path,
            "relative_path": qualified_relative_path,
        }
    )

    document.source = source_metadata

    document.metadata = dict(
        document.metadata or {}
    )

    document.metadata.update(
        {
            "source_key": source_key,
            "local_relative_path": local_relative_path,
            "qualified_relative_path": (
                qualified_relative_path
            ),
        }
    )

    return document


def normalize_source_roots(
    *,
    sources: Iterable[Dict[str, object]],
    normalized_dir: Path,
    limit: Optional[int] = None,
):
    """
    Normalize documents from multiple independent acquisition roots.

    Each source record must contain:

        {
            "key": "cnu_website",
            "root": Path("storage/raw_web"),
        }

    Content hashes are deduplicated across the complete normalization run.
    Source order therefore establishes which observer supplies the canonical
    searchable copy when identical bytes appear in multiple sources.
    """
    normalized_dir = Path(normalized_dir)
    normalized_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    registry = build_default_registry()
    config = load_config()
    policy = CorpusPolicy(config)

    results = {
        "attempted": 0,
        "succeeded": 0,
        "failed": 0,
        "skipped": 0,
        "skipped_duplicate_content": 0,
        "parser_counts": Counter(),
        "source_counts": Counter(),
        "source_attempted": Counter(),
        "source_skipped": Counter(),
        "outputs": [],
        "errors": [],
    }

    seen_content_hashes = set()

    for source in sources:
        source_key = str(source["key"])
        source_root = Path(
            source["root"]
        ).resolve()

        if not source_root.exists():
            print(
                f"[SKIP SOURCE] {source_key}: "
                f"{source_root} does not exist"
            )
            continue

        if not source_root.is_dir():
            raise NotADirectoryError(
                f"Source root is not a directory: "
                f"{source_root}"
            )

        for path in source_root.rglob("*"):
            if not path.is_file():
                continue

            if not policy.should_include(
                path,
                source_root,
            ):
                results["skipped"] += 1
                results["source_skipped"][
                    source_key
                ] += 1
                continue

            parser = registry.get_parser(path)

            if parser is None:
                results["skipped"] += 1
                results["source_skipped"][
                    source_key
                ] += 1
                continue

            if (
                limit is not None
                and results["attempted"] >= limit
            ):
                break

            results["attempted"] += 1
            results["source_attempted"][
                source_key
            ] += 1

            try:
                document = parser.parse(
                    path,
                    source_root,
                )

                if (
                    document.content_hash
                    in seen_content_hashes
                ):
                    results["skipped"] += 1
                    results[
                        "skipped_duplicate_content"
                    ] += 1
                    results["source_skipped"][
                        source_key
                    ] += 1
                    continue

                seen_content_hashes.add(
                    document.content_hash
                )

                document = qualify_document_source(
                    document,
                    source_key=source_key,
                    source_root=source_root,
                )

                outpath = normalized_output_path(
                    document,
                    normalized_dir,
                )

                save_knowledge_object(
                    document,
                    outpath,
                )

                results["parser_counts"][
                    document.parser
                ] += 1

                results["source_counts"][
                    source_key
                ] += 1

                results["succeeded"] += 1
                results["outputs"].append(
                    str(outpath)
                )

                print(
                    f"[OK] "
                    f"{source_key:18} "
                    f"{document.parser:12} "
                    f"{document.relative_path}"
                )

            except Exception as exc:
                results["failed"] += 1

                results["errors"].append(
                    {
                        "source_key": source_key,
                        "path": str(path),
                        "error": str(exc),
                    }
                )

                print(
                    f"[FAIL] "
                    f"{source_key} "
                    f"{path}: {exc}"
                )

        if (
            limit is not None
            and results["attempted"] >= limit
        ):
            break

    for key in (
        "parser_counts",
        "source_counts",
        "source_attempted",
        "source_skipped",
    ):
        results[key] = dict(
            results[key].most_common()
        )

    return results


def normalize_files(
    raw_drive,
    normalized_dir,
    limit=None,
):
    """
    Backward-compatible one-source normalization entry point.
    """
    return normalize_source_roots(
        sources=[
            {
                "key": "sec_google_drive",
                "root": Path(raw_drive),
            }
        ],
        normalized_dir=normalized_dir,
        limit=limit,
    )


def normalize_single_file(
    path,
    raw_drive,
    normalized_dir,
    registry=None,
    source_key="sec_google_drive",
):
    path = Path(path)
    source_root = Path(raw_drive)
    normalized_dir = Path(normalized_dir)

    if registry is None:
        registry = build_default_registry()

    parser = registry.get_parser(path)

    if parser is None:
        raise RuntimeError(
            f"No parser available for file: {path}"
        )

    document = parser.parse(
        path,
        source_root,
    )

    document = qualify_document_source(
        document,
        source_key=source_key,
        source_root=source_root,
    )

    outpath = normalized_output_path(
        document,
        normalized_dir,
    )

    save_knowledge_object(
        document,
        outpath,
    )

    print(
        f"[OK] "
        f"{source_key:18} "
        f"{document.parser:12} "
        f"{document.relative_path}"
    )

    return document, outpath
