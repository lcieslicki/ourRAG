from app.api.routes.chat import safe_event_payload


def test_safe_event_payload_redacts_raw_content_fields() -> None:
    payload = safe_event_payload(
        {
            "message": "How do I request vacation?",
            "query": "vacation policy",
            "messages": [{"role": "user", "content": "secret"}],
            "results": [{"payload": {"text": "retrieved secret", "document_id": "doc-1"}}],
            "source_count": 1,
        }
    )

    assert payload["message"] == {"redacted": True, "length": 26}
    assert payload["query"] == {"redacted": True, "length": 15}
    assert payload["messages"] == {"redacted": True, "count": 1}
    assert payload["results"][0]["payload"]["text"] == {"redacted": True, "length": 16}
    assert payload["results"][0]["payload"]["document_id"] == "doc-1"
    assert payload["source_count"] == 1
