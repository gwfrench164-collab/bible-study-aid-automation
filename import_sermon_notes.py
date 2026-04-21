# LEGACY FILE
# This file was part of the older copy-first import workflow.
# Sermon Notes are now indexed from their original source location through
# the current live indexing system instead of being copied first.
# This file is kept for reference only unless intentionally reused.
from pathlib import Path
import shutil

BASE = Path("/Users/george/Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid")
AUTOMATION_DIR = BASE / "98_Automation"
REGISTRY_FILE = AUTOMATION_DIR / "source_folders.tsv"
SOURCE_KEY = "Sermon Notes"

ALLOWED_EXTENSIONS = {
    ".pdf", ".pages", ".doc", ".docx", ".txt", ".rtf", ".md"
}
SKIP_NAMES = {".DS_Store"}


def load_registry_entry(source_key: str):
    if not REGISTRY_FILE.exists():
        raise FileNotFoundError(f"Missing source folder registry: {REGISTRY_FILE}")

    with REGISTRY_FILE.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            key, source_path, dest_rel = parts
            if key == source_key:
                return Path(source_path), BASE / dest_rel

    raise KeyError(f"Source key not found in registry: {source_key}")


SOURCE, DEST = load_registry_entry(SOURCE_KEY)


def should_copy_file(path: Path) -> bool:
    if path.name in SKIP_NAMES:
        return False
    if path.is_dir():
        return False
    return path.suffix.lower() in ALLOWED_EXTENSIONS


def files_are_same(src: Path, dst: Path) -> bool:
    return (
        dst.exists()
        and src.stat().st_size == dst.stat().st_size
        and int(src.stat().st_mtime) == int(dst.stat().st_mtime)
    )


def copy_file(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if files_are_same(src, dst):
        print(f"SKIP unchanged: {src}")
        return
    shutil.copy2(src, dst)
    print(f"COPIED: {src} -> {dst}")


def main():
    if not SOURCE.exists():
        print(f"Missing source directory: {SOURCE}")
        return

    DEST.mkdir(parents=True, exist_ok=True)

    for path in SOURCE.rglob("*"):
        if path.name in SKIP_NAMES:
            continue
        if should_copy_file(path):
            relative_path = path.relative_to(SOURCE)
            copy_file(path, DEST / relative_path)

    print("Sermon notes import complete.")


if __name__ == "__main__":
    main()