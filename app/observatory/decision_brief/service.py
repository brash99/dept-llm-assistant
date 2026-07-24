from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from openai import OpenAI

from app.constitution.orientation import ConstitutionalOrientation
from app.evidence import (
    Evidence,
    EvidenceClass,
    evidence_role_label,
    group_evidence_by_class,
)
from app.question_scope import QuestionScope, classify_question_scope
from app.observatory.evidence_fitness import (
    EvidenceFitnessAssessment,
    EvidenceFitnessService,
)
from app.observatory.metrics import (
    ObservatoryAssessment,
    build_observatory_assessment,
)
from app.observatory.decision_brief.renderer import (
    render_decision_brief,
)
from app.observatory.topology.bootstrap import build_bootstrap_catalog
from app.observatory.topology.catalog import InstitutionalTopologyCatalog
from app.observatory.topology.entity import InstitutionalEntity
from app.observatory.topology.impact import (
    ImpactSummary,
    InstitutionalImpactService,
)
from app.observatory.topology.query import InstitutionalTopologyQuery
from app.vector_index import RetrievalResult


@dataclass
class EvidenceGroup:
    topic: str
    summary: str
    source_numbers: List[int] = field(default_factory=list)


@dataclass
class DecisionBrief:
    question: str
    executive_summary: str
    evidence_groups: List[EvidenceGroup]
    areas_of_uncertainty: List[str]
    missing_information: List[str]
    recommended_follow_up: List[str]
    sources: List[RetrievalResult]
    evidence_items: List[Evidence]
    observatory_assessment: Optional[ObservatoryAssessment]
    evidence_fitness: object
    topology_entity_id: Optional[str]
    topology_impact: Optional[ImpactSummary]
    raw_markdown: str


def build_grouped_evidence_context(
    evidence_items: List[Evidence],
    constitutional_orientation: Optional[
        ConstitutionalOrientation
    ] = None,
) -> str:
    """Build Decision Brief context with values and facts separated."""
    grouped = group_evidence_by_class(evidence_items)

    constitutional_items = grouped.get(
        EvidenceClass.CONSTITUTIONAL,
        [],
    )

    empirical_classes = [
        evidence_class
        for evidence_class in grouped
        if evidence_class != EvidenceClass.CONSTITUTIONAL
    ]

    sections = []

    constitutional_parts = [
        "=" * 70,
        "Institutional Values",
        "=" * 70,
    ]

    if constitutional_items:
        for item in constitutional_items:
            result = item.result
            citation = result.citation
            metadata = result.metadata

            principles = metadata.get("principles") or []
            principle_text = (
                "\n".join(
                    f"- {principle}"
                    for principle in principles
                )
                if principles
                else "Not specified"
            )

            constitutional_parts.append(
                f"[{item.citation_label}]\n"
                f"Original Source Number: {item.source_number}\n"
                f"Constitutional Type: "
                f"{metadata.get('constitutional_type')}\n"
                f"Evidence Role: {evidence_role_label(item)}\n"
                f"Institutional Scope: "
                f"{metadata.get('institutional_scope')}\n"
                f"Principles:\n{principle_text}\n"
                f"Title: {item.title}\n"
                f"Path: {citation.get('relative_path')}\n"
                f"Chars: {citation.get('start_char')}–"
                f"{citation.get('end_char')}\n"
                f"{result.text}"
            )
    elif (
        constitutional_orientation is not None
        and constitutional_orientation.matches
    ):
        constitutional_parts.append(
            "No constitutional source excerpts were retrieved in the evidence "
            "set. Deterministic Constitutional Orientation was supplied "
            "separately below."
        )
    else:
        constitutional_parts.append(
            "No constitutional evidence was retrieved."
        )

    sections.append("\n\n".join(constitutional_parts))

    empirical_parts = [
        "=" * 70,
        "Empirical Evidence",
        "=" * 70,
    ]

    for evidence_class in empirical_classes:
        items = grouped[evidence_class]

        if not items:
            continue

        empirical_parts.extend(
            [
                "",
                evidence_class.value,
                "-" * 70,
            ]
        )

        for item in items:
            result = item.result
            citation = result.citation

            empirical_parts.append(
                f"[{item.citation_label}]\n"
                f"Original Source Number: {item.source_number}\n"
                f"Evidence Class: {item.evidence_class.value}\n"
                f"Evidence Role: {evidence_role_label(item)}\n"
                f"Classification Confidence: {item.confidence:.2f}\n"
                f"Classification Rationale: {item.rationale}\n"
                f"Title: {item.title}\n"
                f"Path: {citation.get('relative_path')}\n"
                f"Chars: {citation.get('start_char')}–"
                f"{citation.get('end_char')}\n"
                f"{result.text}"
            )

    if not any(
        grouped[evidence_class]
        for evidence_class in empirical_classes
    ):
        empirical_parts.append(
            "No empirical evidence was retrieved."
        )

    sections.append("\n\n".join(empirical_parts))

    return "\n\n" + ("\n\n" + "=" * 70 + "\n\n").join(
        sections
    )


