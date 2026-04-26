

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, unquote

try:
    import requests
except ImportError:  # handled at runtime
    requests = None


# ------------------------------------------------------------
# LFBI Manifest Processor
# ------------------------------------------------------------
#
# Input:
#   02_LFBI/<Course>/course_manifest_raw.json
#
# Output:
#   02_LFBI/<Course>/Week_##/... folders
#   transcripts from YouTube captions first, Whisper fallback
#   downloaded Moodle resources when a cookies.txt file is supplied
#   download_queue.html when automatic Moodle download is not possible
#
# Office 365 / Moodle note:
#   This script does NOT try to log into Moodle. That is intentionally avoided
#   because Office 365 SSO is fragile to automate. Instead, it can use a
#   browser-exported cookies.txt file if you provide one. If not, it creates a
#   clickable download queue so you can use your already-logged-in browser.
# ------------------------------------------------------------

BASE = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid"
LFBI_ROOT = BASE / "02_LFBI"
WORK_ROOT = BASE / "98_Automation" / "lfbi_work"

SKIP_KINDS = {"skip"}
RESOURCE_SUBDIRS = {
    "handout": "handouts",
    "slides": "slides",
    "appendix": "appendices",
    "pdf": "additional_materials",
    "resource": "additional_materials",
    "other": "additional_materials",
}


def slugify(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"[^A-Za-z0-9._ -]+", "", value)
    value = value.strip().replace(" ", "_")
    value = re.sub(r"_+", "_", value)
    return value or "resource"


def normalize_course_title(title: str) -> str:
    title = html.unescape(title or "LFBI Course").strip()
    title = re.sub(r"^Course:\s*", "", title, flags=re.IGNORECASE)
    return title.strip() or "LFBI Course"


def week_number_from_title(value: str) -> Optional[int]:
    match = re.search(r"\bWeek\s+(\d+)\b", value or "", re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))

def canonical_week_title(manifest: dict, week_number: int) -> str:
    weeks = manifest.get("weeks", [])
    for week in weeks:
        if week_number_from_title(week) == week_number:
            cleaned = re.sub(r"\s+", " ", week).strip()
            cleaned = re.sub(r"\bweek\s+\d+\b", "", cleaned, flags=re.IGNORECASE).strip(" -–:_")
            if cleaned and not re.search(r"\b(handout|slides?|ppt|quiz|assignment|exam|watch lecture first)\b", cleaned, re.IGNORECASE):
                return cleaned
    return ""


def infer_week_number_from_resource(resource: dict, fallback: Optional[int] = None) -> Optional[int]:
    text = f"{resource.get('title', '')} {resource.get('url', '')}"
    found = week_number_from_title(text)
    if found is not None:
        return found
    return fallback


def clean_filename_from_response(response, fallback_title: str, url: str) -> str:
    content_disposition = response.headers.get("content-disposition", "") if response is not None else ""
    filename_match = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';]+)', content_disposition, re.IGNORECASE)
    if filename_match:
        return slugify(unquote(filename_match.group(1)))

    url_name = Path(unquote(urlparse(url).path)).name
    if url_name and "." in url_name:
        return slugify(url_name)

    title = fallback_title or "resource"
    filename = slugify(title)
    if not Path(filename).suffix:
        filename += ".pdf"
    return filename


