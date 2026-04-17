import pytest

from app.domain.prompting import (
    PROMPT_TEMPLATE_VERSION,
    ConversationMemory,
    PromptBuilder,
    PromptBuildInput,
    RecentMessage,
)
from app.domain.services.retrieval import RetrievedChunk


def test_prompt_builder_composes_system_context_memory_messages_and_current_user_message() -> None:
    prompt = PromptBuilder().build(
        PromptBuildInput(
            workspace_name="ACME HR",
            workspace_context="Use workspace-specific HR policies.",
            current_user_message="How do I request vacation?",
            memory=ConversationMemory(
                summary="The user previously asked about leave policies.",
                recent_messages=(
                    RecentMessage(role="user", content="Tell me about benefits."),
                    RecentMessage(role="assistant", content="Benefits are described in HR documents."),
                ),
            ),
            retrieved_chunks=(retrieved_chunk(chunk_id="chunk-1"),),
        )
    )

    assert prompt.template_version == PROMPT_TEMPLATE_VERSION
    assert prompt.has_retrieval_context is True
    assert [message.role for message in prompt.messages] == ["system", "system", "system", "user", "assistant", "user"]
    assert "Use only the supplied retrieved document context" in prompt.messages[0].content
    assert "Workspace: ACME HR" in prompt.messages[1].content
    assert "[S1] HR Handbook" in prompt.messages[1].content
    assert "The user previously asked about leave policies." in prompt.messages[2].content
    assert prompt.messages[-1].content == "How do I request vacation?"


def test_prompt_builder_includes_source_metadata_for_retrieved_chunks() -> None:
    chunk = retrieved_chunk(chunk_id="vacation-1", section_path=("HR Handbook", "Vacation"), score=0.87654)

    prompt = PromptBuilder().build(
        PromptBuildInput(
            workspace_name="ACME",
            current_user_message="What is the vacation process?",
            retrieved_chunks=(chunk,),
        )
    )

    context = prompt.messages[1].content
    assert "document_id: document-1" in context
    assert "document_version_id: version-1" in context
    assert "chunk_id: vacation-1" in context
    assert "category: HR" in context
    assert "section_path: HR Handbook > Vacation" in context
    assert "score: 0.8765" in context
    assert "Employees request vacation leave through the HR portal." in context


def test_prompt_builder_no_context_instructs_model_to_say_not_available() -> None:
    prompt = PromptBuilder().build(
        PromptBuildInput(
            workspace_name="ACME",
            current_user_message="What is the travel budget?",
            retrieved_chunks=(),
        )
    )

    assert prompt.has_retrieval_context is False
    combined = "\n\n".join(message.content for message in prompt.messages)
    assert "No retrieved document chunks were provided" in combined
    assert "not available in the current workspace documents" in combined


def test_prompt_builder_allows_versioned_system_prompt_override() -> None:
    prompt = PromptBuilder(template_version="custom_prompt_v2").build(
        PromptBuildInput(
            workspace_name=None,
            current_user_message="Answer this",
            system_prompt_override="You are the ACME policy assistant.",
            language="Polish",
        )
    )

    assert prompt.template_version == "custom_prompt_v2"
    assert "You are the ACME policy assistant." in prompt.messages[0].content
    assert "Answer in Polish." in prompt.messages[0].content


def test_prompt_builder_omits_blank_recent_messages() -> None:
    prompt = PromptBuilder().build(
        PromptBuildInput(
            workspace_name="ACME",
            current_user_message="Continue",
            memory=ConversationMemory(
                recent_messages=(
                    RecentMessage(role="user", content=" "),
                    RecentMessage(role="assistant", content="Previous answer."),
                )
            ),
        )
    )

    assert [message.role for message in prompt.messages] == ["system", "system", "assistant", "user"]
    assert prompt.messages[-2].content == "Previous answer."


def test_prompt_builder_rejects_empty_current_user_message() -> None:
    with pytest.raises(ValueError):
        PromptBuilder().build(PromptBuildInput(workspace_name="ACME", current_user_message="  "))


def retrieved_chunk(
    *,
    chunk_id: str,
    section_path: tuple[str, ...] = ("HR Handbook",),
    score: float = 0.91,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        chunk_text="Employees request vacation leave through the HR portal.",
        document_id="document-1",
        document_version_id="version-1",
        document_title="HR Handbook",
        section_path=section_path,
        score=score,
        category="HR",
        language="pl",
        is_active=True,
        payload={},
    )
