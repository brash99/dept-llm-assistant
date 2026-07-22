from app.semantic_discrepancy import DiscrepancyCategory, SemanticDiscrepancyAnalyzer
from app.subject_ownership import SubjectOwnershipRegistry


def _observation(prefix, confidence=1.0, kind="undergraduate", section="Example"):
    return {"subject_code": prefix, "section_title": section, "extraction_confidence": confidence, "provenance": {"catalog_kind": kind}}


def _candidate(prefix, status="high_confidence_candidate", mapping="mapped", relationship="owns_instructional_subject"):
    return {"subject_code": prefix, "candidate_status": status, "proposed_mapping_status": mapping, "proposed_relationship_type": relationship}


def _schedule(count=1, issues=()):
    return {"offering_count": count, "term_count": 2, "distinct_instructor_count": 3, "normalization_issues": list(issues)}


def _categories(report):
    return {item.prefix: item.category for item in report.records}


def test_primary_explanations_cover_expected_semantic_cases():
    observations = [
        _observation("PHYS"),
        _observation("ARTX"),
        _observation("COLL", section="College Studies"),
        _observation("IDST", section="Interdisciplinary Studies"),
        _observation("LOW", confidence=.4),
        _observation("STRUCT"),
        _observation("GRAD", kind="graduate"),
        _observation("CENT"),
    ]
    candidates = [
        _candidate("PHYS"),
        _candidate("ARTX"),
        _candidate("COLL", "exception_candidate", "service_subject", "centrally_administered_subject"),
        _candidate("IDST", "exception_candidate", "interdisciplinary", "interdisciplinary_subject"),
        _candidate("LOW", "requires_review"),
        _candidate("STRUCT", "requires_review"),
        _candidate("GRAD"),
        _candidate("CENT", "exception_candidate", "mapped", "centrally_administered_subject"),
    ]
    schedule = {
        "PCSE": _schedule(62),
        "ZZZZ": _schedule(12),
        "COLL": _schedule(20),
        "IDST": _schedule(5),
        "STRUCT": _schedule(2),
        "NORM": _schedule(4, ("missing_source_term",)),
    }
    report = SemanticDiscrepancyAnalyzer().analyze(
        SubjectOwnershipRegistry.load(), observations, candidates, schedule
    )
    values = _categories(report)
    assert values["PCSE"] == DiscrepancyCategory.HISTORICAL_PREFIX.value
    assert values["COLL"] == DiscrepancyCategory.SERVICE_SUBJECT.value
    assert values["IDST"] == DiscrepancyCategory.INTERDISCIPLINARY.value
    assert values["ARTX"] == DiscrepancyCategory.GOVERNANCE_GAP.value
    assert values["PHYS"] == DiscrepancyCategory.CURRENT_CATALOG_ONLY.value
    assert values["ZZZZ"] == DiscrepancyCategory.CURRENT_SCHEDULE_ONLY.value
    assert values["LOW"] == DiscrepancyCategory.CATALOG_EXTRACTION_LIMITATION.value
    assert values["STRUCT"] == DiscrepancyCategory.CATALOG_STRUCTURE_LIMITATION.value
    assert values["NORM"] == DiscrepancyCategory.SCHEDULE_NORMALIZATION_LIMITATION.value
    assert values["GRAD"] == DiscrepancyCategory.GRADUATE_ONLY.value
    assert values["CENT"] == DiscrepancyCategory.CENTRAL_ADMINISTRATION.value
    assert values["EENG"] == DiscrepancyCategory.UNKNOWN.value
    assert len(values) == len(report.records)


def test_dashboard_order_priority_fitness_and_fingerprint_are_deterministic():
    observations = [_observation("ARTX"), _observation("COLL")]
    candidates = [_candidate("ARTX"), _candidate("COLL", "exception_candidate", "service_subject", "centrally_administered_subject")]
    schedule = {"ZZZZ": _schedule(100), "COLL": _schedule(2)}
    analyzer = SemanticDiscrepancyAnalyzer()
    first = analyzer.analyze(SubjectOwnershipRegistry.load(), observations, candidates, schedule)
    second = analyzer.analyze(SubjectOwnershipRegistry.load(), tuple(reversed(observations)), tuple(reversed(candidates)), dict(reversed(tuple(schedule.items()))))
    assert first.deterministic_fingerprint == second.deterministic_fingerprint
    assert [item.prefix for item in first.records] == [item.prefix for item in second.records]
    assert first.records[0].review_priority == "high"
    assert sum(first.count_by_category.values()) == len(first.records)
    assert first.evidence_fitness.overall_discrepancy_count == len(first.records)
    assert first.evidence_fitness.semantic_completeness_percent < 100
