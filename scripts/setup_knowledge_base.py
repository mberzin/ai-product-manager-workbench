"""Create or update the synthetic CallGuard AI OpenAI vector store.

Run from the project root after setting OPENAI_API_KEY:
    python scripts/setup_knowledge_base.py

Only the fixed Markdown allowlist in rag/config.py can be uploaded. Output contains
safe filenames, object identifiers, hashes/status summaries, and never credentials
or document contents.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path


# Make project modules importable when the script is run by file path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402
from openai import NotFoundError, OpenAI  # noqa: E402

from rag.config import (  # noqa: E402
    KNOWLEDGE_FILES,
    VECTOR_STORE_NAME,
    knowledge_paths,
    load_config,
    save_config,
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_named_vector_store(client: OpenAI):
    """Reuse an existing exact-name store when local config has no usable ID."""
    for vector_store in client.vector_stores.list(limit=100):
        if vector_store.name == VECTOR_STORE_NAME and vector_store.status != "expired":
            return vector_store
    return None


def get_or_create_vector_store(client: OpenAI, configured_id: str | None):
    if configured_id:
        try:
            return client.vector_stores.retrieve(configured_id)
        except NotFoundError:
            print(f"Configured vector store not found: {configured_id}; finding or creating a replacement.")
    existing = find_named_vector_store(client)
    if existing:
        print(f"Reusing vector store: {existing.id} status={existing.status}")
        return existing
    created = client.vector_stores.create(
        name=VECTOR_STORE_NAME,
        description="Synthetic CallGuard AI company, persona, strategy, architecture, and roadmap knowledge.",
    )
    print(f"Created vector store: {created.id} status={created.status}")
    return created


def attached_file_ids(client: OpenAI, vector_store_id: str) -> set[str]:
    return {item.id for item in client.vector_stores.files.list(vector_store_id, limit=100)}


def upload_changed_file(
    client: OpenAI,
    vector_store_id: str,
    path: Path,
    digest: str,
    old_entry: dict | None,
) -> dict:
    """Upload and attach one changed file, then detach its superseded version."""
    with path.open("rb") as source:
        uploaded = client.files.create(file=source, purpose="assistants")
    vector_file = client.vector_stores.files.create_and_poll(
        uploaded.id,
        vector_store_id=vector_store_id,
        attributes={"source_filename": path.name, "sha256": digest},
    )
    if vector_file.status != "completed":
        raise RuntimeError(f"Indexing failed for {path.name}: status={vector_file.status}")

    old_file_id = old_entry.get("file_id") if old_entry else None
    if old_file_id and old_file_id != uploaded.id:
        try:
            client.vector_stores.files.delete(old_file_id, vector_store_id=vector_store_id)
            client.files.delete(old_file_id)
        except NotFoundError:
            pass
    print(f"Indexed {path.name}: file_id={uploaded.id} status={vector_file.status}")
    return {"file_id": uploaded.id, "sha256": digest, "status": vector_file.status}


def main() -> int:
    load_dotenv()
    paths = knowledge_paths()
    config = load_config()
    client = OpenAI()  # Reads OPENAI_API_KEY from the environment.
    vector_store = get_or_create_vector_store(client, config.get("vector_store_id"))
    attached = attached_file_ids(client, vector_store.id)
    previous_files = config.get("files", {})
    updated_files: dict[str, dict] = {}

    print(f"Allowlisted knowledge files: {len(KNOWLEDGE_FILES)}")
    for path in paths:
        digest = file_sha256(path)
        previous = previous_files.get(path.name)
        unchanged = (
            previous
            and previous.get("sha256") == digest
            and previous.get("file_id") in attached
            and previous.get("status") == "completed"
        )
        if unchanged:
            updated_files[path.name] = previous
            print(f"Unchanged {path.name}: file_id={previous['file_id']} status=completed")
        else:
            updated_files[path.name] = upload_changed_file(
                client, vector_store.id, path, digest, previous
            )

    config.update(
        {
            "vector_store_id": vector_store.id,
            "vector_store_name": VECTOR_STORE_NAME,
            "files": updated_files,
        }
    )
    save_config(config)
    print(f"Knowledge base ready: vector_store_id={vector_store.id} indexed_files={len(updated_files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
