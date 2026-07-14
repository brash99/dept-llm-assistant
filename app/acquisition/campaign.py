from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

from app.acquisition.observer_v2 import (
    ObserverV2,
    ObserverV2Catalog,
)
from app.acquisition.observer_v2_runner import (
    ObserverV2Report,
    ObserverV2Runner,
)


@dataclass(frozen=True)
class ObservationCampaign:
    """
    A governed allocation of observation effort across multiple observers.
    """

    key: str
    name: str
    description: str
    observers: Tuple[ObserverV2, ...]
    configured_budget: Optional[int] = None
    methodology: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError(
                "Campaign key must not be empty."
            )

        if not self.name.strip():
            raise ValueError(
                "Campaign name must not be empty."
            )

        if not self.observers:
            raise ValueError(
                "Campaign must contain at least one observer."
            )

        names = [
            observer.name
            for observer in self.observers
        ]

        if len(names) != len(set(names)):
            raise ValueError(
                "Campaign contains duplicate observer names."
            )

        if (
            self.configured_budget is not None
            and self.configured_budget
            != self.observation_budget
        ):
            raise ValueError(
                "Configured campaign budget does not equal "
                "the sum of observer budgets: "
                f"{self.configured_budget} != "
                f"{self.observation_budget}"
            )

    @property
    def observation_budget(self) -> int:
        return sum(
            observer.budget
            for observer in self.observers
        )

    @classmethod
    def from_yaml(
        cls,
        path: Path,
        *,
        project_root: Optional[Path] = None,
    ) -> "ObservationCampaign":
        path = Path(path)

        if project_root is None:
            project_root = Path.cwd()

        catalog = ObserverV2Catalog.from_yaml(
            path,
            project_root=project_root,
        )

        import yaml

        payload = yaml.safe_load(
            path.read_text(encoding="utf-8")
        ) or {}

        campaign = payload.get(
            "campaign",
            {},
        )

        observers = catalog.all(
            enabled_only=True
        )

        return cls(
            key=str(
                campaign.get(
                    "key",
                    path.stem,
                )
            ),
            name=str(
                campaign.get(
                    "name",
                    path.stem,
                )
            ),
            description=str(
                campaign.get(
                    "description",
                    "",
                )
            ),
            observers=observers,
            configured_budget=(
                int(
                    campaign[
                        "observation_budget"
                    ]
                )
                if campaign.get(
                    "observation_budget"
                )
                is not None
                else None
            ),
            methodology=tuple(
                campaign.get(
                    "methodology",
                    [],
                )
            ),
        )


@dataclass(frozen=True)
class CampaignReport:
    campaign_key: str
    campaign_name: str
    started_at: str
    completed_at: str
    configured_budget: int
    observer_reports: Tuple[
        ObserverV2Report,
        ...,
    ] = field(default_factory=tuple)

    @property
    def observations_acquired(self) -> int:
        return sum(
            report.observations_acquired
            for report in self.observer_reports
        )

    @property
    def observations_attempted(self) -> int:
        return sum(
            report.observations_attempted
            for report in self.observer_reports
        )

    @property
    def completion(self) -> float:
        if not self.configured_budget:
            return 0.0

        return min(
            1.0,
            self.observations_acquired
            / self.configured_budget,
        )

    @property
    def failed_resources(self) -> int:
        return sum(
            report.failed_resources
            for report in self.observer_reports
        )

    @property
    def media_counts(self) -> Dict[str, int]:
        totals: Dict[str, int] = {}

        for report in self.observer_reports:
            for media_type, count in (
                report.media_counts.items()
            ):
                totals[media_type] = (
                    totals.get(media_type, 0)
                    + count
                )

        return dict(
            sorted(
                totals.items(),
                key=lambda item: (
                    -item[1],
                    item[0],
                ),
            )
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_key": self.campaign_key,
            "campaign_name": self.campaign_name,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "configured_budget": (
                self.configured_budget
            ),
            "observations_attempted": (
                self.observations_attempted
            ),
            "observations_acquired": (
                self.observations_acquired
            ),
            "completion": self.completion,
            "failed_resources": (
                self.failed_resources
            ),
            "media_counts": self.media_counts,
            "observer_reports": [
                report.to_dict()
                for report in self.observer_reports
            ],
        }


class ObservationCampaignRunner:
    """
    Execute a governed campaign by running each selected observer.
    """

    def __init__(
        self,
        campaign: ObservationCampaign,
    ) -> None:
        self.campaign = campaign

    def run(
        self,
        *,
        observer_names: Optional[
            Iterable[str]
        ] = None,
    ) -> CampaignReport:
        selected = (
            set(observer_names)
            if observer_names is not None
            else None
        )

        if selected is not None:
            known = {
                observer.name
                for observer
                in self.campaign.observers
            }

            unknown = selected - known

            if unknown:
                raise KeyError(
                    "Unknown campaign observers: "
                    + ", ".join(
                        sorted(unknown)
                    )
                )

        observers = tuple(
            observer
            for observer
            in self.campaign.observers
            if (
                selected is None
                or observer.name in selected
            )
        )

        if not observers:
            raise ValueError(
                "No observers selected."
            )

        started_at = datetime.now(
            timezone.utc
        ).isoformat()

        reports = []

        for observer in observers:
            reports.append(
                ObserverV2Runner(
                    observer
                ).run()
            )

        completed_at = datetime.now(
            timezone.utc
        ).isoformat()

        return CampaignReport(
            campaign_key=self.campaign.key,
            campaign_name=self.campaign.name,
            started_at=started_at,
            completed_at=completed_at,
            configured_budget=sum(
                observer.budget
                for observer in observers
            ),
            observer_reports=tuple(
                reports
            ),
        )
