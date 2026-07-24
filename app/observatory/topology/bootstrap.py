"""Bootstrap a small, curated model of CNU institutional topology.

This is a deliberately limited first model of institutional relationships.
It exists to validate the topology architecture before broader ingestion,
provenance, and quantitative relationship modeling are added.
"""

from __future__ import annotations

from .catalog import InstitutionalTopologyCatalog
from .entity import EntityType, InstitutionalEntity
from .relationship import (
    InstitutionalRelationship,
    RelationshipType,
)


def build_bootstrap_catalog() -> InstitutionalTopologyCatalog:
    """Build and return the initial curated topology catalog."""

    catalog = InstitutionalTopologyCatalog()

    entities = [
        #
        # Academic units and programs. SEC is formally a dependent school and
        # the department-equivalent workforce home; Physics and Computer
        # Science are programmatic specialties, not faculty-home departments.
        #
        InstitutionalEntity(
            id="college:natural_behavioral_sciences",
            name="College of Natural and Behavioral Sciences",
            entity_type=EntityType.COLLEGE,
        ),
        InstitutionalEntity(
            id="academic_unit:sec",
            name="School of Engineering and Computing",
            entity_type=EntityType.SCHOOL,
            metadata={
                "formal_unit_type": "dependent_school",
                "parent_unit_id": "college:natural_behavioral_sciences",
                "operational_roles": [
                    "department_equivalent", "faculty_home_unit",
                    "workforce_allocation_unit",
                ],
            },
        ),
        InstitutionalEntity(
            id="program:physics",
            name="Physics",
            entity_type=EntityType.PROGRAM,
        ),
        InstitutionalEntity(
            id="department:chemistry",
            name="Chemistry",
            entity_type=EntityType.DEPARTMENT,
        ),
        InstitutionalEntity(
            id="department:biology",
            name="Biology",
            entity_type=EntityType.DEPARTMENT,
        ),
        InstitutionalEntity(
            id="department:mathematics",
            name="Mathematics",
            entity_type=EntityType.DEPARTMENT,
        ),
        InstitutionalEntity(
            id="program:computer_science",
            name="Computer Science",
            entity_type=EntityType.PROGRAM,
        ),
        InstitutionalEntity(
            id="department:english",
            name="English",
            entity_type=EntityType.DEPARTMENT,
        ),
        InstitutionalEntity(
            id="department:history",
            name="History",
            entity_type=EntityType.DEPARTMENT,
        ),
        InstitutionalEntity(
            id="department:philosophy",
            name="Philosophy",
            entity_type=EntityType.DEPARTMENT,
        ),

        #
        # Programs
        #
        InstitutionalEntity(
            id="program:mechanical_engineering",
            name="Mechanical Engineering",
            entity_type=EntityType.PROGRAM,
        ),
        InstitutionalEntity(
            id="program:electrical_engineering",
            name="Electrical Engineering",
            entity_type=EntityType.PROGRAM,
        ),
        InstitutionalEntity(
            id="program:computer_engineering",
            name="Computer Engineering",
            entity_type=EntityType.PROGRAM,
        ),
        InstitutionalEntity(
            id="program:nursing",
            name="Nursing",
            entity_type=EntityType.PROGRAM,
        ),
        InstitutionalEntity(
            id="program:teacher_preparation",
            name="Teacher Preparation",
            entity_type=EntityType.PROGRAM,
        ),
        InstitutionalEntity(
            id="program:honors",
            name="Honors Program",
            entity_type=EntityType.PROGRAM,
        ),
        InstitutionalEntity(
            id="program:pre_law",
            name="Pre-Law",
            entity_type=EntityType.PROGRAM,
        ),

        #
        # Curricular functions
        #
        InstitutionalEntity(
            id="curriculum:general_education",
            name="General Education",
            entity_type=EntityType.CURRICULUM,
        ),
        InstitutionalEntity(
            id="curriculum:liberal_learning",
            name="Liberal Learning Core",
            entity_type=EntityType.CURRICULUM,
        ),
    ]

    for entity in entities:
        catalog.add_entity(entity)

    relationships = [
        #
        # Physics
        #
        InstitutionalRelationship(
            source_id="program:physics",
            target_id="program:mechanical_engineering",
            relationship_type=RelationshipType.SUPPORTS,
            confidence=0.95,
            rationale=(
                "Physics provides foundational coursework used by "
                "Mechanical Engineering."
            ),
        ),
        InstitutionalRelationship(
            source_id="program:physics",
            target_id="program:electrical_engineering",
            relationship_type=RelationshipType.SUPPORTS,
            confidence=0.95,
            rationale=(
                "Physics provides foundational coursework used by "
                "Electrical Engineering."
            ),
        ),
        InstitutionalRelationship(
            source_id="program:physics",
            target_id="curriculum:general_education",
            relationship_type=RelationshipType.CONTRIBUTES_TO,
            confidence=0.90,
            rationale=(
                "Physics contributes natural-science coursework to "
                "General Education."
            ),
        ),
        InstitutionalRelationship(
            source_id="program:physics",
            target_id="curriculum:liberal_learning",
            relationship_type=RelationshipType.CONTRIBUTES_TO,
            confidence=0.90,
            rationale=(
                "Physics contributes scientific inquiry to the "
                "Liberal Learning Core."
            ),
        ),

        #
        # Chemistry
        #
        InstitutionalRelationship(
            source_id="department:chemistry",
            target_id="program:nursing",
            relationship_type=RelationshipType.SUPPORTS,
            confidence=0.95,
            rationale="Chemistry provides prerequisite coursework for Nursing.",
        ),
        InstitutionalRelationship(
            source_id="department:chemistry",
            target_id="program:mechanical_engineering",
            relationship_type=RelationshipType.SUPPORTS,
            confidence=0.85,
            rationale=(
                "Chemistry provides supporting scientific coursework "
                "for Mechanical Engineering."
            ),
        ),
        InstitutionalRelationship(
            source_id="department:chemistry",
            target_id="curriculum:general_education",
            relationship_type=RelationshipType.CONTRIBUTES_TO,
            confidence=0.90,
            rationale=(
                "Chemistry contributes natural-science coursework to "
                "General Education."
            ),
        ),

        #
        # Biology
        #
        InstitutionalRelationship(
            source_id="department:biology",
            target_id="program:nursing",
            relationship_type=RelationshipType.SUPPORTS,
            confidence=0.95,
            rationale=(
                "Biology provides foundational life-science coursework "
                "for Nursing."
            ),
        ),
        InstitutionalRelationship(
            source_id="department:biology",
            target_id="curriculum:general_education",
            relationship_type=RelationshipType.CONTRIBUTES_TO,
            confidence=0.90,
            rationale=(
                "Biology contributes natural-science coursework to "
                "General Education."
            ),
        ),

        #
        # Mathematics
        #
        InstitutionalRelationship(
            source_id="department:mathematics",
            target_id="program:mechanical_engineering",
            relationship_type=RelationshipType.SUPPORTS,
            confidence=0.98,
            rationale=(
                "Mathematics provides required quantitative foundations "
                "for Mechanical Engineering."
            ),
        ),
        InstitutionalRelationship(
            source_id="department:mathematics",
            target_id="program:electrical_engineering",
            relationship_type=RelationshipType.SUPPORTS,
            confidence=0.98,
            rationale=(
                "Mathematics provides required quantitative foundations "
                "for Electrical Engineering."
            ),
        ),
        InstitutionalRelationship(
            source_id="department:mathematics",
            target_id="program:computer_engineering",
            relationship_type=RelationshipType.SUPPORTS,
            confidence=0.95,
            rationale=(
                "Mathematics provides quantitative foundations for "
                "Computer Engineering."
            ),
        ),
        InstitutionalRelationship(
            source_id="department:mathematics",
            target_id="curriculum:general_education",
            relationship_type=RelationshipType.CONTRIBUTES_TO,
            confidence=0.95,
            rationale=(
                "Mathematics contributes quantitative reasoning coursework "
                "to General Education."
            ),
        ),

        #
        # Computer Science
        #
        InstitutionalRelationship(
            source_id="program:computer_science",
            target_id="program:computer_engineering",
            relationship_type=RelationshipType.SUPPORTS,
            confidence=0.95,
            rationale=(
                "Computer Science provides programming and computational "
                "foundations for Computer Engineering."
            ),
        ),
        InstitutionalRelationship(
            source_id="program:computer_science",
            target_id="curriculum:general_education",
            relationship_type=RelationshipType.CONTRIBUTES_TO,
            confidence=0.80,
            rationale=(
                "Computer Science contributes computational and "
                "information-literacy coursework to General Education."
            ),
        ),

        #
        # English
        #
        InstitutionalRelationship(
            source_id="department:english",
            target_id="program:teacher_preparation",
            relationship_type=RelationshipType.SUPPORTS,
            confidence=0.90,
            rationale=(
                "English provides disciplinary coursework supporting "
                "Teacher Preparation."
            ),
        ),
        InstitutionalRelationship(
            source_id="department:english",
            target_id="curriculum:general_education",
            relationship_type=RelationshipType.CONTRIBUTES_TO,
            confidence=0.98,
            rationale=(
                "English contributes writing, literature, and humanities "
                "coursework to General Education."
            ),
        ),
        InstitutionalRelationship(
            source_id="department:english",
            target_id="curriculum:liberal_learning",
            relationship_type=RelationshipType.CONTRIBUTES_TO,
            confidence=0.98,
            rationale=(
                "English contributes substantially to the "
                "Liberal Learning Core."
            ),
        ),

        #
        # History
        #
        InstitutionalRelationship(
            source_id="department:history",
            target_id="program:teacher_preparation",
            relationship_type=RelationshipType.SUPPORTS,
            confidence=0.90,
            rationale=(
                "History provides disciplinary coursework supporting "
                "Teacher Preparation."
            ),
        ),
        InstitutionalRelationship(
            source_id="department:history",
            target_id="curriculum:general_education",
            relationship_type=RelationshipType.CONTRIBUTES_TO,
            confidence=0.95,
            rationale=(
                "History contributes historical and humanistic inquiry "
                "to General Education."
            ),
        ),
        InstitutionalRelationship(
            source_id="department:history",
            target_id="curriculum:liberal_learning",
            relationship_type=RelationshipType.CONTRIBUTES_TO,
            confidence=0.95,
            rationale=(
                "History contributes substantially to the "
                "Liberal Learning Core."
            ),
        ),

        #
        # Philosophy
        #
        InstitutionalRelationship(
            source_id="department:philosophy",
            target_id="program:honors",
            relationship_type=RelationshipType.SUPPORTS,
            confidence=0.85,
            rationale=(
                "Philosophy contributes courses and modes of inquiry "
                "relevant to the Honors Program."
            ),
        ),
        InstitutionalRelationship(
            source_id="department:philosophy",
            target_id="program:pre_law",
            relationship_type=RelationshipType.SUPPORTS,
            confidence=0.90,
            rationale=(
                "Philosophy provides logic, ethics, and argumentation "
                "relevant to Pre-Law preparation."
            ),
        ),
        InstitutionalRelationship(
            source_id="department:philosophy",
            target_id="curriculum:general_education",
            relationship_type=RelationshipType.CONTRIBUTES_TO,
            confidence=0.95,
            rationale=(
                "Philosophy contributes ethics, logic, and humanities "
                "coursework to General Education."
            ),
        ),
        InstitutionalRelationship(
            source_id="department:philosophy",
            target_id="curriculum:liberal_learning",
            relationship_type=RelationshipType.CONTRIBUTES_TO,
            confidence=0.95,
            rationale=(
                "Philosophy contributes substantially to the "
                "Liberal Learning Core."
            ),
        ),
    ]

    for relationship in relationships:
        catalog.add_relationship(relationship)

    return catalog
