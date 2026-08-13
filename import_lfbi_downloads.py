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

GENERIC_RESOURCE_WORDS = {
    "week", "wk", "lesson", "handout", "handouts", "slide", "slides",
    "syllabus", "schedule", "class", "course", "material", "materials",
}

# Resource IDs are stable Moodle identifiers.  They let us safely recognize
# downloads whose visible titles are generic (for example, many files are just
# called "Slides") and preserve the week shown in Moodle's breadcrumb.
ACTS_DOWNLOADS = {
    6277: (None, "2019 LFBI Acts Syllabus.pdf"),
    6279: (1, "Handout week 1.pdf"),
    6280: (1, "Acts intro.pdf"),
    6281: (1, "Appendex 1 Historical Picture.pdf"),
    6282: (None, "6282 - LFBI Bible Survey 2 - Acts Handout.pdf"),
    6284: (2, "Handout week 2 Acts 1.pdf"),
    6285: (2, "6285 - Acts 1.pdf"),
    6286: (2, "Appendex 2  Jesus was in the grave 3 days and nights.pdf"),
    6290: (3, "6290 - Handout week 3 - Acts 2.pdf"),
    6291: (3, "Acts 1-2.pdf"),
    6292: (3, "Appendix 4 - The Jewish Calendar and Feast Days. Dr. Best.pdf"),
    6293: (3, "Appendex 5 - The Apostles at Pentecost.pdf"),
    6296: (4, "Handout week 4 - Acts 2b.pdf"),
    6297: (4, "Acts 2b.pdf"),
    6300: (5, "Handout week 5 - Acts 2d.pdf"),
    6301: (5, "Acts 2d.pdf"),
    6302: (5, "Appendix 6 - 7 Baptisms Review.pdf"),
    6305: (6, "Handout week 6 - Acts 2-4.pdf"),
    6306: (6, "Acts 2d-4.pdf"),
    6307: (6, "Appendix 7 - Tongues Overview.pdf"),
    6311: (7, "Handout week 7 - Acts 4-5.pdf"),
    6312: (7, "Acts 4-5.pdf"),
    6315: (8, "Handout week 8 - Acts 6-8.pdf"),
    6316: (8, "Acts 6-8.pdf"),
    6320: (9, "6320 - Handout week 9 - Acts 9-11.pdf"),
    6321: (9, "Acts 8-11.pdf"),
    # Moodle exposes the same file for both Tongues resources.
    6322: (9, "Appendix 7 - Tongues Overview.pdf"),
    6325: (10, "6325 - Handout week 10 - Acts 12-14.pdf"),
    6326: (10, "6326 - Acts 11-14.pdf"),
    6331: (11, "6331 - Handout week 10 - Acts 14-16.pdf"),
    6332: (11, "6332 - Acts 14-16.pdf"),
    6333: (11, "6333 - Appendix 9 - Letters Written.pdf"),
    6336: (12, "6336 - Handout week 12 - Acts 17-19.pdf"),
    6337: (12, "6337 - Acts 17-19.pdf"),
    6340: (13, "6340 - Handout week 13 - Acts 19-21.pdf"),
    6341: (13, "6341 - Acts 19-21.pdf"),
    6342: (13, "Acts 19-21.pptx"),
    6345: (14, "6345 - Handout week 14 - Acts 22-24.pdf"),
    6346: (14, "6346 - Acts 22-24.pdf"),
    6347: (14, "6347 - Appendix 11 - Power of Testimony Acts 22.pdf"),
    6350: (15, "6350 - Handout week 15 - Acts 25-26.pdf"),
    6351: (15, "6351 - Acts 25-26.pdf"),
    6355: (16, "6355 - Handout week 15 - Acts 27-28.pdf"),
    6356: (16, "6356 - Acts 27-28.pdf"),
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
    captured_filename = resource.get("download_filename")
    if captured_filename and candidate.name == captured_filename:
        return True
    resource_id = resource_id_from_url(resource.get("url", ""))
    mapped = ACTS_DOWNLOADS.get(resource_id)
    if mapped and candidate.name == mapped[1]:
        return True
    title = normalized_name(resource.get("title", ""))
    filename = normalized_name(candidate.name)
    if not title or not filename:
        return False
    title_specific = [word for word in title.split() if word not in GENERIC_RESOURCE_WORDS and not word.isdigit()]
    filename_specific = [word for word in filename.split() if word not in GENERIC_RESOURCE_WORDS and not word.isdigit()]
    if not title_specific or not filename_specific:
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


def resource_id_from_url(url: str) -> int | None:
    match = re.search(r"[?&]id=(\d+)", url or "")
    return int(match.group(1)) if match else None


def enriched_resource(resource: dict) -> dict:
    result = dict(resource)
    mapped = ACTS_DOWNLOADS.get(resource_id_from_url(resource.get("url", "")))
    if mapped and mapped[0] is not None:
        result["week_number"] = mapped[0]
        result["week_title"] = f"Week {mapped[0]}"
    return result


def clean_destination_name(name: str) -> str:
    return re.sub(r"^\d+\s*-\s*", "", name)


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
    destination = destination_dir_path / clean_destination_name(source.name)
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
    for raw_resource in queued:
        resource = enriched_resource(raw_resource)
        captured_filename = resource.get("download_filename")
        if captured_filename:
            matches = [path for path in download_files if path.name == captured_filename]
        else:
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
            remaining.append(raw_resource)
        else:
            unmatched.append(resource)
            remaining.append(raw_resource)

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
