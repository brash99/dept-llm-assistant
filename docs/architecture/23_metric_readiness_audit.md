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
units without current references. The current unit registry does not model
effective dates or typed historical-name relationships, so historical
reorganizations remain explicit Evidence Fitness limitations.

Published unit labels are resolved with bounded deterministic precedence:
canonical name, governed alias, cleaned canonical/alias, then a boundary-aware
embedded governed phrase. Embedded matching rejects competing units and never
uses unrestricted fuzzy similarity. Degree history, institutions, and prose
after an identifiable unit phrase are parser contamination; they do not become
ontology aliases.

The current registry includes the departments required by governed semantic
scopes. The former Department of Physics, Computer Science and Engineering is
a distinct deprecated historical unit, not an alias for current SEC. Parent
relationships remain unset where repository evidence does not establish them.

## Emeritus and emerita

Explicit published `emeritus` or `emerita` status is preserved in its source
observation and produces a derived `active_workforce_eligible = false`
assessment. Such observations remain available for historical retrieval, but
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
