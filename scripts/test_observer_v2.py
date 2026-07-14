from pathlib import Path

import pytest

from app.acquisition.observer_v2 import (
    MediaPolicy,
    ObserverV2Catalog,
)


def test_media_policy_accepts_terminal_documents():
    policy = MediaPolicy(
        follow_html=True,
        follow_pdf=True,
        follow_docx=False,
    )

    assert policy.accepts_url(
        "https://example.edu/report.pdf"
    )

    assert not policy.accepts_url(
        "https://example.edu/report.docx"
    )

    assert policy.accepts_media_type(
        "application/pdf"
    )

    assert MediaPolicy.is_html(
        "text/html"
    )


def test_catalog_loads_policy_and_budget(
    tmp_path,
):
    path = tmp_path / "observers.yaml"

    path.write_text(
        """
observers:
  - name: institutional_research
    enabled: true
    type: web
    source_organization: Test University
    authority: institutional_primary
    purposes:
      - enrollment
    priority_terms:
      - retention
      - graduation
    seed_urls:
      - https://example.edu/ir/
    allowed_hosts:
      - example.edu
    allowed_prefixes:
      - https://example.edu/ir/
    storage_root: storage/raw_web
    manifest: storage/manifests/ir.jsonl
    budget: 140
    max_depth: 8
    respect_robots: true
    media_policy:
      follow_html: true
      follow_pdf: true
      follow_docx: false
""",
        encoding="utf-8",
    )

    catalog = (
        ObserverV2Catalog.from_yaml(
            path,
            project_root=tmp_path,
        )
    )

    observer = catalog.get(
        "institutional_research"
    )

    assert observer.budget == 140
    assert observer.media_policy.follow_pdf
    assert observer.priority_terms == (
        "retention",
        "graduation",
    )


def test_robots_override_requires_authorization(
    tmp_path,
):
    path = tmp_path / "observers.yaml"

    path.write_text(
        """
observers:
  - name: unauthorized
    type: web
    source_organization: Test
    authority: institutional_primary
    seed_urls:
      - https://example.edu/
    allowed_hosts:
      - example.edu
    allowed_prefixes:
      - https://example.edu/
    manifest: storage/manifests/test.jsonl
    budget: 10
    respect_robots: false
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="authorization",
    ):
        ObserverV2Catalog.from_yaml(
            path,
            project_root=tmp_path,
        )
