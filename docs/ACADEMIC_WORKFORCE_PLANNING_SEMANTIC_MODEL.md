# Academic Workforce Planning Semantic Model

## Purpose and milestone boundary

This document defines the smallest useful Semantic Layer for the August 1, 2026 Academic Workforce Planning milestone. It is grounded in the current ISO implementation and the benchmark:

> If CNU reduces full-time faculty from roughly 275 to 250, which departments should lose positions?

The benchmark is institution-wide, comparative, and scenario-dependent. A defensible response requires more than documents that mention faculty or enrollment. ISO must know which institutional entities and functions are affected, which quantities were observed for which unit and period, which dependencies are evidenced, and which conclusions remain assumptions or derived judgments.

The design follows the permanent architecture:

1. Evidence Layer
2. Semantic Layer
3. Reasoning Layer
4. Evidence Fitness
5. Scenario Modeling
6. Institutional Digital Twin

Layers 1–5 are in scope for the milestone. Layer 6 is not a design target for this increment. The model deliberately avoids a comprehensive university ontology.

The governing principle is:

> **Knowledge Objects store facts. Services derive meaning.**

Accordingly, the model stores identity, organization, designations, assignments, measurements, constraints, source assertions, and provenance. It does **not** store department rankings, recommendations, indispensability, vulnerability, spare capacity, replaceability, strategic value, or reduction decisions as factual properties.

## Repository baseline

The current implementation already provides useful but disconnected pieces:

- `KnowledgeObject`, `Document`, and `ConstitutionalKnowledgeObject` in `app/knowledge.py` and `app/constitution/objects.py` provide document-centered persistence and provenance.
- `ProgramEntity` and `ProgramCatalog` in `app/control_plane/` represent a small asserted program catalog. Department and school are currently string properties.
- `InstitutionalEntity`, `InstitutionalRelationship`, and `EvidenceReference` in `app/observatory/topology/` provide typed nodes and directed, evidence-capable relationships. The bootstrap graph is intentionally limited and largely course-agnostic.
- `ACADEMIC_WORKFORCE_PLANNING_TOPICS` in `app/observatory/evidence_fitness.py` defines the eight canonical workforce domains.
- `app/observatory/workforce_evidence_scope.py` qualifies support by directness, decision scope, authority role, document-family breadth, and temporal coverage.
- Decision Readiness evaluators state required evidence such as department-level student credit hours, course-section enrollments, faculty FTE, teaching assignments, service-course enrollments, accreditation constraints, financial effects, and post-line-loss coverage.
- Dashboard V2 defines the canonical LLC Core Requirements and Areas of Inquiry and has `InstitutionalParticipationProfile`, `ParticipationFunction`, and `ParticipationRelationship` presentation contracts. Function-level substitutability uses explicit Unknown and insufficient-evidence states.
- The Decision Brief service consumes retrieved evidence, Evidence Fitness, constitutional orientation, and a topology impact summary. It does not consume structured unit profiles or scenario results today.
- `config/institutional_programs.yaml` contains six programs, not a comprehensive program/unit catalog. `app/observatory/topology/bootstrap.py` contains a small curated set of departments, programs, and coarse curriculum nodes.
- The local Git checkout contains no operational faculty, course-section, workload, enrollment, room-capacity, or budget dataset under `storage/`. Production evidence may exist on the A100, but the repository contracts do not currently normalize it into the semantic facts required here.

Two current limitations are especially important:

1. The topology can say that Physics contributes to the Liberal Learning Core, but it cannot identify the designated courses, offerings, seats, enrollments, SCH, qualifications, or feasible alternatives behind that edge.
2. AWP-4 can render an evidence-backed alternative provider when one is supplied, but no service currently derives that provider from capacity, qualification, curricular, and constraint facts.

## Decision Requirements Derived from Quentin’s Benchmark Question

The benchmark asks for a distribution of 25 position reductions, not merely whether evidence about faculty exists. Working backward, ISO requires a comparable profile for every academic unit, explicit institutional obligations, and a scenario calculation for the loss or reassignment of positions. Until those inputs exist, the correct output remains an evidence-gap statement rather than a ranking.

The table uses the repository's exact eight Academic Workforce Planning domain names.

| Existing Evidence Fitness domain | Relevant entities | Required facts and observations | Required relationships | Acceptable evidence | Missing-evidence behavior | August 1 priority |
| --- | --- | --- | --- | --- | --- | --- |
| **Instructional Demand** | Department, Course, Course Offering, Curricular Requirement, enrollment population | Multi-term sections, seats offered/filled, waitlists if available, SCH, class size, modality, course level, requirement/designation contribution, majors/nonmajors | Department delivers Course; Offering instance of Course; Course satisfies requirement; Offering serves population | Registrar schedule and census enrollment extracts; official catalog; authoritative LLC designation registry | Report the units/terms/metrics absent; do not infer demand from a catalog listing or one snapshot | **Essential** |
| **Faculty Capacity** | Faculty Position, Faculty Member, Department, Course Offering, Institutional Function | Position FTE/status, filled/vacant state, member-position occupancy, assigned teaching/workload, qualifications, overload/adjunct commitments, effective period | Position belongs to Department; Member occupies Position; Member teaches Offering; Member qualified for Course; Position supports Function | Authoritative HR position roster; provost workload/assignment data; validated qualification records | Distinguish unknown capacity from zero capacity; do not infer available workload from headcount | **Essential** |
| **Service Teaching Dependence** | Course, Offering, Program, Department, LLC/AOI requirement, population | Nonmajor enrollment, prerequisite role, required/service-course status, sections/seats/SCH delivered to other programs, LLC/AOI contribution | Course supports Program/Department; Program depends on Course; Course satisfies LLC/AOI; Department provides quantified contribution | Registrar course/program mappings; degree audits; catalog requirements; enrollment by student program; LLC designations | Name each unmapped dependency; do not infer service teaching from course title or department name | **Essential** |
| **Accreditation and External Constraints** | Program, Accreditation/Regulatory Requirement, Department, Faculty Position, Course, Institutional Function | Formal requirement text, applicability, effective period, local compliance observation, qualification/minimum coverage constraints | Program subject to Requirement; Function/Course/Position supports compliance | Formal accreditor/regulator source plus authoritative local applicability and compliance records | Distinguish formal rule, local self-study assertion, current practice, and unknown compliance margin | **Essential where applicable** |
| **Enrollment Trends** | Program, Department, Course, enrollment population, Observation | Multi-year majors, applications, yield, retention, completions, course enrollment, SCH, population definition and denominator | Observation measures entity/population; Course serves Program/population | Registrar/IR census series with consistent definitions and periods | A snapshot remains a snapshot; report missing years and incomparable denominators | **Essential** |
| **Financial Implications** | Faculty Position, Department, Program, Offering, Facility, Scenario Assumption | Compensation/benefit cost, adjunct or overload replacement cost, section cost, revenue effects, transition cost, effective period | Cost observation applies to Position/Offering/Department; scenario changes Position | Finance/HR operating records and explicit scenario assumptions | Report no decision-specific financial model; do not translate generic budget language into savings | **Essential for a recommendation; high-value for initial model** |
| **Strategic Priority Alignment** | ConstitutionalKnowledgeObject, Department, Program, Institutional Function | Authoritative institutional commitments and evidence-backed links to supported functions | Function/Program relates to constitutional principle through a service-derived alignment explanation | Strategic Compass and other constitutional sources kept separate from empirical operating evidence | Report orientation without claiming operational proof or a department score | **Essential, already partially implemented** |
| **One-Line Loss Scenario** | Faculty Position, Member, Department, Offering, Program, Requirement, Function, constraints, Scenario Assumption | Position removed/reassigned and effective term; affected assignments; residual qualified coverage; section/seat/SCH loss; alternative capacity; cost and constraints | All core staffing, course, requirement, dependency, and support relationships | Structured facts above plus explicit operator scenario assumptions | Report which effects cannot be calculated and why; never convert missing alternatives into “no alternative exists” | **Essential Layer 5 consumer of this model** |

