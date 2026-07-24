"""Deterministic repair of contradictory schedule-source assertions.

The authoritative CSV remains evidence.  This service derives a best-supported
section representation while retaining every published variant and row
reference.  It does not edit source evidence or infer faculty employment.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

from app.academic_terms import academic_term_sort_key


REPAIR_ALGORITHM = "schedule_source_repair"
REPAIR_VERSION = "1.0"


def _unique(values: Iterable[str], *, include_blank: bool = False) -> tuple[str, ...]:
    result = tuple(dict.fromkeys(str(value) for value in values))
    return result if include_blank else tuple(value for value in result if value.strip())


def _status(value: str) -> str:
    return {"full time": "full_time", "adjunct": "adjunct"}.get(
        value.strip().casefold(), "unknown"
    )


def _person_key(value: str) -> str:
    return " ".join(value.split()).casefold()


def _term_key(value: str) -> tuple[int, int, str]:
    """Sort normalized terms chronologically without asserting calendar dates."""
    key = academic_term_sort_key(value)
    # Retain the historical three-element private helper contract.
    return key[1:] if key[0] == 0 else (0, 0, str(value))


def _fingerprint(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ScheduleRepairRow:
    source_row: int
    values: Mapping[str, str]
    raw_record: Mapping[str, Any]

    @property
    def row_hash(self) -> str:
        return _fingerprint(self.raw_record)


@dataclass(frozen=True)
class ScheduleRepairGroup:
    observation_id: str
    academic_term: str
    course_code: str
    instructor: str
    rows: tuple[ScheduleRepairRow, ...]

    def values(self, field: str, *, include_blank: bool = False) -> tuple[str, ...]:
        return _unique(
            (row.values.get(field, "") for row in self.rows),
            include_blank=include_blank,
        )


@dataclass
class ScheduleRepairAnalysis:
    decisions: dict[str, dict[str, Any]]
    manifest_records: list[dict[str, Any]]
    summary: dict[str, Any]


class ScheduleRepairService:
    """Derive auditable repairs from section-, instructor-, and course-level evidence."""

    def __init__(
        self,
        groups: Sequence[ScheduleRepairGroup],
        *,
        source_sha256: str,
        allow_later_term_fallback: bool = False,
    ) -> None:
        self.groups = tuple(groups)
        self.source_sha256 = source_sha256
        self.allow_later_term_fallback = allow_later_term_fallback
        self._terms = sorted({group.academic_term for group in groups}, key=_term_key)
        self._term_position = {term: index for index, term in enumerate(self._terms)}
        self._status_index: dict[tuple[str, str], list[ScheduleRepairGroup]] = defaultdict(list)
        self._title_index: dict[tuple[str, str], list[ScheduleRepairGroup]] = defaultdict(list)
        self._credit_index: dict[tuple[str, str], list[ScheduleRepairGroup]] = defaultdict(list)
        self._status_family_terms: dict[tuple[str, str], list[ScheduleRepairGroup]] = defaultdict(list)
        self._course_family_terms: dict[tuple[str, str], list[ScheduleRepairGroup]] = defaultdict(list)
        for group in self.groups:
            self._status_family_terms[(_person_key(group.instructor), group.academic_term)].append(group)
            self._course_family_terms[(group.course_code.strip().casefold(), group.academic_term)].append(group)
            if self._consistent_status(group) is not None:
                self._status_index[(_person_key(group.instructor), group.academic_term)].append(group)
            if self._single_value(group, "course_title") is not None:
                self._title_index[(group.course_code.strip().casefold(), group.academic_term)].append(group)
            if self._single_value(group, "credits") is not None:
                self._credit_index[(group.course_code.strip().casefold(), group.academic_term)].append(group)

    @staticmethod
    def _consistent_status(group: ScheduleRepairGroup) -> Optional[str]:
        statuses = {_status(value) for value in group.values("instructor_type")}
        statuses.discard("unknown")
        return next(iter(statuses)) if len(statuses) == 1 else None

    @staticmethod
    def _single_value(group: ScheduleRepairGroup, field: str) -> Optional[str]:
        values = group.values(field)
        return values[0] if len(values) == 1 else None

    def _resolution(
        self,
        *,
        resolved: bool,
        method: str,
        confidence: float,
        support: Sequence[ScheduleRepairGroup] = (),
        notes: str,
    ) -> dict[str, Any]:
        return {
            "resolved": resolved,
            "method": method,
            "confidence": confidence,
            "supporting_section_count": len(support),
            "supporting_observation_ids": [item.observation_id for item in support],
            "supporting_terms": list(dict.fromkeys(item.academic_term for item in support)),
            "source_file_sha256": self.source_sha256,
            "notes": notes,
        }

    def _same_term_support(
        self,
        target: ScheduleRepairGroup,
        *,
        family: str,
        value_getter,
    ) -> tuple[list[ScheduleRepairGroup], set[str]]:
        support = [group for group in self._index_for(value_getter).get((family, target.academic_term), ()) if group.observation_id != target.observation_id]
        return support, {value_getter(group) for group in support}

    def _index_for(self, value_getter):
        if value_getter.__name__ == "status_value":
            return self._status_index
        if value_getter.__name__ == "course_value":
            return self._title_index if getattr(value_getter, "field", None) == "course_title" else self._credit_index
        raise ValueError("Unsupported schedule repair value getter")

    def _nearest_term_support(
        self,
        target: ScheduleRepairGroup,
        *,
        family: str,
        value_getter,
        prior: bool,
    ) -> tuple[list[ScheduleRepairGroup], set[str], int, bool]:
        target_position = self._term_position[target.academic_term]
        positions = range(target_position - 1, -1, -1) if prior else range(target_position + 1, len(self._terms))
        for position in positions:
            term = self._terms[position]
            index = self._index_for(value_getter)
            all_index = self._status_family_terms if value_getter.__name__ == "status_value" else self._course_family_terms
            all_support = list(all_index.get((family, term), ()))
            if all_support:
                support = list(index.get((family, term), ()))
                values = {value_getter(group) for group in support}
                return (
                    support or all_support,
                    values,
                    abs(position - target_position),
                    len(support) != len(all_support),
                )
        return [], set(), 0, False

    def _resolve_status(self, target: ScheduleRepairGroup) -> dict[str, Any]:
        published = target.values("instructor_type", include_blank=True)
        nonblank = tuple(value for value in published if value.strip())
        statuses = {_status(value) for value in nonblank}
        known = statuses - {"unknown"}
        conflicting = len(known) > 1
        base = {
            "published_value": nonblank[0] if len(nonblank) == 1 else None,
            "published_values": list(nonblank),
            "normalized_value": next(iter(known)) if len(known) == 1 and "unknown" not in statuses else "unknown",
            "has_blank_value": any(not value.strip() for value in published) or not published,
            "conflicting": conflicting,
        }
        if not conflicting:
            base["resolution"] = self._resolution(
                resolved=len(known) == 1,
                method="direct_source_assertion" if len(known) == 1 else "unknown_source_value",
                confidence=1.0 if len(known) == 1 else 0.0,
                notes="The grouped source rows contain no contradictory known Instructor Type assertions.",
            )
            return base

        def status_value(group: ScheduleRepairGroup) -> Optional[str]:
            return self._consistent_status(group)

        family = _person_key(target.instructor)
        support, values = self._same_term_support(target, family=family, value_getter=status_value)
        if len(values) == 1:
            base["normalized_value"] = next(iter(values))
            base["resolution"] = self._resolution(
                resolved=True,
                method="same_instructor_same_term_consensus",
                confidence=1.0,
                support=support,
                notes="Resolved from internally consistent unambiguous sections for the same instructor and term.",
            )
            return base
        if len(values) > 1:
            base["resolution"] = self._resolution(
                resolved=False, method="unresolved_source_conflict", confidence=0.0,
                support=support,
                notes="Same-term unambiguous sections contain competing Instructor Type assertions.",
            )
            return base

        support, values, distance, ambiguous = self._nearest_term_support(
            target, family=family, value_getter=status_value, prior=True
        )
        if support:
            if len(values) == 1 and not ambiguous:
                base["normalized_value"] = next(iter(values))
                confidence = max(0.65, round(0.90 - 0.05 * (distance - 1), 2))
                base["resolution"] = self._resolution(
                    resolved=True,
                    method="same_instructor_nearest_prior_term",
                    confidence=confidence,
                    support=support,
                    notes="Resolved from the nearest prior term with internally consistent unambiguous sections; confidence declines 0.05 per intervening observed term from 0.90 to a 0.65 floor.",
                )
            else:
                base["resolution"] = self._resolution(
                    resolved=False, method="unresolved_source_conflict", confidence=0.0,
                    support=support,
                    notes="The nearest prior term with evidence is internally contradictory; older terms were not used.",
                )
            return base

        if self.allow_later_term_fallback:
            support, values, distance, ambiguous = self._nearest_term_support(
                target, family=family, value_getter=status_value, prior=False
            )
            if support and len(values) == 1 and not ambiguous:
                base["normalized_value"] = next(iter(values))
                base["resolution"] = self._resolution(
                    resolved=True,
                    method="same_instructor_nearest_later_term",
                    confidence=max(0.50, round(0.70 - 0.05 * (distance - 1), 2)),
                    support=support,
                    notes="Optional fallback from the nearest later internally consistent term.",
                )
                return base

        base["resolution"] = self._resolution(
            resolved=False, method="unresolved_source_conflict", confidence=0.0,
            notes="No conservative same-term or prior-term evidence resolves the source contradiction.",
        )
        return base

    def _resolve_course_field(self, target: ScheduleRepairGroup, field: str) -> dict[str, Any]:
        published = target.values(field)
        result = {"published_values": list(published), "normalized_value": published[0] if len(published) == 1 else None, "conflicting": len(published) > 1}
        if len(published) <= 1:
            result["resolution"] = self._resolution(
                resolved=len(published) == 1, method="direct_source_assertion", confidence=1.0 if published else 0.0,
                notes="The grouped source rows contain no contradictory published values.",
            )
            return result

        def course_value(group: ScheduleRepairGroup) -> Optional[str]:
            return self._single_value(group, field)
        course_value.field = field  # type: ignore[attr-defined]

        family = target.course_code.strip().casefold()
        support, values = self._same_term_support(target, family=family, value_getter=course_value)
        if len(values) == 1:
            result["normalized_value"] = next(iter(values))
            result["resolution"] = self._resolution(
                resolved=True, method="same_course_same_term_consensus", confidence=1.0, support=support,
                notes="Resolved from internally consistent unambiguous sections of the same course and term.",
            )
            return result
        if field == "credits" and len(values) > 1:
            result["resolution"] = self._resolution(
                resolved=False, method="legitimate_variable_credit", confidence=1.0, support=support,
                notes="Other unambiguous sections of the same course and term publish multiple credit values; no scalar was selected.",
            )
            return result
        if len(values) > 1:
            method = "unresolved_course_title_conflict" if field == "course_title" else "unresolved_credit_conflict"
            result["resolution"] = self._resolution(
                resolved=False, method=method, confidence=0.0, support=support,
                notes="Contemporaneous course evidence is internally ambiguous.",
            )
            return result

        support, values, distance, ambiguous = self._nearest_term_support(
            target, family=family, value_getter=course_value, prior=True
        )
        if support and len(values) == 1 and not ambiguous:
            result["normalized_value"] = next(iter(values))
            result["resolution"] = self._resolution(
                resolved=True, method="same_course_nearest_prior_term",
                confidence=max(0.65, round(0.90 - 0.05 * (distance - 1), 2)), support=support,
                notes="Resolved from the nearest prior term with internally consistent unambiguous course evidence.",
            )
            return result
        if field == "credits" and len(values) > 1:
            method = "legitimate_variable_credit"
        else:
            method = "unresolved_course_title_conflict" if field == "course_title" else "unresolved_credit_conflict"
        result["resolution"] = self._resolution(
            resolved=False, method=method, confidence=1.0 if method == "legitimate_variable_credit" else 0.0,
            support=support, notes="No unique contemporaneous or prior course assertion supports a scalar value.",
        )
        return result

    @staticmethod
    def _meeting_patterns(target: ScheduleRepairGroup) -> list[dict[str, Any]]:
        patterns: dict[tuple[str, str, str], dict[str, Any]] = {}
        for row in target.rows:
            key = (
                row.values.get("meeting_days", ""),
                row.values.get("meeting_time", ""),
                row.values.get("location", ""),
            )
            if key not in patterns:
                patterns[key] = {
                    "days_published": key[0] or None,
                    "time_published": key[1] or None,
                    "location_published": key[2] or None,
                    "source_rows": [],
                }
            patterns[key]["source_rows"].append(row.source_row)
        return list(patterns.values())

    def analyze(self) -> ScheduleRepairAnalysis:
        decisions: dict[str, dict[str, Any]] = {}
        manifest: list[dict[str, Any]] = []
        method_counts = {"instructor_type": Counter(), "title": Counter(), "credits": Counter()}
        multiple_meetings = 0
        for group in self.groups:
            instructor_type = self._resolve_status(group)
            title = self._resolve_course_field(group, "course_title")
            credits = self._resolve_course_field(group, "credits")
            meetings = self._meeting_patterns(group)
            if len(meetings) > 1:
                multiple_meetings += 1
            decision = {
                "instructor_type": instructor_type,
                "course_title": title,
                "credits": credits,
                "meeting_patterns": meetings,
                "source_rows": [row.source_row for row in group.rows],
                "source_row_hashes": [row.row_hash for row in group.rows],
                "source_file_sha256": self.source_sha256,
                "repair_algorithm": REPAIR_ALGORITHM,
                "repair_version": REPAIR_VERSION,
            }
            decision["decision_fingerprint"] = _fingerprint(decision)
            decisions[group.observation_id] = decision
            for name, value in (("instructor_type", instructor_type), ("title", title), ("credits", credits)):
                method_counts[name][value["resolution"]["method"]] += 1
            if len(group.rows) > 1 or instructor_type["conflicting"] or title["conflicting"] or credits["conflicting"] or len(meetings) > 1:
                manifest.append({
                    "knowledge_object_id": group.observation_id,
                    "academic_term": group.academic_term,
                    "course_code": group.course_code,
                    "source_rows": decision["source_rows"],
                    "source_row_hashes": decision["source_row_hashes"],
                    "source_file_sha256": self.source_sha256,
                    "instructor_type": instructor_type,
                    "course_title": title,
                    "credits": credits,
                    "meeting_patterns": meetings,
                    "decision_fingerprint": decision["decision_fingerprint"],
                    "repair_version": REPAIR_VERSION,
                })
        summary = {
            "repair_algorithm": REPAIR_ALGORITHM,
            "repair_version": REPAIR_VERSION,
            "source_file_sha256": self.source_sha256,
            "logical_sections": len(self.groups),
            "manifest_records": len(manifest),
            "instructor_type_methods": dict(method_counts["instructor_type"]),
            "title_methods": dict(method_counts["title"]),
            "credit_methods": dict(method_counts["credits"]),
            "multiple_meeting_pattern_sections": multiple_meetings,
            "later_term_fallback_enabled": self.allow_later_term_fallback,
        }
        return ScheduleRepairAnalysis(decisions=decisions, manifest_records=manifest, summary=summary)


def write_repair_reports(analysis: ScheduleRepairAnalysis, report_directory: Path) -> None:
    """Write compact durable summaries plus a record-per-affected-section manifest."""
    report_directory = Path(report_directory)
    report_directory.mkdir(parents=True, exist_ok=True)
    (report_directory / "repair_summary.json").write_text(json.dumps(analysis.summary, indent=2) + "\n", encoding="utf-8")
    with (report_directory / "repair_manifest.jsonl").open("w", encoding="utf-8") as handle:
        for record in analysis.manifest_records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    conflict_records = [record for record in analysis.manifest_records if record["instructor_type"]["conflicting"]]
    instructor_methods = Counter(record["instructor_type"]["resolution"]["method"] for record in conflict_records)
    instructor_confidence = Counter(str(record["instructor_type"]["resolution"]["confidence"]) for record in conflict_records)
    instructor_examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in conflict_records:
        method = record["instructor_type"]["resolution"]["method"]
        if len(instructor_examples[method]) < 5:
            instructor_examples[method].append({key: record[key] for key in ("knowledge_object_id", "academic_term", "course_code", "source_rows")})
    instructor_summary = {
        "source_conflicts": len(conflict_records),
        "resolved": sum(record["instructor_type"]["resolution"]["resolved"] for record in conflict_records),
        "unresolved": sum(not record["instructor_type"]["resolution"]["resolved"] for record in conflict_records),
        "methods": dict(instructor_methods),
        "confidence_distribution": dict(instructor_confidence),
        "representative_examples": dict(instructor_examples),
    }
    title_conflicts = [record for record in analysis.manifest_records if record["course_title"]["conflicting"]]
    title_summary = {
        "source_conflicts": len(title_conflicts),
        "resolved": sum(record["course_title"]["resolution"]["resolved"] for record in title_conflicts),
        "unresolved": sum(not record["course_title"]["resolution"]["resolved"] for record in title_conflicts),
        "methods": dict(Counter(record["course_title"]["resolution"]["method"] for record in title_conflicts)),
    }
    credit_conflicts = [record for record in analysis.manifest_records if record["credits"]["conflicting"]]
    credit_summary = {
        "source_conflicts": len(credit_conflicts),
        "resolved": sum(record["credits"]["resolution"]["resolved"] for record in credit_conflicts),
        "variable": sum(record["credits"]["resolution"]["method"] == "legitimate_variable_credit" for record in credit_conflicts),
        "unresolved": sum(not record["credits"]["resolution"]["resolved"] and record["credits"]["resolution"]["method"] != "legitimate_variable_credit" for record in credit_conflicts),
        "methods": dict(Counter(record["credits"]["resolution"]["method"] for record in credit_conflicts)),
    }
    for filename, value in (
        ("instructor_type_resolution_summary.json", instructor_summary),
        ("title_resolution_summary.json", title_summary),
        ("credit_resolution_summary.json", credit_summary),
    ):
        (report_directory / filename).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    meeting_counts = Counter(str(len(record["meeting_patterns"])) for record in analysis.manifest_records)
    (report_directory / "meeting_pattern_summary.json").write_text(json.dumps({
        "multiple_meeting_pattern_sections": analysis.summary["multiple_meeting_pattern_sections"],
        "pattern_count_distribution_for_manifest_records": dict(meeting_counts),
    }, indent=2) + "\n", encoding="utf-8")
    report = "\n".join([
        "# Authoritative Schedule Source Repair",
        "",
        f"- Source SHA-256: `{analysis.summary['source_file_sha256']}`",
        f"- Logical sections: {analysis.summary['logical_sections']:,}",
        f"- Affected/duplicate manifest records: {analysis.summary['manifest_records']:,}",
        f"- Multiple-meeting sections: {analysis.summary['multiple_meeting_pattern_sections']:,}",
        "- Original published rows and contradictions are preserved; normalized resolutions are derived assertions.",
        "- Later-term Instructor Type fallback is disabled.",
    ])
    (report_directory / "repair_report.md").write_text(report + "\n", encoding="utf-8")


__all__ = [
    "REPAIR_ALGORITHM", "REPAIR_VERSION", "ScheduleRepairAnalysis",
    "ScheduleRepairGroup", "ScheduleRepairRow", "ScheduleRepairService",
    "write_repair_reports",
]
