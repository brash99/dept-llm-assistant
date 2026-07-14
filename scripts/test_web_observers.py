from app.acquisition import (
    SourceAuthority,
    WebObserverCatalog,
)


def test_web_observer_catalog_loads_configuration(
    tmp_path,
):
    config_path = tmp_path / "observers.yaml"

    config_path.write_text(
        """
observers:
  - name: institutional_research
    enabled: true
    type: web
    source_organization: CNU Institutional Research
    authority: institutional_primary
    purposes:
      - enrollment
      - strategic_planning
    seed_urls:
      - https://example.edu/research/
    allowed_hosts:
      - example.edu
    allowed_prefixes:
      - https://example.edu/research/
    storage_root: storage/raw_web
    manifest: storage/manifests/research.jsonl
    max_depth: 5
    max_pages: 250
    request_delay_seconds: 0.75
    respect_robots: true
""",
        encoding="utf-8",
    )

    project_root = tmp_path / "project"
    project_root.mkdir()

    catalog = WebObserverCatalog.from_yaml(
        config_path,
        project_root=project_root,
    )

    observer = catalog.get(
        "institutional_research"
    )

    assert observer is not None
    assert observer.enabled is True
    assert observer.authority is (
        SourceAuthority.INSTITUTIONAL_PRIMARY
    )
    assert observer.purposes == (
        "enrollment",
        "strategic_planning",
    )
    assert observer.max_depth == 5
    assert observer.max_pages == 250
    assert observer.storage_root == (
        project_root / "storage/raw_web"
    )


def test_catalog_returns_only_enabled_observers(
    tmp_path,
):
    config_path = tmp_path / "observers.yaml"

    config_path.write_text(
        """
observers:
  - name: enabled_observer
    enabled: true
    type: web
    source_organization: Example
    authority: institutional_primary
    purposes: []
    seed_urls: [https://example.edu/a/]
    allowed_hosts: [example.edu]
    allowed_prefixes: [https://example.edu/a/]
    storage_root: storage/raw_web
    manifest: storage/manifests/a.jsonl

  - name: disabled_observer
    enabled: false
    type: web
    source_organization: Example
    authority: institutional_primary
    purposes: []
    seed_urls: [https://example.edu/b/]
    allowed_hosts: [example.edu]
    allowed_prefixes: [https://example.edu/b/]
    storage_root: storage/raw_web
    manifest: storage/manifests/b.jsonl
""",
        encoding="utf-8",
    )

    catalog = WebObserverCatalog.from_yaml(
        config_path,
        project_root=tmp_path,
    )

    assert [
        observer.name
        for observer in catalog.enabled()
    ] == ["enabled_observer"]


def test_disabling_robots_requires_authorization(
    tmp_path,
):
    config_path = tmp_path / "observers.yaml"

    config_path.write_text(
        """
observers:
  - name: unauthorized
    enabled: true
    type: web
    source_organization: Example
    authority: institutional_primary
    purposes: []
    seed_urls: [https://example.edu/research/]
    allowed_hosts: [example.edu]
    allowed_prefixes: [https://example.edu/research/]
    storage_root: storage/raw_web
    manifest: storage/manifests/example.jsonl
    respect_robots: false
""",
        encoding="utf-8",
    )

    import pytest

    with pytest.raises(
        ValueError,
        match="explicit authorization",
    ):
        WebObserverCatalog.from_yaml(
            config_path,
            project_root=tmp_path,
        )


def test_institutional_approval_allows_scoped_override(
    tmp_path,
):
    config_path = tmp_path / "observers.yaml"

    config_path.write_text(
        """
observers:
  - name: institutional_research
    enabled: true
    type: web
    source_organization: CNU Institutional Research
    authority: institutional_primary
    purposes: [enrollment]
    seed_urls:
      - https://example.edu/research/
    allowed_hosts:
      - example.edu
    allowed_prefixes:
      - https://example.edu/research/
    storage_root: storage/raw_web
    manifest: storage/manifests/research.jsonl
    respect_robots: false
    authorization:
      mode: institutional_approval
      approved_by:
        - Provost
        - Assistant Provost
      scope:
        - https://example.edu/research/
      notes: Approved pilot access.
""",
        encoding="utf-8",
    )

    catalog = WebObserverCatalog.from_yaml(
        config_path,
        project_root=tmp_path,
    )

    observer = catalog.get(
        "institutional_research"
    )

    assert observer is not None
    assert observer.respect_robots is False
    assert observer.authorization is not None
    assert observer.authorization.mode == (
        "institutional_approval"
    )
    assert observer.authorization.approved_by == (
        "Provost",
        "Assistant Provost",
    )


