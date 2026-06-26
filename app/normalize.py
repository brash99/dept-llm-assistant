from pathlib import Path
import hashlib

from app.knowledge import save_knowledge_object
from app.parser_registry import ParserRegistry
from app.parsers.pdf_parser import PDFParser
from app.parsers.text_parser import TextParser
from app.parsers.html_parser import HTMLParser


def build_default_registry():
    registry = ParserRegistry()
    registry.register(PDFParser())
    registry.register(TextParser())
    registry.register(HTMLParser())
    return registry


def normalized_output_path(document, normalized_dir):
    rel = document.relative_path
    safe_hash = hashlib.sha256(rel.encode("utf-8")).hexdigest()
    return Path(normalized_dir) / f"{safe_hash}.json"


def normalize_files(raw_drive, normalized_dir, limit=None):
    raw_drive = Path(raw_drive)
    normalized_dir = Path(normalized_dir)
    
    registry = build_default_registry()

    results = {
        "attempted": 0,
        "succeeded": 0,
        "failed": 0,
        "skipped": 0,
        "outputs": [],
        "errors": [],
    }

    for path in raw_drive.rglob("*"):
        if not path.is_file():
            continue

        if path.name.startswith("._") or path.name == ".DS_Store":
            results["skipped"] += 1
            continue

        parser = registry.get_parser(path)

        if parser is None:
            results["skipped"] += 1
            continue

        if limit is not None and results["attempted"] >= limit:
            break

        results["attempted"] += 1

        try:
            document, outpath = normalize_single_file(
                path=path,
                raw_drive=raw_drive,
                normalized_dir=normalized_dir,
                registry=registry,
            )

            results["succeeded"] += 1
            results["outputs"].append(str(outpath))
        except Exception as exc:
            results["failed"] += 1
            results["errors"].append(
                {
                    "path": str(path),
                    "error": str(exc),
                }
            )

            print(f"[FAIL] {path}: {exc}")

    return results

def normalize_single_file(path, raw_drive, normalized_dir, registry=None):
    path = Path(path)
    raw_drive = Path(raw_drive)
    normalized_dir = Path(normalized_dir)

    if registry is None:
        registry = build_default_registry()

    parser = registry.get_parser(path)

    if parser is None:
        raise RuntimeError(f"No parser available for file: {path}")

    document = parser.parse(path, raw_drive)
    outpath = normalized_output_path(document, normalized_dir)

    save_knowledge_object(document, outpath)

    print(f"[OK] {document.parser:12} {document.relative_path}")

    return document, outpath
