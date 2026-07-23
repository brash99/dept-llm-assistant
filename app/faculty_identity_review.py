"""Human-governed review of schedule-only to current-workforce identity matches."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from difflib import SequenceMatcher
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, Mapping

import yaml

from app.faculty_identity import (
    FacultyIdentity,
    IdentityAliasRegistry,
    normalize_person_name,
)
from app.reasoning.academic_unit_mapping import AcademicUnitMappingService


DEFAULT_ALIAS_PATH = Path("config/faculty_identity_aliases.yaml")
DEFAULT_REVIEW_PATH = Path("config/faculty_identity_match_reviews.yaml")
REVIEW_DECISIONS = {"approved", "rejected", "needs_more_evidence"}


def _fingerprint(value: Any) -> str:
    return sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class IdentityMatchProposal:
    proposal_id: str
    schedule_identity_id: str
    schedule_name: str
    workforce_identity_id: str
    workforce_name: str
    workforce_academic_unit_id: str | None
    workforce_academic_unit_name: str | None
    score: float
    proposal_reasons: tuple[str, ...]
    schedule_terms: tuple[str, ...]
    schedule_section_count: int
    schedule_prefixes: tuple[str, ...]
    schedule_sch: float
    schedule_observation_ids: tuple[str, ...]
    candidate_email_addresses: tuple[str, ...]
    candidate_profile_sources: tuple[str, ...]
    candidate_directory_names: tuple[str, ...]
    catalog_and_roster_evidence: tuple[Mapping[str, Any], ...]
    prior_decision: str | None
    prior_review: Mapping[str, Any] | None
    deterministic_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FacultyIdentityMatchReviewService:
    """Propose bounded candidates; never merge identities without approval."""

    def __init__(self, minimum_score: float = 55.0):
        self.minimum_score = minimum_score
        self.mapper = AcademicUnitMappingService()

    def propose(
        self,
        objects: Iterable[Mapping[str, Any]],
        identities: Iterable[FacultyIdentity],
        workforce_decisions: Iterable[Mapping[str, Any] | Any],
        prior_reviews: Iterable[Mapping[str, Any]] = (),
    ) -> tuple[IdentityMatchProposal, ...]:
        objects = tuple(objects)
        identities = tuple(identities)
        by_object = {str(item.get("id") or ""): item for item in objects}
        reviews = {
            str(item["proposal_id"]): dict(item) for item in prior_reviews
        }
        decisions = {
            _value(item, "faculty_identity_id"): item
            for item in workforce_decisions
            if _value(item, "workforce_disposition") == "include"
        }
        by_identity = {item.identity_id: item for item in identities}
        workforce = tuple(
            (by_identity[identity_id], decision)
            for identity_id, decision in sorted(decisions.items())
            if identity_id in by_identity
        )
        schedule_only = tuple(
            identity for identity in identities
            if identity.source_observations
            and {item.source_system for item in identity.source_observations}
            == {"schedule"}
        )
        proposals = []
        for schedule_identity in schedule_only:
            schedule_objects = tuple(
                by_object[source.knowledge_object_id]
                for source in schedule_identity.source_observations
                if source.knowledge_object_id in by_object
            )
            schedule_units = {
                result.analytical_academic_unit_id
                for item in schedule_objects
                for result in (
                    self.mapper.map_subject(
                        item.get("subject"), item.get("academic_term")
                    ),
                )
                if result.review_status == "governed"
                and result.analytical_academic_unit_id
            }
            for workforce_identity, decision in workforce:
                score, reasons = _candidate_score(
                    schedule_identity, workforce_identity, schedule_units,
                    _value(decision, "analytical_academic_unit_id"), by_object,
                )
                if score < self.minimum_score:
                    continue
                semantic = {
                    "schedule_identity_id": schedule_identity.identity_id,
                    "workforce_identity_id": workforce_identity.identity_id,
                    "schedule_name": schedule_identity.display_name,
                    "workforce_name": workforce_identity.display_name,
                }
                proposal_id = f"faculty_identity_match:{_fingerprint(semantic)}"
                review = reviews.get(proposal_id)
                unit_id = _value(decision, "analytical_academic_unit_id")
                unit = self.mapper.unit_registry.get(unit_id) if unit_id else None
                emails, profiles, directory_names = _candidate_directory_context(
                    workforce_identity, by_object
                )
                terms = tuple(sorted({
                    str(item.get("academic_term") or "")
                    for item in schedule_objects if item.get("academic_term")
                }))
                prefixes = tuple(sorted({
                    str(item.get("subject") or "").strip().upper()
                    for item in schedule_objects if item.get("subject")
                }))
                evidence = tuple(sorted((
                    {
                        "source_system": source.source_system,
                        "object_type": source.object_type,
                        "observed_name": source.observed_name,
                        "temporal_label": source.temporal_label,
                        "source_path": source.source_path,
                    }
                    for source in workforce_identity.source_observations
                    if source.source_system in {"catalog_faculty", "department_roster"}
                ), key=lambda item: json.dumps(item, sort_keys=True)))
                payload = {
                    **semantic,
                    "proposal_id": proposal_id,
                    "workforce_academic_unit_id": unit_id,
                    "workforce_academic_unit_name": (
                        unit.published_name if unit else None
                    ),
                    "score": score,
                    "proposal_reasons": reasons,
                    "schedule_terms": terms,
                    "schedule_section_count": len({
                        _section_key(item) for item in schedule_objects
                    }),
                    "schedule_prefixes": prefixes,
                    "schedule_sch": round(sum(
                        _explicit_sch(item) for item in schedule_objects
                    ), 6),
                    "schedule_observation_ids": tuple(sorted({
                        str(item.get("id") or "") for item in schedule_objects
                    })),
                    "candidate_email_addresses": emails,
                    "candidate_profile_sources": profiles,
                    "candidate_directory_names": directory_names,
                    "catalog_and_roster_evidence": evidence,
                    "prior_decision": review.get("decision") if review else None,
                    "prior_review": review,
                }
                digest = _fingerprint(payload)
                proposals.append(IdentityMatchProposal(
                    deterministic_fingerprint=digest, **payload
                ))
        return tuple(sorted(
            proposals,
            key=lambda item: (
                item.prior_decision is not None,
                -item.score,
                item.schedule_name.casefold(),
                item.workforce_name.casefold(),
            ),
        ))


def load_match_reviews(path: Path = DEFAULT_REVIEW_PATH) -> tuple[dict[str, Any], ...]:
    path = Path(path)
    if not path.exists():
        return ()
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    reviews = tuple(dict(item) for item in payload.get("reviews") or ())
    proposal_ids = [str(item.get("proposal_id") or "") for item in reviews]
    if any(not value for value in proposal_ids):
        raise ValueError("Identity match reviews require proposal IDs")
    if len(proposal_ids) != len(set(proposal_ids)):
        raise ValueError("Duplicate faculty identity match review")
    if any(item.get("decision") not in REVIEW_DECISIONS for item in reviews):
        raise ValueError("Invalid faculty identity match review decision")
    return reviews


def save_match_review(
    proposal: IdentityMatchProposal,
    decision: str,
    reviewer: str,
    *,
    alias_path: Path = DEFAULT_ALIAS_PATH,
    review_path: Path = DEFAULT_REVIEW_PATH,
    review_date: str | None = None,
    notes: str = "",
) -> None:
    if decision not in REVIEW_DECISIONS:
        raise ValueError(f"Unsupported identity review decision: {decision}")
    if not reviewer.strip():
        raise ValueError("Identity review requires a reviewer")
    reviewed = review_date or date.today().isoformat()
    if decision == "approved":
        _save_governed_alias(proposal, reviewer, reviewed, Path(alias_path))
    review_path = Path(review_path)
    payload = (
        yaml.safe_load(review_path.read_text(encoding="utf-8")) or {}
        if review_path.exists() else {
            "schema_version": 1,
            "registry_id": "cnu.faculty_identity_match_reviews",
            "description": (
                "Institutional decisions on deterministic faculty identity "
                "match proposals."
            ),
        }
    )
    records = {
        str(item["proposal_id"]): dict(item)
        for item in payload.get("reviews") or ()
    }
    records[proposal.proposal_id] = {
        "proposal_id": proposal.proposal_id,
        "schedule_identity_id": proposal.schedule_identity_id,
        "schedule_name": proposal.schedule_name,
        "workforce_identity_id": proposal.workforce_identity_id,
        "workforce_name": proposal.workforce_name,
        "decision": decision,
        "reviewer": reviewer.strip(),
        "review_date": reviewed,
        "notes": notes.strip() or None,
        "proposal_score": proposal.score,
        "proposal_reasons": list(proposal.proposal_reasons),
        "source_type": "institutional_expert",
    }
    payload["reviews"] = [records[key] for key in sorted(records)]
    _atomic_yaml(review_path, payload)
    load_match_reviews(review_path)


def _save_governed_alias(proposal, reviewer, reviewed, path):
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    records = {
        str(item["identity_key"]): dict(item)
        for item in payload.get("identities") or ()
    }
    identity_key = proposal.workforce_identity_id.split(":", 1)[-1]
    existing = records.get(identity_key)
    if existing:
        observed = set(map(str, existing.get("observed_names") or ()))
        observed.add(proposal.schedule_name)
        existing["observed_names"] = sorted(observed, key=str.casefold)
    else:
        records[identity_key] = {
            "identity_key": identity_key,
            "canonical_display_name": proposal.workforce_name,
            "observed_names": sorted(
                {proposal.workforce_name, proposal.schedule_name},
                key=str.casefold,
            ),
            "confidence": 1.0,
            "evidence": {
                "source": (
                    "institutional_review:faculty_identity_match:"
                    f"{proposal.proposal_id.split(':', 1)[-1]}:{reviewed}"
                ),
                "source_type": "institutional_expert",
                "assertion": (
                    "The reviewed schedule and workforce name forms refer to "
                    "the same institutional person."
                ),
                "reviewer": reviewer,
            },
        }
    payload["identities"] = [records[key] for key in sorted(records)]
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)
        temporary = Path(handle.name)
    try:
        IdentityAliasRegistry.load(temporary)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _candidate_score(schedule, workforce, schedule_units, workforce_unit, objects):
    schedule_names = tuple(filter(None, (
        normalize_person_name(value) for value in schedule.observed_names
    )))
    workforce_names = tuple(filter(None, (
        normalize_person_name(value) for value in workforce.observed_names
    )))
    if not schedule_names or not workforce_names:
        return 0.0, ()
    best_score, best_reasons = 0.0, ()
    directory_text = " ".join(
        str(value or "").casefold()
        for source in workforce.source_observations
        for item in (objects.get(source.knowledge_object_id) or {},)
        for value in (
            item.get("email"), item.get("profile_url"),
            (item.get("source") or {}).get("path"),
        )
    )
    for left in schedule_names:
        for right in workforce_names:
            if left.family_name != right.family_name:
                continue
            score, reasons = 35.0, ["exact_family_name"]
            if left.given_name == right.given_name:
                score += 30
                reasons.append("exact_given_name")
            elif (
                min(len(left.given_name), len(right.given_name)) >= 3
                and (
                    left.given_name.startswith(right.given_name)
                    or right.given_name.startswith(left.given_name)
                )
            ):
                score += 22
                reasons.append("given_name_prefix")
            elif (
                left.given_name in right.middle_names
                or right.given_name in left.middle_names
            ):
                score += 22
                reasons.append("given_name_matches_middle_name")
            elif (
                right.given_name in (left.given_name, *left.middle_names)
                or left.given_name in (right.given_name, *right.middle_names)
            ):
                score += 20
                reasons.append("given_name_token_overlap")
            elif left.given_initial == right.given_initial:
                score += 8
                reasons.append("same_given_initial")
            similarity = SequenceMatcher(
                None, left.normalized_name, right.normalized_name
            ).ratio()
            score += round(15 * similarity, 6)
            reasons.append(f"name_similarity:{similarity:.3f}")
            schedule_tokens = {
                left.given_name, *left.middle_names
            } - {"md", "mohammad", "muhammad"}
            if any(
                len(token) >= 3 and token in directory_text
                for token in schedule_tokens
            ):
                score += 15
                reasons.append("schedule_name_token_in_directory_email_or_profile")
            if workforce_unit and workforce_unit in schedule_units:
                score += 15
                reasons.append("governed_schedule_unit_matches_workforce_home")
            candidate = min(round(score, 6), 100.0)
            if candidate > best_score:
                best_score, best_reasons = candidate, tuple(reasons)
    return best_score, best_reasons


def _candidate_directory_context(identity, objects):
    emails, profiles, names = set(), set(), set()
    for source in identity.source_observations:
        if source.source_system != "faculty_directory":
            continue
        item = objects.get(source.knowledge_object_id) or {}
        if item.get("display_name"):
            names.add(str(item["display_name"]))
        if item.get("email"):
            emails.add(str(item["email"]))
        profile = (
            item.get("profile_url")
            or (item.get("source") or {}).get("url")
            or source.source_path
        )
        if profile:
            profiles.add(str(profile))
    return tuple(sorted(emails)), tuple(sorted(profiles)), tuple(sorted(names))


def _section_key(item):
    return "|".join(str(item.get(key) or "") for key in (
        "academic_term", "crn", "subject", "course_code", "section"
    ))


def _explicit_sch(item):
    credits, enrollment = item.get("credits"), item.get("enrollment")
    if isinstance(credits, (int, float)) and isinstance(enrollment, int):
        return float(credits) * enrollment
    return 0.0


def _value(item, name):
    return item.get(name) if isinstance(item, Mapping) else getattr(item, name)


def _atomic_yaml(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)
        temporary = Path(handle.name)
    os.replace(temporary, path)


__all__ = [
    "DEFAULT_ALIAS_PATH", "DEFAULT_REVIEW_PATH",
    "FacultyIdentityMatchReviewService", "IdentityMatchProposal",
    "load_match_reviews", "save_match_review",
]