LLC and Area of Inquiry capacity is not a ninth optional domain. It is a central component of Instructional Demand, Service Teaching Dependence, Faculty Capacity, institutional dependency within One-Line Loss Scenario, and—where breadth and mission are implicated—Strategic Priority Alignment.

## Semantic boundary and property classes

Every proposed value must be assigned one of these semantic classes:

| Property class | Meaning | Storage rule |
| --- | --- | --- |
| **stable identity fact** | Identifier or durable identity label | May be stored in an asserted registry with provenance |
| **organizational fact** | Current or effective-dated institutional structure, ownership, designation, assignment, or policy applicability | Store with source and effective period; do not assume permanence |
| **time-bounded observation** | Measured quantity or state for a defined period, scope, and denominator | Store through the shared observation contract with provenance |
| **source assertion** | A statement made by a source whose truth or applicability is not independently established | Preserve attribution, locator, role, and effective scope |
| **scenario assumption** | A value introduced for a hypothetical alternative | Store only in scenario context, never as current institutional state |
| **constitutional fact** | An identified institutional value or commitment | Preserve in the separate constitutional channel |
| **service-derived assessment** | Meaning computed from facts, assertions, and assumptions | Return from a service with explanation; do not persist as an unquestioned entity property |

“Current” is never a substitute for a date or term. Organizational facts may change and therefore require `effective_from`, `effective_until`, or `as_of` when they affect a decision.

## Proposed entity inventory

Not every entity should become a `KnowledgeObject` subclass. For August 1, small typed registry records and adapters are preferable for stable identities; a shared observation record is preferable for measurements; existing Documents remain the provenance-bearing source containers.

