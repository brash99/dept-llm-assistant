from pathlib import Path
import hashlib

from app.knowledge import save_knowledge_object
from app.parsers.pdf_parser import PDFParser


PARSERS = [
    PDFParser(),
]


def get_parser(path):
    for parser in PARSERS:
        if parser.can_parse(path):
            return parser
    return None


def normalized_output_path(document, normalized_dir):
    rel = document.relative_path
    safe_hash = hashlib.sha256(rel.encode("utf-8")).hexdigest()
    return Path(normalized_dir) / f"{safe_hash}.json"


def normalize_files(raw_drive, normalized_dir, limit=None):
    raw_drive = Path(raw_drive)
    normalized_dir = Path(normalized_dir)

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

        parser = get_parser(path)

        if parser is None:
            results["skipped"] += 1
            continue

        if limit is not None and results["attempted"] >= limit:
            break

        results["attempted"] += 1

        try:
            document = parser.parse(path, raw_drive)
            outpath = normalized_output_path(document, normalized_dir)
            save_knowledge_object(document, outpath)

            results["succeeded"] += 1
            results["outputs"].append(str(outpath))

            print(f"[OK] {document.relative_path}")

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
