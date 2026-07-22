# Catalog-Derived Subject-Ownership Evidence

> Programs consume courses.
>
> Programs do not necessarily own a course prefix.

`config/institutional_units.yaml` stores organizational facts.
`config/subject_ownership.yaml` stores governed instructional-subject ownership
facts. Catalog extraction produces evidence and candidates, not automatic
governance.

## Three semantic states

The catalog pipeline preserves three distinct states:

1. `CatalogSubjectOwnershipObservation` records that course-description headers
   carrying a prefix occur beneath a named catalog section.
2. `SubjectOwnershipCandidate` proposes a possible organizational
   interpretation and preserves ambiguity, exceptions, and conflicts.
3. A reviewed record in `subject_ownership.yaml` is a governed runtime fact.

No CLI option promotes a candidate. Human review must establish the owning and
analytical units, relationship, evidence, effective period, and governance
status.

## Catalog selection and extraction

The selector orders catalog editions using academic-year metadata parsed from
the catalog identity. It selects the latest undergraduate edition, exposes
ties, and permits an explicit historical override. Filesystem modification time
does not participate.

The extractor reads retained catalog PDFs and recognizes anchored
course-description headers such as `BIOL 108.`. It records full course codes,
page locators, section headings, compact header excerpts, source hash, and a
deterministic fingerprint. Prose abbreviations and program requirement lists
without the course-description header form do not become observations.

Catalog Phase 1 normalized academic units and faculty rosters but deliberately
did not retain course descriptions. This new evidence service reads the
retained source catalog; it does not change those normalized Knowledge Objects.

## Units, exceptions, and history

Exact governed names and reviewed exact section aliases may resolve a catalog
section. Loose substring matching is prohibited. Unknown headings stay
unresolved and do not create institutional units.

College Studies motivates a service or centrally administered exception:
course ownership is not the instructor's faculty-home unit. Interdisciplinary
Studies motivates an interdisciplinary exception. Both enter review rather
than an ordinary department mapping. The extractor reports major/minor status
only when an explicit catalog heading such as `Minor in ...` occurs inside the
section; this remains catalog evidence rather than a governed organizational
claim.

IS was removed from subject ownership because Information Science/BSIS is an
academic program, not an observed instructional prefix. The program remains in
`institutional_programs.yaml`. Conversely, PCSE remains a governed historical
SEC prefix even if a future current catalog omits it. Newest-catalog absence is
evidence to review, not an instruction to delete history.

## Evidence Fitness and architecture

Reports compare catalog prefixes, optional schedule prefixes, and governed
ownership. They identify unresolved and exception candidates, conflicting
sections, missing current-catalog support, and schedule-only prefixes.
Candidate generation may be conditionally suitable; automatic governance and
staffing recommendations are insufficient. Workforce assignment remains
conditional on a governed record.

This work strengthens:

1. Evidence Layer — structured observations from retained catalogs;
2. Semantic Layer — typed candidate and governed relationships;
3. Reasoning Layer — deterministic section and registry comparison;
4. Evidence Fitness — explicit coverage and limitations.

It prepares inputs for Scenario Modeling but does not implement workload, FTE,
or staffing recommendations.

Retrieval identifies which facts matter. Analytical services determine what
the full body of facts implies.