| Entity name | Purpose in Academic Workforce Planning | Required factual properties | Optional properties | Temporal properties | Source/provenance requirements | Existing repository representation | Recommended August 1 representation | Deferred post-August representation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Institution** | Establish the organizational and policy scope of the comparison | ID, official name, short name | System identifiers | Effective identity/name period if changed | Authoritative institutional source | Name in constitutional config; `EntityType.INSTITUTION` exists but is not populated | One registry record/`EntityRef`; not a new KO subclass | Rich institutional hierarchy root |
| **College or School** | Group departments and expose roll-up constraints | ID, name, unit type, parent institution | dean/admin codes | Effective-from/to | Authoritative organization chart or HR/academic master data | Program `school` string; `EntityType.COLLEGE`; AWP-4 `college` metadata | `AcademicUnitRecord` with type `college` or `school` | Full reorganizational history |
| **Department** | Primary comparable unit and owner/deliverer of positions, courses, programs, and functions | ID, name, unit type, parent college/school, active status | local codes, aliases | Effective-from/to | Authoritative organization/HR/catalog source | Topology department nodes; strings in ProgramEntity/AWP-4 | `AcademicUnitRecord` with canonical ID plus crosswalk to topology/program strings | General organizational-unit ontology |
| **Academic Program** | Represent owned obligations, demand, outcomes, and constraints | ID, name, status, degree/credential type, owning/delivering unit IDs | aliases, catalog year, CIP, modality | Effective status and catalog period | Official catalog/program inventory | `ProgramEntity` and YAML catalog; topology program nodes with different IDs | Reuse `ProgramEntity` through an adapter adding canonical unit references and evidence | Versioned curriculum/program-offering model |
| **Faculty Position** | Primary unit of attrition/removal/reallocation scenarios | ID, home department, position type, authorized FTE, filled/vacant state | rank/discipline allocation, funding source, tenure eligibility | State as-of date; occupancy intervals; authorization period | Authoritative HR/position-control source; restricted access | Only phrases/keywords and AWP-4 counts; no contract | `FacultyPositionRecord`; scenario operations target positions | Full position lifecycle and funding history |
| **Faculty Member** | Preserve qualifications, assignments, workload, and specialized functions needed to evaluate position consequences | Internal ID, employment status, current position link(s) | credentials, expertise assertions, appointment type | Employment/occupancy/qualification/assignment intervals | Authoritative HR, credential, and workload sources with privacy controls | Implicit in documents; no entity contract | Minimal `FacultyMemberRecord`, preferably pseudonymous outside restricted services | Rich person profile only if governance and privacy justify it |
| **Course** | Identify the curricular object owned/delivered by units and satisfying requirements | ID (subject/number plus catalog identity), title, credits, owning/delivering unit, active status | description, level, prerequisites, repeatability, lab flag, nonmajor accessibility | Catalog/effective period | Official catalog and curriculum records | Implicit text; no course entity | `CourseRecord` registry | Versioned course/outcome ontology |
| **Course Offering or Section** | Connect a course to term, instructor, schedule, capacity, enrollment, room, and modality | ID, course ID, term, section, delivering unit, modality, cap, status | schedule, room/facility, cross-list group | Term/date range and census date | Registrar schedule; room schedule; assignment data | No entity; metrics named in Evidence Fitness | `CourseOfferingRecord`; observations carry changing census values | Detailed meeting/session and cross-list model |
| **Curricular Requirement** | Represent requirements that courses can satisfy without implying interchangeability | ID, name, kind, governing curriculum/program, active status | formal outcomes/function statement, minimum credits | Catalog/effective period | Authoritative catalog, degree audit, LLC governance record | Coarse topology curriculum nodes; LLC constants in Dashboard V2 | One `CurricularRequirementRecord` with kinds `program`, `llc_core`, `llc_aoi` | Full rule expression and degree-audit logic |
| **LLC Core Requirement** | Identify one canonical LLC Core Requirement | Same as Curricular Requirement; kind=`llc_core` | approved outcomes | Effective designation period | Authoritative LLC governance/catalog source | Five names in Dashboard V2 constants only | Rows in the requirement registry; no subclass | Versioned governance and outcome mappings |
| **Area of Inquiry** | Identify one canonical LLC Area of Inquiry | Same as Curricular Requirement; kind=`llc_aoi` | approved outcomes and breadth intent | Effective designation period | Authoritative LLC governance/catalog source | Five names in Dashboard V2 constants only | Rows in the requirement registry; no subclass | Rich curricular-function semantics |
| **Student or Enrollment Population** | Define who is counted in an observation (majors, nonmajors, cohort, course takers) | Population definition and inclusion rules | program, level, residency, demographic dimensions where permitted | Census/as-of period | Registrar/IR definition and source | Implicit in retrieved reports and keyword domains | A dimension/scope record referenced by Observation, not a KO per cohort | Reusable governed cohort definitions if needed |
| **Accreditation or Regulatory Requirement** | Preserve formal constraints separately from local assertions and compliance judgments | ID, authority, requirement text/locator, applicability target, requirement type | thresholds, reporting cycle | Effective-from/to and version | Formal standard plus evidence of local applicability | Accreditor strings on ProgramEntity; topology type; EvidenceClass/role logic | `ConstraintRecord` plus `subject_to` relationship; local compliance remains an observation/assertion | General policy/constraint ontology |
| **Institutional Function or Capability** | Name the function whose continuity matters when capacity changes | ID, name, function type, scope | service level, owning/stewarding unit | Effective period | Authoritative operating/curricular evidence | AWP-4 `ParticipationFunction`; coarse topology rationale | `InstitutionalFunctionRecord` for only milestone-critical teaching, advising, lab, accreditation, and program functions | Broader capability catalog |
| **Instructional Capacity Observation** | Carry measured workload, sections, seats, enrollments, and SCH with scope and denominator | Shared Observation fields plus capacity metric | dimensions and collection method | Required observation period/as-of/census | Exact source ID and locator; unit/definition required | Evidence Fitness counts and prose only | Use shared `InstitutionalObservation`; not a separate KO subclass | Larger temporal observation store |
| **Evidence Reference** | Link every asserted property, observation, and relationship to source material | Source KO ID, label, locator, evidence role | extraction method, note, assertion ID | Source/effective dates as applicable | Must resolve to a normalized object or curated authoritative record | Topology `EvidenceReference`; chunk citations; acquisition provenance | Extend/reuse a neutral evidence-reference contract | Claim-level provenance graph |
| **Scenario Assumption** | Keep hypothetical capacity, cost, timing, overload, adjunct, reassignment, or course-cap changes out of current facts | ID, scenario ID, parameter/subject, assumed value, unit, rationale | author, sensitivity range | Scenario/effective period | Explicit operator/user provenance | `DecisionContext.metadata` can carry untyped values; no scenario contract | Minimal typed assumption input to Layer 5 | Full scenario/version/comparison model |

### Faculty Position versus Faculty Member

Workforce-reduction scenarios should reason primarily over **Faculty Positions**, not employees. The benchmark describes reduction through attrition; the institutional action is therefore to leave a position vacant, abolish a line, reduce its FTE, or reallocate it after an incumbent departs. This avoids turning ISO into an employee-ranking system and aligns the scenario unit with budgets and authorized capacity.

Faculty Member facts remain necessary because the consequence of changing a position depends on the incumbent's or potential assignee's:

- documented qualifications;
- current course assignments;
- workload commitments;
- advising, research, accreditation, governance, laboratory, or partnership functions;
- occupancy interval for the position.

Those facts support a position-level scenario; they do not authorize a person-level value score. Retirement or departure dates are sensitive source assertions or scenario assumptions unless established in authorized operating records. Names are not required for most Decision Brief outputs; stable restricted identifiers are sufficient.

## Proposed property classification

The following table classifies every property proposed for the August model. Optional post-August properties from the entity inventory are intentionally excluded from the initial contract unless marked.

| Entity/contract | Property | Classification | Notes |
| --- | --- | --- | --- |
| Institution | `id`, official name, short name | stable identity fact | Source-backed registry values |
| Academic Unit | `id`, name, unit type | stable identity fact | Unit type is department/college/school for this slice |
| Academic Unit | parent institution/unit, active status | organizational fact | Effective-dated; not permanent |
| Academic Program | `id`, name, credential type | stable identity fact | Adapt current `ProgramEntity` |
| Academic Program | status, owning/delivering units | organizational fact | Effective-dated catalog fact |
| Faculty Position | `id`, position type | stable identity fact | Position is distinct from occupant |
| Faculty Position | home unit, authorized FTE, filled/vacant state | organizational fact | State requires as-of/effective period; FTE changes should also be observable |
| Faculty Member | restricted `id` | stable identity fact | Names are unnecessary for the milestone output |
| Faculty Member | employment status, position occupancy | organizational fact | Effective-dated and privacy-controlled |
| Faculty Member | credential/qualification record | source assertion | Qualification for a specific course is evidenced; final sufficiency may require service interpretation |
| Faculty Member | assigned teaching/workload/function | organizational fact | Effective term or workload year required |
| Course | `id`, title, credits | stable identity fact | Identity should survive individual offerings |
| Course | owner/deliverer, active status, prerequisites, LLC/AOI designation | organizational fact | Effective catalog/designation period required |
| Course | description and approved learning outcomes | source assertion | Preserve catalog/governance wording and version |
| Course Offering | `id`, course ID, term, section | stable identity fact within term | Offering identity is term-bound by design |
| Course Offering | delivering unit, instructor assignment, modality, schedule, room, cap, status | organizational fact | Effective for offering/term; changes need as-of date |
| Curricular Requirement | `id`, name, kind | stable identity fact | One contract covers program, LLC Core, and AOI requirements |
| Curricular Requirement | governing body/program and active designation | organizational fact | Effective-dated |
| Curricular Requirement | learning-function/outcome statement | source assertion | Do not infer equivalence from shared designation |
| Enrollment Population | definition, inclusion rules, denominator dimensions | organizational fact | Governed definition; observation selects it |
| Constraint | `id`, authority, type | stable identity fact | Refers to a versioned requirement |
| Constraint | requirement text and applicability | source assertion | Formal source role and exact locator required |
| Constraint | local compliance status/margin | time-bounded observation or source assertion | Never infer from the external standard alone |
| Institutional Function | `id`, name, type | stable identity fact | Only milestone-critical functions |
| Institutional Function | stewardship/dependency | organizational fact | Evidence-backed and effective-dated |
| Observation | subject, metric, value, unit, period, denominator, dimensions | time-bounded observation | Must preserve missing versus zero |
| Observation | collection method and source locator | source assertion | Provenance of the measured value |
| Evidence Reference | source KO ID, locator, evidence role | stable provenance fact | Links source to asserted fact/relationship |
| Scenario Assumption | assumed value, timing, rationale | scenario assumption | Exists only within a named scenario |
| Constitutional object | institutional principles and scope | constitutional fact | Continue using separate constitutional architecture |
| Substitutability result | provider status, feasibility, confidence, explanation | service-derived assessment | Never copied into a factual entity registry as truth |
| Reserve capacity result | available/expandable FTE, sections, seats, constraints | service-derived assessment | Derived for an as-of period and scenario |
| Department priority/rank/reduction allocation | any value | service-derived assessment | Requires Layer 5 and adequate evidence; never an entity property |

