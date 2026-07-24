"""Registry-driven, conservative classification of generic documents."""

from __future__ import annotations

from typing import Any, Optional, Tuple

from app.classification.classifiers import ClassificationAbstained, SemanticClassifier
from app.classification.contracts import (
    ClassificationAssertion, ClassificationConfidence, ClassificationMethod,
    ClassificationProposal, EvidenceCitation,
)
from app.classification.document_registry import (
    DocumentFamilyRegistry, InstitutionalPublisherRegistry, RegistryRule,
)
from app.classification.document_signals import DocumentSignalExtractor, DocumentSignals
from app.knowledge import KnowledgeObject
from app.semantic_identity import Authority, TemporalScope


class RegisteredDocumentClassifier:
    name = "registered_document_classifier"

    def classify(self, obj: KnowledgeObject, signals: DocumentSignals, rule: RegistryRule,
                 publisher: Optional[RegistryRule]) -> ClassificationProposal:
        values = self.values(obj, signals, rule, publisher)
        for field, value in values:
            if field == "document_type" and value and rule.allowed_document_types and value not in rule.allowed_document_types:
                raise ClassificationAbstained("unregistered_document_subtype", f"{value!r} is not allowed by {rule.rule_id}.")
            if field == "institutional_role" and value and rule.allowed_institutional_roles and value not in rule.allowed_institutional_roles:
                raise ClassificationAbstained("unregistered_institutional_role", f"{value!r} is not allowed by {rule.rule_id}.")
        assertions = tuple(
            _assertion(obj, field, value, rule, signals)
            for field, value in values
            if value not in (None, "", (), [], {})
        )
        if not assertions:
            raise ClassificationAbstained("registered_rule_no_safe_assertion", f"{rule.rule_id} matched but made no safe assertion.")
        return ClassificationProposal(obj.id, assertions, self.name)

    def values(self, obj, signals, rule, publisher):
        values = [
            ("source_family", rule.source_family),
            ("document_type", rule.document_type),
            ("institutional_role", rule.institutional_role),
        ]
        if rule.institutional_entity:
            values.append(("institutional_entities", [dict(rule.institutional_entity)]))
        authority_rule = publisher or (rule if rule.issuing_authority else None)
        if authority_rule and authority_rule.issuing_authority:
            values.append(("authority", Authority(
                authority_rule.issuing_authority,
                authority_rule.authority_class,
            ).to_dict()))
        return values


class ExplicitProvenanceDocumentClassifier(RegisteredDocumentClassifier):
    name = "explicit_provenance_document_classifier"

    def values(self, obj, signals, rule, publisher):
        if not signals.explicit_external_provenance:
            raise ClassificationAbstained("incomplete_external_provenance", "Curated collection membership lacks complete explicit external provenance.")
        metadata = obj.metadata or {}
        evidence_role = metadata.get("evidence_role")
        document_type = metadata.get("document_type") or _external_document_type(str(evidence_role or ""))
        return [
            ("source_family", rule.source_family),
            ("document_type", document_type),
            ("institutional_role", rule.institutional_role),
            ("authority", Authority(
                signals.issuing_authority or "",
                metadata.get("authority_class"),
                evidence_role,
            ).to_dict()),
        ]


class SchevDocumentClassifier(RegisteredDocumentClassifier):
    name = "schev_document_classifier"


class InstitutionalResearchDocumentClassifier(RegisteredDocumentClassifier):
    name = "institutional_research_document_classifier"

    def values(self, obj, signals, rule, publisher):
        values = super().values(obj, signals, rule, publisher)
        subtype = _ir_type(signals)
        if subtype:
            values = [(field, value) for field, value in values if field != "document_type"]
            values.append(("document_type", subtype))
        temporal = _explicit_temporal_scope(signals)
        if temporal:
            values.append(("temporal_scope", temporal))
        return values


