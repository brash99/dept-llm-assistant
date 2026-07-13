from pathlib import Path
from typing import Dict, Iterable, List, Optional

import yaml

from app.control_plane.entities import ProgramEntity


class ProgramCatalog:
    """
    Read-only catalog of asserted institutional program facts.
    """

    def __init__(self, programs: Iterable[ProgramEntity]):
        self._programs: List[ProgramEntity] = list(programs)
        self._by_id: Dict[str, ProgramEntity] = {}

        for program in self._programs:
            if program.id in self._by_id:
                raise ValueError(f"Duplicate program id: {program.id}")
            self._by_id[program.id] = program

    @classmethod
    def from_yaml(cls, path: Path) -> "ProgramCatalog":
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Program catalog not found: {path}")

        with path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}

        records = payload.get("programs", [])

        if not isinstance(records, list):
            raise ValueError("'programs' must be a YAML list.")

        return cls(ProgramEntity.from_dict(record) for record in records)

    def all(self) -> List[ProgramEntity]:
        return list(self._programs)

    def get(self, program_id: str) -> Optional[ProgramEntity]:
        return self._by_id.get(program_id)
