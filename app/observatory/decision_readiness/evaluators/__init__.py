from app.observatory.decision_readiness.evaluators.keyword import (
    KeywordDomainEvaluator,
)
from app.observatory.decision_readiness.evaluators.curriculum import (
    CurriculumEvaluator,
)
from app.observatory.decision_readiness.evaluators.faculty import (
    FacultyEvaluator,
)
from app.observatory.decision_readiness.evaluators.facilities import (
    FacilitiesEvaluator,
)
from app.observatory.decision_readiness.evaluators.equipment import (
    EquipmentEvaluator,
)
from app.observatory.decision_readiness.evaluators.accreditation import (
    AccreditationEvaluator,
)
from app.observatory.decision_readiness.evaluators.budget import (
    BudgetEvaluator,
)
from app.observatory.decision_readiness.evaluators.enrollment import (
    EnrollmentEvaluator,
)
from app.observatory.decision_readiness.evaluators.strategic import (
    StrategicPlanningEvaluator,
)
from app.observatory.decision_readiness.evaluators.historical import (
    HistoricalPrecedentEvaluator,
)
from app.observatory.decision_readiness.evaluators.academic_workforce import (
    InstructionalDemandEvaluator,
    FacultyCapacityEvaluator,
    ServiceTeachingDependenceEvaluator,
    AccreditationExternalConstraintsEvaluator,
    EnrollmentTrendsEvaluator,
    FinancialImplicationsEvaluator,
    StrategicPriorityAlignmentEvaluator,
    OneLineLossScenarioEvaluator,
    ACADEMIC_WORKFORCE_PLANNING_EVALUATORS,
)

ACADEMIC_PROGRAM_EVALUATORS = [
    CurriculumEvaluator,
    FacultyEvaluator,
    FacilitiesEvaluator,
    EquipmentEvaluator,
    AccreditationEvaluator,
    BudgetEvaluator,
    EnrollmentEvaluator,
    StrategicPlanningEvaluator,
    HistoricalPrecedentEvaluator,
]

__all__ = [
    "KeywordDomainEvaluator",
    "CurriculumEvaluator",
    "FacultyEvaluator",
    "FacilitiesEvaluator",
    "EquipmentEvaluator",
    "AccreditationEvaluator",
    "BudgetEvaluator",
    "EnrollmentEvaluator",
    "StrategicPlanningEvaluator",
    "HistoricalPrecedentEvaluator",
    "InstructionalDemandEvaluator",
    "FacultyCapacityEvaluator",
    "ServiceTeachingDependenceEvaluator",
    "AccreditationExternalConstraintsEvaluator",
    "EnrollmentTrendsEvaluator",
    "FinancialImplicationsEvaluator",
    "StrategicPriorityAlignmentEvaluator",
    "OneLineLossScenarioEvaluator",
    "ACADEMIC_PROGRAM_EVALUATORS",
    "ACADEMIC_WORKFORCE_PLANNING_EVALUATORS",
]
