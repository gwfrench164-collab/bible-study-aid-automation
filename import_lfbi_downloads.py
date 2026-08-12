from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote


BASE = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid"
LFBI_ROOT = BASE / "02_LFBI"
DOWNLOADS = Path.home() / "Downloads"
REPORT_PATH = BASE / "99_Index" / "LFBI_Download_Intake.md"

SUPPORTED_SUFFIXES = {".pdf", ".ppt", ".pptx", ".doc", ".docx", ".rtf", ".txt"}
RESOURCE_SUBDIRS = {
    "handout": "handouts",
    "slides": "slides",
    "appendix": "appendices",
    "pdf": "additional_materials",
    "resource": "additional_materials",
    "other": "additional_materials",
}


def normalized_name(value: str) -> str:
    value = unquote(value or "").lower()
    value = re.sub(r"\s*\(\d+\)\s*$", "", Path(value).stem)
    value = re.sub(r"\b(file|download|document|pdf|ppt|pptx|doc|docx|rtf|txt)\b", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_confident_match(resource: dict, candidate: Path) -> bool:
    title = normalized_name(resource.get("title", ""))
    filename = normalized_name(candidate.name)
    if not title or not filename:
        return False
    if title == filename:
        return True

    title_words = title.split()
    filename_words = filename.split()
    if len(title_words) < 3 or len(filename_words) < 3:
        return False
    shorter = min(len(title_words), len(filename_words))
    common = len(set(title_words) & set(filename_words))
    return common == shorter and abs(len(title_words) - len(filename_words)) <= 1


def destination_dir(course_root: Path, resource: dict) -> Path:
    subdir = RESOURCE_SUBDIRS.get(resource.get("kind", "resource"), "additional_materials")
    week_number = resource.get("week_number")
    if isinstance(week_number, int):
        matches = sorted(path for path in course_root.glob(f"Week_{week_number:02d}*") if path.is_dir())
        week_root = matches[0] if matches else course_root / f"Week_{week_number:02d}"
        return week_root / subdir
    return course_root / "Course_Materials" / subdir


def safe_copy(source: Path, destination_dir_path: Path) -> tuple[Path, str]:
    destination_dir_path.mkdir(parents=True, exist_ok=True)
    destination = destination_dir_path / source.name
    if destination.exists():
        if destination.stat().st_size == source.stat().st_size and file_hash(destination) == file_hash(source):
            return destination, "already_present"
        counter = 2
        while True:
            alternative = destination.with_name(f"{destination.stem}_{counter}{destination.suffix}")
            if not alternative.exists():
                destination = alternative
                break
            counter += 1
    shutil.copy2(source, destination)
    return destination, "copied"


def process_manifest(manifest_path: Path, download_files: list[Path]) -> dict:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    course_root = manifest_path.parent
    queued = data.get("queued_resources", [])
    imported = []
    ambiguous = []
    unmatched = []

    remaining = []
    for resource in queued:
        matches = [path for path in download_files if is_confident_match(resource, path)]
        if len(matches) == 1:
            source = matches[0]
            destination, action = safe_copy(source, destination_dir(course_root, resource))
            record = {
                **resource,
                "path": str(destination),
                "imported_from": str(source),
                "imported_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "intake_action": action,
            }
            imported.append(record)
            if record not in data.setdefault("downloaded_resources", []):
                data["downloaded_resources"].append(record)
        elif len(matches) > 1:
            ambiguous.append({"resource": resource, "matches": [str(path) for path in matches]})
            remaining.append(resource)
        else:
            unmatched.append(resource)
            remaining.append(resource)

    data["queued_resources"] = remaining
    if imported:
        manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    return {
        "course": data.get("course_title") or course_root.name,
        "manifest": str(manifest_path),
        "imported": imported,
        "ambiguous": ambiguous,
        "unmatched": unmatched,
    }


def write_report(results: list[dict], download_count: int) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# LFBI Download Intake",
        "",
        f"Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"Eligible files scanned in Downloads: {download_count}",
        "",
    ]
    for result in results:
        lines.extend([
            f"## {result['course']}",
            "",
            f"- Imported automatically: {len(result['imported'])}",
            f"- Ambiguous matches requiring review: {len(result['ambiguous'])}",
            f"- Still awaiting download: {len(result['unmatched'])}",
            "",
        ])
        for item in result["imported"]:
            lines.append(f"- Imported `{Path(item['imported_from']).name}` as `{item['path']}`")
        if result["ambiguous"]:
            lines.extend(["", "### Ambiguous matches", ""])
            for item in result["ambiguous"]:
                lines.append(f"- {item['resource'].get('title', 'Untitled')}: {', '.join(item['matches'])}")
        lines.append("")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    download_files = sorted(
        path for path in DOWNLOADS.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    ) if DOWNLOADS.exists() else []
    manifests = sorted(LFBI_ROOT.rglob("course_manifest_processed.json"))
    results = [process_manifest(path, download_files) for path in manifests]
    write_report(results, len(download_files))
    imported_count = sum(len(result["imported"]) for result in results)
    ambiguous_count = sum(len(result["ambiguous"]) for result in results)
    waiting_count = sum(len(result["unmatched"]) for result in results)
    print(f"Imported LFBI downloads: {imported_count}")
    print(f"Ambiguous LFBI download matches: {ambiguous_count}")
    print(f"LFBI resources still awaiting download: {waiting_count}")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
