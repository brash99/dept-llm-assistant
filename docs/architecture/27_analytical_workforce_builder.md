# Analytical Workforce Builder

> Knowledge objects store facts. Services derive meaning.

The Analytical Workforce Builder is a Reasoning Layer service. It begins with
identities present in the latest faculty-directory snapshot and applies a
versioned policy to produce two independent decisions: workforce membership
and department assignment.
The result is an inspectable scenario input—not an HR roster, legal employment
assertion, inferred appointment FTE, or final denominator.

Current published instructional ranks can support inclusion. Explicit emeritus,
retired, former, or adjunct-only evidence supports exclusion. Under the default
policy, senior academic administrators, visiting faculty, and unusual titles
are reviewable for workforce membership. Chairs and program directors are not
administrative-only merely because they have leadership roles. Governed
person-specific overrides are separate from policy and preserve review
provenance.

Schedule assignments summarize recent and historical teaching but never create
population membership, prove full-time employment, or exclude someone through
absence. Current directory department evidence outranks historical catalog
evidence. Administrative offices and programs do not become faculty homes;
unsafe or multiple units remain explicit as department-assignment review. A
clearly instructional identity remains included in the workforce when its only
uncertainty is the receiving department.

The workforce population reconciles every starting identity as included,
excluded, or membership-review-required. Department assignment separately
reconciles as resolved, review-required, or not-applicable. Department review
never enters workforce arithmetic. Included-only is the minimum plausible
workforce population; included plus workforce review is the maximum. No central population
is asserted until policy or reviewed overrides define one. Policy sensitivity
reports uncertain visiting, dean/senior-administrator, administrative-only, and
missing-teaching choices. The rules are never adjusted merely to reach 275.

## Reviewed production baseline

The default policy explains which cases require institutional judgment; it is
not the final production disposition. Edward Brash completed the governed
manual review, and the resulting overrides are stored separately from source
evidence and policy logic.

The current validated production baseline contains 282 included analytical
workforce identities with zero remaining workforce-membership decisions and
zero remaining department-assignment decisions. Every included identity has one
governed analytical home. The count emerged from policy plus reviewed
institutional decisions and was not forced to match an approximate target.

Reason codes are dimension-specific. An instructional person with no safe unit
has workforce primary reason `current_directory_instructional_title` and
department primary reason `no_safe_analytical_unit`. This separation is a
prerequisite for later departmental capacity analysis.

This service advances the Reasoning Layer and Evidence Fitness and supplies the
governed analytical denominator used by Department Profiles and workforce
attribution. It does not infer FTE or provide an authoritative HR denominator.
Capacity scores, Scenario Modeling, and reduction recommendations remain
unimplemented.
