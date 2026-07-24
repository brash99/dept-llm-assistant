"""Decision-specific faculty-delivered SCH derived from governed workforce home."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping

from app.academic_terms import academic_term_order
from app.department_profiles import _unique_sections, _valid_number
from app.institutional_units import AcademicUnitRegistry
from app.llc_designations import (
    LLCDesignationMatch,
    LLCDesignationRegistry,
)


ALGORITHM = "faculty_delivered_sch_comparison"
ALGORITHM_VERSION = "1.4"
DEFAULT_ACADEMIC_YEARS = ("2022-23", "2023-24", "2024-25")
QUENTIN_DEPARTMENT_CODES = {
    "ACFN": "academic_unit:department_accounting_finance",
    "BCES": "academic_unit:department_biology_chemistry_environmental_science",
    "COMM": "academic_unit:department_communication_studies",
    "ECON": "academic_unit:department_economics",
    "ENGL": "academic_unit:department_english",
    "FAAH": "academic_unit:department_fine_art_art_history",
    "HIST": "academic_unit:department_history",
    "LAMS": "academic_unit:department_leadership_american_studies",
    "MATH": "academic_unit:department_mathematics",
    "MCLL": "academic_unit:department_modern_classical_languages_literatures",
    "MGMT": "academic_unit:department_management_marketing",
    "MTD": "academic_unit:department_music_theatre_dance",
    "PHIL": "academic_unit:department_philosophy_religion",
    "POLS": "academic_unit:department_political_science",
    "PSYC": "academic_unit:department_psychology",
    "SEC": "academic_unit:sec",
    "SSWA": "academic_unit:department_sociology_social_work_anthropology",
}


def _fingerprint(value: Any) -> str:
    return sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()


def _academic_year(term: str) -> str:
    order = academic_term_order(term)
    if not order.supported:
        raise ValueError(f"Unsupported academic term: {term}")
    start = order.year if order.period == "fall" else order.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


@dataclass(frozen=True)
class DepartmentSCHComparison:
    academic_unit_id: str
    department_name: str
    governed_prefix_owned_sch: float
    workforce_attributed_sch: float
    difference: float
    cross_unit_contribution: float
    governed_owned_section_count: int
    workforce_attributed_section_count: int
    instructor_home_sch: float
    prefix_owner_fallback_sch: float
    workforce_attributed_outside_owned_sch: float
    department_owned_delivered_by_other_homes_sch: float

    def to_dict(self):
        value = asdict(self)
        # Temporary serialization aliases for callers of the original metric name.
        value["faculty_delivered_sch"] = self.workforce_attributed_sch
        value["faculty_delivered_section_count"] = (
            self.workforce_attributed_section_count
        )
        value["faculty_delivered_outside_owned_sch"] = (
            self.workforce_attributed_outside_owned_sch
        )
        return value

    @property
    def faculty_delivered_sch(self):
        return self.workforce_attributed_sch


@dataclass(frozen=True)
class SectionSCHAttribution:
    section_key: str
    term: str
    subject: str
    course_code: str
    llc_area_raw: str | None
    llc_policy_id: str
    llc_matched_designations: tuple[LLCDesignationMatch, ...]
    llc_unknown_tokens: tuple[str, ...]
    governed_prefix_owner_unit_id: str | None
    workforce_attributed_unit_id: str | None
    attribution_method: str
    fallback_reason: str | None
    sch: float

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class FacultyDeliveredSCHReport:
    academic_years: tuple[str, ...]
    fall_only: bool
    llc_only: bool
    llc_policy_ids: tuple[str, ...]
    llc_unknown_token_counts: Mapping[str, int]
    aggregation: str
    rows: tuple[DepartmentSCHComparison, ...]
    section_attributions: tuple[SectionSCHAttribution, ...]
    attribution_pathway_counts: Mapping[str, int]
    attribution_pathway_sch: Mapping[str, float]
    unassigned_instructor_section_count: int
    multi_home_section_count: int
    deterministic_fingerprint: str

    def to_dict(self):
        return {
            "algorithm": ALGORITHM,
            "algorithm_version": ALGORITHM_VERSION,
            "metric_definition": {
                "curriculum_owned_sch": (
                    "SCH assigned to the governed owner of the course prefix."
                ),
                "workforce_attributed_sch": (
                    "SCH assigned to the governed analytical home of an active "
                    "full-time analytical-workforce instructor; otherwise to "
                    "the governed prefix owner."
                ),
            },
            "academic_years": list(self.academic_years),
            "fall_only": self.fall_only,
            "llc_only": self.llc_only,
            "llc_policy_ids": list(self.llc_policy_ids),
            "llc_unknown_token_counts": dict(self.llc_unknown_token_counts),
            "aggregation": self.aggregation,
            "rows": [item.to_dict() for item in self.rows],
            "section_attributions": [
                item.to_dict() for item in self.section_attributions
            ],
            "attribution_pathway_counts": dict(self.attribution_pathway_counts),
            "attribution_pathway_sch": dict(self.attribution_pathway_sch),
            "unassigned_instructor_section_count": self.unassigned_instructor_section_count,
            "multi_home_section_count": self.multi_home_section_count,
            "deterministic_fingerprint": self.deterministic_fingerprint,
        }


def build_faculty_delivered_sch_comparison(
    profiles: Iterable[Mapping[str, Any]],
    rows: Iterable[Mapping[str, Any]],
    *,
    academic_years: Iterable[str] = DEFAULT_ACADEMIC_YEARS,
    fall_only: bool = False,
    llc_only: bool = False,
    llc_registry: LLCDesignationRegistry | None = None,
) -> FacultyDeliveredSCHReport:
    """Compare three-year average ownership SCH with faculty-delivery SCH."""
    years = tuple(academic_years)
    llc_registry = llc_registry or LLCDesignationRegistry.load()
    candidates = tuple(
        row for row in rows
        if _academic_year(row["term"]) in years
        and (
            not fall_only
            or academic_term_order(row["term"]).period == "fall"
        )
    )
    section_groups: dict[str, list[Mapping[str, Any]]] = {}
    for row in candidates:
        section_groups.setdefault(row["section_key"], []).append(row)
    multi_home = 0
    unassigned = 0
    attributions = []
    selected_rows = []
    unknown_token_counts: dict[str, int] = {}
    policy_ids = set()
    for key in sorted(section_groups):
        values = section_groups[key]
        merged = _unique_sections(values)[0]
        llc = llc_registry.classify(
            merged.get("llc_area_raw"), str(merged["term"])
        )
        policy_ids.add(llc.policy_id)
        for token in llc.unknown_tokens:
            unknown_token_counts[token] = unknown_token_counts.get(token, 0) + 1
        if llc_only and not llc.included:
            continue
        selected_rows.extend(values)
        homes = {item["home_unit_id"] for item in values if item["home_unit_id"]}
        multi_home += len(homes) > 1
        unassigned += not homes
        owners = {
            item["owned_unit_id"] for item in values if item["owned_unit_id"]
        }
        owner = next(iter(owners)) if len(owners) == 1 else None
        if len(homes) == 1:
            attributed = next(iter(homes))
            method = "instructor_home"
            fallback_reason = None
        elif owner:
            attributed = owner
            method = "prefix_owner_fallback"
            fallback_reason = (
                "multiple_active_workforce_homes"
                if len(homes) > 1 else "no_active_workforce_home"
            )
        else:
            attributed = None
            method = "unattributed_missing_governed_prefix_owner"
            fallback_reason = "missing_governed_prefix_owner"
        attributions.append(SectionSCHAttribution(
            section_key=key,
            term=str(merged["term"]),
            subject=str(merged["subject"]),
            course_code=str(merged["course_code"]),
            llc_area_raw=(
                str(merged.get("llc_area_raw") or "").strip() or None
            ),
            llc_policy_id=llc.policy_id,
            llc_matched_designations=llc.matched_designations,
            llc_unknown_tokens=llc.unknown_tokens,
            governed_prefix_owner_unit_id=owner,
            workforce_attributed_unit_id=attributed,
            attribution_method=method,
            fallback_reason=fallback_reason,
            sch=round(_sch((merged,)), 6),
        ))
    selected = tuple(selected_rows)

    results = []
    for profile in sorted(profiles, key=lambda item: item["academic_unit_id"]):
        unit_id = profile["academic_unit_id"]
        owned = _unique_sections(
            row for row in selected if row["owned_unit_id"] == unit_id
        )
        attributed = tuple(
            item for item in attributions
            if item.workforce_attributed_unit_id == unit_id
        )
        owned_sch = _sch(owned)
        attributed_sch = sum(item.sch for item in attributed)
        outside_sch = sum(
            item.sch for item in attributed
            if item.governed_prefix_owner_unit_id != unit_id
        )
        inbound_sch = sum(
            item.sch for item in attributions
            if item.governed_prefix_owner_unit_id == unit_id
            and item.workforce_attributed_unit_id != unit_id
        )
        # The report compares like-for-like three-year annual averages.
        divisor = len(years)
        owned_average = round(owned_sch / divisor, 6)
        attributed_average = round(attributed_sch / divisor, 6)
        difference = round(attributed_average - owned_average, 6)
        results.append(DepartmentSCHComparison(
            academic_unit_id=unit_id,
            department_name=profile["department_name"],
            governed_prefix_owned_sch=owned_average,
            workforce_attributed_sch=attributed_average,
            difference=difference,
            cross_unit_contribution=difference,
            governed_owned_section_count=len(owned),
            workforce_attributed_section_count=len(attributed),
            instructor_home_sch=round(sum(
                item.sch for item in attributed
                if item.attribution_method == "instructor_home"
            ) / divisor, 6),
            prefix_owner_fallback_sch=round(sum(
                item.sch for item in attributed
                if item.attribution_method == "prefix_owner_fallback"
            ) / divisor, 6),
            workforce_attributed_outside_owned_sch=round(
                outside_sch / divisor, 6
            ),
            department_owned_delivered_by_other_homes_sch=round(
                inbound_sch / divisor, 6
            ),
        ))
    pathway_counts = {
        method: sum(item.attribution_method == method for item in attributions)
        for method in sorted({item.attribution_method for item in attributions})
    }
    pathway_sch = {
        method: round(sum(
            item.sch for item in attributions if item.attribution_method == method
        ) / len(years), 6)
        for method in pathway_counts
    }
    semantic = {
        "academic_years": years,
        "fall_only": fall_only,
        "llc_only": llc_only,
        "llc_policy_ids": sorted(policy_ids),
        "llc_unknown_token_counts": dict(sorted(unknown_token_counts.items())),
        "aggregation": "mean_annual_sch",
        "rows": [item.to_dict() for item in results],
        "section_attributions": [item.to_dict() for item in attributions],
        "attribution_pathway_counts": pathway_counts,
        "attribution_pathway_sch": pathway_sch,
        "unassigned_instructor_section_count": unassigned,
        "multi_home_section_count": multi_home,
    }
    return FacultyDeliveredSCHReport(
        years, fall_only, llc_only, tuple(sorted(policy_ids)),
        dict(sorted(unknown_token_counts.items())),
        "mean_annual_sch", tuple(results),
        tuple(attributions),
        pathway_counts, pathway_sch, unassigned, multi_home,
        _fingerprint(semantic),
    )


def compare_with_quentin(
    report: FacultyDeliveredSCHReport,
    quentin_rows: Iterable[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Compare faculty-delivered SCH with an explicit Quentin-table extract."""
    by_name = {item.department_name.casefold(): item for item in report.rows}
    by_unit = {item.academic_unit_id: item for item in report.rows}
    units = AcademicUnitRegistry.load()
    output = []
    for source in quentin_rows:
        name = str(source["Department"]).strip()
        metric = float(source["Quentin SCH"])
        governed = units.resolve(name)
        row = (
            by_unit.get(governed.unit_id) if governed else None
        ) or by_unit.get(QUENTIN_DEPARTMENT_CODES.get(name.upper(), "")) or by_name.get(
            name.casefold()
        )
        if row is None and name.upper() in {
            "HONOR & IDST", "HONORS & IDST", "HONR & IDST"
        }:
            subjects = {"HONR", "IDST"}
            values = tuple(
                item for item in report.section_attributions
                if item.subject in subjects
            )
            owned_metric = round(
                sum(item.sch for item in values) / len(report.academic_years), 6
            )
            special_owner_ids = {
                item.governed_prefix_owner_unit_id for item in values
                if item.governed_prefix_owner_unit_id
            }
            attributed_metric = round(sum(
                item.sch for item in values
                if item.workforce_attributed_unit_id in special_owner_ids
            ) / len(report.academic_years), 6)
            output.append(_comparison_row(
                "Honors and IDST", name, metric,
                owned_metric, attributed_metric,
            ))
            continue
        if row is None:
            raise ValueError(f"Quentin department has no ISO profile: {name}")
        output.append(_comparison_row(
            row.department_name, name, metric,
            row.governed_prefix_owned_sch, row.workforce_attributed_sch,
        ))
    return tuple(sorted(output, key=lambda item: item["Department"].casefold()))