def test_authorization_scope_must_cover_allowed_prefixes(
    tmp_path,
):
    config_path = tmp_path / "observers.yaml"

    config_path.write_text(
        """
observers:
  - name: bad_scope
    enabled: true
    type: web
    source_organization: Example
    authority: institutional_primary
    purposes: []
    seed_urls:
      - https://example.edu/research/
    allowed_hosts:
      - example.edu
    allowed_prefixes:
      - https://example.edu/research/
      - https://example.edu/finance/
    storage_root: storage/raw_web
    manifest: storage/manifests/example.jsonl
    respect_robots: false
    authorization:
      mode: institutional_approval
      approved_by:
        - Provost
      scope:
        - https://example.edu/research/
""",
        encoding="utf-8",
    )

    import pytest

    with pytest.raises(
        ValueError,
        match="outside its authorization scope",
    ):
        WebObserverCatalog.from_yaml(
            config_path,
            project_root=tmp_path,
        )


def test_disabling_robots_requires_authorization(
    tmp_path,
):
    config_path = tmp_path / "observers.yaml"

    config_path.write_text(
        """
observers:
  - name: unauthorized
    enabled: true
    type: web
    source_organization: Example
    authority: institutional_primary
    purposes: []
    seed_urls: [https://example.edu/research/]
    allowed_hosts: [example.edu]
    allowed_prefixes: [https://example.edu/research/]
    storage_root: storage/raw_web
    manifest: storage/manifests/example.jsonl
    respect_robots: false
""",
        encoding="utf-8",
    )

    import pytest

    with pytest.raises(
        ValueError,
        match="explicit authorization",
    ):
        WebObserverCatalog.from_yaml(
            config_path,
            project_root=tmp_path,
        )


def test_institutional_approval_allows_scoped_override(
    tmp_path,
):
    config_path = tmp_path / "observers.yaml"

    config_path.write_text(
        """
observers:
  - name: institutional_research
    enabled: true
    type: web
    source_organization: CNU Institutional Research
    authority: institutional_primary
    purposes: [enrollment]
    seed_urls:
      - https://example.edu/research/
    allowed_hosts:
      - example.edu
    allowed_prefixes:
      - https://example.edu/research/
    storage_root: storage/raw_web
    manifest: storage/manifests/research.jsonl
    respect_robots: false
    authorization:
      mode: institutional_approval
      approved_by:
        - Provost
        - Assistant Provost
      scope:
        - https://example.edu/research/
      notes: Approved pilot access.
""",
        encoding="utf-8",
    )

    catalog = WebObserverCatalog.from_yaml(
        config_path,
        project_root=tmp_path,
    )

    observer = catalog.get(
        "institutional_research"
    )

    assert observer is not None
    assert observer.respect_robots is False
    assert observer.authorization is not None
    assert observer.authorization.mode == (
        "institutional_approval"
    )
    assert observer.authorization.approved_by == (
        "Provost",
        "Assistant Provost",
    )


def test_authorization_scope_must_cover_allowed_prefixes(
    tmp_path,
):
    config_path = tmp_path / "observers.yaml"

    config_path.write_text(
        """
observers:
  - name: bad_scope
    enabled: true
    type: web
    source_organization: Example
    authority: institutional_primary
    purposes: []
    seed_urls:
      - https://example.edu/research/
    allowed_hosts:
      - example.edu
    allowed_prefixes:
      - https://example.edu/research/
      - https://example.edu/finance/
    storage_root: storage/raw_web
    manifest: storage/manifests/example.jsonl
    respect_robots: false
    authorization:
      mode: institutional_approval
      approved_by:
        - Provost
      scope:
        - https://example.edu/research/
""",
        encoding="utf-8",
    )

    import pytest

    with pytest.raises(
        ValueError,
        match="outside its authorization scope",
    ):
        WebObserverCatalog.from_yaml(
            config_path,
            project_root=tmp_path,
        )
