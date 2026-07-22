# Authoritative Faculty Roster Contract

> Knowledge objects store facts. Services derive meaning.

Public directory, catalog, roster, and schedule evidence cannot establish a
governed effective-dated faculty population. Catalog presence is historical
edition evidence, directory presence is a public snapshot, and teaching is an
assignment rather than an appointment. None reliably supplies appointment FTE,
instructional FTE, tenure status, primary/secondary appointment structure, or
effective employment intervals for every person.

ISO therefore defines an ingestion contract without claiming that an
authoritative HR or Academic Affairs roster currently exists. The contract is
implemented by `AuthoritativeFacultyRosterObservation`,
`FacultyRosterCSVAdapter`, and `config/faculty_roster_schema.yaml`. Source-column
aliases are configurable, while canonical facts and validation rules remain
deterministic.

## Explicit facts only

An observation may preserve institutional identifiers, published names,
effective or snapshot dates, explicit status and appointment category,
academic-unit labels, position numbers, FTE components, rank, tenure status,
primary/secondary designation, and provenance. It never fills missing FTE,
infers active employment, derives tenure from rank, declares a faculty home,
or assigns denominator eligibility.

Appointment FTE describes the published appointment fraction. Instructional
FTE describes an explicitly published instructional allocation. Administrative
FTE is separate. They are not interchangeable, and the contract does not
require their sum to establish workload meaning. Rank likewise does not imply
tenure status.

Rows are classified as accepted, accepted with limitations, quarantined, or
rejected. Invalid dates and missing required facts are rejected. Invalid FTE,
duplicate position records, and identity conflicts are quarantined rather than
repaired. Unresolved identity or unit evidence remains explicit. Deterministic
identity linkage uses institutional identifier, email, exact name, governed
alias, bounded middle-name variation, and unique initials—in that order—with no
fuzzy, probabilistic, or LLM matching.

## Effective dates and readiness

An effective-dated record says what its authority publishes for an interval; a
snapshot says what it publishes as of one date. Neither alone defines an
“active faculty” reporting policy. The readiness audit reports field coverage
and whether future denominator inputs are supported, partial, blocked, or
unsafe to infer. It never calculates a denominator.

This contract strengthens the Evidence Layer, Semantic Layer, and Evidence
Fitness. Scenario Modeling and the Institutional Digital Twin may later consume
reviewed temporal population services, but this sprint does not implement them.

## Protected-data expectations

An operational roster may contain protected personnel information. Acquisition
must use approved access controls, minimum-necessary fields, retention rules,
and restricted storage. Raw authoritative records must not be committed to Git.
Only synthetic, non-personal fixtures belong in the repository. Production
reports should expose aggregate readiness and limited quarantined examples, not
bulk personnel records.
