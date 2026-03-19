from pathlib import Path
import shutil

SOURCE = Path("/Users/george/Documents/Spiritual/Church/Sermon Notes")
DEST = Path("/Users/george/Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid/03_Sermon_Notes")

ALLOWED_EXTENSIONS = {
    ".pdf", ".pages", ".doc", ".docx", ".txt", ".rtf", ".md"
}

SKIP_NAMES = {".DS_Store"}


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