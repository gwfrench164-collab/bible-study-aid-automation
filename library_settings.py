"""Storage locations shared by desktop search and future hosted deployments."""
import os
from pathlib import Path

DEFAULT_LIBRARY_ROOT = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid"


def configured_path(name, default):
    return Path(os.environ.get(name) or default).expanduser().resolve()


LIBRARY_ROOT = configured_path("BIBLE_STUDY_LIBRARY_ROOT", DEFAULT_LIBRARY_ROOT)
INDEX_PATH = configured_path("BIBLE_STUDY_INDEX_PATH", LIBRARY_ROOT / "99_Index/bible_study.db")
STUDIES_PATH = configured_path(
    "BIBLE_STUDY_STUDIES_PATH",
    Path.home() / "Library/Application Support/Bible Study Aid/saved-passages.sqlite",
)
LEGACY_LIBRARY_ROOT = configured_path("BIBLE_STUDY_LEGACY_LIBRARY_ROOT", DEFAULT_LIBRARY_ROOT)


def source_path(stored_path):
    """Resolve existing index paths after an explicitly configured library move."""
    if not stored_path or not stored_path.strip():
        raise FileNotFoundError("Empty source path")
    path = Path(stored_path)
    if path.is_absolute():
        if LIBRARY_ROOT != LEGACY_LIBRARY_ROOT and path.is_relative_to(LEGACY_LIBRARY_ROOT):
            path = LIBRARY_ROOT / path.relative_to(LEGACY_LIBRARY_ROOT)
        return path.resolve()
    resolved = (LIBRARY_ROOT / path).resolve()
    if not resolved.is_relative_to(LIBRARY_ROOT):
        raise FileNotFoundError("Source path is outside the configured library")
    return resolved
