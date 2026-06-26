from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json

from app.corpus_policy import CorpusPolicy


@dataclass
class FileInfo:
    path: str
    relative_path: str
    suffix: str
    size_bytes: int
    top_folder: str


def human_size(num: int) -> str:
    value = float(num)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} PB"


def scan_directory(root: Path, policy=None) -> list[FileInfo]:
    root = Path(root).resolve()
    files = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        if policy is not None and not policy.should_include(path, root):
            continue

        try:
            size = path.stat().st_size
        except OSError:
            size = 0

        rel = path.relative_to(root)
        parts = rel.parts

        files.append(
            FileInfo(
                path=str(path),
                relative_path=str(rel),
                suffix=path.suffix.lower() or "<none>",
                size_bytes=size,
                top_folder=parts[0] if parts else "<root>",
            )
        )

    return files


def build_inventory(root: Path, config=None) -> dict:
    policy = CorpusPolicy(config) if config is not None else None
    files = scan_directory(root, policy=policy)

    extension_counts = Counter(f.suffix for f in files)
    folder_counts = Counter(f.top_folder for f in files)
    total_bytes = sum(f.size_bytes for f in files)

    largest = sorted(files, key=lambda f: f.size_bytes, reverse=True)[:25]

    return {
        "scan_time": datetime.now().isoformat(timespec="seconds"),
        "root": str(Path(root).resolve()),
        "policy_applied": config is not None,
        "num_files": len(files),
        "total_bytes": total_bytes,
        "total_size_human": human_size(total_bytes),
        "extensions": dict(extension_counts.most_common()),
        "top_level_folders": dict(folder_counts.most_common()),
        "largest_files": [asdict(f) for f in largest],
    }


def print_inventory(inv: dict) -> None:
    print("=" * 70)
    print("Department LLM Corpus Inventory")
    print("=" * 70)
    print()
    print(f"Root directory : {inv['root']}")
    print(f"Scan time      : {inv['scan_time']}")
    print(f"Policy applied : {inv.get('policy_applied', False)}")
    print(f"Files scanned  : {inv['num_files']:,}")
    print(f"Total size     : {inv['total_size_human']}")
    print()

    print("Top File Types")
    print("-" * 70)
    for suffix, count in inv["extensions"].items():
        print(f"{suffix:15} {count:10,d}")
    print()

    print("Top-Level Folders")
    print("-" * 70)
    for folder, count in inv["top_level_folders"].items():
        print(f"{folder:40} {count:10,d}")
    print()

    print("Largest Files")
    print("-" * 70)
    for f in inv["largest_files"]:
        print(f"{human_size(f['size_bytes']):>12}   {f['relative_path']}")
    print()


def write_inventory(inv: dict, log_dir: Path) -> Path:
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outpath = log_dir / f"inventory_{timestamp}.json"

    with outpath.open("w", encoding="utf-8") as f:
        json.dump(inv, f, indent=2)

    return outpath


def run_inventory(raw_drive: Path, log_dir: Path, config=None) -> dict:
    inv = build_inventory(raw_drive, config=config)
    print_inventory(inv)
    outpath = write_inventory(inv, log_dir)
    print(f"Inventory JSON written to: {outpath}")
    return inv
