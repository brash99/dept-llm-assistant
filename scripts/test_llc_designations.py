from dataclasses import replace
from pathlib import Path

import pytest

from app.llc_designations import LLCDesignationRegistry


def test_governed_policy_preserves_categories_and_unknown_tokens():
    result = LLCDesignationRegistry.load().classify(
        " aiwt, WI ; GE ", "2024_fall"
    )
    assert result.included is True
    assert [(item.code, item.category) for item in result.matched_designations] == [
        ("AIWT", "areas_of_inquiry"),
        ("WI", "additional_requirements"),
    ]
    assert result.unknown_tokens == ("GE",)


def test_effective_dated_yaml_documents_select_policy_by_term(tmp_path: Path):
    registry_path = tmp_path / "policies.yaml"
    registry_path.write_text(
        """
schema_version: 1
policy_id: old
title: Old
effective_period: {start_term: null, end_term: 2024_fall}
inclusion_rule: any_matching_token
counting_rule: count_section_once
designations:
  areas: {OLD: {name: Old code}}
---
schema_version: 1
policy_id: new
title: New
effective_period: {start_term: 2025_spring, end_term: null}
inclusion_rule: any_matching_token
counting_rule: count_section_once
designations:
  areas: {NEW: {name: New code}}
""".lstrip(),
        encoding="utf-8",
    )
    registry = LLCDesignationRegistry.load(registry_path)
    assert registry.classify("OLD", "2024_fall").policy_id == "old"
    assert registry.classify("NEW", "2025_spring").policy_id == "new"
    assert registry.classify("NEW", "2024_fall").included is False


def test_overlapping_effective_policies_fail_instead_of_reinterpreting():
    registry = LLCDesignationRegistry.load()
    overlap = replace(registry.policies[0], policy_id="overlapping_policy")
    overlapping_registry = type(registry)(registry.policies + (overlap,))
    with pytest.raises(ValueError, match="exactly one"):
        overlapping_registry.policy_for_term("2024_fall")
