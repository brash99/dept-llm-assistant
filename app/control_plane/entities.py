from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


VALID_PROGRAM_STATUSES = {
    "active",
    "inactive",
    "suspended",
    "teach_out",
    "proposed",
}


@dataclass(frozen=True)
class ProgramEntity:
    """
    Factual representation of an institutional academic program.

    This object stores asserted facts only. Similarity, neighborhood,
    relevance, and decision implications are derived by services.
    """

    id: str
    name: str
    status: str
    aliases: List[str] = field(default_factory=list)
    degree_type: Optional[str] = None
    department: Optional[str] = None
    school: Optional[str] = None
    first_catalog_year: Optional[int] = None
    accreditation: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("ProgramEntity.id cannot be empty.")

        if not self.name.strip():
            raise ValueError("ProgramEntity.name cannot be empty.")

        if self.status not in VALID_PROGRAM_STATUSES:
            raise ValueError(
                f"Unsupported program status {self.status!r}. "
                f"Expected one of {sorted(VALID_PROGRAM_STATUSES)}."
            )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProgramEntity":
        return cls(**data)
