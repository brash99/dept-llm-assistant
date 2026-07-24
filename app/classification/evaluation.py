"""Fixture-driven evaluation for semantic classification and policy decisions."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

import yaml

from app.classification.classifiers import DeterministicSemanticClassifier
from app.classification.contracts import ClassificationMethod
from app.classification.policy import (
    AuditCandidate,
    AuditPolicy,
    ClassificationDisposition,
    ClassificationGovernor,
)
from app.knowledge import KnowledgeObject


@dataclass(frozen=True)
class ExpectedAssertion:
    field_name: str
    value: Any

    @property
    def key(self) -> str:
        return _assertion_key(self.field_name, self.value)


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    fixture: Mapping[str, Any]
    expected_assertions: Tuple[ExpectedAssertion, ...] = ()
    acceptable_assertions: Tuple[ExpectedAssertion, ...] = ()
    forbidden_assertions: Tuple[ExpectedAssertion, ...] = ()
    expected_abstentions: Tuple[str, ...] = ()
    expected_conflict_fields: Tuple[str, ...] = ()
    expected_classifier_method: Optional[ClassificationMethod] = None
    notes: Optional[str] = None


@dataclass
class MetricBucket:
    proposed: int = 0
    expected: int = 0
    true_positive: int = 0
    false_positive: int = 0
    false_negative: int = 0

    @property
    def precision(self) -> float:
        return self.true_positive / self.proposed if self.proposed else 0.0

    @property
    def recall(self) -> float:
        return self.true_positive / self.expected if self.expected else 1.0

    @property
    def f1(self) -> float:
        denominator = self.precision + self.recall
        return 2 * self.precision * self.recall / denominator if denominator else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposed": self.proposed,
            "expected": self.expected,
            "true_positive": self.true_positive,
            "false_positive": self.false_positive,
            "false_negative": self.false_negative,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
        }


@dataclass
class EvaluationMetrics:
    number_of_cases: int = 0
    number_of_assertions_proposed: int = 0
    number_of_cases_classified: int = 0
    number_of_abstentions: int = 0
    false_positive_count: int = 0
    forbidden_assertion_count: int = 0
    auto_accepted_assertions: int = 0
    review_assertions: int = 0
    conflict_assertions: int = 0
    audited_cases: int = 0
    exact: MetricBucket = field(default_factory=MetricBucket)
    by_field: Dict[str, MetricBucket] = field(default_factory=dict)
    by_method: Dict[str, MetricBucket] = field(default_factory=dict)
    by_object_type: Dict[str, MetricBucket] = field(default_factory=dict)

    @property
    def coverage(self) -> float:
        return (
            self.number_of_cases_classified / self.number_of_cases
            if self.number_of_cases else 0.0
        )

    @property
    def abstention_rate(self) -> float:
        return self.number_of_abstentions / self.number_of_cases if self.number_of_cases else 0.0

    @property
    def auto_accept_rate(self) -> float:
        return self.auto_accepted_assertions / self.number_of_assertions_proposed if self.number_of_assertions_proposed else 0.0

    @property
    def review_rate(self) -> float:
        return self.review_assertions / self.number_of_assertions_proposed if self.number_of_assertions_proposed else 0.0

    @property
    def conflict_rate(self) -> float:
        return self.conflict_assertions / self.number_of_assertions_proposed if self.number_of_assertions_proposed else 0.0

    @property
    def audit_selection_rate(self) -> float:
        return self.audited_cases / self.number_of_cases_classified if self.number_of_cases_classified else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "number_of_cases": self.number_of_cases,
            "number_of_assertions_proposed": self.number_of_assertions_proposed,
            "exact_match_precision": self.exact.precision,
            "exact_match_recall": self.exact.recall,
            "f1": self.exact.f1,
            "coverage": self.coverage,
            "abstention_rate": self.abstention_rate,
            "false_positive_count": self.false_positive_count,
            "forbidden_assertion_count": self.forbidden_assertion_count,
            "auto_accept_rate": self.auto_accept_rate,
            "review_rate": self.review_rate,
            "conflict_rate": self.conflict_rate,
            "audit_selection_rate": self.audit_selection_rate,
            "by_field": _buckets_to_dict(self.by_field),
            "by_classifier_method": _buckets_to_dict(self.by_method),
            "by_object_type": _buckets_to_dict(self.by_object_type),
        }


@dataclass(frozen=True)
class CaseEvaluation:
    case_id: str
    object_type: str
    classifier_name: Optional[str]
    proposed_assertions: Tuple[Dict[str, Any], ...]
    dispositions: Mapping[str, str]
    missing_expected: Tuple[str, ...]
    false_positives: Tuple[str, ...]
    forbidden_found: Tuple[str, ...]
    abstention_reasons: Tuple[str, ...]
    conflict_fields: Tuple[str, ...]
    failures: Tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.failures

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "object_type": self.object_type,
            "classifier_name": self.classifier_name,
            "passed": self.passed,
            "proposed_assertions": list(self.proposed_assertions),
            "dispositions": dict(self.dispositions),
            "missing_expected": list(self.missing_expected),
            "false_positives": list(self.false_positives),
            "forbidden_found": list(self.forbidden_found),
            "abstention_reasons": list(self.abstention_reasons),
            "conflict_fields": list(self.conflict_fields),
            "failures": list(self.failures),
        }


@dataclass(frozen=True)
class QualityGates:
    fail_on_forbidden: bool = True
    minimum_precision: Optional[float] = 1.0
    minimum_coverage: Optional[float] = None
    require_cited_auto_acceptance: bool = True
    prevent_conflicted_auto_application: bool = True


@dataclass
class EvaluationReport:
    metrics: EvaluationMetrics
    cases: Tuple[CaseEvaluation, ...]
    audit_selection: Mapping[str, Any]
    quality_gate_failures: Tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.quality_gate_failures and all(case.passed for case in self.cases)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "metrics": self.metrics.to_dict(),
            "quality_gate_failures": list(self.quality_gate_failures),
            "audit_selection": dict(self.audit_selection),
            "cases": [case.to_dict() for case in self.cases],
        }

    def to_text(self, verbose: bool = False) -> str:
        values = self.metrics.to_dict()
        lines = [
            "Semantic Classification Evaluation",
            f"Cases: {self.metrics.number_of_cases}",
            f"Assertions proposed: {self.metrics.number_of_assertions_proposed}",
            f"Exact precision: {values['exact_match_precision']:.3f}",
            f"Exact recall: {values['exact_match_recall']:.3f}",
            f"F1: {values['f1']:.3f}",
            f"Coverage: {values['coverage']:.3f}",
            f"Abstention rate: {values['abstention_rate']:.3f}",
            f"Auto-accept rate: {values['auto_accept_rate']:.3f}",
            f"Review rate: {values['review_rate']:.3f}",
            f"Conflict rate: {values['conflict_rate']:.3f}",
            f"Audit-selection rate: {values['audit_selection_rate']:.3f}",
            f"Forbidden assertions: {self.metrics.forbidden_assertion_count}",
        ]
        if self.quality_gate_failures:
            lines.append("Quality gate failures:")
            lines.extend(f"- {failure}" for failure in self.quality_gate_failures)
        if verbose:
            lines.append("Cases:")
            for case in self.cases:
                status = "PASS" if case.passed else "FAIL"
                lines.append(f"- {status} {case.case_id}")
                lines.extend(f"  - {failure}" for failure in case.failures)
            if self.audit_selection.get("selected_keys"):
                lines.append("Audit selections:")
                lines.extend(
                    f"- {key}" for key in self.audit_selection["selected_keys"]
                )
        return "\n".join(lines)


def load_evaluation_cases(path: Path) -> Tuple[EvaluationCase, ...]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    records = payload.get("cases")
    if not isinstance(records, list):
        raise ValueError("Classification evaluation file must contain a cases list")
    cases = []
    seen = set()
    for record in records:
        case_id = str(record.get("case_id", "")).strip()
        if not case_id or case_id in seen:
            raise ValueError("Evaluation case IDs must be nonempty and unique")
        seen.add(case_id)
        fixture = record.get("fixture")
        if not isinstance(fixture, Mapping) or not fixture.get("object_type"):
            raise ValueError(f"Case {case_id!r} requires a fixture object_type")
        cases.append(
            EvaluationCase(
                case_id=case_id,
                fixture=dict(fixture),
                expected_assertions=_load_expected(record.get("expected_assertions")),
                acceptable_assertions=_load_expected(record.get("acceptable_assertions")),
                forbidden_assertions=_load_expected(record.get("forbidden_assertions")),
                expected_abstentions=tuple(record.get("expected_abstentions") or ()),
                expected_conflict_fields=tuple(record.get("expected_conflict_fields") or ()),
                expected_classifier_method=(
                    ClassificationMethod(record["expected_classifier_method"])
                    if record.get("expected_classifier_method") else None
                ),
                notes=record.get("notes"),
            )
        )
    return tuple(cases)


class ClassificationEvaluationService:
    def __init__(
        self,
        governor: Optional[ClassificationGovernor] = None,
        audit_policy: Optional[AuditPolicy] = None,
    ) -> None:
        self.governor = governor or ClassificationGovernor(
            (DeterministicSemanticClassifier(),)
        )
        self.audit_policy = audit_policy or AuditPolicy()

    def evaluate(
        self,
        cases: Sequence[EvaluationCase],
        *,
        quality_gates: Optional[QualityGates] = None,
    ) -> EvaluationReport:
        gates = quality_gates or QualityGates()
        metrics = EvaluationMetrics(number_of_cases=len(cases))
        results = []
        audit_candidates = []
        decisions = []
        for case in cases:
            obj = _build_fixture(case)
            governed = self.governor.classify(obj)
            result = self._evaluate_case(case, obj, governed, metrics)
            results.append(result)
            if governed.decision is not None:
                decisions.append(governed.decision)
                audit_candidates.append(AuditCandidate(governed.decision, obj.object_type))
        audit = self.audit_policy.select(audit_candidates)
        metrics.audited_cases = len(audit.selected_keys)
        failures = _quality_gate_failures(metrics, decisions, gates)
        return EvaluationReport(metrics, tuple(results), audit.to_dict(), tuple(failures))

    def _evaluate_case(self, case, obj, governed, metrics) -> CaseEvaluation:
        expected = {item.key: item for item in case.expected_assertions}
        acceptable = {item.key for item in case.acceptable_assertions}
        forbidden = {item.key for item in case.forbidden_assertions}
        proposed = {}
        dispositions = {}
        conflicts = set()
        abstentions = []
        classifier_name = None
        method_names = set()

        if governed.abstention is not None:
            metrics.number_of_abstentions += 1
            abstentions = [reason.code for reason in governed.abstention.reasons]
        else:
            metrics.number_of_cases_classified += 1
            classifier_name = governed.proposal.classifier_name
            for decision in governed.decision.assertion_decisions:
                assertion = decision.assertion
                key = _assertion_key(assertion.field_name, assertion.value)
                proposed[key] = assertion
                dispositions[assertion.field_name] = decision.disposition.value
                method_names.add(assertion.classification_method.value)
                metrics.number_of_assertions_proposed += 1
                if decision.disposition in {
                    ClassificationDisposition.AUTO_ACCEPT,
                    ClassificationDisposition.ACCEPT_WITH_AUDIT,
                }:
                    metrics.auto_accepted_assertions += 1
                elif decision.disposition == ClassificationDisposition.REVIEW:
                    metrics.review_assertions += 1
                elif decision.disposition == ClassificationDisposition.CONFLICT:
                    metrics.conflict_assertions += 1
                    conflicts.add(assertion.field_name)

        proposed_keys = set(proposed)
        expected_keys = set(expected)
        true_positive = proposed_keys & expected_keys
        false_positive = proposed_keys - expected_keys - acceptable
        missing = expected_keys - proposed_keys
        forbidden_found = proposed_keys & forbidden
        metrics.false_positive_count += len(false_positive)
        metrics.forbidden_assertion_count += len(forbidden_found)
        _update_bucket(metrics.exact, len(proposed_keys - acceptable), len(expected_keys), len(true_positive), len(false_positive), len(missing))

        for field_name in {item.field_name for item in case.expected_assertions} | {item.field_name for item in proposed.values()}:
            bucket = metrics.by_field.setdefault(field_name, MetricBucket())
            field_proposed = {key for key, item in proposed.items() if item.field_name == field_name and key not in acceptable}
            field_expected = {key for key, item in expected.items() if item.field_name == field_name}
            _update_bucket(bucket, len(field_proposed), len(field_expected), len(field_proposed & field_expected), len(field_proposed - field_expected), len(field_expected - field_proposed))
        object_bucket = metrics.by_object_type.setdefault(obj.object_type, MetricBucket())
        _update_bucket(object_bucket, len(proposed_keys - acceptable), len(expected_keys), len(true_positive), len(false_positive), len(missing))
        for method in method_names or {"abstain"}:
            bucket = metrics.by_method.setdefault(method, MetricBucket())
            method_proposed = {key for key, item in proposed.items() if item.classification_method.value == method and key not in acceptable}
            method_expected = (
                expected_keys
                if case.expected_classifier_method is not None
                and case.expected_classifier_method.value == method
                else set()
            )
            _update_bucket(
                bucket,
                len(method_proposed),
                len(method_expected),
                len(method_proposed & method_expected),
                len(method_proposed - method_expected),
                len(method_expected - method_proposed),
            )

        failures = []
        if missing:
            failures.append(f"Missing expected assertions: {sorted(missing)}")
        if false_positive:
            failures.append(f"Unexpected assertions: {sorted(false_positive)}")
        if set(case.expected_abstentions) != set(abstentions):
            failures.append(f"Expected abstentions {sorted(case.expected_abstentions)}, got {sorted(abstentions)}")
        if set(case.expected_conflict_fields) != conflicts:
            failures.append(f"Expected conflicts {sorted(case.expected_conflict_fields)}, got {sorted(conflicts)}")
        if case.expected_classifier_method and method_names != {case.expected_classifier_method.value}:
            failures.append(f"Expected method {case.expected_classifier_method.value}, got {sorted(method_names)}")

        return CaseEvaluation(
            case.case_id,
            obj.object_type,
            classifier_name,
            tuple(item.to_dict() for item in proposed.values()),
            dispositions,
            tuple(sorted(missing)),
            tuple(sorted(false_positive)),
            tuple(sorted(forbidden_found)),
            tuple(sorted(abstentions)),
            tuple(sorted(conflicts)),
            tuple(failures),
        )


def _build_fixture(case: EvaluationCase) -> KnowledgeObject:
    fixture = dict(case.fixture)
    object_id = str(fixture.pop("id", f"fixture:{case.case_id}"))
    object_type = str(fixture.pop("object_type"))
    metadata = dict(fixture.pop("metadata", {}) or {})
    existing = fixture.pop("existing_semantic_identity", None)
    if existing:
        metadata["semantic_identity"] = existing
    source = dict(fixture.pop("source", {}) or {})
    obj = KnowledgeObject(
        id=object_id,
        object_type=object_type,
        title=str(fixture.pop("title", case.case_id)),
        text=str(fixture.pop("text", "Evaluation fixture")),
        metadata=metadata,
        source=source,
    )
    for name, value in fixture.items():
        setattr(obj, name, value)
    return obj


def _load_expected(values) -> Tuple[ExpectedAssertion, ...]:
    return tuple(
        ExpectedAssertion(str(value["field_name"]), value.get("value"))
        for value in values or ()
    )


def _assertion_key(field_name: str, value: Any) -> str:
    return f"{field_name}={json.dumps(value, sort_keys=True, separators=(',', ':'))}"


def _update_bucket(bucket, proposed, expected, true_positive, false_positive, false_negative):
    bucket.proposed += proposed
    bucket.expected += expected
    bucket.true_positive += true_positive
    bucket.false_positive += false_positive
    bucket.false_negative += false_negative


def _buckets_to_dict(values: Mapping[str, MetricBucket]) -> Dict[str, Any]:
    return {key: bucket.to_dict() for key, bucket in sorted(values.items())}


def _quality_gate_failures(metrics, decisions, gates) -> list[str]:
    failures = []
    if gates.fail_on_forbidden and metrics.forbidden_assertion_count:
        failures.append(f"Forbidden assertions found: {metrics.forbidden_assertion_count}")
    if gates.minimum_precision is not None and metrics.exact.precision < gates.minimum_precision:
        failures.append(f"Precision {metrics.exact.precision:.3f} is below {gates.minimum_precision:.3f}")
    if gates.minimum_coverage is not None and metrics.coverage < gates.minimum_coverage:
        failures.append(f"Coverage {metrics.coverage:.3f} is below {gates.minimum_coverage:.3f}")
    if gates.require_cited_auto_acceptance:
        uncited = [
            item.assertion.field_name
            for decision in decisions
            for item in decision.assertion_decisions
            if item.accepted and not item.assertion.supporting_evidence
        ]
        if uncited:
            failures.append(f"Auto-accepted assertions without citations: {uncited}")
    if gates.prevent_conflicted_auto_application:
        conflicted_accepted = [
            item.assertion.field_name
            for decision in decisions
            for item in decision.assertion_decisions
            if item.conflicts and item.accepted
        ]
        if conflicted_accepted:
            failures.append(f"Conflicted assertions accepted: {conflicted_accepted}")
    return failures


__all__ = [
    "CaseEvaluation",
    "ClassificationEvaluationService",
    "EvaluationCase",
    "EvaluationMetrics",
    "EvaluationReport",
    "ExpectedAssertion",
    "MetricBucket",
    "QualityGates",
    "load_evaluation_cases",
]