def build_constitutional_orientation_context(
    orientation: Optional[ConstitutionalOrientation],
) -> str:
    """Serialize orientation without relabeling it as retrieved evidence."""
    if orientation is None or not orientation.matches:
        return ""

    matches = []
    for match in orientation.matches:
        terms = ", ".join(match.matched_terms) or "None"
        matches.append(
            f"- Principle: {match.principle}\n"
            f"  Source catalog object: {match.constitutional_object_title}\n"
            f"  Constitutional type: {match.constitutional_type}\n"
            f"  Relevance score: {match.score:.2f}\n"
            f"  Matched terms: {terms}"
        )

    return """
======================================================================
Deterministic Constitutional Orientation
======================================================================

This is pre-retrieval semantic orientation, not a retrieved empirical source
and not an institutional-alignment judgment. It identifies potentially
relevant declared principles. Do not claim that constitutional context is
absent when using these matches. If source excerpts were not retrieved, say
that source-level constitutional evidence was not retrieved; do not say that
no constitutional evidence or orientation was available.

{matches}
""".format(matches="\n".join(matches)).strip()


def resolve_topology_entity(
    question: str,
    catalog: InstitutionalTopologyCatalog,
    entity_query: Optional[str] = None,
) -> Optional[InstitutionalEntity]:
    """Resolve one unambiguous topology entity for a Decision Brief.

    An explicit entity_query takes precedence. Otherwise, entity names are
    matched deterministically against the institutional question. Ambiguous
    questions do not receive topology context.
    """
    query_service = InstitutionalTopologyQuery(catalog)

    scope = classify_question_scope(question).scope
    if scope in {QuestionScope.INSTITUTION_WIDE, QuestionScope.MULTI_ENTITY}:
        return None

    if entity_query:
        return query_service.find_entity(entity_query)

    normalized_question = question.casefold()

    matches = [
        entity
        for entity in catalog.entities
        if entity.name.casefold() in normalized_question
    ]

    if not matches:
        return None

    matches.sort(
        key=lambda entity: len(entity.name),
        reverse=True,
    )

    longest_length = len(matches[0].name)
    longest_matches = [
        entity
        for entity in matches
        if len(entity.name) == longest_length
    ]

    if len(longest_matches) != 1:
        return None

    return longest_matches[0]


