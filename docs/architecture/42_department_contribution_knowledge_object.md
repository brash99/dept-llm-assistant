# Department Contribution Knowledge Object

## Status and scope

`DepartmentContributionKnowledgeObject` is the first concrete specialization
of ISO's [Contribution Ontology](41_contribution_ontology_contracts.md). It is
ISO's computational model of a governed department's institutional function
over an explicit temporal scope.

It is not a report, dashboard, score, narrative, recommendation, or LLM
artifact. Reports will be projections of this object. Reasoning will consume
it. Scenario Modeling may later transform a published baseline into an
explicitly counterfactual object.

No faculty, program, or college contribution specialization is implemented in
this pilot.

## Ontological specialization

```text
ContributionKnowledgeObject<T>
              |
              | T = governed department entity
              v
DepartmentContributionKnowledgeObject
              |
              +-- ContributionAssertion
              +-- ContributionAssertion
              +-- ...
```

The specialization adds no report-shaped department metrics. It constrains the
generic subject to a governed current department or department-equivalent unit.
Its institutional function remains a collection of atomic contribution
assertions with attached evidence, measures, provenance, and temporal scope.

## Version 1 assertions

The deterministic builder can establish the following relationships:

| Predicate | Governed basis |
|---|---|
| `owns_curriculum` | Reviewed subject-prefix ownership records |
| `administers_program` | Resolved current ownership in the Undergraduate Major Registry |
| `delivers_instruction_for` | Existing Department Profile department-owned activity |
| `provides_service_teaching_for` | Existing instructor-home attribution to another governed curriculum owner |
| `contributes_to_llc_requirement` | Existing LLC-only attribution with governed designation tokens |
| `provides_capstone_instruction_for` | A governed major capstone course observed in the Department Profile |

`supports_program` is in the contribution vocabulary but is not inferred by
this builder. Neither curricular resemblance nor the presence of related
courses is sufficient to establish program support.

Absence of an assertion means only that the supplied governed semantic objects
did not establish that relationship. It is not a negative assertion.

## Builder composition

`DepartmentContributionBuilder` consumes existing semantic products:

```text
AcademicUnitRegistry ----------------------+
SubjectOwnershipRegistry ------------------+
UndergraduateMajorRegistry ----------------+--> DepartmentContributionBuilder
UndergraduateMajorCapstoneRegistry --------+              |
DepartmentProfile -------------------------+              v
optional instructional attribution --------+   DepartmentContributionKnowledgeObject
optional LLC-only attribution -------------+
```

The builder does not:

- rediscover faculty identity;
- rebuild the Analytical Workforce;
- parse schedules;
- recalculate Department Profiles;
- reinterpret subject ownership;
- tokenize LLC designations;
- extract majors or capstones;
- allocate unsupported shared-program contribution;
- evaluate institutional importance.

This composition boundary ensures that corrections remain in the governed
semantic service responsible for them.

## Evidence and measures

Every assertion contains at least one `ContributionEvidenceBinding`.
Bindings identify the source semantic objects, their fingerprints, the builder
and version, provenance, and the deterministic derivation basis.

Measures remain properties of assertions. For example:

```text
Department of English
    delivers_instruction_for
        Department of English governed curriculum
            has_measure section_count
            has_measure enrollment
            has_measure student_credit_hours
```

Partial SCH remains a valid known measure with an explicit limitation. Missing
SCH does not erase the instruction relationship.

Service-teaching and LLC mean-annual measures preserve the years and
aggregation inherited from the supplied attribution object. The builder does
not silently change their temporal interpretation.

## Canonical serialization example

The complete serialized object contains an array of assertions. One abbreviated
assertion has this shape:

