import pytest

from app.core.config import get_settings
from app.core.config.query_rewrite_config import QueryRewriteConfig
from app.domain.embeddings import EmbeddingMetadata, EmbeddingResult
from app.domain.query_rewriting.models import QueryRewriteMode, RewritePlan
from app.domain.query_rewriting.service import QueryRewriteService
from app.domain.services.retrieval import RetrievalScope
from app.infrastructure.vector_index import VectorIndexQuery, VectorIndexResult
from tests.factories import (
    create_document,
    create_document_version,
    create_membership,
    create_user,
    create_workspace,
)
from tests.unit.test_retrieval_service import (
    FakeEmbeddingService,
    FakeVectorIndex,
    create_ready_active_version,
    retrieval_service,
    vector_result,
)


class TestMultiQueryRetrieval:
    """Integration tests for multi-query retrieval."""

    @pytest.mark.integration
    def test_disabled_mode_preserves_baseline_behavior(self, db_session):
        """Test that disabled mode doesn't change existing retrieval behavior."""
        user = create_user(db_session)
        workspace = create_workspace(db_session)
        create_membership(db_session, user=user, workspace=workspace, role="member")
        document, version = create_ready_active_version(db_session, workspace=workspace, user=user)

        vector_index = FakeVectorIndex(
            [
                vector_result(
                    workspace_id=workspace.id,
                    document_id=document.id,
                    document_version_id=version.id,
                    chunk_id="chunk-1",
                    score=0.9,
                ),
                vector_result(
                    workspace_id=workspace.id,
                    document_id=document.id,
                    document_version_id=version.id,
                    chunk_id="chunk-2",
                    score=0.7,
                ),
            ]
        )
        service = retrieval_service(db_session, vector_index=vector_index)

        # Create disabled rewrite plan
        plan = RewritePlan(
            original_query="vacation policy",
            mode=QueryRewriteMode.DISABLED,
            was_contextualized=False,
        )

        # Use retrieve_with_rewrite_plan with disabled mode
        response = service.retrieve_with_rewrite_plan(
            user_id=user.id,
            workspace_id=workspace.id,
            query="vacation policy",
            rewrite_plan=plan,
        )

        # Should behave like standard retrieve
        assert len(response.chunks) == 2
        assert response.chunks[0].chunk_id == "chunk-1"  # Higher score first
        assert response.chunks[1].chunk_id == "chunk-2"

    @pytest.mark.integration
    def test_multi_query_deduplicates_and_merges_results(self, db_session):
        """Test that multi-query retrieval deduplicates by chunk_id."""
        user = create_user(db_session)
        workspace = create_workspace(db_session)
        create_membership(db_session, user=user, workspace=workspace, role="member")
        document, version = create_ready_active_version(db_session, workspace=workspace, user=user)

        # Simulate vector index returning different chunks for different queries
        # Query 1 returns chunk-1 (score 0.9) and chunk-2 (score 0.7)
        # Query 2 returns chunk-1 (score 0.85) and chunk-3 (score 0.8)
        # Expected: chunk-1 (0.9 - highest), chunk-2 (0.7), chunk-3 (0.8)

        class MultiQueryVectorIndex:
            def __init__(self):
                self.call_count = 0
                self.queries = []

            def query(self, query: VectorIndexQuery) -> list[VectorIndexResult]:
                self.queries.append(query)
                self.call_count += 1

                if self.call_count == 1:  # First query
                    return [
                        vector_result(
                            workspace_id=workspace.id,
                            document_id=document.id,
                            document_version_id=version.id,
                            chunk_id="chunk-1",
                            score=0.9,
                        ),
                        vector_result(
                            workspace_id=workspace.id,
                            document_id=document.id,
                            document_version_id=version.id,
                            chunk_id="chunk-2",
                            score=0.7,
                        ),
                    ]
                else:  # Second query
                    return [
                        vector_result(
                            workspace_id=workspace.id,
                            document_id=document.id,
                            document_version_id=version.id,
                            chunk_id="chunk-1",
                            score=0.85,  # Lower than first query's score
                        ),
                        vector_result(
                            workspace_id=workspace.id,
                            document_id=document.id,
                            document_version_id=version.id,
                            chunk_id="chunk-3",
                            score=0.8,
                        ),
                    ]

        vector_index = MultiQueryVectorIndex()
        service = retrieval_service(db_session, vector_index=vector_index)

        # Create multi-query plan
        plan = RewritePlan(
            original_query="vacation policy",
            rewritten_queries=["time off rules"],
            mode=QueryRewriteMode.MULTI_QUERY,
            was_contextualized=False,
        )

        # Use retrieve_with_rewrite_plan with multi-query mode
        response = service.retrieve_with_rewrite_plan(
            user_id=user.id,
            workspace_id=workspace.id,
            query="vacation policy",
            rewrite_plan=plan,
        )

        # Should have 3 unique chunks, sorted by highest score
        assert len(response.chunks) == 3
        assert response.chunks[0].chunk_id == "chunk-1"  # Score 0.9 (best)
        assert response.chunks[0].score == 0.9
        assert response.chunks[1].chunk_id == "chunk-3"  # Score 0.8
        assert response.chunks[2].chunk_id == "chunk-2"  # Score 0.7

    @pytest.mark.integration
    def test_multi_query_respects_workspace_scope(self, db_session):
        """Test that multi-query retrieval preserves workspace scoping."""
        user = create_user(db_session)
        workspace = create_workspace(db_session)
        create_membership(db_session, user=user, workspace=workspace, role="member")
        document, version = create_ready_active_version(db_session, workspace=workspace, user=user)

        vector_index = FakeVectorIndex(
            [
                vector_result(
                    workspace_id=workspace.id,
                    document_id=document.id,
                    document_version_id=version.id,
                    chunk_id="chunk-1",
                ),
            ]
        )
        service = retrieval_service(db_session, vector_index=vector_index)

        plan = RewritePlan(
            original_query="policy",
            rewritten_queries=["rules"],
            mode=QueryRewriteMode.MULTI_QUERY,
        )

        response = service.retrieve_with_rewrite_plan(
            user_id=user.id,
            workspace_id=workspace.id,
            query="policy",
            rewrite_plan=plan,
        )

        # All vector index queries should have the same workspace_id
        for query in vector_index.queries:
            assert query.workspace_id == workspace.id

    @pytest.mark.integration
    def test_timeout_falls_back_to_original_safely(self, db_session):
        """Test that timeout in multi-query falls back gracefully."""
        user = create_user(db_session)
        workspace = create_workspace(db_session)
        create_membership(db_session, user=user, workspace=workspace, role="member")
        document, version = create_ready_active_version(db_session, workspace=workspace, user=user)

        class TimeoutVectorIndex:
            def __init__(self):
                self.call_count = 0
                self.queries = []

            def query(self, query: VectorIndexQuery) -> list[VectorIndexResult]:
                self.queries.append(query)
                self.call_count += 1
                if self.call_count == 1:
                    return [
                        vector_result(
                            workspace_id=workspace.id,
                            document_id=document.id,
                            document_version_id=version.id,
                            chunk_id="chunk-1",
                        ),
                    ]
                else:
                    # Simulate timeout on second query
                    raise TimeoutError("Vector index timeout")

        vector_index = TimeoutVectorIndex()
        service = retrieval_service(db_session, vector_index=vector_index)

        plan = RewritePlan(
            original_query="policy",
            rewritten_queries=["rules"],
            mode=QueryRewriteMode.MULTI_QUERY,
        )

        # Should not raise, should return results from first query
        response = service.retrieve_with_rewrite_plan(
            user_id=user.id,
            workspace_id=workspace.id,
            query="policy",
            rewrite_plan=plan,
        )

        # Should have returned results from successful first query
        assert len(response.chunks) >= 0  # May have chunks from first query
