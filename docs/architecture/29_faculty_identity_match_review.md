# Faculty Identity Match Review

Schedule instructor names and current faculty-directory names may represent the
same person without satisfying the deterministic identity resolver. Examples
include preferred names, reordered given and middle names, and published short
forms. Schedule teaching alone does not establish current workforce membership,
and a likely textual match must not silently merge people.

`FacultyIdentityMatchReviewService` therefore generates review proposals between
schedule-only identities and included Current Analytical Workforce identities.
Candidate generation is bounded by exact family name and deterministic signals
such as name-token relationships, directory email or profile text, and governed
schedule-unit agreement. The reported similarity score prioritizes review; it
never changes an identity.

The Streamlit entry point is:

```bash
streamlit run scripts/review_faculty_identity_matches.py -- \
  --reviewer "Edward Brash"
```

The reviewer can approve, reject, or request more evidence. All decisions are
written immediately to `config/faculty_identity_match_reviews.yaml`. Approval
also adds the reviewed schedule form to the existing governed identity in
`config/faculty_identity_aliases.yaml`. Raw faculty-directory, catalog, roster,
and schedule observations remain unchanged.

On the next identity rebuild, an approved alias joins the source observations
before the analytical workforce is constructed. Workforce attribution then
recognizes the schedule instructor through the governed current-workforce
identity. Rejections and deferrals remain durable review evidence and never
affect identity resolution.
