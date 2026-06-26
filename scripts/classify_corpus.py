#!/usr/bin/env python3

from pathlib import Path

from app.config import load_config
from app.classify import run_classification


def main():
    config = load_config()

    project_root = Path(config["project"]["root"])
    log_dir = project_root / config["storage"]["logs"]

    run_classification(log_dir)


if __name__ == "__main__":
    main()
