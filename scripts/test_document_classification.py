from __future__ import annotations

from datetime import datetime, timezone
import json

from app.classification import ClassificationDisposition, ClassificationGovernor
from app.classification.corpus import CorpusClassificationOptions, SemanticCorpusPopulationService
from app.classification.document_classifiers import DocumentClassificationRouter
from app.classification.document_registry import DocumentFamilyRegistry, RegistryRule
from app.classification.document_signals import DocumentSignalExtractor
from app.knowledge import KnowledgeObject, load_knowledge_object, save_knowledge_object


def _document(path, *, source_key=None, title="", text="evidence", **metadata):
    source_key = source_key or path.split("/", 1)[0]
    return KnowledgeObject(
        id="doc-" + str(abs(hash((path, title)))), object_type="document", title=title,
        text=text, metadata={"source_key": source_key, "qualified_relative_path": path, **metadata},
        source={"relative_path": path},
    )


def _govern(obj):
    return ClassificationGovernor((DocumentClassificationRouter(),)).classify(obj)


def _accepted(result):
    return {item.assertion.field_name: item.assertion.value for item in result.decision.assertion_decisions if item.accepted}


def test_signal_extractor_normalizes_paths_without_promoting_dates():
    obj = _document(
        r"sec_google_drive\Annual Reports\2023_2024\Report Final.docx",
        title="Report Final.docx", created="2024-01-02", modified_at="2025-04-03",
    )
    signals = DocumentSignalExtractor().extract(obj)
    assert signals.path_segments[:2] == ("sec_google_drive", "annual reports")
    assert signals.candidate_academic_years == ("2023-2024",)
    assert signals.filesystem_modified_at == "2025-04-03"
    assert signals.publication_date is None
    assert signals.title_is_filename

    monthly = DocumentSignalExtractor().extract(_document(
        "sec_google_drive/SEC Statistics/Majors/2023/08/report.html"
    ))
    assert monthly.candidate_academic_years == ()
    assert monthly.candidate_reporting_periods == ("2023",)

    nonconsecutive = DocumentSignalExtractor().extract(_document(
        "cnu_website/cnu.edu/institutionalresearch/report_2014-2022.pdf"
    ))
    assert nonconsecutive.candidate_academic_years == ()


def test_institutional_research_exact_path_classifies_but_adjacent_path_abstains():
    result = _govern(_document(
        "cnu_website/cnu.edu/institutionalresearch/pdf/commondataset/cds_2023-2024.pdf",
        source_key="cnu_website", title="Common Data Set 2023-2024",
    ))
    values = _accepted(result)
    assert values["source_family"] == "cnu_institutional_research"
    assert values["document_type"] == "common_data_set"
    assert values["institutional_role"] == "institutional_operating_record"
    assert values["temporal_scope"]["reporting_period"] == "2023-2024"
    assert "trend" not in json.dumps(values).casefold()
    assert result.decision.disposition == ClassificationDisposition.ACCEPT_WITH_AUDIT

    near = _govern(_document(
        "cnu_website/cnu.edu/academics/institutionalresearch_notes.pdf",
        source_key="cnu_website", title="Institutional Research Notes",
    ))
    assert near.abstention.reasons[0].code == "unsupported_document_family"


def test_sec_statistics_scope_is_academic_unit_not_institution():
    values = _accepted(_govern(_document(
        "sec_google_drive/SEC Statistics/Majors/2026/02/SEC_Majors.html",
        title="", source_key="sec_google_drive",
    )))
    assert values["document_type"] == "academic_unit_statistical_record"
    assert values["institutional_entities"][0]["entity_id"] == "academic_unit:sec"
    assert all(item.get("entity_id") != "institution:cnu" for item in values["institutional_entities"])
    assert "authority" not in values


def test_program_review_subtypes_draft_final_supporting_and_feedback():
    cases = {
        "Program Review/2023/Data/table.xlsx": "program_review_supporting_evidence",
        "Program Review/2023/PCSE Review Final.pdf": "final_program_review",
        "Program Review/2023/PCSE Review Draft.docx": "program_review_draft",
        "Program Review/2023/Reviewer Feedback.docx": "program_review_feedback",
    }
    for suffix, expected in cases.items():
        values = _accepted(_govern(_document(f"sec_google_drive/{suffix}", source_key="sec_google_drive")))
        assert values["document_type"] == expected


def test_annual_report_period_is_path_based_not_filesystem_date():
    values = _accepted(_govern(_document(
        "sec_google_drive/Annual Reports/2022_2023/Departmental Report.pdf",
        source_key="sec_google_drive", modified_at="2026-07-01",
    )))
    assert values["temporal_scope"]["reporting_period"] == "2022-2023"
    assert "2026" not in json.dumps(values["temporal_scope"])


