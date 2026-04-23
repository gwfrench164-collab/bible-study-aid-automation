

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ------------------------------------------------------------
# LFBI pilot importer configuration
# ------------------------------------------------------------
#
# Edit the SOURCE_* paths below to point at the files you want to import.
# This pilot script is intentionally scoped to one course/week first:
#   Acts - Spring 2019 / Week 2 / Acts 1
#
# Workflow:
#   1. Copy the handout, slides, and appendix into 02_LFBI
#   2. Save metadata for the course/week/video
#   3. Try YouTube captions first
#   4. Fall back to Whisper transcription if captions are unavailable
#
# Requirements for transcript generation:
#   - yt-dlp must be installed and on PATH
#   - optional fallback: whisper or whisper.cpp command on PATH
# ------------------------------------------------------------

BASE = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid"
LFBI_ROOT = BASE / "02_LFBI"
WORK_ROOT = BASE / "98_Automation" / "lfbi_work"

COURSE_SLUG = "Acts_Spring_2019"
COURSE_TITLE = "Acts - Spring 2019"
WEEK_SLUG = "Week_02_Acts_1"
WEEK_TITLE = "Week 2 - Acts 1"
VIDEO_URL = "https://www.youtube.com/live/okk4Dex89lM?si=XrhskT-qWQZ0V3W5"
VIDEO_TITLE = "Acts - Week 2 - Acts 1"

# Update these paths to match the real local files you downloaded.
SOURCE_HANDOUT = Path.home() / "Downloads" / "Handout week 2 Acts 1.pdf"
SOURCE_SLIDES = Path.home() / "Downloads" / "Acts 1.pdf"
SOURCE_APPENDIX = Path.home() / "Downloads" / "Appendex 2  Jesus was in the grave 3 days and nights.pdf"
SOURCE_COURSE_PAGE_PDF = Path.home() / "Downloads" / "Course: Acts - Spring 2019 | myLFBI(2).pdf"


@dataclass(frozen=True)
class ResourceSpec:
    kind: str
    source_path: Path
    dest_subdir: str
    title: str


RESOURCE_SPECS = [
    ResourceSpec(
        kind="handout",
        source_path=SOURCE_HANDOUT,
        dest_subdir="handouts",
        title="Handout week 2 Acts 1",
    ),
    ResourceSpec(
        kind="slides",
        source_path=SOURCE_SLIDES,
        dest_subdir="slides",
        title="Acts 1",
    ),
    ResourceSpec(
        kind="appendix",
        source_path=SOURCE_APPENDIX,
        dest_subdir="appendices",
        title="Appendix 2 - Jesus was in the grave 3 days and nights",
    ),
    ResourceSpec(
        kind="course_page_pdf",
        source_path=SOURCE_COURSE_PAGE_PDF,
        dest_subdir="metadata",
        title="Course page export",
    ),
]


def slugify_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "", value).strip()
    cleaned = cleaned.replace(" ", "_")
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned or "resource"


def ensure_directories() -> dict[str, Path]:
    week_root = LFBI_ROOT / COURSE_SLUG / WEEK_SLUG
    directories = {
        "course_root": LFBI_ROOT / COURSE_SLUG,
        "week_root": week_root,
        "handouts": week_root / "handouts",
        "slides": week_root / "slides",
        "appendices": week_root / "appendices",
        "transcripts": week_root / "transcripts",
        "metadata": week_root / "metadata",
        "work": WORK_ROOT / COURSE_SLUG / WEEK_SLUG,
    }
    for path in directories.values():
        path.mkdir(parents=True, exist_ok=True)
    return directories


def copy_resource(spec: ResourceSpec, directories: dict[str, Path]) -> Optional[dict]:
    if not spec.source_path.exists():
        print(f"[WARN] Missing source file for {spec.kind}: {spec.source_path}")
        return None

    destination_dir = directories[spec.dest_subdir]
    destination_name = spec.source_path.name
    destination = destination_dir / destination_name
    shutil.copy2(spec.source_path, destination)
    print(f"[OK] Copied {spec.kind}: {destination}")

    return {
        "kind": spec.kind,
        "title": spec.title,
        "source_path": str(spec.source_path),
        "stored_path": str(destination.relative_to(BASE)),
        "filename": destination.name,
    }