class SecStatisticsDocumentClassifier(RegisteredDocumentClassifier):
    name = "sec_statistics_document_classifier"

    def values(self, obj, signals, rule, publisher):
        values = super().values(obj, signals, rule, publisher)
        temporal = _explicit_temporal_scope(signals)
        if temporal:
            values.append(("temporal_scope", temporal))
        return values


class ProgramReviewDocumentClassifier(RegisteredDocumentClassifier):
    name = "program_review_document_classifier"

    def values(self, obj, signals, rule, publisher):
        values = super().values(obj, signals, rule, publisher)
        subtype = _program_review_type(signals)
        if subtype:
            values.append(("document_type", subtype))
        temporal = _explicit_temporal_scope(signals)
        if temporal:
            values.append(("temporal_scope", temporal))
        return values


class AnnualReportDocumentClassifier(RegisteredDocumentClassifier):
    name = "annual_report_document_classifier"

    def values(self, obj, signals, rule, publisher):
        values = super().values(obj, signals, rule, publisher)
        # Templates are planning artifacts, not completed annual reports.
        dtype = "annual_report_template" if "template" in signals.filename.casefold() else "academic_unit_annual_report"
        values.append(("document_type", dtype))
        temporal = _explicit_temporal_scope(signals)
        if temporal:
            values.append(("temporal_scope", temporal))
        return values


class PlanningDocumentClassifier(RegisteredDocumentClassifier):
    name = "planning_document_classifier"

    def values(self, obj, signals, rule, publisher):
        values = super().values(obj, signals, rule, publisher)
        name = f"{signals.filename} {signals.title}".casefold()
        dtype = "planning_proposal" if "proposal" in name else "planning_material"
        if "draft" in name:
            dtype = "planning_draft"
        values.append(("document_type", dtype))
        return values


CLASSIFIERS = {
    item.name: item for item in (
        ExplicitProvenanceDocumentClassifier(), SchevDocumentClassifier(),
        InstitutionalResearchDocumentClassifier(), SecStatisticsDocumentClassifier(),
        ProgramReviewDocumentClassifier(), AnnualReportDocumentClassifier(),
        PlanningDocumentClassifier(),
    )
}


class DocumentClassificationRouter(SemanticClassifier):
    """Select exactly one reviewed document-family rule or abstain."""

    name = "document_classification_router"
    version = "1"
    method = ClassificationMethod.DETERMINISTIC_RULE
    supported_object_types = ("document",)

    def __init__(self, family_registry=None, publisher_registry=None, extractor=None):
        self.family_registry = family_registry or DocumentFamilyRegistry.load()
        self.publisher_registry = publisher_registry or InstitutionalPublisherRegistry.load()
        self.extractor = extractor or DocumentSignalExtractor()
        self.classifiers = tuple(CLASSIFIERS.values())

    def classify(self, obj: KnowledgeObject) -> ClassificationProposal:
        signals = self.extractor.extract(obj)
        if signals.sensitive_reasons:
            raise ClassificationAbstained("sensitive_document_family", "Potentially sensitive custody path is intentionally withheld from semantic promotion.")
        matches = self.family_registry.matches(signals)
        if not matches:
            raise ClassificationAbstained("unsupported_document_family", "No reviewed deterministic document-family rule applies.")
        highest = matches[0].priority
        candidates = tuple(rule for rule in matches if rule.priority == highest)
        classifiers = {rule.classifier for rule in candidates}
        if len(classifiers) != 1:
            ids = ", ".join(rule.rule_id for rule in candidates)
            raise ClassificationAbstained("ambiguous_document_route", f"Competing registered routes matched: {ids}.")
        rule = candidates[0]
        if _institutional_external_conflict(signals, rule):
            raise ClassificationAbstained(
                "conflicting_document_signals",
                "An institutional custody route conflicts with an explicit external-authority title signal.",
            )
        classifier = CLASSIFIERS.get(rule.classifier)
        if classifier is None:
            raise ClassificationAbstained("unregistered_document_classifier", f"Registry rule {rule.rule_id} names no installed classifier.")
        publishers = self.publisher_registry.matches(signals)
        publisher = publishers[0] if len(publishers) == 1 else None
        proposal = classifier.classify(obj, signals, rule, publisher)
        # Report the concrete classifier, while citations preserve the router rule.
        proposal.classifier_name = classifier.name
        return proposal