def build_topology_context(
    impact: Optional[ImpactSummary],
) -> str:
    """Render deterministic topology facts for the governed LLM prompt."""
    if impact is None:
        return ""

    def render_items(items) -> str:
        if not items:
            return "- None represented in the current topology"

        return "\n".join(
            f"- {item}"
            for item in items
        )

    return f"""
======================================================================
Institutional Topology Assessment
======================================================================

Entity:
{impact.entity.name}

Supports:
{render_items(impact.supports)}

Contributes To:
{render_items(impact.contributes_to)}

Supported By:
{render_items(impact.supported_by)}

Receives Contributions From:
{render_items(impact.contributed_to_by)}

Institutional Reach:
- {impact.total_relationships} direct institutional relationship{
    "" if impact.total_relationships == 1 else "s"
  }

Deterministic Assessment:
{impact.narrative()}

Topology Scope Notice:
- This topology is a small, manually curated model of institutional
  relationships.
- It represents only relationships currently encoded in the catalog.
- Absence of a relationship does not establish absence of a real-world
  institutional connection.
- These structural facts are derived from the institutional topology, not
  retrieved documentary evidence.
""".strip()


def render_topology_markdown(
    impact: Optional[ImpactSummary],
) -> str:
    """Render the authoritative topology section of a Decision Brief."""
    if impact is None:
        return ""

    def bullets(items) -> str:
        if not items:
            return "- None represented in the current topology"

        return "\n".join(
            f"- {item}"
            for item in items
        )

    relationship_word = (
        "relationship"
        if impact.total_relationships == 1
        else "relationships"
    )

    return f"""
## Institutional Topology Assessment

**Entity:** {impact.entity.name}

### Supports

{bullets(impact.supports)}

### Contributes To

{bullets(impact.contributes_to)}

### Supported By

{bullets(impact.supported_by)}

### Receives Contributions From

{bullets(impact.contributed_to_by)}

### Institutional Reach

The current institutional topology records **{impact.total_relationships} direct institutional {relationship_word}** for {impact.entity.name}.

### Deterministic Assessment

{impact.narrative()}

> **Topology scope notice:** This is a small, manually curated model of
> institutional relationships. It represents only relationships currently
> encoded in the catalog. Absence of a represented relationship does not
> establish absence of a real-world institutional connection. These structural
> facts are derived from the institutional topology, not from retrieved
> documentary evidence.
""".strip()


def assemble_decision_brief_markdown(
    synthesis_markdown: str,
    topology_impact: Optional[ImpactSummary] = None,
) -> str:
    """Assemble LLM synthesis and deterministic service products."""
    sections = [synthesis_markdown.strip()]

    topology_markdown = render_topology_markdown(
        topology_impact
    )

    if topology_markdown:
        sections.append(topology_markdown)

    return "\n\n".join(
        section
        for section in sections
        if section
    ).strip()