## Minimum relationship model

The August model should reuse the directionality, evidence references, and deterministic query behavior of `InstitutionalRelationship`, while adding the specific relation vocabulary required below. Cardinality describes the institutional model, not database implementation.

| Source entity | Relationship type | Target entity | Direction and cardinality | Temporal behavior | Evidence requirements | Factual or derived | August 1? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Department | `belongs_to` | College/School | Department → one current parent; parent → many departments | Effective-dated | Organization chart/HR master data | Factual organizational relation | Yes |
| Department | `offers` | Academic Program | Department → many; program → one or more owning/delivering units | Effective-dated | Official catalog/program inventory | Factual organizational relation | Yes |
| Department | `owns` / `delivers` | Course | Unit → many; course may have one owner and one or more deliverers | Effective catalog period | Official catalog/curriculum record | Factual organizational relation | Yes |
| Faculty Position | `belongs_to` | Department | Position → one home unit at an instant; unit → many positions | Effective-dated | HR position-control record | Factual organizational relation | Yes |
| Faculty Member | `occupies` | Faculty Position | Member ↔ zero or more position fractions; position zero or more occupants over time | Occupancy interval and FTE fraction | HR appointment record | Factual organizational relation | Yes |
| Faculty Member | `qualified_to_teach` | Course | Many-to-many | Qualification effective/as-of period | Credentials, approved teaching history, or authoritative assignment/qualification record | Source-backed factual assertion; service may judge sufficiency | Yes |
| Faculty Member | `teaches` | Course Offering | Member → many offerings; offering → one or more instructors | Term-bound | Official teaching assignment | Factual organizational relation | Yes |
| Course Offering | `instance_of` | Course | Many offerings → one course | Offering term | Registrar schedule | Factual | Yes |
| Course | `satisfies` | Program requirement | Many-to-many | Effective catalog period | Catalog/degree-audit rule | Factual organizational relation | Yes |
| Course | `satisfies` | LLC Core Requirement | Many-to-many | Designation effective period | Authoritative LLC designation | Factual organizational relation | Yes |
| Course | `satisfies` | Area of Inquiry | Many-to-many | Designation effective period | Authoritative LLC/AOI designation | Factual organizational relation | Yes |
| Department | `provides_contribution_to` | LLC Core Requirement | Derived department → requirement aggregation | Observation period | Underlying course designation, offerings, and observations | **Derived view** of sections/seats/enrollment/SCH, not a bare fact | Yes |
| Department | `provides_contribution_to` | Area of Inquiry | Derived department → AOI aggregation | Observation period | Same as above | **Derived view** | Yes |
| Course | `provides_service_to` | Program or Department | Course → many consumers | Effective requirement/use period | Program requirement plus enrollment population evidence | Factual if formally required; otherwise source-backed usage assertion | Yes |
| Program | `depends_on` | Course | Program → many courses | Effective catalog period | Official requirement/prerequisite record | Factual organizational relation | Yes |
| Program | `subject_to` | Accreditation/Regulatory Requirement | Many-to-many | Standard/applicability effective period | Formal standard plus local applicability evidence | Factual applicability relation; compliance is separate | Yes where applicable |
| Department or Faculty Position | `supports` | Institutional Function | Many-to-many | Effective assignment/operating period | Assignment, governance, accreditation, or operating record | Factual/source assertion, not value judgment | Yes for material functions |
| Institutional Function | `depends_on` | Department, Program, Course, or Position | Function → one or many providers | Effective period | Evidence-backed operating/curricular dependency | Factual when formally established; otherwise attributed source assertion | Yes for material functions |
| Course | `shares_curricular_function_with` | Course | Symmetric many-to-many | Catalog/designation period | Shared outcomes/function evidence beyond designation | **Service-derived interpretation** with evidence; not inferred from names/designation alone | Yes for substitution analysis |
| Department | `shares_curricular_function_with` | Department | Symmetric, derived from course/function coverage | As-of/scenario period | Underlying course and function relations | **Service-derived summary** | Yes as output, not stored fact |
| Evidence source | `supports` | Entity property, Observation, or Relationship | Source → many assertions; assertion → one or more sources | Source/effective period | KO ID, exact locator, authority/evidence role | Factual provenance relation; support does not guarantee truth | Yes |
| Course | `prerequisite_for` | Course | Directed many-to-many | Effective catalog period | Official catalog/curriculum record | Factual organizational relation | Yes where relevant |
| Offering | `uses` | Facility/Room | Offering → zero/one primary room; room → many offerings across time | Meeting/term interval | Registrar/room schedule | Factual organizational relation | High-value if constrained |

The existing topology enum already provides `supports`, `requires`, `contributes_to`, `depends_on`, `accredits`, and `shares_resources_with`. It does not provide the granularity above, and its bootstrap relations often lack evidence references. The milestone should extend or adapt the relationship contract rather than encode new relations as ad hoc prose in Dashboard V2.

