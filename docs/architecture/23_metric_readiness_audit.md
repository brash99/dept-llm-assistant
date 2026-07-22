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

## Current evidence position

Schedule Knowledge Objects preserve section credit hours, enrollment, academic
term, status, instructor, Instructor Type, repair provenance, and source rows.
Governed subject ownership can assign supported schedule subjects to academic
workforce units. These facts are necessary but not sufficient for SCH.

Before an SCH service is decision-ready, ISO still needs governed rules for:

- calendar-year versus academic-year versus fiscal-year reporting;
- cancelled and future sections;
- cross-listed sections;
- laboratories and zero-credit components;
- variable-credit and independent-study registration credits;
- team-taught sections; and
- minimum production coverage for enrollment, credit, status, and academic-unit
  mapping.

The audit reports coverage of these inputs but never multiplies enrollment by
credits.

## Faculty observer position

ISO currently has four complementary faculty-related evidence families:

- institutional directory profile snapshots;
- catalog faculty entries;
- catalog department rosters; and
- term- and section-scoped schedule instructor assignments.

They provide published names, some unit labels and titles, catalog appointment
years, snapshot/catalog temporal scope, and teaching assignments. They do not
provide a shared governed person ID, effective-dated appointment status,
appointment FTE, teaching FTE, tenure-line status, or a reliable official
employment history. Schedule `Instructor Type` remains a source assertion about
one section; it is not a timeless faculty-employment fact.

Consequently, SCH per teaching FTE, full-time faculty, instructional faculty,
or tenure-line faculty is blocked. A term-scoped distinct published-instructor
count is available as a name-based analytical proxy, but it is not yet a
governed faculty denominator.

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
`Finance` and `Fine Arts and Art History` remain unresolved because inspected
Mac-accessible evidence does not establish one deterministic interpretation.

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
3. **Reasoning Layer** will eventually calculate approved metrics.
4. **Evidence Fitness** reports whether the required facts and policies are
   adequate.
5. **Scenario Modeling** must consume only governed, fitness-qualified metrics.
6. **Institutional Digital Twin** may later retain effective organizational and
   appointment histories.

The smallest next milestone is policy approval plus production coverage
measurement, followed by a separate reviewed SCH aggregation service and an
authorized effective-dated faculty appointment observer.
