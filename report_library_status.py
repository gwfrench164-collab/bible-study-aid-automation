from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


BASE = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid"
AUTOMATION_DIR = BASE / "98_Automation"
INDEX_DIR = BASE / "99_Index"
DB_PATH = INDEX_DIR / "bible_study.db"
SOURCE_REGISTRY = AUTOMATION_DIR / "source_folders.tsv"
PODCAST_REGISTRIES = [
    AUTOMATION_DIR / "podcast_sources.tsv",
    AUTOMATION_DIR / "lff_church_sources.tsv",
]
LOG_DIR = AUTOMATION_DIR / "logs"
ARCHIVE_DIR = AUTOMATION_DIR / "archives"

READABLE_SUFFIXES = {".txt", ".md", ".rtf", ".pdf", ".docx", ".pages"}


def load_tab_registry(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    rows = []
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        rows.append([part.strip() for part in line.split("\t")])
    return rows


def load_pipe_registry(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    rows = []
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        rows.append([part.strip() for part in line.split("|")])
    return rows


def suffix_counts(root: Path) -> Counter:
    if not root.exists():
        return Counter()
    return Counter(
        path.suffix.lower() or "[none]"
        for path in root.rglob("*")
        if path.is_file()
    )


def database_status() -> dict:
    status = {
        "exists": DB_PATH.exists(),
        "documents": 0,
        "chunks": 0,
        "scripture_references": 0,
        "documents_by_source_type": {},
    }
    if not DB_PATH.exists():
        return status

    connection = sqlite3.connect(DB_PATH)
    try:
        status["documents"] = connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        status["chunks"] = connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        status["scripture_references"] = connection.execute("SELECT COUNT(*) FROM chunk_refs").fetchone()[0]
        status["documents_by_source_type"] = {
            source_type: count
            for source_type, count in connection.execute(
                "SELECT source_type, COUNT(*) FROM documents GROUP BY source_type ORDER BY source_type"
            )
        }
    finally:
        connection.close()
    return status


def registered_sources_status() -> list[dict]:
    sources = []
    for row in load_tab_registry(SOURCE_REGISTRY):
        if len(row) < 2:
            continue
        key, raw_path = row[:2]
        root = Path(raw_path)
        counts = suffix_counts(root)
        readable = sum(count for suffix, count in counts.items() if suffix in READABLE_SUFFIXES)
        sources.append({
            "name": key,
            "path": str(root),
            "exists": root.exists(),
            "files": sum(counts.values()),
            "readable_files": readable,
            "unsupported_files": sum(counts.values()) - readable,
            "files_by_extension": dict(counts.most_common()),
        })
    return sources


def newest_completed_log_status() -> tuple[str | None, dict[str, dict]]:
    completed_log = None
    for path in sorted(LOG_DIR.glob("update_*.log"), reverse=True):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "Update complete." in text:
            completed_log = path
            break

    if completed_log is None:
        return None, {}

    status: dict[str, dict] = defaultdict(lambda: {"feed_items": None, "errors": 0})
    current_source = None
    for line in completed_log.read_text(encoding="utf-8", errors="ignore").splitlines():
        source_match = re.search(r"Processing source:\s*(.+)$", line)
        if source_match:
            current_source = source_match.group(1).strip()
            status[current_source]
            continue
        if not current_source:
            continue
        total_match = re.search(r"Downloading item\s+\d+\s+of\s+(\d+)", line)
        if total_match and status[current_source]["feed_items"] is None:
            status[current_source]["feed_items"] = int(total_match.group(1))
        if "ERROR:" in line:
            status[current_source]["errors"] += 1

    return completed_log.name, dict(status)


def podcast_status() -> dict:
    latest_log, feed_status = newest_completed_log_status()
    sources = []
    total_transcripts = 0
    total_estimated_remaining = 0

    registry_rows = [row for path in PODCAST_REGISTRIES for row in load_pipe_registry(path)]
    for row in registry_rows:
        if len(row) < 4:
            continue
        name, source_type, url, destination = row[:4]
        destination_path = BASE / destination
        counts = suffix_counts(destination_path)
        transcript_count = counts.get(".txt", 0)
        archive_path = ARCHIVE_DIR / f"{name}_downloaded.txt"
        archive_entries = 0
        if archive_path.exists():
            archive_entries = sum(1 for line in archive_path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip())

        observed = feed_status.get(name, {})
        feed_items = observed.get("feed_items")
        estimated_remaining = max(feed_items - transcript_count, 0) if isinstance(feed_items, int) else None
        if estimated_remaining is not None:
            total_estimated_remaining += estimated_remaining
        total_transcripts += transcript_count

        sources.append({
            "name": name,
            "type": source_type,
            "url": url,
            "destination": str(destination_path),
            "transcripts": transcript_count,
            "pending_audio": counts.get(".mp3", 0),
            "metadata_files": counts.get(".json", 0),
            "archive_entries": archive_entries,
            "feed_items_in_latest_completed_run": feed_items,
            "estimated_remaining": estimated_remaining,
            "errors_in_latest_completed_run": observed.get("errors", 0),
        })

    return {
        "latest_completed_update_log": latest_log,
        "source_count": len(sources),
        "transcripts": total_transcripts,
        "estimated_remaining_known_feeds": total_estimated_remaining,
        "sources": sources,
    }


def lfbi_manifest_status() -> list[dict]:
    courses = []
    for path in sorted((BASE / "02_LFBI").rglob("course_manifest_processed.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as error:
            courses.append({"manifest": str(path), "error": str(error)})
            continue
        course_root = path.parent
        courses.append({
            "course": data.get("course_title") or course_root.name,
            "manifest": str(path),
            "transcripts": len(list(course_root.rglob("*.txt"))),
            "downloaded_resources": len(data.get("downloaded_resources", [])),
            "queued_resources": len(data.get("queued_resources", [])),
            "already_available_resources": len(data.get("already_available_resources", [])),
        })
    return courses


def duplicate_lfbi_names() -> list[dict]:
    roots = [BASE / "02_LFBI", Path.home() / "Documents/Spiritual/LFBI"]
    by_key: dict[tuple[str, int], list[str]] = defaultdict(list)
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.name.startswith("."):
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            normalized = re.sub(r"[^a-z0-9]+", " ", path.stem.lower()).strip()
            if normalized:
                by_key[(normalized, size)].append(str(path))
    return [
        {"normalized_name": key[0], "size": key[1], "paths": paths}
        for key, paths in sorted(by_key.items())
        if len(paths) > 1
    ]


def markdown_report(report: dict) -> str:
    db = report["database"]
    podcasts = report["podcasts"]
    lines = [
        "# Bible Study Aid Library Status",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Search index",
        "",
        f"- Documents: {db['documents']:,}",
        f"- Searchable chunks: {db['chunks']:,}",
        f"- Scripture references: {db['scripture_references']:,}",
    ]
    for source_type, count in db["documents_by_source_type"].items():
        lines.append(f"- {source_type}: {count:,}")

    lines.extend(["", "## Registered local sources", ""])
    for source in report["registered_sources"]:
        state = "available" if source["exists"] else "MISSING"
        lines.append(
            f"- {source['name']}: {source['readable_files']:,} readable files, "
            f"{source['unsupported_files']:,} other files ({state})"
        )

    lines.extend([
        "",
        "## Podcasts",
        "",
        f"- Configured sources: {podcasts['source_count']}",
        f"- Local transcripts: {podcasts['transcripts']:,}",
        f"- Estimated remaining across feeds with known totals: {podcasts['estimated_remaining_known_feeds']:,}",
        f"- Latest completed update log: {podcasts['latest_completed_update_log'] or 'none'}",
        "",
    ])
    for source in podcasts["sources"]:
        total = source["feed_items_in_latest_completed_run"]
        remaining = source["estimated_remaining"]
        total_text = str(total) if total is not None else "unknown"
        remaining_text = str(remaining) if remaining is not None else "unknown"
        lines.append(
            f"- {source['name']}: {source['transcripts']} transcripts / {total_text} feed items; "
            f"estimated remaining {remaining_text}; latest errors {source['errors_in_latest_completed_run']}"
        )

    lines.extend(["", "## LFBI processed courses", ""])
    if not report["lfbi_courses"]:
        lines.append("- No processed LFBI course manifests found.")
    for course in report["lfbi_courses"]:
        if "error" in course:
            lines.append(f"- Could not read {course['manifest']}: {course['error']}")
            continue
        lines.append(
            f"- {course['course']}: {course['transcripts']} transcripts; "
            f"{course['downloaded_resources']} downloaded resources; "
            f"{course['queued_resources']} queued; "
            f"{course['already_available_resources']} already available"
        )

    lines.extend([
        "",
        "## Data-quality checks",
        "",
        f"- Possible exact LFBI duplicates by normalized filename and size: {len(report['possible_lfbi_duplicates'])}",
        "",
        "Podcast feed totals and remaining counts are estimates from the latest completed updater log.",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "database": database_status(),
        "registered_sources": registered_sources_status(),
        "podcasts": podcast_status(),
        "lfbi_courses": lfbi_manifest_status(),
        "possible_lfbi_duplicates": duplicate_lfbi_names(),
    }

    json_path = INDEX_DIR / "library_status.json"
    markdown_path = INDEX_DIR / "Library_Status.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown_path.write_text(markdown_report(report), encoding="utf-8")
    print(f"Wrote: {json_path}")
    print(f"Wrote: {markdown_path}")


if __name__ == "__main__":
    main()
