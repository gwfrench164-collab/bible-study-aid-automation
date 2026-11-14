from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from pipeline_support import atomic_write_text, excluded_resource
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote


BASE = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid"
LFBI_ROOT = BASE / "02_LFBI"
DOWNLOADS = Path.home() / "Downloads"
REPORT_PATH = BASE / "99_Index" / "LFBI_Download_Intake.md"
TRASH_ROOT = Path.home() / ".Trash"

SUPPORTED_SUFFIXES = {".pdf", ".ppt", ".pptx", ".doc", ".docx", ".rtf", ".txt", ".xlsx", ".zip"}
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

PASTORAL_PROCEDURES_DOWNLOADS = {
    9229: (None, "Syllabus Pastoral Procedures 2021.pdf"),
    9379: (1, "Week ONE - Handout.pdf"),
    9385: (1, "Week ONE.pdf"),
    9380: (1, "Marriage Divorce and Remarriage - Shelby.pdf"),
    9478: (2, "Week TWO - The Ordinances.pdf"),
    9477: (2, "Week TWO.pdf"),
    9506: (4, "Week FOUR - Handout.pdf"),
    9549: (5, "Week FIVE - Handout.pdf"),
    9548: (5, "Week FIVE.pdf"),
    9626: (6, "Week SIX - Handout.pdf"),
    9591: (6, "Week SIX.pdf"),
    9587: (6, "Focus handout - Day 2.pdf"),
    9590: (6, "Ministry. Approach to Discipleship.pdf"),
    9633: (7, "Week SEVEN - Handout.pdf"),
    9709: (8, "Week EIGHT - Handout.pdf"),
    10254: (9, "membership content overview.pdf"),
    9712: (9, "RSO Policy final draft 4.pdf"),
    10330: (10, "Safegaurd.pdf"),
    10329: (10, "Safegaurds.pdf"),
    10362: (11, "Week 11 - Safeguard continued.pdf"),
    10363: (11, "Safegaurds 2.pdf"),
    10415: (12, "Week TWELVE- Handout.pdf"),
    10417: (12, "Safegaurds 3.pdf"),
    10450: (13, "Week 13 handout.pdf"),
    10492: (14, "THE ASSOCIATE PASTOR - Handout.pdf"),
    10514: (15, "Week 15 - budget Larry S. Handout.pdf"),
    10534: (15, "Church Budgeting PP.pdf"),
}

