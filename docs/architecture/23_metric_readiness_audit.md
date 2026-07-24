# Institutional Metric Readiness Audit

> Knowledge objects store facts. Services derive meaning.

`scripts/audit_metric_readiness.py` inspects three prerequisites for governed
institutional metrics without calculating those metrics:

1. institutional-unit governance and references;
2. faculty-observation capabilities and gaps; and
3. evidence readiness for SCH numerators and faculty denominators.

The audit belongs to the existing Semantic Layer and Evidence Fitness work. It
does not add an architectural layer, implement Scenario Modeling, or turn
schedule observations into employment records.

## Original readiness question

Schedule Knowledge Objects preserve section credit hours, enrollment, academic
term, status, instructor, Instructor Type, repair provenance, and source rows.
Governed subject ownership can assign supported schedule subjects to academic
workforce units. The first readiness audit correctly treated these facts as
necessary but not sufficient for a governed SCH metric.

The original blockers included governed rules for:

- calendar-year versus academic-year versus fiscal-year reporting;
- cancelled and future sections;
- cross-listed sections;
- laboratories and zero-credit components;
- variable-credit and independent-study registration credits;
- team-taught sections; and
- minimum production coverage for enrollment, credit, status, and academic-unit
  mapping.

The audit itself remains an Evidence Fitness diagnostic and does not calculate
SCH. Later Reasoning Layer services resolved the bounded calculation and
reporting questions required by Department Profiles. They now derive SCH only
from explicit scalar credits and enrollment, deduplicate governed section
identity deterministically, retain partial input coverage, and expose every
unrepaired failure rather than imputing values.

Production Department Profile validation currently reports complete SCH input
coverage across all 18 governed profiles for the available schedule evidence.
That resolves the former SCH-construction blocker; it does not make every
possible institutional SCH definition equivalent.

ISO now preserves two separate department-level interpretations:

- **curriculum-owned SCH**, assigned through governed subject-prefix ownership;
- **workforce-attributed SCH**, assigned through an eligible analytical
  workforce instructor's governed home and otherwise through an explicit
  prefix-owner fallback.

Reporting periods, LLC-only subsets, and administrative comparisons select
among governed views; they do not rewrite schedule evidence or subject
ownership.

## Faculty observer position

ISO currently has four complementary faculty-related evidence families:

- institutional directory profile snapshots;
- catalog faculty entries;
- catalog department rosters; and
- term- and section-scoped schedule instructor assignments.

They provide published names, some unit labels and titles, catalog appointment
years, snapshot/catalog temporal scope, and teaching assignments. The Faculty
Identity service can connect supported observations while reporting ambiguity,
but most sources still do not provide a shared authoritative person ID. They do
not provide effective-dated appointment status,
appointment FTE, teaching FTE, tenure-line status, or a reliable official
employment history. Schedule `Instructor Type` remains a source assertion about
one section; it is not a timeless faculty-employment fact.

Consequently, SCH per authoritative teaching FTE, HR-confirmed full-time
faculty, or tenure-line faculty remains blocked. Identity establishes who, and
the appointment evidence service preserves what dated sources explicitly
publish. ISO now also has an institutionally reviewed 282-person analytical
workforce with governed home assignments. That population is ready for the
August analytical baseline, but it is not an effective-dated HR roster and
does not supply appointment or instructional FTE.

## Institutional-unit limitations

The deterministic unit audit reports governed units, parent/subordinate
relationships, aliases, references from subject ownership and normalized
Semantic Identity, unknown unit IDs, unresolved published labels, and governed
units without current references. The registry preserves distinct deprecated
historical units and explicit successor references where reviewed evidence
supports them. Effective ranges remain unset rather than guessed when governed
dates are unavailable.

Published unit labels are resolved with bounded deterministic precedence:
canonical name, governed alias, cleaned canonical/alias, then a boundary-aware
embedded governed phrase. Embedded matching rejects competing units and never
uses unrestricted fuzzy similarity. Degree history, institutions, and prose
after an identifiable unit phrase are parser contamination; they do not become
ontology aliases.

The current college-level structure distinguishes the three formal colleges
from the Joseph W. Luter, III School of Business: Luter remains formally an
independent school while carrying a college-equivalent analytical rollup role.
Its former combined Accounting, Finance, Management and Marketing department
is a distinct deprecated historical unit, not either current Luter department.
Historical biology and arts departments likewise remain distinct from their
current successors. Parent relationships remain unset where reviewed evidence
does not establish them.

Four named graduate programs are governed program-level units. A bounded
`Graduate Program Director -` cleaner preserves the role title and resolves
the remaining text to the program; it never turns the administrative role into
a department. Honors is a university-wide curriculum-owning program, not a
faculty-home or conventional denominator unit. Graduate Studies is an academic
coordination unit. Curricular ownership, faculty-home membership, conventional
faculty denominators, and analytical rollups are separate eligibility facts.
Final reviewed aliases resolve Finance and Management to their current Luter
departments; Music, Performing Arts, and the published typo `Performimg Arts`
to the current Department of Music, Theatre, and Dance; and Fine Arts and Art
History to its current School of the Arts department. The exact parser fragment
`and Marketing Department` is cleaned by a bounded governed rule rather than
fuzzy matching. Neuroscience is an interdisciplinary curriculum-owning program,
while the Provost and ORCA are governed administrative units; none is a
faculty-home or conventional denominator unit.

## Emeritus and emerita

Explicit published `emeritus` or `emerita` status is preserved in its source
observation and produces a derived `active_workforce_eligible = false`
assessment. This exclusion remains primary even when the underlying historical
unit phrase is unresolved, so those records do not inflate active-workforce
mapping failures. Such observations remain available for historical retrieval, but
are excluded by default from active faculty populations, instructional faculty
denominators, workforce capacity, teaching-load analysis, current staffing,
and scenario inputs. The rule is based only on explicit structured published
text; age, appointment year, and absence of teaching are never substitutes.

## Six-layer role

1. **Evidence Layer** supplies schedule, catalog, roster, and directory facts.
2. **Semantic Layer** governs institutional units and subject ownership.
3. **Reasoning Layer** derives the reviewed analytical workforce, Department
   Profiles, curriculum-owned and workforce-attributed SCH, LLC SCH, and
   related timelines and comparisons.
4. **Evidence Fitness** reports whether the required facts and policies are
   adequate.
5. **Scenario Modeling** must consume only governed, fitness-qualified metrics.
6. **Institutional Digital Twin** may later retain effective organizational and
   appointment histories.

The reviewed analytical population and complete department SCH aggregation
resolve the original public-evidence baseline questions. They remain distinct
from an authoritative HR denominator. Scenario Modeling, governed
substitutability and capacity assumptions, financial effects, and an authorized
effective-dated faculty appointment source remain unresolved.