def _comparison_row(department, code, quentin, owned, attributed):
    return {
        "Department": department,
        "Quentin Department Code": code,
        "Quentin SCH": quentin,
        "Governed-Prefix-Owned SCH": owned,
        "Workforce-Attributed SCH": attributed,
        "Difference (Governed - Quentin)": round(owned - quentin, 6),
        "Difference (Workforce-Attributed - Quentin)": round(
            attributed - quentin, 6
        ),
        "Absolute Difference Improvement": round(
            abs(owned - quentin) - abs(attributed - quentin), 6
        ),
        "Percent Difference (Workforce-Attributed)": (
            round(100 * (attributed - quentin) / quentin, 6)
            if quentin else None
        ),
    }


def _sch(rows: Iterable[Mapping[str, Any]]) -> float:
    total = 0.0
    for row in rows:
        if not _valid_number(row.get("credits")) or not _valid_number(
            row.get("enrollment"), integer=True
        ):
            raise ValueError(
                f"Faculty-delivered SCH requires explicit inputs: {row['section_key']}"
            )
        total += float(row["credits"]) * int(row["enrollment"])
    return total


def parse_llc_designation_codes(value: Any) -> tuple[str, ...]:
    """Compatibility helper backed by the governed designation registry."""
    policy = LLCDesignationRegistry.load().policies[0]
    return tuple(item.code for item in policy.classify(value).matched_designations)


__all__ = [
    "DEFAULT_ACADEMIC_YEARS", "DepartmentSCHComparison",
    "FacultyDeliveredSCHReport", "SectionSCHAttribution",
    "build_faculty_delivered_sch_comparison",
    "compare_with_quentin", "parse_llc_designation_codes",
]