def build_decision_brief_prompt(
    question: str,
    evidence_context: str,
    evidence_fitness=None,
    evidence_topics: Optional[List[str]] = None,
    topology_context: Optional[str] = None,
    constitutional_orientation_context: Optional[str] = None,
) -> str:
    """
    Build the reasoning prompt sent to the LLM.

    Important architecture note:
    - The retriever should receive only the user's institutional question.
    - This prompt is constructed only after retrieval and evidence classification.
    - The LLM receives the question plus grouped evidence plus reasoning guidance.
    """
    if evidence_topics is None:
        if evidence_fitness is not None:
            evidence_topics = (
                EvidenceFitnessService.expected_topics(
                    evidence_fitness.decision_type
                )
            )
        else:
            evidence_topics = DEFAULT_EVIDENCE_TOPICS

    topics = "\n".join(
        f"- {topic}"
        for topic in evidence_topics
    )

    supporting_sections = "\n\n".join(
        f"### {topic}"
        for topic in evidence_topics
    )

    decision_type_guidance = ""

    if evidence_fitness is not None:
        scope_label = getattr(
            evidence_fitness,
            "question_scope_label",
            "Scope Unresolved",
        )
        domain_lines = []
        for topic, grade in evidence_fitness.topic_grades.items():
            support = evidence_fitness.topic_support.get(topic, {}) or {}
            limitation = support.get("scope_limitation")
            detail = f"- {topic}: {grade}"
            if limitation:
                detail += f" — {limitation}"
            domain_lines.append(detail)
        decision_type_guidance = (
            f"Decision type: "
            f"{evidence_fitness.decision_type_label}\n"
            f"Question scope: {scope_label}\n"
            f"Evidence Fitness score: "
            f"{evidence_fitness.fitness_score:.0f}%\n"
            f"Covered domains: "
            f"{', '.join(evidence_fitness.covered_topics) or 'None'}\n"
            f"Missing domains: "
            f"{', '.join(evidence_fitness.missing_topics) or 'None'}\n"
            "Scope-aware domain support:\n"
            + "\n".join(domain_lines)
        )

    topology_context = topology_context or ""
    constitutional_orientation_context = (
        constitutional_orientation_context or ""
    )

    if topology_context:
        topology_guidance = """
A deterministic Institutional Topology Assessment is provided below.

Treat it as structural context derived from the institutional topology:

- Do not describe topology relationships as documentary findings.
- Do not assign constitutional or empirical citations to topology facts.
- Do not invent relationships that are absent from the supplied assessment.
- The application will append the authoritative topology section after LLM
  synthesis.
- Do not create an "Institutional Topology Assessment" section yourself.
- Use the topology only to explain structural implications in the Executive
  Summary and Strategic Considerations.
- Make clear when an implication is an inference from represented topology
  rather than a documentary finding.
"""
    else:
        topology_guidance = """
No unambiguous institutional topology entity was resolved for this question.

Do not infer graph relationships from general knowledge.
"""

    return f"""
You are an AI assistant helping university administrators make evidence-based institutional decisions.

Your task is NOT simply to answer the question.

Your task is to synthesize the retrieved evidence into an explainable Decision Brief.

The retrieved material has been organized into two distinct semantic categories:

1. Institutional Values
   Constitutional evidence expresses institutional commitments, mission,
   values, and strategic directions. It informs what the institution ought
   to prioritize, but it does not by itself establish empirical facts.

2. Empirical Evidence
   Empirical sources describe institutional conditions, plans, history,
   external requirements, comparators, or background information.

Never treat an institutional value as though it were an empirical fact.
Never imply that empirical evidence alone determines institutional values.
Explain explicitly how empirical evidence relates to institutional values.

Claim-strength and language policy:

- Use each source's explicit Evidence Role. Distinguish a formal requirement,
  local institutional statement, self-study assertion, observed practice, and
  analyst inference; do not substitute one role for another.
- A statement in a self-study or departmental report must not be generalized
  into a universal accreditation requirement unless a retrieved Formal
  External Standard supports that claim.
- When a requirement's institutional or unit-level applicability is not
  established, say so explicitly and use uncertainty language.

- Constitutional Evidence may support statements such as:
  "The institution values...", "The Strategic Compass prioritizes...",
  or "This proposal may align with..."
  Constitutional evidence does not establish that a proposal is approved,
  funded, implemented, feasible, or successful.

- Institutional Evidence may support statements such as:
  "Meeting minutes report...", "The annual report records...",
  or "Current institutional records indicate..."
  Do not strengthen the claim beyond what the source explicitly establishes.

- Planning Documents may support statements such as:
  "The document proposes...", "The plan identifies...",
  "The draft anticipates...", "The minutes record an intended timeline...",
  or "Planning materials include a proposed allocation..."
  Do NOT convert planning language into established fact.

  In particular, avoid unsupported phrases such as:
  "has been allocated"
  "is scheduled"
  "has been approved"
  "will launch"
  "the institution has committed"

  unless a current authoritative institutional source explicitly establishes
  the allocation, schedule, approval, launch, or commitment.

- Historical Documents may support statements such as:
  "Earlier records indicate...", "Historically...", or
  "A previous proposal recommended..."
  Do not imply that historical conditions remain current.

- External Standards may support statements such as:
  "The standard requires...", "The accreditor specifies...", or
  "State guidance expects..."
  Do not imply that the institution presently satisfies the requirement
  unless institutional evidence confirms that it does.

- External Comparators may support statements such as:
  "A peer institution provides an example..." or
  "Comparator evidence suggests..."
  Never treat comparator evidence as evidence about CNU itself.

- Background Knowledge must be clearly identified as general context or an
  inference. It must not be presented as retrieved institutional evidence.

When sources conflict, differ in authority, or use tentative language,
preserve that uncertainty in the Decision Brief.

Empirical Evidence Classes have different purposes and should not be treated as equally authoritative.

Empirical Evidence Classes:

• Institutional Evidence
  Current factual information about this institution, including annual reports, faculty documents, curriculum proposals, policies, budgets, facilities, committee documents, and official university records.
  Treat this as the primary evidence.

• Institutional Planning
  Strategic plans, program reviews, major initiatives, budget planning documents, committee recommendations, and planning reports.
  These describe intended future directions rather than established facts.

• Institutional History
  Historical documents, archived reports, previous proposals, and institutional precedent.
  These provide historical context but may no longer reflect current policy.

• External Standards
  Accreditation standards, SCHEV guidance, SACSCOC requirements, government regulations, and other normative external requirements.
  These describe constraints or expectations that may apply to the institution.

• External Comparators
  Reports from peer institutions, self-studies, national surveys, and examples from other universities.
  These provide context and comparison but do NOT describe this institution.

• Background Knowledge
  Your own general knowledge.
  Use this only when necessary, and clearly distinguish it from retrieved evidence.

When synthesizing the evidence:

• Give greatest weight to Institutional Evidence.

• Use Institutional Planning documents to discuss future directions and proposed initiatives.

• Use Institutional History only for historical context.

• Use External Standards to explain requirements that may affect institutional decisions.

• Use External Comparators only as illustrative examples.
  Never treat comparator evidence as if it describes this institution.

• Clearly distinguish between:
    - established institutional facts
    - proposed plans
    - historical precedent
    - external requirements
    - external examples
    - inferred conclusions

If evidence is missing, incomplete, tentative, or conflicting,
explicitly identify this.

Before writing each factual claim, determine:

1. Which source supports the claim?
2. What evidence class does that source belong to?
3. What is the strongest wording justified by that class and the source text?
4. Does the wording distinguish proposal, intention, approval,
   implementation, and observed outcome?

Do not speculate.

If the available evidence does not support a conclusion, state that additional information would be required.

Use only the retrieved sources below.

Cite institutional values as [Constitutional Source N].
Cite factual or documentary claims as [Empirical Source N].
Do not use the internal "Original Source Number" in the written brief.

Institutional Question:
{question}

Question-aware Evidence Fitness guidance:
{decision_type_guidance}

Evidence domains appropriate to this question:
{topics}

Retrieved constitutional and empirical evidence:
{evidence_context}

Pre-retrieval constitutional orientation:
{constitutional_orientation_context or "No constitutional orientation was supplied."}

Institutional topology guidance:
{topology_guidance}

Deterministic institutional topology context:
{topology_context or "No topology context was supplied."}

Generate a Decision Brief with the following sections:

# Decision Brief

## Executive Summary

## Institutional Question

## Evidence Summary

## Supporting Evidence

{supporting_sections}

## Areas of Agreement

## Areas of Uncertainty

## Missing Information

## Strategic Considerations

## Recommended Follow-Up

## Sources Used

Throughout the Decision Brief:

- Explicitly distinguish institutional values from empirical evidence.
- Explain how empirical findings support, complicate, or fail to address the institutional values.
- Keep deterministic topology facts distinct from both constitutional and
  empirical evidence; topology describes represented institutional structure.
- Explicitly distinguish internal institutional evidence from external standards and external comparator institutions.
- Preserve the source's epistemic status: proposed, recommended, intended,
  requested, budgeted in planning, approved, implemented, or observed.
- Prefer precise attribution over unqualified institutional claims.
  For example, write:
  "A budget-planning document proposes $500,000 per year"
  rather than:
  "CNU has allocated $500,000 per year."
- Write:
  "Meeting minutes record an intended Fall 2027 launch"
  rather than:
  "The program is scheduled to begin in Fall 2027,"
  unless authoritative evidence confirms a formal schedule.
""".strip()


