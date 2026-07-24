# Estimated Graduates by Major

> **Status:** Implemented, partially estimable Reasoning Layer observable,
> synchronized July 23, 2026.

> Knowledge objects store facts. Services derive meaning.

Estimated Graduates by Major is an independent semantic experiment that uses
observed enrollment in governed capstone sections as a proxy for graduates. It
is implemented by `app/estimated_graduates.py` and
`scripts/build_estimated_graduates.py`.

It is not a graduation record, degree audit, completion census, or replacement
for Institutional Research. Its purpose is to test how much institutional
structure ISO can reproduce from governed curriculum relationships and
schedule evidence alone.

## Evidence chain

The observable uses only:

1. the governed
   [Undergraduate Major Registry](31_undergraduate_major_registry.md);
2. the governed
   [Major → Capstone Registry](32_undergraduate_major_capstones.md); and
3. normalized schedule sections and explicit enrollment.

The derivation is:

`Department → owns → Major → requires → Capstone → offered_as → Section`

`Section enrollment → bounded estimated graduates`

Every output retains the major, academic year, owning unit, capstone sections,
estimation method, confidence, limitations, and deterministic fingerprint.

## Governed methodology

The service:

- locates scheduled sections matching governed capstone course identifiers;
- groups them by academic year;
- uses explicit enrollment only;
- uses the terminal course of a required sequence to reduce duplicate counting;
- sums governed mutually exclusive alternatives only where the registry
  supports that interpretation;
- uses a major-specific capstone where a pathway also contains a shared
  degree-level capstone and the governed rule permits that choice; and
- aggregates estimable major rows to department totals through governed Major
  Registry ownership.

It never substitutes Quentin’s completion totals into the calculation.

## Shared-capstone allocation

A shared capstone section does not reveal how its students divide among majors.
Without student-major evidence, ISO cannot allocate that enrollment safely.
Shared-only capstones therefore remain excluded or unavailable unless a
separate governed major-specific course provides a bounded method.

Department ownership of a shared course is not evidence of each student’s
major.

## Unobserved is not zero

If a governed capstone has no matching section in an academic year, the result
is unobserved or unavailable—not zero graduates. Possible explanations include:

- the capstone was not scheduled in the available evidence;
- the pathway uses a non-course assessment;
- the relevant course identity differs across catalog years;
- students complete the requirement on a different timetable; or
- the normalized schedule evidence is incomplete for that period.

Only an observed section with explicit zero enrollment can support a numeric
zero for that section.

## Evidence Fitness

Fitness is reported categorically:

- higher-confidence estimates have an identifiable governed capstone and
  complete observed terminal-course enrollment;
- sequence and alternative methods disclose their anti-duplication
  assumptions;
- shared, unresolved, or non-course pathways are unavailable;
- department totals disclose excluded or unobserved majors; and
- every estimate remains a proxy rather than an authoritative completion
  count.

The principal unsupported assumptions deliberately avoided are:

- capstone enrollment equals degrees conferred without attrition or timing
  differences;
- every capstone enrollee belongs to the associated major;
- shared-capstone enrollment can be proportionally allocated;
- repeated required courses may be summed without duplicate students; and
- missing schedule evidence means zero.

## Held-out administrative comparison

A July 2026 held-out comparison against Quentin Kidd’s departmental completion
totals found that the independent capstone proxy covered approximately 72% of
institution-wide completions. This is a dated validation result, not a stable
generated table or a universal accuracy rate.

Quentin’s totals are evidence about the observable’s fitness. They are not the
definition of Estimated Graduates and are not used to tune catalog
relationships, ownership, pathway rules, or schedule enrollment. Differences
may expose shared capstones, missing pathways, timing differences, reporting
ownership, or majors whose culminating requirements are not observable as one
course.

## Architectural boundary

ISO does not model Quentin’s report as reality. ISO models majors, capstone
requirements, sections, enrollment, and ownership. The report may then be
explained, validated, or partly reproduced as a consequence of those
institutional facts.

The observable is useful for evidence diagnosis and bounded comparison. It is
not yet suitable as a complete departmental outcome measure or as an
independent basis for faculty-reduction recommendations.