def test_planning_proposal_and_draft_are_not_implemented_facts():
    values = _accepted(_govern(_document(
        "sec_google_drive/Planning/Budget/New Program Proposal draft.docx",
        source_key="sec_google_drive", title="New Program Proposal draft",
    )))
    assert values["document_type"] == "planning_draft"
    assert values["institutional_role"] == "academic_unit_planning_material"
    assert "implemented" not in json.dumps(values)


def test_explicit_external_provenance_classifies_only_explicit_fields():
    result = _govern(_document(
        "external_abet/criteria.html", source_key="external_abet", title="Criteria",
        canonical_url="https://www.abet.org/criteria", issuing_authority="ABET",
        authority_class="accreditation_authority", evidence_role="Formal External Standard",
    ))
    values = _accepted(result)
    assert values["document_type"] == "formal_external_standard"
    assert values["authority"]["issuing_authority"] == "ABET"
    assert "institutional_entities" not in values

    incomplete = _govern(_document("external_abet/local.html", source_key="external_abet"))
    assert incomplete.abstention.reasons[0].code == "incomplete_external_provenance"


def test_local_abet_strategic_web_and_generic_documents_remain_abstained():
    for obj in (
        _document("sec_google_drive/ABET/Self Studies/Local Self Study.pdf", source_key="sec_google_drive"),
        _document("cnu_website/cnu.edu/strategiccompass/index.html", source_key="cnu_website", title="Strategic Compass"),
        _document("sec_google_drive/Course Materials/slides.pptx", source_key="sec_google_drive", title="Lecture"),
        _document("sec_google_drive/Misc/blank.pdf", source_key="sec_google_drive", text=""),
    ):
        result = _govern(obj)
        assert result.abstention.reasons[0].code == "unsupported_document_family"


def test_copied_external_material_gets_no_authority_and_conflicting_title_abstains():
    copied = _govern(_document(
        "sec_google_drive/ABET/Course Displays/copied_standard.pdf",
        source_key="sec_google_drive", title="ABET Criteria for Accrediting Programs",
    ))
    assert copied.abstention.reasons[0].code == "unsupported_document_family"

    conflict = _govern(_document(
        "sec_google_drive/Planning/copied_standard.pdf",
        source_key="sec_google_drive", title="ABET Criteria for Accrediting Programs",
    ))
    assert conflict.abstention.reasons[0].code == "conflicting_document_signals"


def test_sensitive_paths_are_flagged_and_not_promoted():
    result = _govern(_document(
        "sec_google_drive/Planning/Faculty Searches/candidate notes.docx",
        source_key="sec_google_drive", title="Candidate notes",
    ))
    assert result.abstention.reasons[0].code == "sensitive_document_family"
    assert result.proposal is None


def test_competing_equal_priority_routes_abstain_as_ambiguous():
    base = dict(priority=10, source_keys=("x",), path_prefixes=("x/",), path_segments_all=(), domains=(),
                source_family="x", document_type=None, institutional_role=None, issuing_authority=None,
                allowed_document_types=(), allowed_institutional_roles=(),
                authority_class=None, institutional_entity=None, audit_required=False, notes="", version="1")
    rules = (
        RegistryRule(rule_id="a", classifier="annual_report_document_classifier", **base),
        RegistryRule(rule_id="b", classifier="planning_document_classifier", **base),
    )
    router = DocumentClassificationRouter(family_registry=DocumentFamilyRegistry(rules, "1"))
    result = ClassificationGovernor((router,)).classify(_document("x/file.pdf", source_key="x"))
    assert result.abstention.reasons[0].code == "ambiguous_document_route"


def test_dry_run_preserves_existing_classified_object_and_second_pass_is_deterministic(tmp_path):
    existing = _document("sec_google_drive/Planning/plan.docx", source_key="sec_google_drive", title="Plan")
    existing.metadata["semantic_identity"] = {"object_type": "document", "source_family": "sec_google_drive"}
    path = tmp_path / "input" / "document.json"
    path.parent.mkdir()
    save_knowledge_object(existing, path)
    before = path.read_bytes()
    clock = lambda: datetime(2026, 7, 21, tzinfo=timezone.utc)
    service = SemanticCorpusPopulationService(clock=clock)
    reports = []
    for name in ("one", "two"):
        report_dir = tmp_path / name
        reports.append(service.run(CorpusClassificationOptions((tmp_path / "input",), report_dir)))
    assert path.read_bytes() == before
    assert (tmp_path / "one" / "classification_manifest.jsonl").read_bytes() == (tmp_path / "two" / "classification_manifest.jsonl").read_bytes()
    assert reports[0].overall.changed == 1
    assert load_knowledge_object(path).semantic_identity.document_type is None
    summary = json.loads((tmp_path / "one" / "classification_summary.json").read_text())
    assert summary["field_metrics"]["source_family"]["present_before"] == 1
    assert summary["field_metrics"]["document_type"]["present_after"] == 1
    assert summary["registry_rules"] == {"sec.planning.v1": 1}