class DecisionBriefService:
    """
    Synthesize retrieved evidence into a governed institutional
    Decision Brief.

    This service begins after retrieval. It is responsible for:

    - assessing the retrieved evidence;
    - measuring evidence fitness;
    - constructing the governed reasoning prompt;
    - invoking the configured language model; and
    - assembling the DecisionBrief knowledge product.

    Retrieval configuration and retrieval tracing remain the
    responsibility of the calling application layer.
    """

    @staticmethod
    def generate(
        question: str,
        evidence_items: List[Evidence],
        sources: List[RetrievalResult],
        llm_base_url: str,
        llm_model: str,
        observatory_assessment: Optional[
            ObservatoryAssessment
        ] = None,
        evidence_fitness: Optional[
            EvidenceFitnessAssessment
        ] = None,
        evidence_topics: Optional[List[str]] = None,
        topology_entity_query: Optional[str] = None,
        topology_catalog: Optional[
            InstitutionalTopologyCatalog
        ] = None,
        temperature: float = 0.2,
        constitutional_orientation: Optional[
            ConstitutionalOrientation
        ] = None,
    ) -> DecisionBrief:
        question = question.strip()

        if not question:
            raise ValueError(
                "Decision Brief question must not be empty."
            )

        if observatory_assessment is None:
            observatory_assessment = (
                build_observatory_assessment(
                    evidence_items
                )
            )

        if evidence_fitness is None:
            evidence_fitness = (
                EvidenceFitnessService.evaluate(
                    question,
                    evidence_items,
                )
            )

        evidence_context = (
            build_grouped_evidence_context(
                evidence_items,
                constitutional_orientation=(
                    constitutional_orientation
                ),
            )
        )

        constitutional_orientation_context = (
            build_constitutional_orientation_context(
                constitutional_orientation
            )
        )

        if topology_catalog is None:
            topology_catalog = build_bootstrap_catalog()

        topology_entity = resolve_topology_entity(
            question=question,
            catalog=topology_catalog,
            entity_query=topology_entity_query,
        )

        topology_impact = None

        if topology_entity is not None:
            topology_impact = InstitutionalImpactService(
                topology_catalog
            ).summarize(topology_entity.id)

        topology_context = build_topology_context(
            topology_impact
        )

        prompt = build_decision_brief_prompt(
            question,
            evidence_context,
            evidence_fitness=evidence_fitness,
            evidence_topics=evidence_topics,
            topology_context=topology_context,
            constitutional_orientation_context=(
                constitutional_orientation_context
            ),
        )

        client = OpenAI(
            base_url=llm_base_url,
            api_key="not-needed",
        )

        response = client.chat.completions.create(
            model=llm_model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=temperature,
        )

        synthesis_markdown = (
            response.choices[0].message.content
            or ""
        )

        brief_markdown = render_decision_brief(
            question=question,
            synthesis_markdown=synthesis_markdown,
            observatory_assessment=observatory_assessment,
            evidence_fitness=evidence_fitness,
            topology_impact=topology_impact,
            evidence_count=len(evidence_items),
        )

        return DecisionBrief(
            question=question,
            executive_summary="",
            evidence_groups=[],
            areas_of_uncertainty=[],
            missing_information=[],
            recommended_follow_up=[],
            sources=sources,
            evidence_items=evidence_items,
            observatory_assessment=(
                observatory_assessment
            ),
            evidence_fitness=evidence_fitness,
            topology_entity_id=(
                topology_entity.id
                if topology_entity is not None
                else None
            ),
            topology_impact=topology_impact,
            raw_markdown=brief_markdown,
        )
