"""Operational population of Semantic Identity across Knowledge Object files."""

from __future__ import annotations

import copy
import json
import os
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from app.classification.classifiers import DeterministicSemanticClassifier
from app.classification.contracts import (
    ClassificationAssertion,
    ClassificationConfidence,
    ClassificationMethod,
    EvidenceCitation,
)
from app.classification.policy import (
    AssertionDecision,
    AuditCandidate,
    AuditPolicy,
    ClassificationDecision,
    ClassificationDisposition,
    ClassificationGovernor,
    GovernedClassificationResult,
    POLICY_VERSION,
    PolicyReason,
)
from app.knowledge import KnowledgeObject, load_knowledge_object


MANIFEST_NAME = "classification_manifest.jsonl"
QUEUE_NAMES = {
    "review": "review_required.jsonl",
    "conflict": "conflicts.jsonl",
    "abstention": "abstentions.jsonl",
    "unsupported": "unsupported_objects.jsonl",
    "audit": "audit_sample.jsonl",
}
IDENTITY_FIELD_NAMES = (
    "object_type",
    "institutional_entities",
    "authority",
    "decision_domains",
    "temporal_scope",
    "organizational_relationships",
    "institutional_relevance",
)


@dataclass(frozen=True)
class CorpusClassificationOptions:
    input_roots: Tuple[Path, ...]
    report_dir: Path
    apply: bool = False
    limit: Optional[int] = None
    object_types: Tuple[str, ...] = ()
    knowledge_object_ids: Tuple[str, ...] = ()
    resume: bool = False
    verbose: bool = False

    @property
    def mode(self) -> str:
        return "apply" if self.apply else "dry_run"


@dataclass
class CoverageCounter:
    processed: int = 0
    classified: int = 0
    changed: int = 0
    unchanged: int = 0
    unsupported: int = 0
    conflicted: int = 0
    reviewed: int = 0
    abstained: int = 0
    audited: int = 0
    failed: int = 0
    resumed: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "processed": self.processed,
            "classified": self.classified,
            "changed": self.changed,
            "unchanged": self.unchanged,
            "unsupported": self.unsupported,
            "conflicted": self.conflicted,
            "reviewed": self.reviewed,
            "abstained": self.abstained,
            "audited": self.audited,
            "failed": self.failed,
            "resumed": self.resumed,
        }


