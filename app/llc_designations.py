"""Governed, effective-dated Liberal Learning Curriculum designations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Any, Iterable

import yaml

from app.academic_terms import academic_term_sort_key


DEFAULT_LLC_DESIGNATION_REGISTRY = (
    Path(__file__).resolve().parents[1] / "config" / "llc_designations.yaml"
)
VALID_INCLUSION_RULES = {"any_matching_token"}
VALID_COUNTING_RULES = {"count_section_once"}


@dataclass(frozen=True)
class LLCDesignation:
    code: str
    name: str
    category: str
    rationale: str | None = None


@dataclass(frozen=True)
class LLCDesignationMatch:
    code: str
    name: str
    category: str


@dataclass(frozen=True)
class LLCDesignationResult:
    policy_id: str
    raw_value: str | None
    normalized_tokens: tuple[str, ...]
    matched_designations: tuple[LLCDesignationMatch, ...]
    unknown_tokens: tuple[str, ...]

    @property
    def included(self) -> bool:
        return bool(self.matched_designations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "raw_value": self.raw_value,
            "normalized_tokens": list(self.normalized_tokens),
            "matched_designations": [
                asdict(item) for item in self.matched_designations
            ],
            "unknown_tokens": list(self.unknown_tokens),
        }


@dataclass(frozen=True)
class LLCDesignationPolicy:
    schema_version: str
    policy_id: str
    title: str
    effective_start_term: str | None
    effective_end_term: str | None
    inclusion_rule: str
    counting_rule: str
    designations: tuple[LLCDesignation, ...]

    def applies_to(self, term: str) -> bool:
        key = academic_term_sort_key(term)
        if key[0] != 0:
            raise ValueError(f"Unsupported academic term: {term}")
        if (
            self.effective_start_term
            and key < academic_term_sort_key(self.effective_start_term)
        ):
            return False
        if (
            self.effective_end_term
            and key > academic_term_sort_key(self.effective_end_term)
        ):
            return False
        return True

    def classify(self, value: Any) -> LLCDesignationResult:
        raw = str(value or "").strip() or None
        tokens = tuple(sorted({
            token.upper()
            for token in re.findall(r"[A-Za-z0-9]+", raw or "")
        }))
        by_code = {item.code: item for item in self.designations}
        matches = tuple(
            LLCDesignationMatch(code, by_code[code].name, by_code[code].category)
            for code in tokens if code in by_code
        )
        return LLCDesignationResult(
            policy_id=self.policy_id,
            raw_value=raw,
            normalized_tokens=tokens,
            matched_designations=matches,
            unknown_tokens=tuple(code for code in tokens if code not in by_code),
        )


class LLCDesignationRegistry:
    """Loads one or more non-overlapping YAML policy documents."""

    def __init__(self, policies: Iterable[LLCDesignationPolicy], source_path=None):
        self.policies = tuple(policies)
        self.source_path = Path(source_path) if source_path else None
        self.validate()

    @classmethod
    def load(
        cls, path: Path = DEFAULT_LLC_DESIGNATION_REGISTRY
    ) -> "LLCDesignationRegistry":
        source = Path(path)
        documents = tuple(
            item for item in yaml.safe_load_all(source.read_text(encoding="utf-8"))
            if item
        )
        return cls((_policy_from_dict(item) for item in documents), source)

    def policy_for_term(self, term: str) -> LLCDesignationPolicy:
        matches = tuple(item for item in self.policies if item.applies_to(term))
        if len(matches) != 1:
            raise ValueError(
                f"Expected exactly one LLC policy for {term}; found {len(matches)}"
            )
        return matches[0]

    def classify(self, value: Any, term: str) -> LLCDesignationResult:
        return self.policy_for_term(term).classify(value)

    def validate(self) -> None:
        if not self.policies:
            raise ValueError("LLC designation registry has no policies")
        policy_ids = [item.policy_id for item in self.policies]
        if len(policy_ids) != len(set(policy_ids)):
            raise ValueError("Duplicate LLC policy_id")
        for policy in self.policies:
            if policy.inclusion_rule not in VALID_INCLUSION_RULES:
                raise ValueError(f"Unsupported LLC inclusion rule: {policy.inclusion_rule}")
            if policy.counting_rule not in VALID_COUNTING_RULES:
                raise ValueError(f"Unsupported LLC counting rule: {policy.counting_rule}")
            codes = [item.code for item in policy.designations]
            if len(codes) != len(set(codes)):
                raise ValueError(f"Duplicate designation in {policy.policy_id}")


def _policy_from_dict(payload: dict[str, Any]) -> LLCDesignationPolicy:
    designations = []
    for category, values in (payload.get("designations") or {}).items():
        for code, item in (values or {}).items():
            designations.append(LLCDesignation(
                code=str(code).strip().upper(),
                name=str((item or {}).get("name") or "").strip(),
                category=str(category),
                rationale=str((item or {}).get("rationale") or "").strip() or None,
            ))
    period = payload.get("effective_period") or {}
    return LLCDesignationPolicy(
        schema_version=str(payload.get("schema_version", "1")),
        policy_id=str(payload.get("policy_id") or "").strip(),
        title=str(payload.get("title") or "").strip(),
        effective_start_term=period.get("start_term"),
        effective_end_term=period.get("end_term"),
        inclusion_rule=str(payload.get("inclusion_rule") or ""),
        counting_rule=str(payload.get("counting_rule") or ""),
        designations=tuple(sorted(designations, key=lambda item: item.code)),
    )


__all__ = [
    "DEFAULT_LLC_DESIGNATION_REGISTRY", "LLCDesignation",
    "LLCDesignationMatch", "LLCDesignationPolicy", "LLCDesignationRegistry",
    "LLCDesignationResult",
]
