from pathlib import Path
import shutil

SOURCE = Path("/Users/george/Documents/Spiritual/LFBI")
DEST = Path("/Users/george/Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid/02_LFBI")

ALLOWED_EXTENSIONS = {
    ".pdf", ".pages", ".doc", ".docx", ".txt", ".rtf", ".key", ".xml", ".mp4"
}

SKIP_NAMES = {".DS_Store"}

TOP_LEVEL_MISC = DEST / "_Top_Level_Misc"


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
    TOP_LEVEL_MISC.mkdir(parents=True, exist_ok=True)

    for item in SOURCE.iterdir():
        if item.name in SKIP_NAMES:
            continue

        if item.is_file():
            if should_copy_file(item):
                copy_file(item, TOP_LEVEL_MISC / item.name)
            continue

        if item.is_dir():
            course_dest = DEST / item.name
            for path in item.rglob("*"):
                if path.name in SKIP_NAMES:
                    continue
                if should_copy_file(path):
                    relative_path = path.relative_to(item)
                    copy_file(path, course_dest / relative_path)

    print("LFBI import complete.")


if __name__ == "__main__":
    main()