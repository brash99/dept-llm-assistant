# Faculty Appointment Observations

> Knowledge objects store facts. Services derive meaning.

Faculty identity answers which observations refer to the same person. It does
not say what appointment that person held. The appointment evidence service
therefore emits three separate, source-scoped contracts:

- `FacultyAppointmentObservation` preserves a published faculty title, rank,
  roster category, unit label, identifiers, and temporal context.
- `AdministrativeAppointmentObservation` preserves an explicit administrative
  title and governed unit when deterministically resolvable.
- `EmploymentStatusObservation` preserves an explicit status phrase such as
  emeritus, retired, former, adjunct, visiting, current, or active.

These observations may reference a deterministic `FacultyIdentity`. Ambiguous
identity evidence leaves the reference unset without discarding the source fact.

## Source and temporal meaning

Directory evidence is a dated snapshot, not automatic proof of an effective
employment interval. Catalog faculty and department rosters are catalog-edition
claims and do not prove current employment. An appointment year is retained as
published but is not silently converted into a verified start date. Schedule
instructor evidence is a teaching assignment; it never creates a faculty
appointment, and section-scoped Instructor Type never becomes employment status.

## Bounded normalization

Small explicit vocabularies normalize common faculty ranks, administrative
roles, and status phrases. Original text is always retained. Combined or unknown
titles remain published-only when a unique rank is not supported. Unit labels
use the governed institutional registry; unit association is not renamed as a
faculty-home fact.

Rank is not tenure, full-time status, or FTE. Administrative title is not faculty
home, release time, percentage effort, or denominator exclusion. Program
leadership does not make all participating faculty members employees of the
program.

## Evidence Fitness

The audit distinguishes directory snapshots, catalog-edition claims, roster
claims, explicit status claims, administrative-title claims, teaching
assignments that are not appointments, unresolved identity, and missing temporal
scope. Full-time, tenure-line, FTE, active-faculty, and current-unit denominators
remain blocked or unsafe until stronger effective-dated evidence is observed.

This work strengthens the Evidence Layer, Semantic Layer, and Evidence Fitness.
It does not calculate SCH, workforce metrics, or scenarios.