@dataclass
class CorpusClassificationReport:
    mode: str
    timestamp: str
    input_roots: Tuple[str, ...]
    manifest_path: str
    overall: CoverageCounter = field(default_factory=CoverageCounter)
    field_metrics: Dict[str, Counter] = field(default_factory=dict)
    by_object_type: Dict[str, Counter] = field(default_factory=dict)
    by_classifier: Dict[str, Counter] = field(default_factory=dict)
    institutional_entities: Counter[str] = field(default_factory=Counter)
    audit_selection: Dict[str, Any] = field(default_factory=dict)
    failures: list[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        classified = self.overall.classified
        field_metrics = {}
        for name in IDENTITY_FIELD_NAMES:
            counts = Counter(self.field_metrics.get(name, {}))
            counts["coverage"] = (
                counts.get("present_after", 0) / classified if classified else 0.0
            )
            field_metrics[name] = dict(sorted(counts.items()))
        return {
            "mode": self.mode,
            "timestamp": self.timestamp,
            "input_roots": list(self.input_roots),
            "policy_version": POLICY_VERSION,
            "manifest_path": self.manifest_path,
            "overall": self.overall.to_dict(),
            "field_metrics": field_metrics,
            "by_object_type": _nested_counters(self.by_object_type),
            "by_classifier": _nested_counters(self.by_classifier),
            "institutional_entities": dict(
                sorted(self.institutional_entities.items())
            ),
            "audit_selection": self.audit_selection,
            "failures": self.failures,
        }

    def to_markdown(self) -> str:
        payload = self.to_dict()
        overall = payload["overall"]
        lines = [
            "# Semantic Corpus Population Report",
            "",
            f"- Mode: `{self.mode}`",
            f"- Timestamp: `{self.timestamp}`",
            f"- Policy version: `{POLICY_VERSION}`",
            "",
            "## Overall",
            "",
            "| Measure | Count |",
            "|---|---:|",
        ]
        lines.extend(
            f"| {name.replace('_', ' ').title()} | {value} |"
            for name, value in overall.items()
        )
        lines.extend(
            [
                "",
                "## Semantic Field Coverage",
                "",
                "| Field | Present After | Coverage | Auto Accepted | Audit Accepted | Review | Abstain | Conflict |",
                "|---|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for name, values in payload["field_metrics"].items():
            lines.append(
                f"| {name} | {values.get('present_after', 0)} | "
                f"{values.get('coverage', 0.0):.1%} | "
                f"{values.get('auto_accept', 0)} | "
                f"{values.get('accept_with_audit', 0)} | "
                f"{values.get('review', 0)} | {values.get('abstain', 0)} | "
                f"{values.get('conflict', 0)} |"
            )
        lines.extend(_counter_section("Coverage by Object Type", payload["by_object_type"]))
        lines.extend(_counter_section("Classifier Contribution", payload["by_classifier"]))
        lines.extend(
            [
                "",
                "## Institutional Entities Represented",
                "",
            ]
        )
        if payload["institutional_entities"]:
            lines.extend(
                f"- `{name}`: {count}"
                for name, count in payload["institutional_entities"].items()
            )
        else:
            lines.append("No institutional entities were represented.")
        if self.failures:
            lines.extend(["", "## Failures", ""])
            lines.extend(
                f"- `{item['relative_path']}`: {item['error']}"
                for item in self.failures
            )
        return "\n".join(lines) + "\n"


class SemanticCorpusPopulationService:
    """Classify normalized files and optionally persist policy-approved identity."""

    def __init__(
        self,
        *,
        governor: Optional[ClassificationGovernor] = None,
        audit_policy: Optional[AuditPolicy] = None,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        classifier = DeterministicSemanticClassifier()
        self.governor = governor or ClassificationGovernor((classifier,))
        self.audit_policy = audit_policy or AuditPolicy()
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def run(self, options: CorpusClassificationOptions) -> CorpusClassificationReport:
        timestamp = self.clock().isoformat()
        report_dir = Path(options.report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = report_dir / MANIFEST_NAME
        existing_records = _read_manifest(manifest_path) if options.resume else []
        completed = {
            str(record["knowledge_object_id"])
            for record in existing_records
            if record.get("application_mode") == options.mode
            and record.get("knowledge_object_id")
        }
        report = CorpusClassificationReport(
            mode=options.mode,
            timestamp=timestamp,
            input_roots=tuple(str(Path(root)) for root in options.input_roots),
            manifest_path=str(manifest_path),
            field_metrics={name: Counter() for name in IDENTITY_FIELD_NAMES},
        )
        paths = discover_knowledge_object_paths(options.input_roots)
        audit_candidates = []
        audit_candidates_by_key = {}
        audit_records = {}
        new_audit_keys = set()
        for record in existing_records:
            if record.get("application_mode") != options.mode:
                continue
            candidate = _audit_candidate_from_manifest(record)
            if candidate is not None:
                audit_candidates.append(candidate)
                audit_candidates_by_key[candidate.key] = candidate
                audit_records[candidate.key] = _audit_record_from_manifest(record)
        mode = "a" if options.resume else "w"
        queue_handles = {
            name: (report_dir / filename).open(mode, encoding="utf-8")
            for name, filename in QUEUE_NAMES.items()
            if name != "audit"
        }
        audit_path = report_dir / QUEUE_NAMES["audit"]
        audit_path.write_text("", encoding="utf-8")
        try:
            with manifest_path.open(mode, encoding="utf-8") as manifest_handle:
                for path in paths:
                    if options.limit is not None and report.overall.processed >= options.limit:
                        break
                    relative_path = _relative_to_roots(path, options.input_roots)
                    try:
                        obj = load_knowledge_object(path)
                    except Exception as exc:
                        report.overall.failed += 1
                        report.failures.append(
                            {"relative_path": relative_path, "error": f"{type(exc).__name__}: {exc}"}
                        )
                        continue
                    if options.object_types and obj.object_type not in options.object_types:
                        continue
                    if options.knowledge_object_ids and obj.id not in options.knowledge_object_ids:
                        continue
                    if obj.id in completed:
                        report.overall.resumed += 1
                        continue

                    report.overall.processed += 1
                    governed = self.governor.classify(obj, apply=False)
                    record, preview = self._record_for(
                        obj, path, relative_path, governed, options, timestamp
                    )
                    if governed.decision is not None:
                        candidate = AuditCandidate(governed.decision, obj.object_type)
                        audit_candidates.append(candidate)
                        audit_candidates_by_key[candidate.key] = candidate
                        new_audit_keys.add(candidate.key)
                        audit_records[candidate.key] = _audit_record(
                            obj, relative_path, governed.decision
                        )
                    self._update_report(report, obj, governed, preview, record)
                    self._write_queues(queue_handles, obj, relative_path, governed)

                    if options.apply and record["semantic_identity_changed"]:
                        governed.decision.apply_to_knowledge_object(obj)
                        if obj.id != record["knowledge_object_id"]:
                            raise RuntimeError("Knowledge Object ID changed during application")
                        atomic_save_knowledge_object(obj, path)
                    _write_json_line(manifest_handle, record)
                    manifest_handle.flush()
                    if options.verbose:
                        print(
                            f"{report.overall.processed}: {obj.object_type} "
                            f"{relative_path} ({'changed' if record['semantic_identity_changed'] else 'unchanged'})"
                        )
        finally:
            for handle in queue_handles.values():
                handle.close()

        audit = self.audit_policy.select(audit_candidates)
        report.audit_selection = audit.to_dict()
        report.overall.audited = sum(
            key in new_audit_keys for key in audit.selected_keys
        )
        audit_mode = "w"
        for key in audit.selected_keys:
            record = dict(audit_records[key])
            record["audit_flags"] = list(audit.reasons[key])
            _append_json_line(audit_path, record, mode=audit_mode)
            audit_mode = "a"
            candidate = audit_candidates_by_key[key]
            if key in new_audit_keys:
                report.by_object_type[candidate.object_type]["audited"] += 1
                report.by_classifier[candidate.decision.classifier_name]["audited"] += 1
        self._finalize_manifest(manifest_path, audit.reasons)
        summary_path = report_dir / "classification_summary.json"
        markdown_path = report_dir / "classification_report.md"
        _atomic_write_text(
            summary_path,
            json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        )
        _atomic_write_text(markdown_path, report.to_markdown())
        return report

    def _record_for(self, obj, path, relative_path, governed, options, timestamp):
        before_identity = obj.semantic_identity.to_dict() if obj.semantic_identity else None
        preview = copy.deepcopy(obj)
        decision = governed.decision
        if decision is not None and decision.accepted_assertions:
            decision.apply_to_knowledge_object(preview)
        after_identity = preview.semantic_identity.to_dict() if preview.semantic_identity else None
        decisions = decision.assertion_decisions if decision is not None else ()
        classifier_name = (
            governed.proposal.classifier_name if governed.proposal is not None else None
        )
        classifier_version = _classifier_version(self.governor, classifier_name)
        abstentions = []
        if governed.abstention is not None:
            abstentions = [reason.to_dict() for reason in governed.abstention.reasons]
        abstentions.extend(
            _decision_record(item)
            for item in decisions
            if item.disposition == ClassificationDisposition.ABSTAIN
        )
        return {
            "knowledge_object_id": obj.id,
            "relative_path": relative_path,
            "object_type_before": obj.object_type,
            "object_type_after": preview.object_type,
            "accepted_assertions": [
                _decision_record(item) for item in decisions if item.accepted
            ],
            "review_assertions": [
                _decision_record(item)
                for item in decisions
                if item.disposition in {
                    ClassificationDisposition.REVIEW,
                    ClassificationDisposition.REJECT,
                }
            ],
            "abstentions": abstentions,
            "conflicts": [
                _decision_record(item)
                for item in decisions
                if item.disposition == ClassificationDisposition.CONFLICT
            ],
            "audit_flags": [],
            "classifier_versions": (
                {classifier_name: classifier_version} if classifier_name else {}
            ),
            "policy_version": POLICY_VERSION,
            "semantic_identity_changed": before_identity != after_identity,
            "application_mode": options.mode,
            "applied": bool(options.apply and before_identity != after_identity),
            "decision_fingerprint": decision.fingerprint() if decision else None,
            "timestamp": timestamp,
        }, preview

    def _update_report(self, report, obj, governed, preview, record):
        object_counts = report.by_object_type.setdefault(obj.object_type, Counter())
        object_counts["processed"] += 1
        if governed.abstention is not None:
            report.overall.unsupported += 1
            report.overall.abstained += 1
            object_counts["unsupported"] += 1
            return
        report.overall.classified += 1
        object_counts["classified"] += 1
        classifier_name = governed.proposal.classifier_name
        classifier_counts = report.by_classifier.setdefault(classifier_name, Counter())
        classifier_counts["processed"] += 1
        classifier_counts["classified"] += 1
        if record["semantic_identity_changed"]:
            report.overall.changed += 1
            object_counts["changed"] += 1
            classifier_counts["changed"] += 1
        else:
            report.overall.unchanged += 1
            object_counts["unchanged"] += 1
        dispositions = {
            item.disposition for item in governed.decision.assertion_decisions
        }
        if ClassificationDisposition.CONFLICT in dispositions:
            report.overall.conflicted += 1
            object_counts["conflicted"] += 1
            classifier_counts["conflicted"] += 1
        if ClassificationDisposition.REVIEW in dispositions or ClassificationDisposition.REJECT in dispositions:
            report.overall.reviewed += 1
            object_counts["reviewed"] += 1
            classifier_counts["reviewed"] += 1
        if ClassificationDisposition.ABSTAIN in dispositions:
            report.overall.abstained += 1
            object_counts["abstained"] += 1
            classifier_counts["abstained"] += 1
        for item in governed.decision.assertion_decisions:
            report.field_metrics[item.assertion.field_name][item.disposition.value] += 1
        identity = preview.semantic_identity
        if identity is not None:
            serialized = identity.to_dict()
            for field_name in IDENTITY_FIELD_NAMES:
                if _identity_field_present(serialized, field_name):
                    report.field_metrics[field_name]["present_after"] += 1
            for entity in identity.institutional_entities:
                report.institutional_entities[
                    f"{entity.entity_type}:{entity.entity_id}"
                ] += 1

    def _write_queues(self, handles, obj, relative_path, governed):
        if governed.abstention is not None:
            record = {
                "knowledge_object_id": obj.id,
                "relative_path": relative_path,
                "object_type": obj.object_type,
                "field": None,
                "classifier": governed.abstention.classifier_name,
                "confidence": None,
                "reason": [reason.to_dict() for reason in governed.abstention.reasons],
                "citations": [],
                "policy_decision": "abstain",
            }
            _write_json_line(handles["abstention"], record)
            _write_json_line(handles["unsupported"], record)
            return
        for item in governed.decision.assertion_decisions:
            if item.disposition in {
                ClassificationDisposition.REVIEW,
                ClassificationDisposition.REJECT,
            }:
                _write_json_line(handles["review"], _queue_record(obj, relative_path, governed, item))
            elif item.disposition == ClassificationDisposition.CONFLICT:
                _write_json_line(handles["conflict"], _queue_record(obj, relative_path, governed, item))
            elif item.disposition == ClassificationDisposition.ABSTAIN:
                _write_json_line(handles["abstention"], _queue_record(obj, relative_path, governed, item))

    def _finalize_manifest(self, manifest_path, audit_reasons):
        lines = []
        for record in _read_manifest(manifest_path):
            classifier = next(iter(record["classifier_versions"]), None)
            key = (
                f"{record['knowledge_object_id']}:{classifier}"
                if classifier else None
            )
            record["audit_flags"] = list(audit_reasons.get(key, ()))
            lines.append(json.dumps(record, sort_keys=True, separators=(",", ":")))
        _atomic_write_text(
            manifest_path,
            ("\n".join(lines) + "\n") if lines else "",
        )


def discover_knowledge_object_paths(input_roots: Iterable[Path]) -> Tuple[Path, ...]:
    paths = {}
    for root in input_roots:
        root = Path(root)
        if root.is_file() and root.suffix.casefold() == ".json":
            paths[str(root.resolve())] = root
        elif root.is_dir():
            for path in root.rglob("*.json"):
                if path.is_file():
                    paths[str(path.resolve())] = path
    return tuple(paths[key] for key in sorted(paths))


def atomic_save_knowledge_object(obj: KnowledgeObject, output_path: Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    original_mode = output_path.stat().st_mode if output_path.exists() else None
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.", suffix=".tmp", dir=str(output_path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(obj.to_json(indent=2))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if original_mode is not None:
            os.chmod(temporary, original_mode)
        os.replace(temporary, output_path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _read_manifest(path: Path) -> list[Dict[str, Any]]:
    records = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            records.append(record)
    return records


def _audit_candidate_from_manifest(record: Mapping[str, Any]) -> Optional[AuditCandidate]:
    classifier = next(iter(record.get("classifier_versions") or {}), None)
    if not classifier or not record.get("accepted_assertions"):
        return None
    decisions = []
    for category in ("accepted_assertions", "review_assertions", "conflicts"):
        for item in record.get(category) or ():
            if "field" not in item or "value" not in item:
                continue
            assertion = ClassificationAssertion(
                field_name=str(item["field"]),
                value=item.get("value"),
                confidence=ClassificationConfidence.from_dict(item["confidence"]),
                classification_method=ClassificationMethod(
                    item["classification_method"]
                ),
                supporting_evidence=tuple(
                    EvidenceCitation.from_dict(citation)
                    for citation in item.get("citations") or ()
                ),
            )
            decisions.append(
                AssertionDecision(
                    assertion=assertion,
                    disposition=ClassificationDisposition(item["policy_decision"]),
                    reasons=tuple(
                        PolicyReason.from_dict(reason)
                        for reason in item.get("reasons") or ()
                    ),
                )
            )
    decision = ClassificationDecision(
        knowledge_object_id=str(record["knowledge_object_id"]),
        classifier_name=classifier,
        assertion_decisions=tuple(decisions),
    )
    return AuditCandidate(decision, str(record["object_type_before"]))


def _audit_record_from_manifest(record: Mapping[str, Any]) -> Dict[str, Any]:
    accepted = record.get("accepted_assertions") or ()
    return {
        "knowledge_object_id": record["knowledge_object_id"],
        "relative_path": record["relative_path"],
        "object_type": record["object_type_before"],
        "field": [item["field"] for item in accepted],
        "classifier": next(iter(record.get("classifier_versions") or {}), None),
        "confidence": [item["confidence"] for item in accepted],
        "reason": "deterministic_audit_selection",
        "citations": [
            citation
            for item in accepted
            for citation in item.get("citations") or ()
        ],
        "policy_decision": [item["policy_decision"] for item in accepted],
    }


def _classifier_version(governor, classifier_name):
    for classifier in governor.classifiers:
        nested = getattr(classifier, "classifiers", ())
        for candidate in (classifier, *nested):
            if candidate.name == classifier_name:
                return str(getattr(candidate, "version", "unknown"))
    return "unknown"


def _decision_record(item) -> Dict[str, Any]:
    return {
        "field": item.assertion.field_name,
        "value": item.assertion.value,
        "confidence": item.assertion.confidence.to_dict(),
        "classification_method": item.assertion.classification_method.value,
        "citations": [value.to_dict() for value in item.assertion.supporting_evidence],
        "policy_decision": item.disposition.value,
        "reasons": [reason.to_dict() for reason in item.reasons],
        "conflicts": [conflict.to_dict() for conflict in item.conflicts],
    }


def _queue_record(obj, relative_path, governed, item) -> Dict[str, Any]:
    record = _decision_record(item)
    return {
        "knowledge_object_id": obj.id,
        "relative_path": relative_path,
        "object_type": obj.object_type,
        "field": record["field"],
        "classifier": governed.proposal.classifier_name,
        "confidence": record["confidence"],
        "reason": record["reasons"],
        "citations": record["citations"],
        "policy_decision": record["policy_decision"],
        "conflicts": record["conflicts"],
    }


def _audit_record(obj, relative_path, decision: ClassificationDecision) -> Dict[str, Any]:
    return {
        "knowledge_object_id": obj.id,
        "relative_path": relative_path,
        "object_type": obj.object_type,
        "field": [item.field_name for item in decision.accepted_assertions],
        "classifier": decision.classifier_name,
        "confidence": [item.confidence.to_dict() for item in decision.accepted_assertions],
        "reason": "deterministic_audit_selection",
        "citations": [
            citation.to_dict()
            for item in decision.accepted_assertions
            for citation in item.supporting_evidence
        ],
        "policy_decision": [
            item.disposition.value
            for item in decision.assertion_decisions
            if item.accepted
        ],
    }


def _relative_to_roots(path: Path, roots: Sequence[Path]) -> str:
    for root in roots:
        root = Path(root)
        try:
            relative = path.resolve().relative_to(root.resolve())
            return f"{root.name}/{relative.as_posix()}"
        except ValueError:
            continue
    return path.name


def _identity_field_present(identity: Mapping[str, Any], field_name: str) -> bool:
    value = identity.get(field_name)
    return value is not None and value != [] and value != {}


def _nested_counters(values: Mapping[str, Counter]) -> Dict[str, Dict[str, int]]:
    return {key: dict(sorted(counter.items())) for key, counter in sorted(values.items())}


def _counter_section(title: str, values: Mapping[str, Mapping[str, int]]) -> list[str]:
    lines = ["", f"## {title}", ""]
    if not values:
        return lines + ["No records."]
    lines.extend(["| Name | Processed | Classified | Changed |", "|---|---:|---:|---:|"])
    lines.extend(
        f"| {name} | {counts.get('processed', 0)} | {counts.get('classified', 0)} | {counts.get('changed', 0)} |"
        for name, counts in values.items()
    )
    return lines


def _write_json_line(handle, value: Mapping[str, Any]) -> None:
    handle.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def _append_json_line(path: Path, value: Mapping[str, Any], *, mode: str = "a") -> None:
    with Path(path).open(mode, encoding="utf-8") as handle:
        _write_json_line(handle, value)


def _atomic_write_text(path: Path, text: str) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


__all__ = [
    "CorpusClassificationOptions",
    "CorpusClassificationReport",
    "CoverageCounter",
    "SemanticCorpusPopulationService",
    "atomic_save_knowledge_object",
    "discover_knowledge_object_paths",
]
