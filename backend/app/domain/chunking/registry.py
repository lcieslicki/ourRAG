"""
Chunking strategy registry (A7).

Named strategies with explicit metadata.
Production default: markdown_structure_v1 (baseline, unchanged).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkingStrategyMeta:
    name: str
    version: str
    description: str
    default_chunk_size: int
    default_chunk_overlap: int
    experimental: bool = False


# ── Strategy registry ─────────────────────────────────────────────────────────

_REGISTRY: dict[str, ChunkingStrategyMeta] = {}


def register(meta: ChunkingStrategyMeta) -> ChunkingStrategyMeta:
    _REGISTRY[meta.name] = meta
    return meta


STRATEGY_MARKDOWN_V1 = register(
    ChunkingStrategyMeta(
        name="markdown_structure_v1",
        version="v1",
        description="Baseline structure-aware markdown chunking.",
        default_chunk_size=1200,
        default_chunk_overlap=150,
    )
)

STRATEGY_MARKDOWN_V2_SMALLER = register(
    ChunkingStrategyMeta(
        name="markdown_structure_v2_smaller_chunks",
        version="v2",
        description="Smaller chunks for higher retrieval precision.",
        default_chunk_size=600,
        default_chunk_overlap=80,
    )
)

STRATEGY_MARKDOWN_V3_LARGER = register(
    ChunkingStrategyMeta(
        name="markdown_structure_v3_larger_context",
        version="v3",
        description="Larger context windows for more coherent answers.",
        default_chunk_size=2400,
        default_chunk_overlap=300,
    )
)

STRATEGY_TABLE_AWARE_V1 = register(
    ChunkingStrategyMeta(
        name="markdown_table_aware_v1",
        version="v1",
        description="Table-aware markdown chunking: preserves header row in every sub-chunk.",
        default_chunk_size=1200,
        default_chunk_overlap=0,
    )
)

STRATEGY_PARENT_CHILD_EXPERIMENTAL = register(
    ChunkingStrategyMeta(
        name="parent_child_experimental_v1",
        version="v1",
        description="Experimental parent-child chunking for hierarchical context.",
        default_chunk_size=1200,
        default_chunk_overlap=150,
        experimental=True,
    )
)


def get_strategy(name: str) -> ChunkingStrategyMeta:
    if name not in _REGISTRY:
        raise ValueError(
            f"Unknown chunking strategy: {name!r}. "
            f"Available: {sorted(_REGISTRY.keys())}"
        )
    return _REGISTRY[name]


def list_strategies() -> list[ChunkingStrategyMeta]:
    return list(_REGISTRY.values())
