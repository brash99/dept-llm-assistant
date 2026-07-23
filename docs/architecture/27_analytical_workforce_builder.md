# Analytical Workforce Builder

> Knowledge objects store facts. Services derive meaning.

The Analytical Workforce Builder is a Reasoning Layer service. It begins with
identities present in the latest faculty-directory snapshot and applies a
versioned policy to produce two independent decisions: workforce membership
and department assignment.
The result is an inspectable scenario input—not an HR roster, legal employment
assertion, inferred appointment FTE, or final denominator.

Current published instructional ranks can support inclusion. Explicit emeritus,
retired, former, or adjunct-only evidence supports exclusion. Senior academic
administrators, visiting faculty, and unusual titles remain reviewable for
workforce membership. Chairs and program directors are not
administrative-only merely because they have leadership roles. Governed
person-specific overrides are separate, empty by default, and preserve review
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

Reason codes are dimension-specific. An instructional person with no safe unit
has workforce primary reason `current_directory_instructional_title` and
department primary reason `no_safe_analytical_unit`. This separation is a
prerequisite for later departmental capacity analysis.

This service advances the Reasoning Layer and Evidence Fitness and prepares a
governed denominator candidate for later departmental capacity metrics and
Scenario Modeling. SCH, FTE, capacity, and reduction recommendations remain
outside this sprint.
