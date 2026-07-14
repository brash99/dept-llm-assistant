from dataclasses import replace
from pathlib import Path

import pytest

from app.acquisition.campaign import (
    CampaignReport,
    ObservationCampaign,
)
from app.acquisition.observer_v2_runner import (
    ObserverV2Report,
)


def make_report(
    name,
    budget,
    observed,
):
    return ObserverV2Report(
        observer_name=name,
        budget=budget,
        observations_attempted=observed,
        observations_acquired=observed,
        new_documents=observed,
        unchanged_documents=0,
        changed_documents=0,
        duplicate_documents=0,
        robots_denied=0,
        offsite_links_skipped=0,
        outside_scope_links_skipped=0,
        unsupported_links_skipped=0,
        duplicate_urls_skipped=0,
        failed_resources=0,
        media_counts={
            "text/html": observed,
        },
        elapsed_seconds=1.0,
    )


def test_cnu_campaign_loads_with_1000_budget():
    campaign = ObservationCampaign.from_yaml(
        Path("config/observers_v2.yaml"),
        project_root=Path.cwd(),
    )

    assert len(campaign.observers) == 11
    assert campaign.observation_budget == 1000


def test_campaign_report_aggregates():
    report = CampaignReport(
        campaign_key="test",
        campaign_name="Test",
        started_at="start",
        completed_at="end",
        configured_budget=100,
        observer_reports=(
            make_report(
                "one",
                40,
                40,
            ),
            make_report(
                "two",
                60,
                30,
            ),
        ),
    )

    assert report.observations_acquired == 70
    assert report.completion == 0.7
    assert report.media_counts == {
        "text/html": 70,
    }


def test_campaign_rejects_wrong_budget():
    campaign = ObservationCampaign.from_yaml(
        Path("config/observers_v2.yaml"),
        project_root=Path.cwd(),
    )

    with pytest.raises(
        ValueError,
        match="does not equal",
    ):
        replace(
            campaign,
            configured_budget=999,
        )
