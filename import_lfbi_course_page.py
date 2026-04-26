from __future__ import annotations

import html as html_lib
import json
import re
import sys
from pathlib import Path
from typing import List, Dict
from urllib.parse import unquote, urljoin, urlparse, urlunparse

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


def clean_url(raw_url: str) -> str:
    url = html_lib.unescape(raw_url or "").strip()
    url = url.split("&quot;")[0]
    url = url.split("&#34;")[0]
    url = url.rstrip('"\'<>),.;')
    url = unquote(url)
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return urlunparse(parsed)
    return url



def unique_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    output = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            output.append(item)
    return output



def extract_youtube_links(html: str) -> List[str]:
    patterns = [
        r"https?://(?:www\.)?youtube\.com/(?:watch\?v=|live/|embed/)[^\"'\s<]+",
        r"https?://youtu\.be/[^\"'\s<]+",
    ]
    links = []
    for pattern in patterns:
        links.extend(clean_url(match) for match in re.findall(pattern, html, re.IGNORECASE))
    return unique_preserve_order(links)


def classify_resource(title: str, url: str) -> str:
    text = f"{title} {url}".lower()
    if any(skip in text for skip in ["quiz", "exam", "grade", "assignment", "submit", "submission", "profile", "attendance"]):
        return "skip"
    if "handout" in text:
        return "handout"
    if any(word in text for word in ["slide", "slides", "ppt", "powerpoint"]):
        return "slides"
    if any(word in text for word in ["appendix", "appendex", "appendices"]):
        return "appendix"
    if ".pdf" in text:
        return "pdf"
    if "mod/resource" in text or "pluginfile" in text:
        return "resource"
    return "other"



def extract_links(html: str) -> List[Dict[str, str]]:
    base_match = re.search(r'<base\s+href=["\']([^"\']+)["\']', html, re.IGNORECASE)
    base_url = base_match.group(1) if base_match else ""

    anchor_pattern = re.compile(
        r'<a\b[^>]*?href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )

    links = []
    for raw_href, raw_title in anchor_pattern.findall(html):
        href = clean_url(urljoin(base_url, html_lib.unescape(raw_href)))
        title = re.sub(r"<[^>]+>", " ", raw_title)
        title = html_lib.unescape(title)
        title = re.sub(r"\s+", " ", title).strip()

        kind = classify_resource(title, href)
        if kind == "skip":
            continue

        if kind in {"handout", "slides", "appendix", "pdf", "resource"}:
            links.append({
                "kind": kind,
                "title": title or Path(urlparse(href).path).name or "Untitled resource",
                "url": href,
            })

    direct_pdf_pattern = re.compile(r"https?://[^\"'\s<]+\.pdf(?:\?[^\"'\s<]+)?", re.IGNORECASE)
    for raw_url in direct_pdf_pattern.findall(html):
        url = clean_url(raw_url)
        title = Path(urlparse(url).path).name or "PDF resource"
        links.append({"kind": classify_resource(title, url), "title": title, "url": url})

    deduped = []
    seen = set()
    for link in links:
        key = link["url"]
        if key not in seen:
            seen.add(key)
            deduped.append(link)
    return deduped


def extract_weeks(html: str) -> List[str]:
    plain = re.sub(r"<[^>]+>", "\n", html)
    plain = html_lib.unescape(plain)
    candidates = re.findall(r"\bWeek\s+\d+\b(?:\s*[-–:]\s*[^\n\r]{1,80})?", plain, re.IGNORECASE)

    cleaned = []
    for candidate in candidates:
        value = re.sub(r"\s+", " ", candidate).strip()
        lower = value.lower()
        if any(skip in lower for skip in ["handout", "slides", "ppt", "quiz", "assignment", "exam"]):
            value = re.match(r"Week\s+\d+", value, re.IGNORECASE).group(0)
        cleaned.append(value)

    return unique_preserve_order(cleaned)


def build_manifest(course_title: str, weeks: List[str], resources: List[Dict[str, str]], videos: List[str]) -> Dict:
    return {
        "source_type": "lfbi",
        "course_title": course_title,
        "course_slug": slugify(course_title),
        "weeks": weeks,
        "resources": resources,
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
    resources = extract_links(html)
    youtube_links = extract_youtube_links(html)

    manifest = build_manifest(course_title, weeks, resources, youtube_links)

    manifest_path = write_manifest(manifest)

    print("\n=== LFBI COURSE PARSE COMPLETE ===")
    print(f"Course: {course_title}")
    print(f"Weeks found: {len(weeks)}")
    resource_counts = {}
    for resource in resources:
        resource_counts[resource["kind"]] = resource_counts.get(resource["kind"], 0) + 1
    print(f"Resources found: {len(resources)} {resource_counts}")
    print(f"YouTube links found: {len(youtube_links)}")
    print(f"Manifest written to: {manifest_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())