```json
{
  "contribution_object_type": "department_contribution",
  "contribution_object_id": "department_contribution:department_english:ay_2022_23_to_2024_25:...",
  "entity": {
    "entity_type": "department",
    "entity_id": "academic_unit:department_english",
    "published_name": "Department of English"
  },
  "temporal_scope": {
    "reporting_period": {
      "start": "2022-07-01",
      "end": "2025-06-30",
      "label": "AY 2022-23 to 2024-25"
    }
  },
  "assertions": [
    {
      "assertion_id": "contribution_assertion:academic_unit:department_english:owns_curriculum:ENGL",
      "predicate": "owns_curriculum",
      "object": {
        "entity_type": "instructional_subject",
        "entity_id": "instructional_subject:ENGL",
        "published_name": "English"
      },
      "evidence_bindings": ["..."],
      "measures": [],
      "deterministic_fingerprint": "..."
    }
  ],
  "deterministic_fingerprint": "..."
}
```

The example is structural, not a generated institutional report.

## Determinism and validation

The specialization inherits canonical serialization and SHA-256 fingerprints
from the contribution foundation. The builder:

- sorts profiles and assertions by stable identifiers;
- rejects duplicate Department Profiles;
- rejects non-department entities;
- checks serialized specialization type;
- retains source semantic fingerprints;
- does not mutate input semantic objects;
- reproduces byte-identical JSON from the same governed inputs and temporal
  scope.

Entity-specific reports, APIs, web integration, reasoning, and scenario
transformation remain future consumers and are outside this implementation.

## Developer ontology inspection

`scripts/inspect_department_contributions.py` is a developer inspection entry
point, not a reporting product. It reads existing Department Profiles and
optional existing instructional/LLC attribution semantic outputs, constructs
canonical department contribution objects, and exposes:

- object and assertion identity;
- object-level and assertion-level temporal scope;
- fingerprints;
- governed subject-predicate-object relationships;
- attached measures;
- evidence bindings and source fingerprints;
- explicitly preserved Evidence Fitness categories;
- provenance;
- canonical JSON serialization;
- a structural signature containing predicate and target-entity-type counts.

The inspector adds no narrative, evaluation, ranking, or inferred assertion.
Its human-readable rendering is analogous to examining a reconstructed event:
it exposes exactly what the semantic object contains so the ontology can be
reviewed before downstream reasoning.

Department Profile measures may cover all available schedule history while
service-teaching or LLC attribution objects cover a narrower set of academic
years. The builder therefore preserves assertion-specific reporting periods
inside the broader department contribution object. It does not relabel
historical aggregate measures as though they covered a narrower interval.

## ISO Ontology Explorer

Version 1 of the developer Ontology Explorer is a separate Streamlit
instrument:

```bash
bash scripts/run_ontology_explorer.sh /path/to/canonical/contribution/objects
```

It is intentionally not integrated into the executive web application.

The explorer loads already serialized semantic objects through
`OntologyObjectRepository`. `OntologyExplorerRegistry` dispatches each object
to a registered type adapter. Version 1 registers only
`DepartmentContributionExplorerAdapter`. Future contribution or constitutional
object families can register their own deserializer, hierarchy, graph, and
canonical serialization projections without changing repository loading or
top-level navigation.

```text
canonical semantic-object JSON
             |
             v
OntologyObjectRepository
             |
             v
OntologyExplorerRegistry
             |
             +--> Department Contribution adapter
             +--> future Faculty Contribution adapter
             +--> future Program Contribution adapter
             +--> future Constitutional adapter
```

For the selected canonical object, the instrument exposes:

- governed entity and object identity;
- object-level temporal scope and provenance;
- expandable subject → predicate → object assertions;
- assertion-level temporal scope and qualifiers;
- attached measures;
- complete evidence bindings and available Evidence Fitness;
- deterministic fingerprints;
- exact canonical JSON;
- an experimental directed graph with one edge per assertion.

Predicate and target-type controls filter only the visible event display. They
never alter the canonical object. Unknown JSON object types are ignored and
listed; malformed or fingerprint-invalid supported objects are surfaced as
errors rather than silently displayed.

The graph is not an inferred institutional network. Its nodes and edges are
direct projections of governed entities and `ContributionAssertion` values.
Likewise, the hierarchy performs no summarization, evaluation, or ontology-gap
classification. Ontology engineers inspect the exposed structure and remain
responsible for identifying awkward assertions and missing concepts.
