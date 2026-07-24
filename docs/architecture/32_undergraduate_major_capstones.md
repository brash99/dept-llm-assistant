# Governed Undergraduate Major Capstones

> **Status:** Implemented Semantic Layer registry, synchronized July 23, 2026.

> Knowledge objects store facts. Services derive meaning.

The Major → Capstone Registry governs the curriculum relationship between a
stable undergraduate major and the capstone requirement published by an
undergraduate catalog. It is implemented by
`app/undergraduate_major_capstones.py` and
`config/undergraduate_major_capstones.yaml`.

The registry is separate from the
[Undergraduate Major Registry](31_undergraduate_major_registry.md). The Major
Registry establishes the identity, status, degree, names, provenance, and
source-specific ownership assertions of a major. The capstone registry records
only the governed curriculum relationship required to identify culminating
work. It does not copy the full curriculum into the ontology.

## Evidence model

Each major-capstone record retains:

- the governed major identifier;
- the overall requirement type;
- one or more explicit pathways;
- course identifiers where the catalog publishes them;
- non-course requirements where relevant;
- catalog year and page citations;
- source assertions;
- evidence confidence;
- limitations; and
- a deterministic fingerprint.

Catalog text is evidence for a catalog edition. The registry does not invent
effective dates, equivalencies, or historical continuity that the available
catalogs do not establish.

## Supported relationship types

The registry distinguishes:

- `single_required_capstone` — one identified course is required;
- `required_capstone_sequence` — multiple ordered courses form the requirement;
- `multiple_required_capstones` — multiple identified courses are all required;
- `alternative_capstone_choices` — a student completes one of multiple
  governed alternatives;
- `thesis_or_seminar_options` — governed thesis, seminar, or sequence pathways;
- `multiple_pathways` — degree or concentration pathways have materially
  different culminating requirements;
- `no_identifiable_capstone` — an exhaustive reviewed catalog requirement does
  not identify a governed capstone course; and
- `unresolved` — the available evidence does not safely determine the
  relationship.

These types preserve curriculum meaning for later services. They are not
automatically interchangeable counting rules.

## Sequences and multiple requirements

A sequence records every governed required component. A later estimation
service may select the terminal course as a bounded anti-duplication proxy, but
that is a Reasoning Layer method—not a mutation of the curriculum fact.

Likewise, `multiple_required_capstones` records that all named requirements
exist. It does not imply that their enrollments can safely be summed; the same
students may appear in more than one required course.

## Alternatives and thesis/seminar pathways

Alternative courses are recorded only when catalog evidence explicitly permits
them. A thesis/seminar pathway may include a single seminar, a thesis sequence,
or a non-course culminating assessment. If schedule evidence cannot observe the
published requirement, the relationship remains governed while the downstream
estimate remains unavailable.

## Shared capstones

Some capstone courses serve multiple majors or degree pathways. The registry
preserves the shared course relationship. It does not allocate a section’s
enrollment among majors without explicit student-major evidence.

This is a central semantic boundary: course enrollment identifies participation
in a course, not necessarily the major distribution of that participation.

## Unresolved and no-identifiable-capstone cases

`unresolved` and `no_identifiable_capstone` are different:

- `unresolved` means evidence is insufficient or conflicting;
- `no_identifiable_capstone` means the reviewed catalog requirements do not
  identify a capstone course suitable for this relationship.

Neither state is treated as a zero. Both remain visible to validation and
Evidence Fitness.

## Why unsupported allocations are not invented

The registry does not:

- infer a capstone from a high course number or title alone;
- treat every senior seminar, internship, recital, or independent study as a
  major requirement;
- split shared enrollment using department size or historical completions;
- assume every student enrolled in a capstone graduates in that academic year;
- infer a historical rule from the current catalog; or
- use an administrative completion report to redefine catalog requirements.

The deterministic audit in
`scripts/audit_undergraduate_major_capstones.py` verifies registry coverage,
relationship vocabulary, governed course structure, provenance, and
fingerprints.

## Architectural role

The registry supplies a governed Semantic Layer edge:

`Major → requires → Capstone`

Schedule observations may supply:

`Capstone → offered_as → Section`

The [Estimated Graduates observable](33_estimated_graduates.md) derives meaning
from those facts while retaining the limitations of both evidence streams.
