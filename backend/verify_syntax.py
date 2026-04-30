#!/usr/bin/env python3
"""Simple syntax verification script."""

import sys

try:
    print("Verifying models.py...")
    from app.domain.query_rewriting.models import (
        QueryRewriteMode,
        RewritePlan,
        QueryRewriteRequest,
    )
    print("✓ models.py imports OK")

    print("Verifying query_rewrite_config.py...")
    from app.core.config.query_rewrite_config import QueryRewriteConfig
    print("✓ query_rewrite_config.py imports OK")

    print("Verifying service.py...")
    from app.domain.query_rewriting.service import QueryRewriteService
    print("✓ service.py imports OK")

    print("Verifying multi_query_retrieval.py...")
    from app.domain.query_rewriting.multi_query_retrieval import (
        MultiQueryRetrievalService,
    )
    print("✓ multi_query_retrieval.py imports OK")

    print("Verifying retrieval.py has new method...")
    from app.domain.services.retrieval import RetrievalService
    assert hasattr(RetrievalService, "retrieve_with_rewrite_plan")
    print("✓ retrieval.py has retrieve_with_rewrite_plan method")

    print("\n✓ All syntax checks passed!")
    sys.exit(0)

except Exception as e:
    print(f"\n✗ Syntax verification failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
