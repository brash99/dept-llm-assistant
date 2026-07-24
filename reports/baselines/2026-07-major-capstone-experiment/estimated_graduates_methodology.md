# Estimated Graduates by Major — Methodology

> Independent semantic experiment based only on governed majors, governed capstones, and normalized schedule enrollment. These are not official graduation counts.

## Method

1. Normalize governed capstone course identifiers to schedule subject and course number.
2. Deduplicate schedule observations to one section before enrollment is counted.
3. Assign sections to academic years using Fall as the start; Spring, Maymester, and Summer belong to that Fall's academic year.
4. For a single unique capstone, sum section enrollment.
5. For a required sequence, count only the terminal course to avoid counting the same cohort twice.
6. For multiple required capstones, use one major-specific required capstone when exactly one such course exists; never add the shared degree capstone.
7. Sum alternative terminal capstones only when the alternatives are governed and do not also identify another major.
8. Do not estimate when capstone enrollment cannot be allocated to one major, a pathway is unresolved, enrollment is incomplete, or no section is observed.

## Assumptions

- Enrollment in a required terminal capstone is a proxy for students approaching completion of that major.
- Governed alternatives are mutually exclusive for counting purposes.
- The terminal course of a governed sequence is the least duplicative proxy for completion.
- Duplicate instructor observations for one section describe one enrolled class, not multiple student cohorts.

## Unsupported assumptions deliberately not made

- Schedule enrollment contains no student-major identifier.
- Shared capstone enrollment cannot be allocated among majors.
- Capstone enrollment is not proof that every enrollee graduates in the same academic year.
- Absence of an observed capstone section is not treated as zero graduates.
- Course withdrawals, failures, repeated capstones, and delayed graduation are not observable.

## Evidence Fitness

- **High:** a unique, explicitly governed capstone or terminal sequence course with complete observed enrollment.
- **Medium:** a unique major-specific capstone selected from multiple required capstones, or catalog evidence that identifies a culminating course without explicitly calling it a capstone.
- **Unavailable:** shared capstone, unresolved pathway, no identifiable capstone, missing enrollment, or no observed section.
- Even a high-confidence estimate remains a proxy and is not degree-conferral evidence.

## Majors excluded by governed method

- **Accounting** — `excluded_shared_capstone`: One or more capstone courses are shared with another governed major and schedule enrollment has no major field.
- **Anthropology** — `excluded_shared_capstone`: One or more capstone courses are shared with another governed major and schedule enrollment has no major field.
- **Biochemistry** — `excluded_no_identifiable_capstone`: The governed registry identifies no required capstone.
- **Biology** — `excluded_no_identifiable_capstone`: The governed registry identifies no required capstone.
- **Cellular, Molecular and Physiological Biology** — `excluded_no_identifiable_capstone`: The governed registry identifies no required capstone.
- **Classical Studies** — `excluded_no_identifiable_capstone`: The governed registry identifies no required capstone.
- **Computational and Applied Mathematics** — `excluded_shared_capstone`: One or more capstone courses are shared with another governed major and schedule enrollment has no major field.
- **Criminology** — `excluded_shared_capstone`: One or more capstone courses are shared with another governed major and schedule enrollment has no major field.
- **Environmental Studies** — `excluded_shared_capstone`: One or more capstone courses are shared with another governed major and schedule enrollment has no major field.
- **French** — `excluded_shared_capstone`: One or more capstone courses are shared with another governed major and schedule enrollment has no major field.
- **German** — `excluded_shared_capstone`: One or more capstone courses are shared with another governed major and schedule enrollment has no major field.
- **Integrative Biology** — `excluded_no_identifiable_capstone`: The governed registry identifies no required capstone.
- **Interdisciplinary Studies** — `excluded_shared_capstone`: One or more capstone courses are shared with another governed major and schedule enrollment has no major field.
- **International Affairs** — `excluded_shared_capstone`: One or more capstone courses are shared with another governed major and schedule enrollment has no major field.
- **Kinesiology** — `excluded_no_identifiable_capstone`: The governed registry identifies no required capstone.
- **Leadership Studies** — `excluded_no_identifiable_capstone`: The governed registry identifies no required capstone.
- **Marketing** — `excluded_shared_capstone`: One or more capstone courses are shared with another governed major and schedule enrollment has no major field.
- **Mathematics** — `excluded_shared_capstone`: One or more capstone courses are shared with another governed major and schedule enrollment has no major field.
- **Music** — `excluded_unresolved_pathway`: At least one governed pathway lacks an estimable capstone.
- **Organismal and Environmental Biology** — `excluded_no_identifiable_capstone`: The governed registry identifies no required capstone.
- **Political Science** — `excluded_shared_capstone`: One or more capstone courses are shared with another governed major and schedule enrollment has no major field.
- **Sociology** — `excluded_shared_capstone`: One or more capstone courses are shared with another governed major and schedule enrollment has no major field.
- **Spanish** — `excluded_shared_capstone`: One or more capstone courses are shared with another governed major and schedule enrollment has no major field.

## Pathway ambiguities and special handling

- Finance
- Management
- Music is excluded because its BA and BM pathways have different final assessments and at least one pathway lacks a uniquely governed schedule course.
- Shared course examples include BUSN 418, MLAN 490, POLS 490, IDST 490, SOCL 490/498, and the Mathematics alternatives.

## Coverage snapshot

- Academic years: 2020-21, 2021-22, 2022-23, 2023-24, 2024-25, 2025-26, 2026-27
- Current majors: 46
- Methodologically estimable majors: 23
- Excluded majors: 23
- Latest observed academic-year rows (2026-27): 46

Deterministic fingerprint: `171f1fb5dae202e4f4033927aaceeee5484e46d23f063c6a1809dd39bd406774`
