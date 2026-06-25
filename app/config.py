from pathlib import Path
from typing import Union
import yaml


DEFAULT_CONFIG = Path("config/settings.yaml")


def load_config(config_path: Union[str, Path] = DEFAULT_CONFIG) -> dict:
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)
