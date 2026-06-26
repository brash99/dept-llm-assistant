from collections import Counter
from datetime import datetime
from pathlib import Path
import json


TEXT_FIRST_PASS = {
    ".pdf", ".docx", ".txt", ".html", ".htm", ".csv", ".tex", ".md"
}

TEXT_SECOND_PASS = {
    ".doc", ".pptx", ".ppt", ".xlsx", ".xls"
}

CODE = {
    ".py", ".java", ".cpp", ".c", ".h", ".js", ".xml", ".css", ".php"
}

MEDIA_IGNORE = {
    ".jpg", ".jpeg", ".png", ".gif", ".cr2", ".swf", ".mp4", ".mov", ".avi",
    ".eps", ".ai", ".stl"
}

ARCHIVE_MAYBE = {
    ".zip", ".tar", ".gz", ".tgz", ".7z"
}


def classify_suffix(suffix):
    if suffix in TEXT_FIRST_PASS:
        return "text_first_pass"
    if suffix in TEXT_SECOND_PASS:
        return "text_second_pass"
    if suffix in CODE:
        return "code"
    if suffix in MEDIA_IGNORE:
        return "media_ignore"
    if suffix in ARCHIVE_MAYBE:
        return "archive_maybe"
    return "unknown"


def classify_inventory(inventory):
    extension_counts = inventory["extensions"]

    categories = Counter()
    extension_categories = {}

    for suffix, count in extension_counts.items():
        category = classify_suffix(suffix)
        categories[category] += count
        extension_categories[suffix] = {
            "count": count,
            "category": category,
        }

    return {
        "classification_time": datetime.now().isoformat(timespec="seconds"),
        "source_inventory_time": inventory.get("scan_time"),
        "num_files": inventory["num_files"],
        "total_bytes": inventory["total_bytes"],
        "categories": dict(categories.most_common()),
        "extensions": extension_categories,
    }


def print_classification(result):
    print("=" * 70)
    print("Department LLM Corpus Classification")
    print("=" * 70)
    print()
    print(f"Files classified : {result['num_files']:,}")
    print()

    print("Categories")
    print("-" * 70)
    for category, count in result["categories"].items():
        pct = 100.0 * count / result["num_files"]
        print(f"{category:20} {count:10,d}   {pct:6.2f}%")
    print()

    print("Extensions by Category")
    print("-" * 70)

    by_category = {}
    for suffix, info in result["extensions"].items():
        by_category.setdefault(info["category"], []).append((suffix, info["count"]))

    for category, items in sorted(by_category.items()):
        print()
        print(category)
        print("~" * len(category))
        for suffix, count in sorted(items, key=lambda x: x[1], reverse=True):
            print(f"  {suffix:12} {count:8,d}")


def load_latest_inventory(log_dir):
    log_dir = Path(log_dir)
    files = sorted(log_dir.glob("inventory_*.json"))

    if not files:
        raise FileNotFoundError(f"No inventory_*.json files found in {log_dir}")

    latest = files[-1]

    with latest.open("r", encoding="utf-8") as f:
        return json.load(f), latest


def write_classification(result, log_dir):
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outpath = log_dir / f"classification_{timestamp}.json"

    with outpath.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return outpath


def run_classification(log_dir):
    inventory, inventory_path = load_latest_inventory(log_dir)

    print(f"Using inventory file: {inventory_path}")
    print()

    result = classify_inventory(inventory)
    print_classification(result)

    outpath = write_classification(result, log_dir)
    print()
    print(f"Classification JSON written to: {outpath}")

    return result