## Minimum shared observation model

Different metrics do not require different object classes. A shared, provenance-bearing `InstitutionalObservation` contract is appropriate for quantities and states that vary over time.

### Required observation fields

| Field | Purpose |
| --- | --- |
| `id` | Stable record identity or deterministic source-row identity |
| `subject_ref` | Entity or relationship being measured, such as department, position, offering, program, or requirement |
| `metric` | Controlled metric name such as `seats_filled` or `faculty_fte` |
| `value` | Numeric, boolean, or controlled categorical observed value; missing is not zero |
| `unit` | FTE, positions, sections, seats, students, SCH, dollars, percent, hours, or count |
| `period_start`, `period_end`, or `as_of` | Observation time; academic term and census date where relevant |
| `denominator` | Population/capacity basis for rates or ratios; required when value is not a raw count |
| `dimensions` | Department, program, course, requirement, modality, student population, position type, or other grouping needed to interpret the value |
| `collection_method` | Census extract, schedule snapshot, HR position control, workload assignment, survey, audited report, or other method |
| `evidence_ref` | Source Knowledge Object or authoritative record and exact locator |
| `authority_role` | Institutional operating record, formal standard, local self-study, planning document, etc. |
| `status` | Observed, revised, provisional, or source-asserted; not an evaluative fitness grade |

The contract must preserve the scope and denominator. “75% utilization” is unusable without defining whether the denominator is room capacity, course cap, seats offered, faculty workload norm, or another quantity.

### Metric coverage

| Metric family | Example controlled metrics | Subject/scope | August use |
| --- | --- | --- | --- |
| Faculty inventory | `authorized_position_fte`, `filled_position_fte`, `vacant_position_fte`, headcount | Department and position; as-of date | Essential |
| Faculty workload | `assigned_instructional_fte`, `assigned_courses`, `assigned_contact_hours`, overload, release time | Member/position and term/year | Essential |
| Instructional workload | sections, contact hours, credit hours delivered | Department/course/offering and term | Essential |
| Course supply | `sections_offered`, `section_capacity`, `seats_offered` | Course/department/requirement and term | Essential |
| Course utilization | `seats_filled`, census enrollment, fill rate, cancellations | Offering/course and census date | Essential |
| Unmet demand | waitlist count, denied enrollment if available | Offering/course/requirement and date | High-value; Unknown if unavailable |
| Student credit hours | `student_credit_hours` with credit basis | Course/department/program/population and term | Essential |
| Program demand/outcomes | majors, graduates, applications, yield, retention | Program/department/population and year | Essential multi-year series |
| Financial | salary/benefit cost, adjunct/overload cost, operating budget, revenue attribution | Position/department/offering/scenario and fiscal period | Essential for financial recommendation; may begin Partial |
| Research/grants | sponsored activity, supervision load | Member/department/function and period | Include only when decision-relevant and sourced |
| Service teaching | nonmajor enrollment, seats/SCH delivered to consumer program | Course/department/program and term | Essential |
| LLC Core contribution | sections, seats, enrollment, SCH by Core Requirement | Department/course/requirement and term | Essential |
| AOI contribution | sections, seats, enrollment, SCH by Area of Inquiry | Department/course/AOI and term | Essential |
| Accreditation staffing | qualified FTE, coverage count, required threshold, compliance observation | Program/constraint and period | Essential where applicable |

### Observation versus derivation versus assumption

- “Department B taught 20 sections last year” is a time-bounded observation when the department, academic year, definition of section, and registrar source are present.
- “Department B's faculty had 3.0 FTE of assigned instructional workload” is a time-bounded observation when the workload convention and denominator are present.
- “Department B had unfilled seats in existing LLC sections” is derived directly from observed offered and filled seats, or may be stored as an observation if the authoritative source supplies it with the same definitions.
- “Department B could add sections without overloads” is a service-derived assessment requiring workload norms, assignments, qualified faculty, schedule, room, and course constraints. It is not a raw observation.
- “Department B could add sections if 0.25 FTE were reassigned” is a scenario result based on an explicit scenario assumption.
- “Department B offers courses in the same AOI but does not provide an equivalent curricular function” is a curricular/service interpretation based on designations, learning functions, accessibility, and disciplinary breadth.

An empty value is Unknown. A measured zero is valid only when an authoritative source explicitly establishes zero for the defined subject, metric, and period.

## LLC and Area of Inquiry Capacity and Substitutability

The Liberal Learning Core is a university-wide instructional dependency, not merely a catalog label. The existing Dashboard V2 contract correctly names:

- **Core Requirements:** Mathematics, Second Language Literacy, English, Logical Reasoning, Economics.
- **Areas of Inquiry:** Creative Expressions, Civic and Democratic Engagement, Western Traditions, Global and Multicultural Perspectives, Investigating the Natural World.

The current topology represents the LLC only as a coarse curriculum node and also contains a legacy “General Education” node. Dashboard V2 explicitly refuses to recast that legacy label as LLC without a mapping. The August model must preserve that discipline.

## Minimum factual structure

For each LLC Core Requirement or Area of Inquiry, ISO needs:

1. a canonical requirement identity and effective period;
2. the authoritative statement of its learning function or approved outcomes;
3. every currently designated course and the designation's effective period;
4. the course owner/deliverer and accessibility constraints, including prerequisites and availability to nonmajors;
5. each offering by term, modality, schedule, room/facility, course cap, seats offered, seats filled, and waitlist if available;
6. department contribution aggregates by sections, seats, enrollment, and SCH, computed from offering-level facts;
7. at least several comparable terms of utilization so one anomalous schedule is not treated as stable reserve;
8. instructors, documented course qualifications, assigned workload, release/overload commitments, and position FTE;
9. room, laboratory, equipment, modality, scheduling, and course-cap constraints;
10. dependencies on those same courses for majors, prerequisites, service teaching, accreditation, and other institutional functions;
11. exact evidence references for every designation, observation, qualification, and constraint.

## Four distinct questions

A substitution service must answer four questions separately:

1. **Formal designation overlap:** Do courses from both departments satisfy the same LLC requirement or AOI during the relevant catalog period?
2. **Curricular-function overlap:** Do the courses serve sufficiently overlapping learning functions for the scenario, while preserving intended disciplinary breadth and student access?
3. **Provider capability:** Are qualified instructors, workload, sections, seats, rooms, modality, schedule, and facilities actually available?
4. **System consequence:** Would expansion displace the provider's majors, service teaching, accreditation coverage, research/advising obligations, or other functions?

