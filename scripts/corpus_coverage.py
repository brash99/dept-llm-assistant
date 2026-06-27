from pathlib import Path
from collections import Counter

from app.config import load_config
from app.corpus_policy import CorpusPolicy
from app.normalize import build_default_registry


def format_bytes(n):
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(n)

    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024


def main():

    config = load_config()

    project_root = Path(config["project"]["root"])
    raw_drive = project_root / config["storage"]["raw_drive"]

    policy = CorpusPolicy(config)
    registry = build_default_registry()

    extension_counts = Counter()
    supported_counts = Counter()
    unsupported_counts = Counter()

    total_files = 0
    supported_files = 0
    total_bytes = 0
    supported_bytes = 0

    for path in raw_drive.rglob("*"):

        if not path.is_file():
            continue

        if not policy.should_include(path, raw_drive):
            continue

        total_files += 1
        total_bytes += path.stat().st_size

        suffix = path.suffix.lower()
        extension_counts[suffix] += 1

        parser = registry.get_parser(path)

        if parser is None:
            unsupported_counts[suffix] += 1
            continue

        supported_files += 1
        supported_bytes += path.stat().st_size
        supported_counts[parser.name] += 1

    print("=" * 70)
    print("Corpus Coverage Report")
    print("=" * 70)
    print()

    print(f"Corpus size           : {total_files:,} files")
    print(f"Supported             : {supported_files:,} "
          f"({100*supported_files/total_files:.1f}%)")
    print(f"Unsupported           : {total_files-supported_files:,} "
          f"({100*(total_files-supported_files)/total_files:.1f}%)")
    print()

    print(f"Total size            : {format_bytes(total_bytes)}")
    print(f"Supported size        : {format_bytes(supported_bytes)} "
          f"({100*supported_bytes/total_bytes:.1f}%)")
    print()

    print("-" * 70)
    print("Parser Usage")
    print("-" * 70)

    for parser, count in supported_counts.most_common():
        print(f"{parser:20} {count:8,d}")

    print()
    print("-" * 70)
    print("Unsupported Extensions")
    print("-" * 70)

    for ext, count in unsupported_counts.most_common():
        print(f"{ext or '[no extension]':20} {count:8,d}")

    print()
    print("-" * 70)
    print("Extension Summary")
    print("-" * 70)

    supported_suffixes = set(registry.supported_suffixes())

    for ext, count in sorted(extension_counts.items()):

        mark = "✓" if ext in supported_suffixes else " "

        print(f"[{mark}] {ext or '[no extension]':15} {count:8,d}")


if __name__ == "__main__":
    main()