def _assertion(obj, field, value, rule, signals):
    return ClassificationAssertion(
        field_name=field, value=value,
        confidence=ClassificationConfidence(1.0, f"Exact reviewed registry rule {rule.rule_id}."),
        classification_method=ClassificationMethod.DETERMINISTIC_RULE,
        supporting_evidence=(EvidenceCitation(
            source_kind="document_routing_signal", field="metadata.qualified_relative_path",
            knowledge_object_id=obj.id,
            attributes={
                "registered_rule": True, "predicates_satisfied": True, "unambiguous": True,
                "rule_id": rule.rule_id, "rule_version": rule.version,
                "source_key": signals.source_key,
                "qualified_relative_path": signals.qualified_relative_path,
            },
        ),),
    )


def _ir_type(signals):
    path = signals.qualified_relative_path.casefold()
    for marker, dtype in (
        ("/commondataset/", "common_data_set"),
        ("/degreesconferred", "degrees_conferred_record"),
        ("/studentinfo/", "institutional_student_statistics"),
        ("retention", "retention_snapshot"),
        ("/historical", "historical_institutional_statistics"),
        ("/enrollment", "enrollment_snapshot"),
        ("/freshmanprofile/", "student_profile_snapshot"),
    ):
        if marker in path:
            return dtype
    return "institutional_research_publication"


def _program_review_type(signals):
    path = signals.qualified_relative_path.casefold()
    name = f"{signals.filename} {signals.title}".casefold()
    if "/data/" in path or "/appendix/" in path:
        return "program_review_supporting_evidence"
    if "external review" in name or "external reviewer" in name:
        return "external_program_review"
    if "response" in name:
        return "program_review_administrative_response"
    if "feedback" in name:
        return "program_review_feedback"
    if "draft" in name:
        return "program_review_draft"
    if "final" in name:
        return "final_program_review"
    return "program_review_material"


def _explicit_temporal_scope(signals):
    if signals.candidate_academic_years:
        period = signals.candidate_academic_years[0]
        return TemporalScope(reporting_period=period, published_label=period).to_dict()
    # A directory segment consisting only of a year is explicit period context.
    exact_years = [segment for segment in signals.path_segments if len(segment) == 4 and segment.isdigit()]
    if exact_years:
        return TemporalScope(reporting_period=exact_years[0], published_label=exact_years[0]).to_dict()
    return None


def _external_document_type(role):
    value = role.casefold()
    if "standard" in value:
        return "formal_external_standard"
    if "statistic" in value or "labor-market" in value:
        return "external_statistical_source"
    if "study" in value:
        return "external_research_report"
    if "regulatory" in value:
        return "external_regulatory_source"
    return "curated_external_reference"


def _institutional_external_conflict(signals, rule):
    if rule.classifier not in {
        "institutional_research_document_classifier",
        "sec_statistics_document_classifier",
        "program_review_document_classifier",
        "annual_report_document_classifier",
        "planning_document_classifier",
    }:
        return False
    title = signals.title.casefold()
    return any(
        marker in title
        for marker in (
            "u.s. bureau of labor statistics",
            "u.s. department of energy",
            "nuclear regulatory commission",
            "state council of higher education for virginia",
            "abet criteria for accrediting",
        )
    ) and not signals.explicit_external_provenance


__all__ = [
    "DocumentClassificationRouter", "ExplicitProvenanceDocumentClassifier",
    "SchevDocumentClassifier", "InstitutionalResearchDocumentClassifier",
    "SecStatisticsDocumentClassifier", "ProgramReviewDocumentClassifier",
    "AnnualReportDocumentClassifier", "PlanningDocumentClassifier",
]
