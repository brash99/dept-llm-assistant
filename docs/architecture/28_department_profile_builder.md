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

Headline teaching history is the deterministic union of home-faculty
assignments and governed department-owned assignments. It therefore does not
mistake incomplete subject-ownership coverage for an absence of teaching. The
two sources remain separately reported, and an unmapped subject is never
assigned from faculty home.

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

Department profiles assemble institutional state and reconcile every included
identity exactly once. They do not score capacity, rank departments, recommend
reductions, or implement Scenario Modeling. They are the governed input for the
next Department Capacity increment.
