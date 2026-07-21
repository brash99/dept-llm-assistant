# Faculty Directory Structure Report

This report characterizes the raw HTML snapshot structurally. It does not extract faculty values, normalize names, infer departments, resolve entities, or create semantic records.

**Snapshot:** `data/acquisition/faculty/raw/2026-07-21`

## 1. Corpus Summary

- Total HTML profile pages: **301**
- Total unique SHA-256 hashes: **301**
- Duplicate files beyond the first copy: **0**
- Average profile page size: **69,827.1 bytes**
- Minimum page size: **61,543 bytes** (`faculty_diegosantiago.html`)
- Maximum page size: **160,036 bytes** (`faculty_johnfinn.html`)

### Duplicate content groups

No byte-identical profile files were detected.

## 2. HTML Structure

### Page title formats

| Title format | Pages | Coverage |
| --- | --- | --- |
| `<profile name> \| Christopher Newport University` | 301 | 100.0% |

### Most common H1/H2 sequences

The profile-name heading is represented as `<profile name>` so the count measures structure rather than individual text.

| H1/H2 sequence | Pages | Coverage |
| --- | --- | --- |
| `h2:<profile name> → h2:biography → h2:teaching → h2:research → h2:selected accomplishments` | 121 | 40.2% |
| `h2:<profile name> → h2:education → h2:teaching → h2:research → h2:selected accomplishments` | 51 | 16.9% |
| `h2:<profile name> → h2:biography → h2:teaching → h2:research` | 49 | 16.3% |
| `h2:<profile name> → h2:education` | 24 | 8.0% |
| `h2:<profile name> → h2:education → h2:teaching → h2:research` | 17 | 5.6% |
| `h2:<profile name> → h2:education → h2:selected accomplishments` | 13 | 4.3% |
| `h2:<profile name> → h2:biography` | 9 | 3.0% |
| `h2:<profile name> → h2:biography → h2:selected accomplishments` | 5 | 1.7% |
| `h2:<profile name> → h2:biography → h2:teaching` | 4 | 1.3% |
| `h2:<profile name> → h2:biography → h2:research` | 2 | 0.7% |
| `h2:<profile name> → h2:education → h2:research` | 2 | 0.7% |
| `h2:<profile name> → h2:education → h2:research → h2:selected accomplishments` | 2 | 0.7% |
| `h2:<profile name> → h2:biography → h2:research → h2:selected accomplishments` | 1 | 0.3% |
| `h2:<profile name> → h2:education → h2:teaching → h2:selected accomplishments` | 1 | 0.3% |

### Common HTML classes

Counts below are pages containing the class within `section.component-faculty-page`, not site chrome or raw class occurrences.

| Class | Pages | Coverage |
| --- | --- | --- |
| `col-12` | 301 | 100.0% |
| `contact-info` | 301 | 100.0% |
| `degrees` | 301 | 100.0% |
| `education` | 301 | 100.0% |
| `email` | 301 | 100.0% |
| `faux-title-caps` | 301 | 100.0% |
| `g-4` | 301 | 100.0% |
| `inline-list` | 301 | 100.0% |
| `job` | 301 | 100.0% |
| `name` | 301 | 100.0% |
| `profile` | 301 | 100.0% |
| `profile-image` | 301 | 100.0% |
| `row` | 301 | 100.0% |
| `phone` | 272 | 90.4% |
| `disciplines` | 250 | 83.1% |
| `research` | 245 | 81.4% |
| `teaching` | 243 | 80.7% |
| `accomplishments` | 194 | 64.5% |
| `accordion` | 194 | 64.5% |
| `accordion-body` | 194 | 64.5% |
| `accordion-button` | 194 | 64.5% |
| `accordion-collapse` | 194 | 64.5% |
| `accordion-header` | 194 | 64.5% |
| `accordion-item` | 194 | 64.5% |
| `cn-accordion` | 194 | 64.5% |

### Common CSS selectors

| Selector | Pages | Coverage | Matched nodes |
| --- | --- | --- | --- |
| `main.cn-page-template-cnu` | 301 | 100.0% | 301 |
| `section.component-faculty-page` | 301 | 100.0% | 301 |
| `section.component-faculty-page .profile` | 301 | 100.0% | 301 |
| `section.component-faculty-page .profile-image img` | 301 | 100.0% | 301 |
| `section.component-faculty-page .contact-info` | 301 | 100.0% | 301 |
| `section.component-faculty-page .contact-info .name` | 301 | 100.0% | 301 |
| `section.component-faculty-page .contact-info .job` | 301 | 100.0% | 301 |
| `section.component-faculty-page .contact-info a[href^="mailto:"]` | 301 | 100.0% | 301 |
| `section.component-faculty-page .contact-info a[href^="tel:"]` | 272 | 90.4% | 272 |
| `section.component-faculty-page .contact-info .inline-list a` | 301 | 100.0% | 663 |
| `section.component-faculty-page .contact-info a[href*="/academics/departments/"]` | 298 | 99.0% | 324 |
| `section.component-faculty-page .bio` | 191 | 63.5% | 191 |
| `section.component-faculty-page .education` | 301 | 100.0% | 301 |
| `section.component-faculty-page .education .degrees` | 301 | 100.0% | 301 |
| `section.component-faculty-page .disciplines` | 250 | 83.1% | 250 |
| `section.component-faculty-page .teaching` | 243 | 80.7% | 243 |
| `section.component-faculty-page .research` | 245 | 81.4% | 245 |
| `section.component-faculty-page .accomplishments` | 194 | 64.5% | 194 |
| `section.component-faculty-page .accomplishments .accordion-item` | 194 | 64.5% | 394 |
| `section.component-faculty-page .accomplishments .facultyData` | 194 | 64.5% | 394 |