A shared designation establishes only the first condition. It is not evidence of interchangeability.

## Capacity dimensions

The service should expose components, not one opaque spare-capacity score:

- **Existing-seat availability:** observed unfilled seats in suitable current offerings.
- **Expandable section capacity:** additional sections feasible with current qualified staffing and normal workload.
- **Conditional capacity:** capacity possible only under an explicit assumption such as overload, adjunct hiring, reassignment, larger caps, new room access, or modality change.
- **Qualified capacity:** the subset supportable by appropriately qualified instructors.
- **Scheduled/facility capacity:** the subset feasible under time, room, laboratory, equipment, modality, and course-cap constraints.
- **Net capacity:** capacity remaining after protecting the provider's own program, prerequisites, service obligations, and other functions.

Historical empty seats do not by themselves prove expandable capacity. They may show immediately available student seats in an existing section, but they do not establish that the section occurs at the required time, is open to the affected population, provides equivalent learning function, or can absorb a different course obligation.

## Service-derived assessment

The existing AWP-4 statuses should remain the outer status vocabulary:

- **Alternative providers evidenced** — named providers have evidence for relevant function, qualifications, and feasible capacity under the stated current conditions.
- **Potential alternative providers indicated** — named providers share relevant function, but feasibility depends on unresolved evidence or explicit assumptions.
- **No alternative provider evidenced** — the supplied evidence establishes no provider; this does not claim none exists institutionally.
- **Substitutability not assessed** — the service has not evaluated the function.
- **Insufficient evidence** — the service attempted evaluation but essential facts are absent or incompatible.

The assessment should additionally report:

- function and lost-capacity quantity being tested;
- candidate provider and same-designation evidence;
- curricular-function overlap and disciplinary-breadth caveats;
- qualified-instructor coverage;
- current utilization and observed seat availability;
- workload and position availability;
- feasible additional sections and seats;
- schedule, room, lab, equipment, modality, and cap constraints;
- effects on the provider's programs and services;
- assumptions required;
- evidence sources, missing facts, and confidence/fitness explanation;
- feasibility mode: immediate, conditional, costly, infeasible from supplied constraints, or unknown.

This result belongs to a deterministic service. It may be cached as a versioned assessment product for audit, but it must never be treated as an unquestioned institutional fact.

## Example: same AOI, not fully substitutable

Suppose a Physics course and a Biology course are both authoritatively designated **Investigating the Natural World**. That shared formal designation supports candidate discovery. It does not establish full substitution if the Physics course provides quantitative physical-science inquiry required by an engineering pathway, while the Biology course provides life-science inquiry, has laboratory prerequisites, or is unavailable to nonmajors. Even if Biology has empty seats, replacing Physics capacity may reduce disciplinary breadth or fail the engineering service function. The service should report designation overlap but insufficient or limited curricular-function substitution.

This example is illustrative, not an assertion about actual CNU courses or capacity.

## Example: conditional partial substitution

Suppose two departments offer courses in Creative Expressions with overlapping approved outcomes. Department A loses one section. Department B has qualified faculty but no normal-load availability and an appropriate room is free only in one time block. A service may report **Potential alternative providers indicated** and conditional capacity if the scenario explicitly assumes a 0.25-FTE reassignment, an authorized overload, adjunct hiring, or a higher approved course cap. The assumption, cost, affected workload, and scheduling constraint must remain visible. Without that assumption, the evidence does not establish spare capacity.

## Unknown and evidence-fitness behavior

The service must return Unknown or Insufficient Evidence when any essential link is absent: designation, current offerings, utilization history, qualification, workload, facility/schedule feasibility, or downstream dependency. Evidence Fitness should grade LLC/AOI substitutability as institution-wide support only when unit coverage is comparative and current. One department's course list or one semester's schedule cannot establish institution-wide replacement capacity.

## Minimum Viable August 1 Model

The smallest coherent implementation slice is five reusable contract families plus adapters and two services. It should coexist with the document corpus rather than replace it.

### 1. Shared identity records

Introduce dependency-light semantic records for:

- `EntityRef` (`id`, `entity_type`, `name`);
- `AcademicUnitRecord`;
- `FacultyPositionRecord` and restricted `FacultyMemberRecord`;
- `CourseRecord`, `CourseOfferingRecord`, and `CurricularRequirementRecord`;
- `ConstraintRecord` and `InstitutionalFunctionRecord`.

Do not make each a `KnowledgeObject` subclass initially. Store authoritative registry records with evidence references and effective periods. Reuse `ProgramEntity` through an adapter rather than creating a competing program catalog.

### 2. Evidence-backed relationship record

Reuse the shape and validation principles of topology `InstitutionalRelationship` and `EvidenceReference`, extending the vocabulary only for milestone relations such as belongs-to, owns/delivers, occupies, teaches, qualified-to-teach, instance-of, satisfies, provides-service-to, subject-to, prerequisite-for, and supports-function. Preserve direction, IDs, effective period, evidence, and factual-versus-asserted status.

### 3. Shared observation record

Add one `InstitutionalObservation` contract with subject, controlled metric, value, unit, period/as-of, denominator, dimensions, method, status, and evidence reference. Use adapters to transform faculty, registrar, workload, course, enrollment, and finance extracts into this contract. Do not introduce one class per metric.

### 4. Scenario assumption and effect inputs

Add a minimal typed `ScenarioAssumption` and position-change input so Layer 5 can express removal, vacancy, reassignment, adjunct/overload use, course-cap change, and effective term without altering current facts. The scenario service computes effects; it does not mutate the registry.

### 5. Explainable substitutability assessment

Implement a deterministic service output compatible with `ParticipationFunction` statuses. It should expose its factual inputs, candidate-provider reasoning, constraints, assumptions, missing evidence, and component feasibility. Dashboard V2 can adapt this output into the existing Institutional Participation Profile rather than owning the logic.

### Existing modules to reuse

- `app/knowledge.py`, `app/acquisition/source_document.py`, and chunk metadata for source provenance;
- `ProgramEntity`/`ProgramCatalog` for initial programs;
- topology `InstitutionalEntity`, `InstitutionalRelationship`, `EvidenceReference`, catalog, and query directionality;
- Dashboard V2 LLC constants as the current canonical presentation vocabulary, with a parity test against the new authoritative registry;
- `ParticipationFunction` statuses and disclaimer semantics;
- `EvidenceFitnessAssessment.topic_support` for presentation, extended by services rather than by the dashboard;
- the eight canonical AWP domains and Decision Readiness required-evidence statements;
- `DecisionContext.metadata` only as a temporary adapter boundary, not the permanent observation store.

