from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from app.acquisition.external import (
    EvidenceAcquisitionPlanner,
    ExternalEvidenceAcquisitionService,
    ExternalSourceRegistry,
    FetchedArtifact,
)
from app.knowledge import load_knowledge_object
from app.chunk import chunk_document
from app.evidence import EvidenceClass, classify_evidence
from app.observatory.evidence_fitness import EvidenceFitnessService


REGISTRY_PATH = Path("config/external_evidence_sources.yaml")


class FixtureFetcher:
    def __init__(self, *, duplicate_content: bool = False) -> None:
        self.duplicate_content = duplicate_content
        self.urls = []

    def fetch(self, url: str) -> FetchedArtifact:
        self.urls.append(url)
        marker = "same fixture" if self.duplicate_content else url
        return FetchedArtifact(
            content=(
                "<html><head><title>Fixture</title></head>"
                f"<body>Authoritative fixture evidence for {marker}.</body></html>"
            ).encode("utf-8"),
            media_type="text/html",
            final_url=url,
        )


def assessment(*domains: str):
    return SimpleNamespace(
        decision_type="academic_program",
        decision_type_label="Health Physics",
        missing_topics=list(domains),
    )


def service(tmp_path: Path, fetcher: FixtureFetcher):
    return ExternalEvidenceAcquisitionService(
        registry=ExternalSourceRegistry.from_yaml(REGISTRY_PATH),
        staging_dir=tmp_path / "external_staging",
        normalized_dir=tmp_path / "normalized",
        fetcher=fetcher,
    )


def test_plan_is_deterministic_and_maps_authorities() -> None:
    registry = ExternalSourceRegistry.from_yaml(REGISTRY_PATH)
    assert tuple(source.key for source in registry.sources) == (
        "abet",
        "orise",
        "bls",
        "onet",
        "nrc",
        "doe",
        "schev",
    )
    planner = EvidenceAcquisitionPlanner(registry)
    fitness = assessment(
        "Accreditation",
        "Workforce Demand",
        "Facilities",
        "Equipment",
        "Historical Precedent",
    )

    first = planner.plan(fitness)
    second = planner.plan(fitness)

    assert first == second
    assert first.missing_domains == tuple(fitness.missing_topics)
    assert first.unmapped_domains == ()
    assert set(first.candidate_authorities) == {
        "ABET",
        "Oak Ridge Institute for Science and Education",
        "U.S. Bureau of Labor Statistics",
        "U.S. Department of Labor O*NET Program",
        "U.S. Nuclear Regulatory Commission",
        "U.S. Department of Energy",
        "State Council of Higher Education for Virginia",
    }
    accreditation = [item.source_key for item in first.items if item.evidence_domain == "Accreditation"]
    assert accreditation == ["abet", "abet"]
    assert "Validation Status\n\nPending" in planner.render_dry_run(first)


def test_unknown_decision_type_does_not_weaken_registry_scope() -> None:
    plan = EvidenceAcquisitionPlanner(
        ExternalSourceRegistry.from_yaml(REGISTRY_PATH)
    ).plan(
        SimpleNamespace(
            decision_type="budget_finance",
            decision_type_label="Budget",
            missing_topics=["Budget"],
        )
    )
    assert plan.items == ()
    assert plan.unmapped_domains == ("Budget",)


def test_canonical_academic_program_fitness_domains_are_all_mapped() -> None:
    fitness = EvidenceFitnessService.evaluate(
        "Should CNU develop a Health Physics academic program?",
        [],
    )
    plan = EvidenceAcquisitionPlanner(
        ExternalSourceRegistry.from_yaml(REGISTRY_PATH)
    ).plan(fitness)

    assert plan.unmapped_domains == ()
    assert plan.decision_type == "academic_program"
    assert plan.missing_domains == tuple(fitness.missing_topics)
    assert plan.estimated_documents == 13
    assert len(plan.candidate_authorities) == 7


def test_stage_validation_and_promotion_preserve_provenance(tmp_path: Path) -> None:
    fetcher = FixtureFetcher()
    acquisition = service(tmp_path, fetcher)
    plan = EvidenceAcquisitionPlanner(acquisition.registry).plan(
        assessment("Accreditation")
    )

    staged = acquisition.stage(plan)
    validations = acquisition.validate(staged)
    promoted = acquisition.promote(staged, validations)

    assert len(staged) == 2
    assert all(item.valid for item in validations)
    assert len(promoted) == 2
    assert len(fetcher.urls) == 2

    record = staged[0]
    provenance = record.provenance()
    assert provenance["issuing_authority"] == "ABET"
    assert provenance["authority_class"] == "accreditation_authority"
    assert provenance["evidence_role"] == "Formal External Standard"
    assert provenance["decision_types"] == ["academic_program"]
    assert provenance["canonical_url"].startswith("https://www.abet.org/")
    assert provenance["retrieval_timestamp"]
    assert provenance["effective_period"]
    assert provenance["version"]

    sidecar = (
        acquisition.staging_dir / record.source_document.relative_path
    ).with_suffix(".html.provenance.json")
    assert sidecar.exists()

    normalized = load_knowledge_object(promoted[record.resource_id])
    assert normalized.source["kind"] == "curated_external"
    assert normalized.metadata["external_provenance"] == provenance
    assert normalized.metadata["evidence_domains"]

    chunk = chunk_document(normalized)[0]
    assert chunk.metadata["issuing_authority"] == "ABET"
    assert chunk.metadata["authority_class"] == "accreditation_authority"
    assert chunk.metadata["evidence_role"] == "Formal External Standard"
    assert chunk.metadata["external_provenance"] == provenance

    result = SimpleNamespace(
        object_type=chunk.object_type,
        citation=chunk.citation,
        metadata=chunk.metadata,
    )
    evidence_class, confidence, rationale = classify_evidence(result)
    assert evidence_class is EvidenceClass.EXTERNAL_STANDARD
    assert confidence == 0.98
    assert "Curated external provenance" in rationale


def test_duplicate_content_is_not_promoted(tmp_path: Path) -> None:
    fetcher = FixtureFetcher(duplicate_content=True)
    acquisition = service(tmp_path, fetcher)
    plan = EvidenceAcquisitionPlanner(acquisition.registry).plan(
        assessment("Accreditation")
    )

    staged = acquisition.stage(plan)
    validations = acquisition.validate(staged)
    promoted = acquisition.promote(staged, validations)

    assert validations[0].valid
    assert not validations[1].valid
    assert validations[1].duplicate
    assert len(promoted) == 1

    repeated = acquisition.validate((staged[0],))
    assert not repeated[0].valid
    assert "already acquired" in " ".join(repeated[0].errors)


def test_stale_or_incomplete_staged_record_fails_validation(tmp_path: Path) -> None:
    acquisition = service(tmp_path, FixtureFetcher())
    plan = EvidenceAcquisitionPlanner(acquisition.registry).plan(
        assessment("Accreditation")
    )
    record = acquisition.stage(plan)[0]
    old_source = replace(
        record.source_document,
        acquired_at=datetime.now(timezone.utc) - timedelta(days=record.max_age_days + 1),
    )
    stale = replace(record, source_document=old_source, version=None)

    validation = acquisition.validate((stale,))[0]
    assert not validation.valid
    assert not validation.fresh
    assert "version" in " ".join(validation.errors)
    assert "refresh-policy" in " ".join(validation.errors)
