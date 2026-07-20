from __future__ import annotations

from datetime import date, datetime, timezone
import json

import pytest

from app.knowledge import KnowledgeObject, load_knowledge_object, save_knowledge_object


def test_knowledge_object_serializes_dates_and_round_trips(tmp_path) -> None:
    obj = KnowledgeObject(
        id="serialization-fixture",
        object_type="fixture",
        title="Serialization fixture",
        text="Evidence text",
        metadata={
            "effective_date": date(2026, 7, 20),
            "retrieved_at": datetime(2026, 7, 20, 14, 30, tzinfo=timezone.utc),
        },
    )
    output = tmp_path / "knowledge_object.json"

    save_knowledge_object(obj, output)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["metadata"]["effective_date"] == "2026-07-20"
    assert payload["metadata"]["retrieved_at"] == "2026-07-20T14:30:00+00:00"

    loaded = load_knowledge_object(output)
    assert loaded.id == obj.id
    assert loaded.title == obj.title
    assert loaded.text == obj.text
    assert loaded.metadata == payload["metadata"]


def test_knowledge_object_json_does_not_stringify_unsupported_objects() -> None:
    obj = KnowledgeObject(
        id="unsupported-fixture",
        object_type="fixture",
        title="Unsupported fixture",
        text="Evidence text",
        metadata={"unsupported": object()},
    )

    with pytest.raises(TypeError, match="is not JSON serializable"):
        obj.to_json()
