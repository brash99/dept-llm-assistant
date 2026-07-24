• # Department Contribution Ontology Review

  I inspected all 18 generated DepartmentContributionKnowledgeObjects comprising 273 assertions:

   Predicate                            Assertions    Departments represented
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━
   owns_curriculum                              82                         18
  ───────────────────────────────────  ────────────  ─────────────────────────
   contributes_to_llc_requirement               75                         17
  ───────────────────────────────────  ────────────  ─────────────────────────
   provides_service_teaching_for                48                         17
  ───────────────────────────────────  ────────────  ─────────────────────────
   administers_program                          39                         17
  ───────────────────────────────────  ────────────  ─────────────────────────
   delivers_instruction_for                     18                         18
  ───────────────────────────────────  ────────────  ─────────────────────────
   provides_capstone_instruction_for            11                          4

  The objects genuinely feel ontological: they model departments through governed relationships rather
  than scalar performance summaries. The inspection also reveals several important gaps.

  ## Department-by-department review

  ### Accounting and Finance

  Correct:

  - Owns ACCT and FINC.
  - Administers Accounting and Finance.
  - Captures substantial service teaching for shared BUSN curriculum.
  - Captures smaller service relationships with Management and Marketing.

  Review observations:

  - The relationship to Music, Theatre, and Dance through 18 BTMG sections has zero SCH. The
    relationship may be real, but the object lacks a qualifier explaining the zero-credit instructional
    form.

  - BUSN service is directed to the Luter School while other service relationships target departments.
    This is legitimate heterogeneity, but it demonstrates that “service teaching” can target different
    levels of the institutional hierarchy.

  - No capstone relationship appears.

  ### Biology, Chemistry, and Environmental Science

  Correct:

  - Seven administered majors and eight owned prefixes reveal a genuinely heterogeneous department.
  - Service relationships to Honors and Neuroscience are institutionally natural.
  - Its substantial Natural World LLC contribution is plausible and well grounded.

  Gaps:

  - Biology, Chemistry, Environmental Science, Biochemistry, Kinesiology, and related biological fields
    remain flattened into one department-level portfolio.

  - Neuroscience appears only as a service-teaching destination. The stronger relationship that BCES
    institutionally supports the interdisciplinary program is absent.

  - No capstone relationships appear despite the breadth of governed majors.

  ### Communication Studies

  Correct:

  - Owns COMM and HEAL.
  - Service to LAMS, Honors, and IDST is visible.
  - LLC relationships span several distinct requirements.

  Gaps:

  - HEAL curriculum ownership is present, but the unresolved Health Studies/Health Sciences program
    relationship is invisible.

  - The object cannot express the difference between owning Health curriculum and administering or
    supporting a Health program.

  - Mixed faculty-home and prefix-fallback LLC attribution is combined inside single assertions.

  ### Economics

  Correct:

  - Owns ECON and DTAN.
  - Administers Economics.
  - Honors instruction and multiple LLC relationships are represented.

  Review observation:

  - The very large LLFE contribution is evidence-backed but ontologically opaque when viewed only at
    department level. The object cannot reveal which discipline, course family, or curricular function
    generates it.

  - DTAN and ECON are grouped without an internal contribution distinction.

  ### English

  Correct:

  - Strong LLC contribution is visible.
  - Extensive Honors and IDST service is represented.
  - Teacher Preparation and limited History service appear separately.

  Gaps:

  - The scale of Honors instruction is institutionally important, but the object only describes it as
    service to a program. It cannot distinguish recurring program support from incidental cross-unit
    teaching.

  - No capstone assertion appears, even though capstone evidence exists elsewhere in the semantic
    corpus.

  - The combined attribution-method qualifier obscures how much LLC contribution comes from English
    faculty versus English-owned curriculum.

  ### Fine Arts and Art History

  Correct:

  - Owns FNAR.
  - Administers Art History.
  - Creative Expressions contribution appears naturally.

  Significant gap:

  - Studio Art does not appear because its current ownership carries conflicting catalog structure and
    is excluded by the builder’s strict resolved-ownership rule.

  - The resulting object is internally valid but institutionally incomplete: it makes the department
    appear narrower than the source evidence suggests.

  - The object does not expose that an omitted program relationship exists under governance review.

  ### History

  Correct:

  - Owns HIST and administers History.
  - Its unusually broad LLC participation is visible.
  - Service involving Classics/Latin, Teacher Preparation, Honors, and IDST is preserved.

  Gaps:

  - Service to CLST and LATN is modeled as a relationship to MCLL, but the disciplinary nature of that
    contribution is invisible.

  - The object cannot distinguish durable interdisciplinary participation from isolated cross-unit
    sections.

  - No capstone relationship appears.

  ### Leadership and American Studies

  Correct:

  - Owns both AMST and LDSP.
  - Administers Leadership Studies.
  - Broad Democratic Engagement and Western Traditions contributions are visible.

  Significant gap:

  - It owns American Studies curriculum but does not administer the American Studies major in this
    object because that major’s governed owner is the Office of the Provost with conflicting catalog
    structure.

  - This is not necessarily wrong. It reveals that curriculum ownership, instructional delivery, and
    program administration are distinct institutional relationships.

  - The object needs a way to expose “supports or contributes to American Studies” without falsely
    asserting administrative ownership.

  ### Management and Marketing

  Correct:

  - Owns MGMT and MKTG.
  - Administers both majors.
  - Large-scale delivery for shared BUSN curriculum is visible.
  - Cross-unit SEC instruction is preserved.

  Gaps:

  - Shared Luter curriculum is represented only as service to the school; the object cannot express co-
    stewardship of school-level curriculum.

  - No capstone relationship appears.
  - Management and Marketing remain internally undifferentiated.

  ### Mathematics

  Correct:

  - Owns MATH.
  - Administers Mathematics and Computational and Applied Mathematics.
  - Both programs connect to the governed MATH 499 capstone relationship.
  - The object naturally shows extensive Mathematical Literacy contribution.

  Review observation:

  - The two capstone assertions share the same observed course but do not express whether the course
    population or pathway is shared between majors.

  - The one-section Physics service relationship is valid but may represent episodic rather than
    durable institutional function; that temporal distinction is unavailable.

  ### Military Science

  Correct:

  - Owns MLSC and NAVS.
  - Reports actual instructional activity.
  - Does not invent majors, LLC contribution, or program administration.

  Gaps:

  - The sparse object correctly reflects available governed evidence, but it cannot distinguish
    “evidence absent” from “relationship does not exist.”

  - Army and Naval activity are flattened into a single administrative unit without internal
    organizational semantics.

  - External institutional sponsorship or appointment relationships cannot yet be represented.

  ### Modern and Classical Languages and Literatures

  Correct:

  - Twelve governed prefixes and four majors accurately reveal a broad curriculum.
  - Language-foundation, global, and cultural contributions are visible.
  - Teacher Preparation, Honors, and IDST service is represented.

  Significant gap:

  - Arabic, Chinese, Classics, French, German, Greek, Hebrew, Italian, Latin, Spanish, and Humanities
    are flattened into a single contribution profile.

  - Some disciplines have majors; others contribute only curriculum.
  - This is one of the clearest demonstrations that departments and disciplines are not
    interchangeable.

  ### Music, Theatre, and Dance

  Correct:

  - The object exposes a very large and varied curriculum.
  - Music and Theater programs and their capstone relationships appear.
  - Creative Expressions and cross-program instruction are visible.

  Significant gaps:

  - Twenty-seven prefixes include disciplines, instruments, ensembles, and instructional modes.
    Treating all of them as equivalent instructional_subject objects loses important ontological
    structure.

  - Dance is visible through curriculum but not as an administered major.
  - Music and Theater capstones appear, but unresolved Studio Art governance remains invisible.
  - This object strongly demonstrates the need for internal contribution profiles below the department
    level.

  ### Philosophy and Religion

  Correct:

  - Owns PHIL and RSTD.
  - Administers Philosophy.
  - Its broad LLC function is clearly visible.
  - Honors and IDST service are represented.

  Significant gaps:

  - Philosophy and Religion remain indistinguishable inside the department-wide instruction aggregate.
  - Religion has a substantial curricular identity without a corresponding major.
  - PHIL 490 capstone evidence exists elsewhere but does not appear as a capstone assertion. This is
    likely an evidence-intersection or Department Profile representation limitation, not proof that the
    relationship is absent.

  ### Political Science

  Correct:

  - Owns POLS.
  - Administers Political Science and International Affairs.
  - Democratic Engagement and other LLC contributions appear naturally.

  Gaps:

  - The object cannot distinguish Political Science instruction from International Affairs support
    because both flow through one prefix and one department portfolio.

  - No capstone relationship appears.
  - IDST and Honors relationships do not indicate whether they are incidental sections or durable
    program responsibilities.

  ### Psychology

  Correct:

  - Owns PSYC and CHLF.
  - Captures substantial Natural World and Writing Intensive contribution.
  - Service to Neuroscience, BCES, SSWA, and Honors is visible.

  Significant gap:

  - Like BCES, Psychology clearly supports Neuroscience, but the ontology currently expresses only
    instruction delivered in NEUR.

  - This is compelling evidence that supports_program is ontologically distinct from
    provides_service_teaching_for.

  - Psychology and Child Life curriculum are aggregated without internal profiles.

  ### Sociology, Social Work, and Anthropology

  Correct:

  - Four majors, five prefixes, and four capstone relationships create a rich institutional model.
  - Cross-unit and LLC contribution are visible.
  - Shared use of SOCL 497 across several majors is preserved.

  Significant gaps:

  - Sociology, Social Work, Anthropology, Criminology, and Geography remain flattened.
  - The repeated SOCL 497 assertions do not explain shared enrollment, pathway overlap, or whether the
    same section serves multiple programs.

  - The model needs a governed way to express shared curricular components without double
    interpretation.

  ### School of Engineering and Computing

  Correct:

  - Six majors, nine prefixes, four LLC relationships, and three capstone relationships reveal
    substantial institutional function.

  - The object correctly models SEC as the administrative entity. It does not falsely create Physics or
    Computer Science departments.

  Most important gap:

  - Physics, Computer Science, Information Science, Cybersecurity, Computer Engineering, Electrical
    Engineering, and general Engineering remain one undifferentiated instructional portfolio.

  - Only three of six administered majors have visible capstone assertions.
  - The department-level object cannot express that Physics has a materially different instructional
    and LLC contribution profile from Computing and Engineering.

  - SEC is the strongest evidence for a governed discipline-level semantic object or an internal
    contribution-profile relationship.

  ## Recurring structural patterns

  ### 1. The common departmental backbone is sound

  All departments contain:

  - one or more owns_curriculum assertions;
  - one department-owned delivers_instruction_for assertion.

  Seventeen of eighteen also contain program, LLC, or service relationships. Military Science is the
  sole sparse case.

  This shared backbone feels natural and should remain small.

  ### 2. Internal heterogeneity is the dominant missing structure

  The clearest examples are:

  - SEC: Physics, Computing, and Engineering;
  - BCES: Biology, Chemistry, Environmental Science, Biochemistry, and Kinesiology;
  - MCLL: numerous language and classical disciplines;
  - Music, Theatre, and Dance: disciplines, performance media, and instruments;
  - SSWA: Sociology, Social Work, Anthropology, Criminology, and Geography;
  - Philosophy and Religion;
  - Psychology and Child Life.

  The objects accurately model departments but inadequately model their internal academic composition.

  ### 3. supports_program is governed but unused

  No object contains supports_program.

  Yet the corpus repeatedly reveals the underlying reality:

  - BCES and Psychology support Neuroscience;
  - departments support Honors and Teacher Preparation;
  - LAMS owns American Studies curriculum while program administration lies elsewhere;
  - multiple departments contribute to IDST;
  - business departments jointly support shared BUSN curriculum.

  The absence is not merely a builder omission. It reflects missing governed relationships establishing
  when recurring instructional participation becomes institutional program support.

  ### 4. Attribution dimensions are conflated inside LLC assertions

  A single LLC assertion can combine:

  - instructor_home;
  - prefix_owner_fallback.

  These mean different things:

  - faculty from the department delivered the instruction;
  - curriculum owned by the department received fallback attribution.

  The assertion preserves both method names, but its measures do not separate them. That makes the
  institutional meaning harder to inspect.

  ### 5. Section totals and mean annual SCH use different aggregation semantics

  Service and LLC assertions attach:

  - total section count across three years;
  - mean annual SCH across those years.

  Both are valid, but their different aggregation bases are not equally explicit. The SCH measure
  includes an academic-year-count qualifier; section count does not.

  ### 6. Capstone representation is systematically incomplete

  The governed capstone registry contains far more relationships than the 11 assertions appearing
  across four departments. Absence from an object can mean:

  - no capstone was observed in Department Profile course history;
  - normalization failed to intersect the course;
  - the capstone belongs to an omitted or conflicted major;
  - the requirement is unresolved;
  - the course was not offered during the observation period.

  These states are currently indistinguishable.

  ### 7. Evidence bindings are consistent but Evidence Fitness is not first-class

  Every assertion has exactly one evidence binding. That is structurally clean.

  However:

  - assertion-level Evidence Fitness is not a formal field;
  - object-level Evidence Fitness is absent;
  - source fitness is sometimes buried in binding provenance;
  - limitations are attached mainly to quantitative measures.

  The Explorer can expose the evidence, but cannot consistently compare epistemic status across
  assertions.

  ### 8. Almost every department has a unique structural signature

  Only Communication Studies and Philosophy and Religion share identical predicate counts. Even those
  two objects differ materially in targets and measures.

  This is a positive result: the ontology is not forcing departments into an artificial uniform
  template.

  ## Assertions that feel awkward or require review

  1. delivers_instruction_for a synthetic self-owned curriculum portfolio

     The target is a constructed curriculum_portfolio:<department> entity. The assertion aggregates
     every section in department-owned subjects, including sections delivered by outside faculty. It
     therefore expresses curricular delivery by the department as an institution—not necessarily
     delivery by its own faculty. That distinction is not obvious from the predicate alone.

  2. owns_curriculum targets prefixes

     Prefix governance is a real institutional fact, but “curriculum” and “instructional subject
     prefix” are not always identical. MTD’s instrument prefixes make this especially clear.

  3. Zero-SCH service relationships

     Accounting and Finance’s 18 BTMG sections establish observed activity but attach zero mean SCH.
     The relationship may be correct; its instructional form is unexplained.

  4. Program omissions are silent

     Studio Art, American Studies, Neuroscience, and Health Studies demonstrate that unresolved or
     conflicting governance disappears from department objects rather than appearing as an explicit
     limitation.

  5. Temporal scopes are uneven
      - Department instruction spans all available schedule history.
      - Service and LLC assertions cover 2022–23 through 2024–25.
      - Program and curriculum assertions inherit the broad object scope.
      - Major and capstone catalog editions are preserved in evidence provenance but not always
        reflected in effective periods.

      - Most subject-ownership assertions have open-ended effective dates.

  These are not necessarily wrong, but the semantic object requires careful inspection to avoid
  treating unlike periods as directly comparable.

  ## Prioritized ontological gaps

  ### Priority 1: A governed internal academic-component concept

  The strongest finding is the need to model academic composition below the department.

  A future DisciplineKnowledgeObject, or a more carefully named governed academic-component object, is
  supported by evidence from SEC, BCES, MCLL, MTD, SSWA, Psychology, and Philosophy and Religion.

  It would need to answer:

  - which department contains the discipline;
  - which prefixes express it;
  - which programs it supports or administers;
  - which faculty contribute to it;
  - which LLC and service relationships arise from it.

  This should not be implemented until CNU’s actual discipline boundaries can be governed. Prefixes
  alone are insufficient.

  ### Priority 2: Program-support relationships distinct from teaching activity

  The existing supports_program predicate appears ontologically necessary, but governing evidence is
  missing.

  Multiple departments demonstrate the need:

  - BCES and Psychology → Neuroscience;
  - departments → Honors;
  - departments → Teacher Preparation;
  - LAMS → American Studies;
  - departments → interdisciplinary IDST programs.

  A section taught for a program is evidence of activity. It is not automatically proof of
  institutional responsibility for supporting that program.

  ### Priority 3: Contribution mode as a governed qualifier

  Contribution assertions need to distinguish at least conceptually between:

  - contribution through curriculum ownership;
  - contribution through faculty instructional delivery;
  - contribution through program administration;
  - contribution through recurring institutional support.

  The current LLC assertions demonstrate this need most clearly because they combine instructor-home
  and prefix-owner-fallback evidence.

  ### Priority 4: Explicit epistemic status and Evidence Fitness

  Evidence Fitness should become consistently inspectable at assertion and possibly object level.

  Concrete needs include:

  - governed relationship;
  - observed relationship;
  - partial temporal observation;
  - unresolved governance excluded;
  - conflicting governance;
  - complete or incomplete quantitative evidence;
  - no observed evidence versus asserted nonexistence.

  ### Priority 5: Shared curricular-component relationships

  Shared capstones expose this gap:

  - SOCL 497 serves Anthropology, Criminology, and Sociology;
  - MATH 499 supports two majors;
  - school-level BUSN curriculum is delivered by both Luter departments.

  The ontology can currently create parallel assertions, but cannot express that the underlying
  curricular component is jointly used.

  ### Priority 6: More explicit temporal qualification

  The ontology already has the correct four-dimensional temporal contract. The generated objects reveal
  where source relationships do not yet populate it fully:

  - catalog-edition applicability;
  - effective ownership dates;
  - historical versus current prefixes;
  - recurring versus episodic service;
  - capstone requirement period versus observed-offering period.

  This is primarily a governance and builder-input gap, not a defect in the temporal contract.

  ## Overall assessment

  The pilot ontology succeeds at its central purpose. The objects are models of departmental
  institutional function, not reports about departments.

  The most important scientific result is that department-level contribution is real but not
  compositionally sufficient. CNU’s departments contain disciplines, shared curricula,
  interdisciplinary programs, and instructional relationships that cannot be reconstructed faithfully
  from administrative units alone.

  The next ontology should not be chosen because a new screen or metric needs it. It should be chosen
  because repeated inspection across SEC, BCES, MCLL, MTD, SSWA, Psychology, and Philosophy and
  Religion demonstrates that institutional reality contains a governed academic structure below the
  department level that ISO cannot yet name.
