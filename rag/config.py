"""Safe, auditable configuration for CallGuard AI knowledge retrieval."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
CONFIG_PATH = PROJECT_ROOT / "config" / "vector_store.json"
VECTOR_STORE_NAME = "CallGuard AI synthetic knowledge base"
CONFIG_VERSION = 1

# This is the complete production indexing boundary. Callers cannot add paths.
KNOWLEDGE_FILES = (
    "company_overview.md",
    "personas.md",
    "product_strategy.md",
    "architecture.md",
    "roadmap.md",
)

VECTOR_STORE_ID_PATTERN = re.compile(r"^vs_[A-Za-z0-9_-]+$")
FILE_ID_PATTERN = re.compile(r"^file-[A-Za-z0-9_-]+$")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def default_config() -> dict[str, Any]:
    return {
        "config_version": CONFIG_VERSION,
        "vector_store_name": VECTOR_STORE_NAME,
        "vector_store_id": None,
        "files": {},
    }


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate config shape and prevent non-allowlisted file manifests."""
    if config.get("config_version") != CONFIG_VERSION:
        raise ValueError(f"Unsupported vector-store config version; expected {CONFIG_VERSION}.")
    if config.get("vector_store_name") != VECTOR_STORE_NAME:
        raise ValueError("Unexpected vector-store name in config.")
    vector_store_id = config.get("vector_store_id")
    if vector_store_id is not None and not is_valid_vector_store_id(vector_store_id):
        raise ValueError("vector_store_id must be null or a valid OpenAI vector-store ID.")
    files = config.get("files")
    if not isinstance(files, dict):
        raise ValueError("files must be an object keyed by allowlisted filename.")
    unexpected_files = set(files) - set(KNOWLEDGE_FILES)
    if unexpected_files:
        raise ValueError("Config contains files outside the production knowledge allowlist.")
    for filename, entry in files.items():
        if not isinstance(entry, dict):
            raise ValueError(f"Manifest entry for {filename} must be an object.")
        if not FILE_ID_PATTERN.fullmatch(str(entry.get("file_id", ""))):
            raise ValueError(f"Manifest entry for {filename} has an invalid file_id.")
        if not SHA256_PATTERN.fullmatch(str(entry.get("sha256", ""))):
            raise ValueError(f"Manifest entry for {filename} has an invalid SHA-256 hash.")
        if entry.get("status") != "completed":
            raise ValueError(f"Manifest entry for {filename} must have completed status.")
    return config


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    if not path.exists():
        return default_config()
    with path.open(encoding="utf-8") as config_file:
        config = json.load(config_file)
    return validate_config(config)


def save_config(config: dict[str, Any], path: Path = CONFIG_PATH) -> None:
    """Persist identifiers and hashes only; no credentials or document contents."""
    validate_config(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def is_valid_vector_store_id(value: object) -> bool:
    return isinstance(value, str) and bool(VECTOR_STORE_ID_PATTERN.fullmatch(value))


def load_vector_store_id() -> str | None:
    """Load an environment override or the validated local non-secret config ID."""
    environment_id = os.getenv("CALLGUARD_VECTOR_STORE_ID")
    if environment_id:
        if not is_valid_vector_store_id(environment_id):
            raise ValueError("CALLGUARD_VECTOR_STORE_ID is not a valid vector-store ID.")
        return environment_id
    return load_config().get("vector_store_id")


def knowledge_paths() -> tuple[Path, ...]:
    """Resolve and validate every upload path inside knowledge/."""
    resolved_directory = KNOWLEDGE_DIR.resolve()
    paths = tuple((KNOWLEDGE_DIR / filename).resolve() for filename in KNOWLEDGE_FILES)
    for path in paths:
        if path.parent != resolved_directory or path.suffix.lower() != ".md":
            raise ValueError("Knowledge allowlist must contain direct Markdown children only.")
        if not path.is_file():
            raise FileNotFoundError(f"Allowlisted knowledge file is missing: {path.name}")
    return paths