### Likely registries and adapters

The milestone needs small authoritative registries for academic units, LLC/AOI requirements, course designations, and institutional functions. The existing `config/institutional_programs.yaml` can remain the program source initially. The current hard-coded topology bootstrap should not become the authoritative home for operational course and capacity facts.

Adapters are needed for whatever authoritative CNU extracts are actually available:

- HR position and appointment roster;
- faculty workload and teaching assignments;
- catalog/program/course inventory;
- registrar course offerings, census enrollment, seats, caps, and SCH;
- LLC/AOI designation list;
- program requirements/prerequisites;
- room/facility constraints;
- finance and compensation data;
- formal accreditation constraints and local applicability/compliance records.

Adapters must preserve source file/record identity, row or cell locator, extraction time, effective/census period, definitions, and authority. They must not infer missing relationships from names.

### Validation requirements

At minimum, validate:

- unique canonical IDs and resolvable references;
- program/topology/string crosswalks without silent collisions;
- valid effective periods and non-overlapping single-parent/position occupancy where required;
- observation unit, period, denominator, dimensions, and provenance completeness;
- course offering references an existing course and term;
- LLC/AOI designations use the canonical registry and carry an authoritative source;
- positions and assignments reference valid units and people;
- zero is explicit and never substituted for missing;
- derived assessments identify all scenario assumptions;
- sensitive faculty data does not leak into executive rendering.

### Interaction with retrieval and Evidence Fitness

Structured records should become searchable evidence through deterministic textual projections or factual Knowledge Objects only where useful, while retaining their structured identity for services. Retrieval remains available for source context and narrative evidence. Structured comparison must not depend on an LLM recovering tables from arbitrary chunks at decision time.

Evidence Fitness can then evaluate concrete coverage:

- percentage of departments with current position/FTE and workload records;
- terms and units covered by section/enrollment/SCH observations;
- proportion of LLC/AOI courses with current designation and offering data;
- dependency mappings with provenance;
- qualifications and constraints available for candidate providers;
- financial and scenario inputs available by unit.

This replaces keyword presence with inspectable semantic completeness while preserving current grades and scope limitations.

### Interaction with Scenario Modeling and Decision Briefs

Layer 5 should take a baseline snapshot plus explicit position-change assumptions and return effects on staffing, offerings, seats, SCH, programs, LLC/AOI requirements, functions, constraints, and costs. It should compare alternatives without embedding the final recommendation in source records.

The existing Decision Brief pipeline need not be redesigned. It can receive:

- a structured institution-wide comparison summary;
- Evidence Fitness coverage based on semantic facts;
- scenario results with assumptions and missing inputs;
- unit participation profiles adapted into existing Dashboard V2 contracts;
- constitutional orientation through the existing separate channel.

The deterministic panels should show component evidence and Unknown states; governed narrative can explain the results with citations.

### Explicitly out of scope

- a comprehensive university ontology or graph database;
- the Institutional Digital Twin;
- individual faculty ranking or performance scoring;
- automatic department reduction recommendations without Layer 5 and adequate evidence;
- inferred qualifications, course equivalence, or relationships based on names;
- optimizing schedules at meeting-level granularity;
- predictive enrollment or financial models not supported by explicit assumptions;
- replacing the retrieval, Decision Brief, or constitutional architecture.

## Concrete hypothetical representation

The following is an illustrative CNU-shaped example only. IDs, courses, people, quantities, and sources are hypothetical and must not be interpreted as CNU facts.

### Facts and provenance

| Record | Factual representation | Exact hypothetical provenance |
| --- | --- | --- |
| Primary department | `unit:physics`, Department, belongs to `unit:school_engineering_computing` | `ko:org-chart-2026`, locator `row 14` |
| Alternative provider | `unit:chemistry`, Department, belongs to `unit:college_natural_behavioral_sciences` | `ko:org-chart-2026`, locator `row 9` |
| Program | `program:mechanical_engineering`, active B.S., offered by its recorded unit | `ko:catalog-2026`, locator `Mechanical Engineering BS` |
| Position 1 | `position:physics-01`, 1.0 authorized FTE, filled, home `unit:physics` | `ko:hr-position-control-2026-06-30`, locator `position row P001` |
| Position 2 | `position:chemistry-01`, 1.0 authorized FTE, filled, home `unit:chemistry` | `ko:hr-position-control-2026-06-30`, locator `position row C001` |
| Faculty member 1 | `person:restricted-101` occupies Physics position; qualification assertion for PHY 201 and PHY 105 | `ko:appointments-2025-26`, `row 101`; `ko:faculty-qualifications-2025`, `row 101` |
| Faculty member 2 | `person:restricted-202` occupies Chemistry position; qualification assertion for CHEM 110 | `ko:appointments-2025-26`, `row 202`; `ko:faculty-qualifications-2025`, `row 202` |
| Course 1 | `course:phy-201`, 4 credits, delivered by Physics; satisfies a Mechanical Engineering requirement and Investigating the Natural World | `ko:catalog-2026`, locators `PHY 201` and `Mechanical Engineering requirements`; `ko:llc-designations-2026`, row `PHY 201` |
| Course 2 | `course:phy-105`, 3 credits, delivered by Physics; satisfies Investigating the Natural World and is open to nonmajors | `ko:catalog-2026`, locator `PHY 105`; `ko:llc-designations-2026`, row `PHY 105` |
| Course 3 | `course:chem-110`, 3 credits, delivered by Chemistry; satisfies Investigating the Natural World and is open to nonmajors | `ko:catalog-2026`, locator `CHEM 110`; `ko:llc-designations-2026`, row `CHEM 110` |
| Offering 1 | `offering:2025F-PHY201-01`, in person, cap 24, Physics instructor | `ko:schedule-2025F`, row `PHY 201-01` |
| Offering 2 | `offering:2025F-PHY105-01`, in person, cap 30, Physics instructor | `ko:schedule-2025F`, row `PHY 105-01` |
| Offering 3 | `offering:2025F-CHEM110-01`, in person, cap 32, Chemistry instructor | `ko:schedule-2025F`, row `CHEM 110-01` |
| Requirement | `requirement:llc-aoi-investigating-natural-world`, kind `llc_aoi` | `ko:llc-policy-2026`, locator `Investigating the Natural World` |
| Service teaching | PHY 201 provides service to Mechanical Engineering; program depends on PHY 201 | `ko:catalog-2026`, locator `Mechanical Engineering requirements` |
| Constraint/function | PHY 201 supports `function:engineering-prerequisite-physics`; lab room limits offering cap to 24 | `ko:catalog-2026`, same locator; `ko:room-capacity-2025F`, locator `LAB-X` |