### Common metadata tags

Counts are pages containing at least one matching metadata key.

| Metadata selector | Pages | Coverage |
| --- | --- | --- |
| `meta[charset]` | 301 | 100.0% |
| `meta[http-equiv="X-UA-Compatible"]` | 301 | 100.0% |
| `meta[itemprop="name"]` | 301 | 100.0% |
| `meta[name="description"]` | 301 | 100.0% |
| `meta[name="twitter:card"]` | 301 | 100.0% |
| `meta[name="twitter:site"]` | 301 | 100.0% |
| `meta[name="viewport"]` | 301 | 100.0% |
| `meta[property="article:published_time"]` | 301 | 100.0% |
| `meta[property="og:description"]` | 301 | 100.0% |
| `meta[property="og:site_name"]` | 301 | 100.0% |
| `meta[property="og:title"]` | 301 | 100.0% |
| `meta[property="og:url"]` | 301 | 100.0% |

## 3. Common Field Labels and Structural Markers

Several contact fields are encoded by classes or link schemes rather than visible labels. `Department` below means only the presence of a department-path organizational link; no department value is extracted or inferred.

| Field | Structural rule | Pages present | Coverage |
| --- | --- | --- | --- |
| Name | `.component-faculty-page .contact-info .name` | 301 | 100.0% |
| Title | `.component-faculty-page .contact-info .job` | 301 | 100.0% |
| Office | `direct .contact-info child paragraph other than .job` | 269 | 89.4% |
| Phone | `.contact-info a.phone or a[href^="tel:"]` | 272 | 90.4% |
| Email | `.contact-info a.email or a[href^="mailto:"]` | 301 | 100.0% |
| Department | `organizational link whose href contains "/academics/departments/"` | 298 | 99.0% |
| Education | `.education` | 301 | 100.0% |
| Biography | `heading/label exactly "Biography"` | 191 | 63.5% |
| Teaching | `.teaching` | 243 | 80.7% |
| Research | `.research` | 245 | 81.4% |
| Courses | `heading/label exactly "Course" or "Courses"` | 0 | 0.0% |
| CV | `CV/vita link text or URL pattern` | 0 | 0.0% |

## 4. Structural Consistency

- Pages using `section.component-faculty-page`: **301 / 301**
- All pages use the common faculty component shell: **Yes**
- Estimated structural variants: **14**

The variant estimate is intentionally coarse. It fingerprints the faculty component, biography/no-biography layout, Education heading level, Teaching, Research, and Selected Accomplishments. It ignores repeated publication/award items and other content volume, so content differences are not misreported as separate templates.

| Structural variant | Pages | Coverage |
| --- | --- | --- |
| `faculty-component; biography-present; education-h3; teaching; research; accomplishments` | 121 | 40.2% |
| `faculty-component; no-biography-layout; education-h2; teaching; research; accomplishments` | 51 | 16.9% |
| `faculty-component; biography-present; education-h3; teaching; research; no-accomplishments` | 49 | 16.3% |
| `faculty-component; no-biography-layout; education-h2; no-teaching; no-research; no-accomplishments` | 24 | 8.0% |
| `faculty-component; no-biography-layout; education-h2; teaching; research; no-accomplishments` | 17 | 5.6% |
| `faculty-component; no-biography-layout; education-h2; no-teaching; no-research; accomplishments` | 13 | 4.3% |
| `faculty-component; biography-present; education-h3; no-teaching; no-research; no-accomplishments` | 9 | 3.0% |
| `faculty-component; biography-present; education-h3; no-teaching; no-research; accomplishments` | 5 | 1.7% |
| `faculty-component; biography-present; education-h3; teaching; no-research; no-accomplishments` | 4 | 1.3% |
| `faculty-component; biography-present; education-h3; no-teaching; research; no-accomplishments` | 2 | 0.7% |
| `faculty-component; no-biography-layout; education-h2; no-teaching; research; accomplishments` | 2 | 0.7% |
| `faculty-component; no-biography-layout; education-h2; no-teaching; research; no-accomplishments` | 2 | 0.7% |
| `faculty-component; biography-present; education-h3; no-teaching; research; accomplishments` | 1 | 0.3% |
| `faculty-component; no-biography-layout; education-h2; teaching; no-research; accomplishments` | 1 | 0.3% |

### Distinguishing characteristics