def run_command(command: list[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    print("[CMD]", " ".join(command))
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
    )


def ensure_week_dirs(course_root: Path, week_number: int, week_title: Optional[str] = None) -> dict[str, Path]:
    if week_title:
        week_slug = f"Week_{week_number:02d}_{slugify(week_title)}"
    else:
        week_slug = f"Week_{week_number:02d}"

    week_root = course_root / week_slug
    dirs = {
        "week_root": week_root,
        "handouts": week_root / "handouts",
        "slides": week_root / "slides",
        "appendices": week_root / "appendices",
        "additional_materials": week_root / "additional_materials",
        "transcripts": week_root / "transcripts",
        "metadata": week_root / "metadata",
        "work": WORK_ROOT / course_root.name / week_slug,
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_netscape_cookies(cookies_path: Optional[Path]):
    if not cookies_path:
        return None
    if requests is None:
        raise RuntimeError("The 'requests' package is required for cookie-based downloads. Install it with: python3 -m pip install requests")
    if not cookies_path.exists():
        raise FileNotFoundError(f"cookies.txt not found: {cookies_path}")

    jar = requests.cookies.RequestsCookieJar()
    for line in cookies_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        domain, _flag, path, secure, expires, name, value = parts[:7]
        jar.set(name, value, domain=domain, path=path, secure=(secure.upper() == "TRUE"))
    return jar


def download_resource(resource: dict, destination_dir: Path, cookies_jar=None) -> Optional[Path]:
    if requests is None:
        print("[WARN] requests is not installed; cannot download Moodle resources automatically.")
        return None

    url = resource.get("url")
    title = resource.get("title", "resource")
    if not url:
        return None

    try:
        response = requests.get(url, cookies=cookies_jar, allow_redirects=True, timeout=60)
    except Exception as exc:
        print(f"[WARN] Download failed for {title}: {exc}")
        return None

    content_type = response.headers.get("content-type", "").lower()
    if response.status_code >= 400:
        print(f"[WARN] Download HTTP {response.status_code} for {title}: {url}")
        return None

    if "text/html" in content_type and "moodle" in response.text[:2000].lower() and "login" in response.text[:5000].lower():
        print(f"[WARN] Moodle login page received instead of file for {title}. Cookies are missing or expired.")
        return None

    filename = clean_filename_from_response(response, title, response.url or url)
    destination = destination_dir / filename
    destination.write_bytes(response.content)
    print(f"[OK] Downloaded {resource.get('kind', 'resource')}: {destination}")
    return destination


def normalize_caption_text(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.upper() == "WEBVTT":
            continue
        if re.match(r"^\d+$", line):
            continue
        if "-->" in line:
            continue
        if line.startswith("NOTE "):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        line = line.replace("&nbsp;", " ")
        if lines and lines[-1] == line:
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def find_first_matching_file(folder: Path, patterns: tuple[str, ...]) -> Optional[Path]:
    for path in sorted(folder.iterdir()):
        if path.is_file() and any(path.name.endswith(pattern) for pattern in patterns):
            return path
    return None


def try_youtube_captions(video_url: str, transcript_dir: Path, work_dir: Path, title: str) -> Optional[Path]:
    output_template = work_dir / slugify(title)
    command = [
        "yt-dlp",
        "--skip-download",
        "--write-auto-subs",
        "--write-subs",
        "--sub-langs",
        "en.*",
        "--convert-subs",
        "vtt",
        "-o",
        str(output_template) + ".%(ext)s",
        video_url,
    ]
    result = run_command(command)
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr.strip())
        return None

    caption_file = find_first_matching_file(work_dir, (".en.vtt", ".vtt", ".en-US.vtt", ".en-orig.vtt"))
    if not caption_file:
        return None

    transcript_text = normalize_caption_text(caption_file.read_text(encoding="utf-8", errors="ignore"))
    if not transcript_text:
        return None

    transcript_path = transcript_dir / f"{slugify(title)}.txt"
    transcript_path.write_text(transcript_text + "\n", encoding="utf-8")
    print(f"[OK] Saved transcript from captions: {transcript_path}")
    return transcript_path


def try_whisper_fallback(video_url: str, transcript_dir: Path, work_dir: Path, title: str) -> Optional[Path]:
    audio_template = work_dir / f"{slugify(title)}_audio"
    download_command = ["yt-dlp", "-f", "bestaudio/best", "-o", str(audio_template) + ".%(ext)s", video_url]
    download_result = run_command(download_command)
    if download_result.returncode != 0:
        if download_result.stderr:
            print(download_result.stderr.strip())
        return None

    audio_file = find_first_matching_file(work_dir, (".m4a", ".mp3", ".webm", ".mp4", ".opus"))
    if not audio_file:
        return None

    command = [
        "whisper",
        str(audio_file),
        "--model",
        "base",
        "--language",
        "en",
        "--output_format",
        "txt",
        "--output_dir",
        str(transcript_dir),
    ]
    result = run_command(command)
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr.strip())
        return None

    txt_output = transcript_dir / f"{audio_file.stem}.txt"
    if txt_output.exists():
        final_path = transcript_dir / f"{slugify(title)}.txt"
        if final_path.exists():
            final_path.unlink()
        txt_output.rename(final_path)
        print(f"[OK] Saved transcript from Whisper fallback: {final_path}")
        return final_path
    return None

def process_videos(manifest: dict, course_root: Path) -> list[dict]:
    videos = manifest.get("youtube_links", [])
    processed = []

    for index, video_url in enumerate(videos, start=1):
        week_number = index
        canonical_title = canonical_week_title(manifest, week_number)
        dirs = ensure_week_dirs(course_root, week_number, canonical_title)

        title = f"{normalize_course_title(manifest.get('course_title'))} - Week {week_number:02d}"

        transcript_path = try_youtube_captions(video_url, dirs["transcripts"], dirs["work"], title)
        strategy = "captions"
        if transcript_path is None:
            print(f"[INFO] Falling back to Whisper for Week {week_number:02d}...")
            transcript_path = try_whisper_fallback(video_url, dirs["transcripts"], dirs["work"], title)
            strategy = "whisper" if transcript_path else "failed"

        processed.append({
            "week_number": week_number,
            "week_title": canonical_title or f"Week {week_number}",
            "url": video_url,
            "transcript_path": str(transcript_path.relative_to(BASE)) if transcript_path else None,
            "strategy": strategy,
        })
        time.sleep(1)

    return processed


def process_resources(manifest: dict, course_root: Path, cookies_jar=None) -> tuple[list[dict], list[dict]]:
    resources = [r for r in manifest.get("resources", []) if r.get("kind") not in SKIP_KINDS]
    weeks = manifest.get("weeks", [])
    downloaded = []
    queued = []

    for index, resource in enumerate(resources, start=1):
        week_number = infer_week_number_from_resource(resource)
        if week_number is None:
            # Most Moodle pages list resources in order. Use a rough placement when no week is visible.
            week_number = min(max(1, index), max(1, len(weeks)))
        week_title = canonical_week_title(manifest, week_number)
        dirs = ensure_week_dirs(course_root, week_number, week_title)
        kind = resource.get("kind", "resource")
        subdir = RESOURCE_SUBDIRS.get(kind, "additional_materials")

        downloaded_path = download_resource(resource, dirs[subdir], cookies_jar=cookies_jar) if cookies_jar else None
        if downloaded_path:
            downloaded.append({
                **resource,
                "week_number": week_number,
                "stored_path": str(downloaded_path.relative_to(BASE)),
            })
        else:
            queued.append({**resource, "week_number": week_number, "week_title": week_title})

    return downloaded, queued


def write_download_queue(course_root: Path, queued: list[dict]) -> Optional[Path]:
    if not queued:
        return None

    rows = []
    for item in queued:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('week_number', '')))}</td>"
            f"<td>{html.escape(item.get('kind', 'resource'))}</td>"
            f"<td>{html.escape(item.get('title', 'Untitled'))}</td>"
            f"<td><a href=\"{html.escape(item.get('url', ''), quote=True)}\">Open/download</a></td>"
            "</tr>"
        )

    page = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>LFBI Download Queue</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 32px; line-height: 1.4; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
    th {{ background: #f4f4f4; text-align: left; }}
  </style>
</head>
<body>
  <h1>LFBI Download Queue</h1>
  <p>These resources could not be downloaded automatically. Open this file in Safari while logged into Moodle, click each link, and save the files into the matching week folder.</p>
  <table>
    <thead><tr><th>Week</th><th>Kind</th><th>Title</th><th>Link</th></tr></thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</body>
</html>
"""
    queue_path = course_root / "download_queue.html"
    queue_path.write_text(page, encoding="utf-8")
    print(f"[OK] Wrote download queue: {queue_path}")
    return queue_path


def write_processing_summary(course_root: Path, manifest: dict, downloaded: list[dict], queued: list[dict], videos: list[dict]) -> Path:
    summary = {
        "source_type": "lfbi",
        "course_title": normalize_course_title(manifest.get("course_title", "LFBI Course")),
        "course_slug": course_root.name,
        "downloaded_resources": downloaded,
        "queued_resources": queued,
        "processed_videos": videos,
    }
    summary_path = course_root / "course_manifest_processed.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[OK] Wrote processed manifest: {summary_path}")
    return summary_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Process an LFBI course manifest into organized local course material.")
    parser.add_argument("manifest", nargs="?", default=None, help="Path to course_manifest_raw.json")
    parser.add_argument("--cookies", default=None, help="Optional Netscape-format cookies.txt file for Moodle downloads")
    parser.add_argument("--skip-videos", action="store_true", help="Do not generate YouTube transcripts")
    parser.add_argument("--skip-resources", action="store_true", help="Do not process Moodle resource links")
    args = parser.parse_args()

    manifest_path = Path(args.manifest) if args.manifest else LFBI_ROOT / "Course_Acts_Spring_2019" / "course_manifest_raw.json"
    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}")
        return 1

    manifest = load_manifest(manifest_path)
    course_title = normalize_course_title(manifest.get("course_title", "LFBI Course"))
    course_slug = slugify(course_title)
    course_root = LFBI_ROOT / course_slug
    course_root.mkdir(parents=True, exist_ok=True)

    print(f"=== Processing LFBI course: {course_title} ===")
    print(f"Course root: {course_root}")

    cookies_jar = None
    if args.cookies:
        cookies_jar = load_netscape_cookies(Path(args.cookies))
        print("[OK] Loaded cookies.txt for Moodle downloads.")
    else:
        print("[INFO] No cookies.txt supplied. Moodle resources will be placed in download_queue.html if automatic download is not possible.")

    downloaded = []
    queued = []
    if not args.skip_resources:
        downloaded, queued = process_resources(manifest, course_root, cookies_jar=cookies_jar)
        write_download_queue(course_root, queued)

    processed_videos = []
    if not args.skip_videos:
        processed_videos = process_videos(manifest, course_root)

    write_processing_summary(course_root, manifest, downloaded, queued, processed_videos)

    print("\n=== LFBI PROCESSING COMPLETE ===")
    print(f"Downloaded resources: {len(downloaded)}")
    print(f"Queued resources: {len(queued)}")
    print(f"Processed videos: {len(processed_videos)}")
    print("[NEXT] Re-run the main update/index pipeline after downloads/transcripts are complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())