# LLC Designation Governance

ISO preserves the schedule's published `llc_area_raw` text as source evidence.
The Semantic Layer interprets that text through
`config/llc_designations.yaml`; it does not embed CNU curriculum vocabulary in
the SCH service.

The registry records the policy identifier, effective term range, designation
codes, categories, names, inclusion rule, and counting rule. A section is LLC
instruction when at least one discrete, case-normalized token matches the
effective policy. A section carrying multiple designations contributes its SCH
once, while every matched designation and category remains available for later
analysis. Unrecognized tokens are reported and are never silently interpreted.

The YAML file supports multiple documents. If the curriculum changes, append a
new policy document with non-overlapping effective dates instead of modifying
the historical vocabulary. The service requires exactly one applicable policy
for every analyzed term and fails closed on gaps or overlaps.
