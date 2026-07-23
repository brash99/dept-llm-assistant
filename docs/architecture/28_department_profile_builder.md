# Department Profile Builder

> Knowledge objects store facts. Services derive meaning.

`DepartmentProfile` is an immutable Reasoning Layer object built from the
completed Current Analytical Workforce, governed institutional units, governed
subject ownership, appointment observations, and schedule evidence. It does not
alter source observations or re-decide faculty membership and home assignment.

The profile preserves two different institutional relationships. Workforce home
comes only from the governed analytical-workforce assignment. Instructional
activity comes from observed teaching and governed subject ownership. The
builder therefore reports home-faculty instruction, department-owned subject
instruction, home faculty teaching outside the department, and department
subjects taught by faculty from elsewhere separately.

Headline departmental teaching history comes only from governed
department-owned subjects. Home-faculty assignments remain separately reported
and are never used as a fallback ownership rule. This prevents an incomplete
crosswalk from producing plausible but semantically incomplete departmental
SCH. The production coverage audit lists every observed prefix, its governed
owner, profile target, and any missing or non-department ownership.

The reconciled 282-person production workforce is ready as the analytical
denominator for the August milestone. It remains a public-evidence analytical
baseline rather than an authoritative HR roster. The builder reports
`analytical_workforce_denominator_ready: true` and
`authoritative_hr_denominator_ready: false` so that this limitation remains
visible without blocking profiles.

Enrollment and SCH are reported only for unique sections with explicit source
values. Known enrollment and known SCH remain reportable for covered sections,
while independent coverage counts and strict completeness flags disclose
missing inputs. Values are never imputed. The latest complete academic year requires observed fall
and spring terms and is distinct from the latest observed term.

## SCH completeness

Complete SCH means every unique section in the profile's governed owned-subject
activity has explicit valid enrollment and scalar credits. Partial SCH is the
known sum from SCH-ready sections; it is never presented as the missing total.
The audit reports every non-ready section and independent enrollment, credit,
and SCH-ready coverage.

Repairable incompleteness is limited to deterministic evidence already present:
an explicit duplicate-section value or one uncontested scalar credit value for
the same course and term. A repeated-snapshot credit conflict is also repairable
when the earlier section preserves exactly two explicit values and all later
unambiguous observations for that course publish one of them. In that bounded
revision pattern, the other preserved value is retained as the explicit
pre-revision credit. The repair records both values, the later supporting
observation, the effective term ordering, and its method; it neither invents a
credit nor contains course-specific rules. Repairs retain their method and
evidence key.
Variable-credit courses, conflicting duplicate values, missing enrollment, and
missing credits without a unique explicit source remain irreducible. The
normalized catalog corpus currently has no structured course-credit table, and
the schedule has no governed cross-list identifier, so neither source can be
silently inferred.

The missing-section forensic report lists every non-ready section rather than
only department totals. It records normalized schedule identity, title,
instructor, enrollment and credit status, deterministic reason codes,
recoverability, required additional evidence, systematic patterns, and one
pipeline trace per failure category. Its before/after repair accounting is based
only on explicit duplicate-section consolidation and uncontested course-term
credit consensus.

Department profiles assemble institutional state and reconcile every included
identity exactly once. They do not score capacity, rank departments, recommend
reductions, or implement Scenario Modeling. They are the governed input for the
next Department Capacity increment.
