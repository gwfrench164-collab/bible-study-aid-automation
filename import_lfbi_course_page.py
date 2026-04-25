

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import List, Dict

# ------------------------------------------------------------
# LFBI Course Page Importer (WebArchive Version)
# ------------------------------------------------------------
#
# Usage:
#   python import_lfbi_course_page.py /path/to/course.webarchive
#
# What this does:
#   - Extracts HTML from Safari .webarchive
#   - Finds:
#       - Week/module headings
#       - Resource links (PDFs, etc.)
#       - YouTube links
#   - Writes a structured manifest
#   - DOES NOT download files yet (next step)
# ------------------------------------------------------------

BASE = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid"
LFBI_ROOT = BASE / "02_LFBI"


def extract_html_from_webarchive(path: Path) -> str:
    import plistlib

    with path.open("rb") as f:
        plist = plistlib.load(f)

    main = plist.get("WebMainResource")
    if not main:
        raise RuntimeError("Invalid webarchive: no WebMainResource")

    data = main.get("WebResourceData")
    if not data:
        raise RuntimeError("Invalid webarchive: no WebResourceData")

    return data.decode("utf-8", errors="ignore")


def extract_course_title(html: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
    if match:
        title = match.group(1)
        title = re.sub(r"\s*\|.*", "", title)
        return title.strip()
    return "LFBI_Course"


def slugify(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9 ]+", "", value)
    value = value.strip().replace(" ", "_")
    return re.sub(r"_+", "_", value)


def extract_youtube_links(html: str) -> List[str]:
    return list(set(re.findall(r"https://www\.youtube\.com[^\"'\s]+", html)))


def extract_pdf_links(html: str) -> List[str]:
    return list(set(re.findall(r"https://[^\"'\s]+\.pdf", html)))


def extract_weeks(html: str) -> List[str]:
    # Moodle typically uses "Week X" or similar
    weeks = re.findall(r">\s*(Week[^<]+)<", html, re.IGNORECASE)
    return list(dict.fromkeys(w.strip() for w in weeks))


def build_manifest(course_title: str, weeks: List[str], pdfs: List[str], videos: List[str]) -> Dict:
    return {
        "source_type": "lfbi",
        "course_title": course_title,
        "course_slug": slugify(course_title),
        "weeks": weeks,
        "pdf_links": pdfs,
        "youtube_links": videos,
    }


def write_manifest(manifest: Dict) -> Path:
    course_root = LFBI_ROOT / manifest["course_slug"]
    course_root.mkdir(parents=True, exist_ok=True)

    manifest_path = course_root / "course_manifest_raw.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return manifest_path


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: import_lfbi_course_page.py <path_to_webarchive>")
        return 1

    webarchive_path = Path(sys.argv[1])
    if not webarchive_path.exists():
        print(f"File not found: {webarchive_path}")
        return 1

    print("[INFO] Extracting HTML...")
    html = extract_html_from_webarchive(webarchive_path)

    print("[INFO] Parsing course info...")
    course_title = extract_course_title(html)
    weeks = extract_weeks(html)
    pdf_links = extract_pdf_links(html)
    youtube_links = extract_youtube_links(html)

    manifest = build_manifest(course_title, weeks, pdf_links, youtube_links)

    manifest_path = write_manifest(manifest)

    print("\n=== LFBI COURSE PARSE COMPLETE ===")
    print(f"Course: {course_title}")
    print(f"Weeks found: {len(weeks)}")
    print(f"PDF links found: {len(pdf_links)}")
    print(f"YouTube links found: {len(youtube_links)}")
    print(f"Manifest written to: {manifest_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())