#!/usr/bin/env python3

from pathlib import Path

from app.config import load_config
from app.inventory import run_inventory


def main():
    config = load_config()

    project_root = Path(config["project"]["root"])
    raw_drive = project_root / config["storage"]["raw_drive"]
    log_dir = project_root / config["storage"]["logs"]

    run_inventory(raw_drive, log_dir)


if __name__ == "__main__":
    main()