### Time-bounded observations

| Subject | Metric and value | Period/scope/denominator | Provenance |
| --- | --- | --- | --- |
| Physics | 2 sections; 54 seats offered; 51 seats filled; 177 SCH in the AOI | Fall 2025; designated offerings only; SCH uses enrolled students × course credits | `ko:schedule-2025F` and `ko:enrollment-census-2025F`, exact offering rows |
| Chemistry | 1 section; 32 seats offered; 25 seats filled; 75 SCH in the AOI | Fall 2025; CHEM 110; census date specified | Same schedule/census sources, CHEM 110 row |
| Physics position/member | 0.75 instructional FTE assigned; two named offering assignments | 2025–26 workload year; institutional workload definition attached | `ko:workload-2025-26`, row `P001` |
| Chemistry position/member | 1.0 instructional FTE assigned; one named offering plus other assignments | 2025–26 workload year | `ko:workload-2025-26`, row `C001` |

The observations show seven unfilled CHEM 110 seats at the census date. They do **not** establish that Chemistry can add a section, teach Physics, replace the engineering prerequisite, or preserve disciplinary breadth.

### Missing evidence

No source establishes whether an appropriate room, time block, and qualified Chemistry instructor are available for an additional section in the affected term. This remains an explicit missing-evidence condition.

### Scenario assumption

Scenario `scenario:remove-physics-position-01` assumes that 0.25 FTE can be reassigned to Chemistry and that an approved additional CHEM 110 section may be scheduled. This is not current institutional state. Its cost, room feasibility, faculty agreement, and effect on Chemistry's own obligations must be evaluated.

### Service-derived substitutability inputs and result

Inputs:

- both PHY 105 and CHEM 110 have the same formal AOI designation;
- PHY 201 has a distinct program/service dependency;
- historical seats, enrollment, and SCH are observed for the specified term;
- qualifications are course-specific, not department-wide;
- Chemistry workload is fully assigned in the baseline;
- additional room/schedule feasibility is missing;
- reassigned FTE is a scenario assumption;
- disciplinary-function equivalence is not established.

A deterministic service could therefore report:

- PHY 201 engineering-prerequisite function: **Insufficient evidence** or **No alternative provider evidenced**, because same-AOI designation does not replace the program requirement and no qualified alternative is established.
- Some PHY 105 AOI seat capacity: **Potential alternative providers indicated**, conditional on reassigned workload, schedule/room validation, and an explicit curricular-breadth judgment.

It may not store “Physics is replaceable,” “Chemistry has spare capacity,” “Physics is overstaffed,” or “remove the Physics position.” Those are derived claims, and the final reduction decision remains outside the facts.

## Implementation Sequence Through August 1

### Absolutely required

1. **Define a small shared contract set.** Establish canonical IDs, evidence references, effective periods, academic units, positions/members, courses/offerings/requirements, relationships, observations, and scenario assumptions. Do not add one KO subclass per noun or metric.
2. **Build adapters for available authoritative data.** Start with unit/program/course catalogs, HR position/FTE, faculty workload/assignments/qualifications, registrar offerings/enrollment/SCH, and current LLC/AOI designations. Preserve row-level provenance and Unknown values.
3. **Create the LLC/AOI requirement and designation registry.** Use the canonical Dashboard V2 terms, authoritative course mappings, effective periods, and parity validation. Do not infer designations from topology or names.
4. **Load time-bounded instructional-capacity observations.** Cover multiple comparable terms where available, with explicit units, populations, denominators, and census dates.
5. **Represent essential dependencies and constraints.** Program requirements, prerequisites, service teaching, material institutional functions, accreditation applicability, room/lab constraints, and position/function support need evidence-backed relations.
6. **Implement an explainable substitutability service.** Derive component capacity and the existing AWP-4 provider status; expose missing inputs and scenario assumptions.
7. **Make Evidence Fitness semantic-coverage aware.** Report unit/period/metric completeness for the eight existing domains, particularly institution-wide comparison and LLC/AOI substitution.
8. **Provide Layer 5 position-change inputs.** Evaluate removal or reassignment of positions and calculate lost/retained functions, sections, seats, SCH, program obligations, and constraints without ranking individuals.
9. **Adapt results into current Decision Briefs.** Populate existing AWP-2/AWP-3/AWP-4 panels and governed narrative context; preserve constitutional separation and current non-recommendation behavior when evidence is insufficient.

### High-value if time permits

1. Add room/facility scheduling, waitlists, adjunct/overload cost, compensation, and detailed program-outcome adapters.
2. Add multi-term anomaly checks and source freshness diagnostics.
3. Add sensitivity comparisons for reassignment, overload, adjunct, course-cap, and modality assumptions.
4. Add broader institutional functions such as advising, research supervision, governance, and partnerships where authoritative assignments exist.

### Explicitly deferred until after August 1

- comprehensive ontology or Institutional Digital Twin work;
- graph database adoption;
- full historical organization/version reconstruction;
- automated schedule optimization;
- inferred faculty expertise from publications or free text;
- predictive demand, finance, or employee-performance modeling;
- broad entity extraction from all documents;
- person-level rankings or recommendations.

## Concise recommendation

The minimum semantic structure ISO must add now is a canonical identity layer for departments, programs, faculty positions/members, courses, offerings, LLC/AOI requirements, constraints, and institutional functions; evidence-backed directed relationships among them; and one shared, time-bounded observation contract for FTE, workload, sections, seats, enrollment, SCH, and costs. These facts must be populated by provenance-preserving adapters and paired with explicit scenario assumptions.

On top of that small factual substrate, ISO needs one deterministic substitutability service that separates formal designation overlap, curricular-function overlap, qualified staffing, observed utilization, feasible expansion, operational constraints, downstream dependencies, and assumptions. That is the smallest increment that makes workforce reasoning materially more defensible and allows ISO to say whether lost LLC or Area of Inquiry capacity is evidenced as absorbable, conditionally absorbable, unsupported, unassessed, or unknown—without storing or fabricating a department reduction recommendation.