- Biography-present pages commonly nest `.education` inside `.bio`, where Education may use an `h3`.
- No-biography pages commonly use `.no-bio` and may present Education as an `h2`.
- Teaching, Research, and Selected Accomplishments are optional structural regions, not guaranteed fields.
- Publication, award, and similar accomplishment lists vary in length within the same outer template.

## 5. Missing Sections

| Section/field | Pages present | Pages missing | Missing coverage |
| --- | --- | --- | --- |
| Office | 269 | 32 | 10.6% |
| Phone | 272 | 29 | 9.6% |
| Email | 301 | 0 | 0.0% |
| Department | 298 | 3 | 1.0% |
| Education | 301 | 0 | 0.0% |
| Biography | 191 | 110 | 36.5% |

A missing structural marker means the field was not located by the stated rule. It does not establish that the real-world information is absent.

## 6. Index Page Analysis

- Profile cards matched by `.cardHolder.cn-funnel a.flex-card.cn-index-funnel.filter-select[href]`: **301**
- Relative profile links: **301**
- Absolute profile links: **0**
- Cards with a `title` attribute: **301**
- Cards with visible text: **301**
- Cards with an image source: **301**
- Cards with image alt text: **301**

### Department organization

No explicit department grouping, department data attributes, or department headings were detected inside `.cardHolder.cn-funnel`. The index is structurally a flat searchable card list; department membership must not be inferred from card order.

### Profile-link representation

Profiles are represented as anchor cards inside `.cardHolder.cn-funnel`, adjacent to the `#facultyList` search controls. The current cards carry URL-relative `href` values, a `title` attribute, visible text, and a nested headshot image. These are index metadata structures only; this report does not extract their values.

| Card class signature | Count |
| --- | --- |
| `flex-card cn-index-funnel filter-select background-image` | 301 |

### Index-only normalization implications

- Use `.cardHolder.cn-funnel a.flex-card.cn-index-funnel.filter-select[href]` as the primary discovery selector.
- Preserve card `title`, visible label, and image metadata as source-level fallbacks only; do not assume they supersede profile-page fields.
- The index supplies no reliable department grouping in its current structure.

## 7. Normalization Recommendations

### Recommended selector order

| Later extraction target | Primary selector | Fallback / caution |
| --- | --- | --- |
| Profile component | `section.component-faculty-page` | Reject or quarantine pages lacking the component rather than parsing global navigation |
| Name | `.component-faculty-page .contact-info h2.name` | Page `<title>` and index card title are fallbacks; compare rather than silently overwrite |
| Job title | `.component-faculty-page .contact-info p.job` | May contain `<br>`-separated multiple roles |
| Email | `.component-faculty-page .contact-info a.email[href^="mailto:"]` | Fall back to a scoped `a[href^="mailto:"]`; never use the footer contact block |
| Phone | `.component-faculty-page .contact-info a.phone[href^="tel:"]` | Fall back to a scoped `a[href^="tel:"]`; global telephone selectors match the site footer |
| Office | `.component-faculty-page .contact-info > p:not(.job)` | Fragile because the current office line has no office-specific class or label; retain source locator and require fallback validation |
| Affiliations | `.component-faculty-page .contact-info ul.inline-list a` | Links may represent departments, colleges, schools, programs, or offices; classify by authoritative URL pattern later, never by list order |
| Department link candidate | `.component-faculty-page .contact-info a[href*="/academics/departments/"]` | Structural candidate only; preserve URL and label and do not infer when absent |
| Biography | `.bio > h2` followed by content within `.bio` | Do not absorb nested `.education`; support `.no-bio` pages |
| Education | `.education` then `.degrees > li` | Heading level varies (`h2`/`h3`) with biography layout; select by class, not heading level |
| Teaching | `.disciplines .teaching` | Optional and free-form |
| Research | `.disciplines .research` | Optional and free-form |
| Accomplishments | `.accomplishments .accordion-item` paired with its collapse body | Categories and list lengths vary; preserve category/source context |
| CV | Link label/URL fallback rules reported above | Low structural reliability; do not treat arbitrary PDF links as CVs |

### Reliability and fallback guidance

- The faculty component, contact block, name, and job classes are the strongest current structural anchors; use measured coverage above as the acceptance baseline.
- Email and phone should be detected by both semantic class and URI scheme. Record absence explicitly.
- Always scope contact selectors to the faculty component; global `.contact-info` and `tel:` selectors also match the common footer.
- Office is structurally weak because it is an unlabeled paragraph. A parser should validate position within `.contact-info` and preserve the raw locator.
- Education must be class-selected because its heading level changes with biography presence.
- Organizational links must not be collapsed into a single department field. Department, college, school, program, and office links can coexist.
- Same outer template does not guarantee the same optional sections. Missing Biography, Education, Research, Teaching, accomplishments, or CV must remain missing.
- Nested paragraph markup and variable accordion content are structural anomalies that favor scoped selectors over sibling-position assumptions.
- Use the index for profile discovery and source-level fallback metadata, not for department inference.
- A future normalizer should retain source filename, SHA-256, exact selector/locator, and snapshot date for every extracted assertion.