BIBLICAL_COUNSELING_DOWNLOADS = {
    8487: (None, "IntroBiblCounseling_Syllabus_Miles_F2020.pdf"),
    8481: (None, "Counseling book chapter summaries.pdf"),
    8486: (None, "chicago_turabian.pdf"),
    8600: (1, "LFBI Intro to Biblical Counseling - week 1.pdf"),
    8605: (1, "Intro to Biblical Counseling - Week 1.pdf"),
    8649: (None, "Many scientific studies can’t be replicated. That’s a problem.pdf"),
    8666: (None, "The QA_ Samuel Arbesman_ The half-life of facts _ The Economis.pdf"),
    8640: (2, "LFBI Intro to Biblical Counseling - week 2.pdf"),
    8642: (2, "Intro to Biblical Counseling - Week 2.pdf"),
    8690: (3, "LFBI Intro to Biblical Counseling - week 3.pdf"),
    8692: (3, "Slides - Week 3.pdf"),
    8720: (4, "LFBI – Intro to Biblical Counseling - week 4 handout.pdf"),
    8734: (4, "Intro to Biblical Counseling - Week 4 2020 copy copy.pdf"),
    8754: (5, "LFBI – Intro to BC- wk 5_HANDOUT_kindler.pdf"),
    9086: (5, "Intro to Biblical Counseling - Week 5 Kindler copy (1).pdf"),
    8801: (6, "LFBI Intro to Biblical Counseling - week 6.pdf"),
    8803: (6, "Intro to Biblical Counseling - Week 6.pdf"),
    8838: (7, "LFBI Intro to Biblical Counseling - week 7.pdf"),
    8841: (7, "Intro to Biblical Counseling - Week 7.pdf"),
    8862: (8, "LFBI Intro to Biblical Counseling - week 8.pdf"),
    8863: (8, "Slides - Week 8.pdf"),
    8932: (9, "LFBI Intro to Biblical Counseling - week 9.pdf"),
    8937: (9, "Intro to Biblical Counseling - Week 9.pdf"),
    8956: (10, "LFBI Intro to Biblical Counseling - week 10.pdf"),
    8964: (10, "Intro to Biblical Counseling - Week 10.pdf"),
    8957: (10, "Handout - Week 10 #2 from Self-Confrontation.pdf"),
    8958: (10, "Handout - Week 10 #3 (RECORD) from Self-Confrontation.pdf"),
    8999: (11, "LFBI – Intro to Biblical Counseling - week 11.pdf"),
    9000: (11, "Intro to Biblical Counseling - Week 11.pdf"),
    9038: (12, "Handout.pdf"),
    9084: (12, "Intro to Biblical Counseling - Week 12 (1).pdf"),
    9064: (13, "LFBI – Intro to Biblical Counseling - week 13.pdf"),
    9085: (13, "Intro to Biblical Counseling - Week 13 (1).pdf"),
    9093: (14, "LFBI Intro to Biblical Counseling - week 14.pdf"),
    9095: (14, "Scenario One  Two Review.pdf"),
    9097: (14, "Handout - Week 14 #4a from Self-Confrontation.pdf"),
    9098: (14, "Handout - Week 14 #4 from Self-Confrontation.pdf"),
    9094: (14, "Intro to Biblical Counseling - Week 14.pdf"),
    9126: (15, "LFBI Intro to Biblical Counseling - week 15.pdf"),
    9127: (15, "Slides - Week 15.pdf"),
    9129: (15, "Scenario Three Review.pdf"),
    9158: (16, "Intro to Biblical Financial Counseling - December 2020.pptx"),
    9159: (16, "Financial Counseling for LFBI Dec 2020 Handout.docx"),
    9160: (16, "Personal Budget 2020.xlsx"),
}

INTRO_NT2_DOWNLOADS = {
    22448: (None, "IntroNT2_Syllabus_Spring2024_Dobson - Copy.pdf"),
    22451: (1, "SurveyNotes.pdf"),
    22452: (1, "1TimothySlides.pdf"),
    22454: (1, "1TimothyTeacherNotes.pdf"),
    22457: (2, "2TimothyStudentHandout.pdf"),
    22458: (2, "2TimothySlides.pdf"),
    22460: (2, "2TimothyTeacherNotes.pdf"),
    22469: (3, "2TimothyStudentHandout (1).pdf"),
    22470: (3, "TitusSlides.pdf"),
    22472: (3, "TitusTeacherHandout.pdf"),
    22463: (4, "PhilemonStudentHandout.pdf"),
    22464: (4, "PhilemonSlides.pdf"),
    22466: (4, "PhilemonTeacherNotes.pdf"),
    22475: (5, "Pauline Epistles Student Handout.pdf"),
    22476: (5, "Pauline Epistle Overview Slides.pdf"),
    22478: (5, "Pauline Epistle Teacher Notes.pdf"),
    22481: (6, "GeneralEpistlesStudentHandout.pdf"),
    22482: (6, "General Epistles Flyover Slides.pdf"),
    22484: (6, "GeneralEpistlesTeacherHandout.pdf"),
    22487: (7, "HebrewsStudentHandout.pdf"),
    22488: (7, "HebrewsSlides.pdf"),
    22490: (7, "HebrewsTeacherNotes.pdf"),
    22493: (8, "JamesStudentHandout.pdf"),
    22494: (8, "JamesSlides.pdf"),
    22497: (8, "JamesTeacherHandout.pdf"),
    22500: (9, "1PeterStudentHandout.pdf"),
    22501: (9, "1PeterSlides.pdf"),
    22503: (9, "1PeterTeacherNotes.pdf"),
    22506: (10, "2PeterStudentHandout.pdf"),
    22507: (10, "2PeterSlides.pdf"),
    22509: (10, "2PeterTeacherNotes.pdf"),
    22512: (11, "1JohnStudentHandout.pdf"),
    22513: (11, "1JohnSlides.pdf"),
    22515: (11, "1JohnTeacherNotes.pdf"),
    22519: (12, "2JohnStudentHandout.pdf"),
    22520: (12, "2JohnSlides.pdf"),
    22522: (12, "2JohnTeacherNotes.pdf"),
    22525: (13, "3JohnStudentHandout.pdf"),
    22526: (13, "3JohnSlides.pdf"),
    22528: (13, "3JohnTeacherNotes.pdf"),
    22531: (14, "JudeStudentHandout.pdf"),
    22532: (14, "JudeSlides.pdf"),
    22534: (14, "JudeTeacherNotes.pdf"),
    22537: (15, "RevelationTeacherNotes.pdf"),
    22540: (16, "Week16NTReviewStudentHandout.pdf"),
    22541: (16, "Week16NTReviewSlides.pdf"),
}

