"""Reusable File Search construction for allowlisted specialist knowledge scopes."""

from __future__ import annotations

from collections.abc import Collection

from agents import FileSearchTool

from rag.config import KNOWLEDGE_FILES, is_valid_vector_store_id


def build_file_search_tool(
    vector_store_id: str,
    filenames: Collection[str],
    *,
    max_num_results: int = 5,
) -> FileSearchTool:
    """Build File Search restricted to a validated subset of indexed knowledge."""
    if not is_valid_vector_store_id(vector_store_id):
        raise ValueError("A valid OpenAI vector-store ID is required for retrieval.")
    requested_files = tuple(dict.fromkeys(filenames))
    if not requested_files or not set(requested_files).issubset(KNOWLEDGE_FILES):
        raise ValueError("Retrieval filenames must be a non-empty subset of the knowledge allowlist.")
    return FileSearchTool(
        vector_store_ids=[vector_store_id],
        max_num_results=max(1, min(max_num_results, 10)),
        include_search_results=True,
        filters={"type": "in", "key": "source_filename", "value": list(requested_files)},
    )