def run_command(command: list[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    print("[CMD]", " ".join(command))
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
    )


def find_first_matching_file(folder: Path, patterns: tuple[str, ...]) -> Optional[Path]:
    for path in sorted(folder.iterdir()):
        if path.is_file() and any(path.name.endswith(pattern) for pattern in patterns):
            return path
    return None


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


def try_youtube_captions(video_url: str, directories: dict[str, Path]) -> Optional[Path]:
    work_dir = directories["work"]
    output_template = work_dir / "captions"

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
        print("[WARN] yt-dlp captions step failed.")
        if result.stderr:
            print(result.stderr.strip())
        return None

    caption_file = find_first_matching_file(work_dir, (".en.vtt", ".vtt", ".en-US.vtt", ".en-orig.vtt"))
    if not caption_file:
        print("[WARN] No caption file was created by yt-dlp.")
        return None

    transcript_text = normalize_caption_text(caption_file.read_text(encoding="utf-8", errors="ignore"))
    if not transcript_text:
        print("[WARN] Caption file was created but transcript text was empty.")
        return None

    transcript_path = directories["transcripts"] / f"{slugify_filename(VIDEO_TITLE)}.txt"
    transcript_path.write_text(transcript_text + "\n", encoding="utf-8")
    print(f"[OK] Saved transcript from captions: {transcript_path}")
    return transcript_path


def try_whisper_fallback(video_url: str, directories: dict[str, Path]) -> Optional[Path]:
    work_dir = directories["work"]
    audio_template = work_dir / "lecture_audio"

    download_command = [
        "yt-dlp",
        "-f",
        "bestaudio/best",
        "-o",
        str(audio_template) + ".%(ext)s",
        video_url,
    ]
    download_result = run_command(download_command)
    if download_result.returncode != 0:
        print("[WARN] yt-dlp audio download failed.")
        if download_result.stderr:
            print(download_result.stderr.strip())
        return None

    audio_file = find_first_matching_file(
        work_dir,
        (".m4a", ".mp3", ".webm", ".mp4", ".opus"),
    )
    if not audio_file:
        print("[WARN] Audio file was not found after download.")
        return None

    transcript_dir = directories["transcripts"]

    whisper_commands = [
        [
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
        ],
        [
            "python3",
            "-m",
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
        ],
    ]

    for command in whisper_commands:
        result = run_command(command)
        if result.returncode == 0:
            txt_output = transcript_dir / f"{audio_file.stem}.txt"
            if txt_output.exists():
                final_path = transcript_dir / f"{slugify_filename(VIDEO_TITLE)}.txt"
                if txt_output != final_path:
                    if final_path.exists():
                        final_path.unlink()
                    txt_output.rename(final_path)
                print(f"[OK] Saved transcript from Whisper fallback: {final_path}")
                return final_path
        else:
            if result.stderr:
                print(result.stderr.strip())

    print("[WARN] Whisper fallback did not produce a transcript.")
    return None


def build_week_metadata(resources: list[dict], transcript_path: Optional[Path]) -> dict:
    metadata = {
        "source_type": "lfbi",
        "course_title": COURSE_TITLE,
        "course_slug": COURSE_SLUG,
        "week_title": WEEK_TITLE,
        "week_slug": WEEK_SLUG,
        "video": {
            "title": VIDEO_TITLE,
            "url": VIDEO_URL,
            "transcript_path": str(transcript_path.relative_to(BASE)) if transcript_path else None,
            "transcript_strategy": "captions_first_whisper_fallback",
        },
        "resources": resources,
        "skip_categories": [
            "quizzes",
            "exams",
            "grades",
            "administrative",
            "profile tasks",
            "submission links",
        ],
    }
    return metadata


def write_metadata_files(directories: dict[str, Path], resources: list[dict], transcript_path: Optional[Path]) -> None:
    week_metadata = build_week_metadata(resources, transcript_path)
    week_json = directories["metadata"] / "week.json"
    week_json.write_text(json.dumps(week_metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[OK] Wrote metadata: {week_json}")

    course_manifest = {
        "source_type": "lfbi",
        "course_title": COURSE_TITLE,
        "course_slug": COURSE_SLUG,
        "weeks": [
            {
                "week_title": WEEK_TITLE,
                "week_slug": WEEK_SLUG,
                "path": str((LFBI_ROOT / COURSE_SLUG / WEEK_SLUG).relative_to(BASE)),
            }
        ],
    }
    manifest_path = directories["course_root"] / "course_manifest.json"
    manifest_path.write_text(json.dumps(course_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[OK] Wrote course manifest: {manifest_path}")


def main() -> int:
    print("=== LFBI pilot import: Acts - Spring 2019 / Week 2 / Acts 1 ===")
    directories = ensure_directories()

    resources: list[dict] = []
    for spec in RESOURCE_SPECS:
        copied = copy_resource(spec, directories)
        if copied:
            resources.append(copied)

    transcript_path = try_youtube_captions(VIDEO_URL, directories)
    if transcript_path is None:
        print("[INFO] Falling back to Whisper transcription...")
        transcript_path = try_whisper_fallback(VIDEO_URL, directories)

    write_metadata_files(directories, resources, transcript_path)

    if transcript_path is None:
        print("[DONE] Import finished, but no transcript was created.")
        print("[NEXT] Check yt-dlp / Whisper availability, or generate the transcript manually.")
        return 1

    print("[DONE] Import finished successfully.")
    print(f"[NEXT] Re-run your index/update pipeline so the new LFBI material is searchable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())