BIBLE_SURVEY_4_DOWNLOADS = {
    6363: (None, "lfbi bible survey sched 042719.pdf"),
    6365: (None, "52 weeks of pursuit - weeks 05 - 48.zip"),
    6366: (None, "Weeks 1-4 - Blake Sidebottom.pdf"),
    6367: (None, "lfbi Bible Survey 4 Syllabus 010919.pdf"),
    6368: (1, "lfbi bib sur 4 week 1 handout 010919.pdf"),
    6369: (1, "lfbi bib sur 4 week 1 slides 010919.pdf"),
    6370: (1, "Week 1 Notes.pdf"),
    6373: (2, "lfbi bib sur 4 week 2 handout 011619.pdf"),
    6374: (2, "lfbi bible sur 4 week 2 ppt 011619.pdf"),
    6378: (3, "lfbi bib sur 4 week 3 handout 012319.pdf"),
    6379: (3, "lfbi bible sur 4 week 3 ppt pdf 020619.pdf"),
    6382: (4, "Week 4 Hand Out.pdf"),
    6383: (4, "lfbi bible sur 4 week 4 ppt 021319.pdf"),
    6386: (5, "lfbi bib sur 4 week 5 handout 022019.pdf"),
    6387: (5, "lfbi bible sur 4 week 5 ppt 022019.pdf"),
    6390: (6, "lfbi bible sur 4 week 6 ppt 031319.pdf"),
    6391: (6, "lfbi bib sur 4 week 6 handout 031319.pdf"),
    6394: (7, "lfbi bib sur 4 week 7 handout 032719.pdf"),
    6395: (7, "lfbi bible sur 4 week 7 ppt 032719.pdf"),
    6398: (8, "lfbi bib sur 4 week 8 handout 040319.pdf"),
    6399: (8, "lfbi bible sur 4 week 8 040319.pdf"),
    6402: (9, "lfbi bib sur 4 week 9 handout 041019.pdf"),
    6403: (9, "lfbi bible sur 4 week 9 pdf 041019.pdf"),
    6409: (10, "lfbi bible sur 4 week 10 ppt 041719.pdf"),
    6410: (10, "lfbi bib sur 4 week 10 handout 041719.pdf"),
    6413: (11, "lfbi bib sur 4 week 11 handout 042419.pdf"),
    6414: (11, "lfbi bible sur 4 week 11 ppt 042419.pdf"),
    6417: (12, "lfbi bib sur 4 week 12 handout 050119.pdf"),
    6418: (12, "lfbi bible sur 4 week 12 ppt 050119(1).pdf"),
    6421: (13, "Week 13 Handout.pdf"),
    6422: (13, "Week 13 Power Point.pdf"),
    6425: (14, "Hand Out Week 14.pdf"),
    6426: (14, "lfbi bible sur 4 week 14 slides 051519.pdf"),
    6429: (15, "lfbi bib sur 4 week 15 handout 052219.pdf"),
    6430: (15, "lfbi bible sur 4 week 15 ppt 052219.pdf"),
}


def mapped_download(resource: dict) -> tuple[int | None, str] | None:
    resource_id = resource_id_from_url(resource.get("url", ""))
    return (
        ACTS_DOWNLOADS.get(resource_id)
        or PASTORAL_PROCEDURES_DOWNLOADS.get(resource_id)
        or BIBLICAL_COUNSELING_DOWNLOADS.get(resource_id)
        or INTRO_NT2_DOWNLOADS.get(resource_id)
        or BIBLE_SURVEY_4_DOWNLOADS.get(resource_id)
    )


def normalized_name(value: str) -> str:
    value = unquote(value or "").lower()
    value = re.sub(r"\s*\(\d+\)\s*$", "", Path(value).stem)
    value = re.sub(r"\b(file|download|document|pdf|ppt|pptx|doc|docx|rtf|txt)\b", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


_HASH_CACHE = {}
_LIBRARY_FILES = None

def file_hash(path: Path) -> str:
    stat = path.stat()
    key = (str(path.resolve()), stat.st_size, stat.st_mtime_ns)
    if key in _HASH_CACHE:
        return _HASH_CACHE[key]
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    _HASH_CACHE[key] = digest.hexdigest()
    return _HASH_CACHE[key]


def is_confident_match(resource: dict, candidate: Path) -> bool:
    captured_filename = resource.get("download_filename")
    if captured_filename and candidate.name == captured_filename:
        return True
    mapped = mapped_download(resource)
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
    mapped = mapped_download(resource)
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
    # Compare all collision variants before creating another one.
    for candidate in destination_dir_path.glob(f"*{source.suffix}"):
        if candidate.is_file() and candidate.stat().st_size == source.stat().st_size and file_hash(candidate) == file_hash(source):
            return candidate, "already_present"
    # A new browser download is filed once, not duplicated locally.
    shutil.move(str(source), str(destination))
    return destination, "moved_into_library"


def extract_supported_archive(archive_path: Path) -> list[Path]:
    if archive_path.suffix.lower() != ".zip":
        return []
    output_root = archive_path.parent / archive_path.stem
    output_root.mkdir(parents=True, exist_ok=True)
    output_root_resolved = output_root.resolve()
    extracted = []
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            relative = Path(info.filename)
            if relative.is_absolute() or ".." in relative.parts:
                continue
            if relative.suffix.lower() not in SUPPORTED_SUFFIXES - {".zip"}:
                continue
            destination = output_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.resolve().is_relative_to(output_root_resolved):
                continue
            if destination.exists():
                if destination.stat().st_size == info.file_size and file_hash(destination) == hashlib.sha256(archive.read(info)).hexdigest():
                    extracted.append(destination)
                    continue
                counter = 2
                while destination.exists():
                    destination = destination.with_name(
                        f"{destination.stem}_{counter}{destination.suffix}"
                    )
                    counter += 1
            with archive.open(info) as source, destination.open("xb") as target:
                shutil.copyfileobj(source, target)
            extracted.append(destination)
    return extracted


def existing_library_files():
    global _LIBRARY_FILES
    if _LIBRARY_FILES is not None:
        return _LIBRARY_FILES
    from process_lfbi_manifest import LOCAL_DUPLICATE_SEARCH_ROOTS
    roots = list(LOCAL_DUPLICATE_SEARCH_ROOTS)
    registry = Path(__file__).with_name("source_folders.tsv")
    if registry.exists():
        for line in registry.read_text().splitlines():
            parts = line.split("\t")
            if not line.startswith("#") and len(parts) >= 2:
                roots.append(Path(parts[1]))
    _LIBRARY_FILES = sorted({p.resolve() for root in roots if root.exists() for p in root.rglob("*")
                   if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES})
    return _LIBRARY_FILES


def process_manifest(manifest_path: Path, download_files: list[Path]) -> dict:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    course_root = manifest_path.parent
    queued = data.get("queued_resources", [])
    local_files = existing_library_files()
    imported = []
    ambiguous = []
    unmatched = []

    remaining = []
    for raw_resource in queued:
        resource = enriched_resource(raw_resource)
        if excluded_resource(resource):
            data.setdefault("excluded_resources", []).append(resource)
            continue
        download_files = [p for p in download_files if p.is_file()]
        captured_filename = resource.get("download_filename")
        if captured_filename:
            matches = [path for path in download_files if path.name == captured_filename]
        else:
            matches = [path for path in download_files if is_confident_match(resource, path)]
        if not matches:
            # Only exact captured/resource-ID mapped filenames are candidates.
            expected = captured_filename or (mapped_download(resource) or (None, None))[1]
            if expected and len([w for w in normalized_name(expected).split() if w not in GENERIC_RESOURCE_WORDS and not w.isdigit()]) >= 2:
                local_matches = [p for p in local_files if p.name == expected]
                if local_matches and len({file_hash(p) for p in local_matches}) == 1:
                    matches = [local_matches[0]]
        if len(matches) > 1 and len({file_hash(p) for p in matches}) == 1:
            matches = matches[:1]
        if len(matches) == 1:
            source = matches[0]
            identical = next((p for p in local_files if p.stat().st_size == source.stat().st_size and file_hash(p) == file_hash(source)), None)
            if identical:
                destination, action = identical, "reused_local"
            else:
                destination, action = safe_copy(source, destination_dir(course_root, resource))
                local_files.append(destination)
            extracted_paths = extract_supported_archive(destination) if action != "reused_local" else []
            record = {
                **resource,
                "path": str(destination),
                "imported_from": str(source),
                "imported_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "intake_action": action,
            }
            if extracted_paths:
                record["extracted_paths"] = [str(path) for path in extracted_paths]
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
    if imported or len(remaining) != len(queued):
        atomic_write_text(manifest_path, json.dumps(data, indent=2))

    return {
        "course": data.get("course_title") or course_root.name,
        "manifest": str(manifest_path),
        "imported": imported,
        "ambiguous": ambiguous,
        "unmatched": unmatched,
    }


def cleanup_imported_downloads(results: list[dict]) -> list[dict]:
    sources = sorted({
        Path(item["imported_from"])
        for result in results
        for item in result["imported"]
        if item.get("imported_from")
    })
    sources = [path for path in sources if path.parent == DOWNLOADS and path.exists()]
    if not sources:
        return []

    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d_%H%M%S")
    cleanup_dir = TRASH_ROOT / f"LFBI_Downloads_{timestamp}"
    cleanup_dir.mkdir(parents=True, exist_ok=False)
    cleaned = []
    for source in sources:
        destination = cleanup_dir / source.name
        counter = 2
        while destination.exists():
            destination = cleanup_dir / f"{source.stem}_{counter}{source.suffix}"
            counter += 1
        shutil.move(str(source), str(destination))
        cleaned.append({"source": str(source), "trash_path": str(destination)})
    return cleaned


def write_report(results: list[dict], download_count: int, cleaned: list[dict]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# LFBI Download Intake",
        "",
        f"Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"Eligible files scanned in Downloads: {download_count}",
        f"Imported files moved out of Downloads: {len(cleaned)}",
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
    cleaned = []  # Preserve original downloads; cleanup requires an explicit separate action.
    write_report(results, len(download_files), cleaned)
    imported_count = sum(len(result["imported"]) for result in results)
    ambiguous_count = sum(len(result["ambiguous"]) for result in results)
    waiting_count = sum(len(result["unmatched"]) for result in results)
    print(f"Imported LFBI downloads: {imported_count}")
    print(f"Ambiguous LFBI download matches: {ambiguous_count}")
    print(f"LFBI resources still awaiting download: {waiting_count}")
    print(f"Imported files moved out of Downloads: {len(cleaned)}")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
