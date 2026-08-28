#!/usr/bin/env python3
"""Convert caption sidecars or transcribe a batch of audio files.

The process deliberately stays alive for the whole batch so the speech model is
loaded only once. Audio is deleted only after a non-empty transcript is safely
written. Cooling pauses apply to speech recognition, not caption conversion.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import html
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np


AUDIO_EXTENSIONS = {".mp3", ".m4a", ".webm", ".opus", ".wav", ".mp4"}
SIDE_CAR_EXTENSIONS = {".vtt", ".srt", ".tsv", ".json"}
LANGUAGE_TAG = re.compile(r"^[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]+)*$")
ENGLISH_LANGUAGE_NAMES = {"en", "eng", "english"}
UNKNOWN_LANGUAGE_NAMES = {"", "und", "unknown", "none", "null"}


def load_audio_excerpt(audio_path: Path, seconds: int = 30) -> np.ndarray:
    ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    if not Path(ffmpeg).is_file():
        raise RuntimeError("ffmpeg is required for language detection")
    completed = subprocess.run(
        [
            ffmpeg,
            "-nostdin",
            "-threads",
            "0",
            "-i",
            str(audio_path),
            "-t",
            str(seconds),
            "-f",
            "s16le",
            "-ac",
            "1",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-",
        ],
        capture_output=True,
        check=True,
    )
    return np.frombuffer(completed.stdout, np.int16).astype(np.float32) / 32768.0


def clean_caption_line(raw_line: str) -> str:
    line = re.sub(r"<\d{2}:\d{2}:\d{2}\.\d{3}>", "", raw_line)
    line = re.sub(r"<[^>]+>", "", line)
    return html.unescape(line).replace("\u00a0", " ").strip()


def merge_caption_cues(cues: list[str]) -> str:
    """Merge rolling YouTube cues without repeating their overlapping words."""
    words: list[str] = []
    for cue in cues:
        cue_words = cue.split()
        if not cue_words:
            continue
        overlap = 0
        for size in range(min(len(words), len(cue_words)), 0, -1):
            if [word.casefold() for word in words[-size:]] == [
                word.casefold() for word in cue_words[:size]
            ]:
                overlap = size
                break
        words.extend(cue_words[overlap:])
    return " ".join(words).strip()


def normalize_caption_text(text: str) -> str:
    cues: list[str] = []
    current_lines: list[str] = []
    in_cue = False

    def finish_cue() -> None:
        nonlocal current_lines
        if current_lines:
            cue = merge_caption_cues(current_lines)
            if cue:
                cues.append(cue)
        current_lines = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if "-->" in line:
            finish_cue()
            in_cue = True
            continue
        if not line:
            finish_cue()
            in_cue = False
            continue
        if not in_cue or line.upper() == "WEBVTT" or re.match(r"^\d+$", line):
            continue
        cleaned = clean_caption_line(line)
        if cleaned:
            current_lines.append(cleaned)
    finish_cue()
    return merge_caption_cues(cues)


def is_related_sidecar(audio_path: Path, candidate: Path) -> bool:
    base = audio_path.with_suffix("")
    if (
        candidate.parent != base.parent
        or candidate.suffix.lower() not in SIDE_CAR_EXTENSIONS
    ):
        return False
    remainder = candidate.name[len(base.name) :]
    if remainder == candidate.suffix:
        return True
    if not remainder.startswith("."):
        return False
    middle = remainder[1 : -len(candidate.suffix)].rstrip(".")
    return middle == "info" or bool(middle and LANGUAGE_TAG.fullmatch(middle))


def normalize_language(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().casefold().replace("_", "-")
    if normalized in UNKNOWN_LANGUAGE_NAMES:
        return None
    if normalized in ENGLISH_LANGUAGE_NAMES or normalized.startswith("en-"):
        return "en"
    return normalized


def metadata_language(audio_path: Path) -> str | None:
    info_path = audio_path.with_suffix(".info.json")
    if not info_path.is_file():
        return None
    try:
        info = json.loads(info_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return normalize_language(info.get("language"))


def language_skip_marker(audio_path: Path) -> Path:
    return audio_path.with_suffix(".skipped-language.json")


def write_language_skip_marker(
    audio_path: Path, language: str, confidence: float | None, source: str
) -> Path:
    marker_path = language_skip_marker(audio_path)
    marker = {
        "audio_title": audio_path.stem,
        "detected_language": language,
        "confidence": confidence,
        "source": source,
        "reason": "Only English-language material is processed.",
        "skipped_at": datetime.now(timezone.utc).isoformat(),
    }
    marker_path.write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")
    return marker_path


def caption_candidates(audio_path: Path) -> list[Path]:
    base = audio_path.with_suffix("")
    matches = sorted(base.parent.glob(f"{base.name}*.vtt"))
    return [
        path
        for path in matches
        if path.is_file() and is_related_sidecar(audio_path, path)
    ]


def transcript_from_caption(audio_path: Path) -> Path | None:
    for caption_path in caption_candidates(audio_path):
        text = normalize_caption_text(
            caption_path.read_text(encoding="utf-8", errors="ignore")
        )
        if not text:
            continue
        output_path = audio_path.with_suffix(".txt")
        output_path.write_text(text + "\n", encoding="utf-8")
        print(f"Caption transcript created: {output_path.name}", flush=True)
        return output_path
    return None


def cleanup_completed_audio(audio_path: Path) -> None:
    base = audio_path.with_suffix("")
    for path in base.parent.glob(f"{base.name}*"):
        if path == audio_path or is_related_sidecar(audio_path, path):
            path.unlink(missing_ok=True)


class OpenAIBackend:
    def __init__(self, model_name: str) -> None:
        import whisper

        print(f"Loading OpenAI Whisper model once: {model_name}", flush=True)
        self.whisper = whisper
        self.model = whisper.load_model(model_name, device="cpu")

    def detect_language(self, audio_path: Path) -> tuple[str, float]:
        if not self.model.is_multilingual:
            raise RuntimeError("language detection requires a multilingual Whisper model")
        audio = load_audio_excerpt(audio_path)
        audio = self.whisper.pad_or_trim(audio)
        mel = self.whisper.log_mel_spectrogram(
            audio, n_mels=self.model.dims.n_mels
        ).to(self.model.device)
        _, probabilities = self.model.detect_language(mel)
        language = max(probabilities, key=probabilities.get)
        return language, float(probabilities[language])

    def transcribe(self, audio_path: Path) -> str:
        result = self.model.transcribe(
            str(audio_path), language="en", fp16=False, verbose=False
        )
        return str(result.get("text", "")).strip()


class MLXBackend:
    def __init__(self, model_name: str) -> None:
        import mlx.core as mx
        import mlx_whisper
        from mlx_whisper.audio import (
            N_FRAMES,
            N_SAMPLES,
            log_mel_spectrogram,
            pad_or_trim,
        )
        from mlx_whisper.transcribe import ModelHolder

        print(f"Loading MLX Whisper model once: {model_name}", flush=True)
        self.mx = mx
        self.mlx_whisper = mlx_whisper
        self.model_name = model_name
        self.n_frames = N_FRAMES
        self.n_samples = N_SAMPLES
        self.log_mel_spectrogram = log_mel_spectrogram
        self.pad_or_trim = pad_or_trim
        self.model = ModelHolder.get_model(model_name, dtype=mx.float16)

    def detect_language(self, audio_path: Path) -> tuple[str, float]:
        if not self.model.is_multilingual:
            raise RuntimeError("language detection requires a multilingual Whisper model")
        audio = load_audio_excerpt(audio_path)
        mel = self.log_mel_spectrogram(
            audio, n_mels=self.model.dims.n_mels, padding=self.n_samples
        )
        mel_segment = self.pad_or_trim(mel, self.n_frames, axis=-2).astype(
            self.mx.float16
        )
        _, probabilities = self.model.detect_language(mel_segment)
        language = max(probabilities, key=probabilities.get)
        return language, float(probabilities[language])

    def transcribe(self, audio_path: Path) -> str:
        result = self.mlx_whisper.transcribe(
            str(audio_path),
            path_or_hf_repo=self.model_name,
            language="en",
            verbose=False,
        )
        return str(result.get("text", "")).strip()


def collect_audio(paths: list[str]) -> list[Path]:
    found: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path).expanduser()
        if path.is_dir():
            found.extend(
                child
                for child in sorted(path.iterdir())
                if child.is_file() and child.suffix.lower() in AUDIO_EXTENSIONS
            )
        elif path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
            found.append(path)
    return list(dict.fromkeys(found))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", help="Audio files or folders")
    parser.add_argument("--backend", choices=("openai", "mlx"), default="openai")
    parser.add_argument("--model", default=None)
    parser.add_argument("--pause-seconds", type=float, default=5.0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--time-budget-minutes", type=float, default=0.0)
    parser.add_argument("--language-confidence", type=float, default=0.75)
    parser.add_argument("--keep-audio", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.language_confidence <= 1:
        parser.error("--language-confidence must be between 0 and 1")
    return args


def main() -> int:
    args = parse_args()
    audio_files = collect_audio(args.paths)
    if not audio_files:
        print("No audio files need transcription.")
        return 0

    started = time.monotonic()
    completed = 0
    failed = 0
    skipped = 0
    non_english = 0
    backend = None

    for audio_path in audio_files:
        transcript_path = audio_path.with_suffix(".txt")
        if transcript_path.exists() and transcript_path.stat().st_size > 0:
            print(f"Transcript already exists: {audio_path.name}", flush=True)
            if not args.keep_audio:
                cleanup_completed_audio(audio_path)
            skipped += 1
            continue

        if language_skip_marker(audio_path).is_file():
            print(f"Previously marked non-English: {audio_path.name}", flush=True)
            non_english += 1
            continue

        if args.limit > 0 and completed >= args.limit:
            print(f"Transcription limit reached ({args.limit}).", flush=True)
            break
        if args.time_budget_minutes > 0 and completed > 0:
            elapsed_minutes = (time.monotonic() - started) / 60
            if elapsed_minutes >= args.time_budget_minutes:
                print(
                    f"Transcription time budget reached ({args.time_budget_minutes:g} minutes).",
                    flush=True,
                )
                break

        known_language = metadata_language(audio_path)
        language_source = "download metadata"
        language_confidence: float | None = None

        if known_language is None:
            language_source = "Whisper language detection"
            if backend is None:
                if args.backend == "mlx":
                    model_name = args.model or "mlx-community/whisper-base-mlx"
                    backend = MLXBackend(model_name)
                else:
                    model_name = args.model or "base"
                    backend = OpenAIBackend(model_name)
            try:
                known_language, language_confidence = backend.detect_language(audio_path)
                print(
                    f"Detected language for {audio_path.name}: {known_language} "
                    f"({language_confidence:.1%})",
                    flush=True,
                )
            except Exception as exc:
                failed += 1
                print(
                    f"Language detection failed for {audio_path.name}: {exc}",
                    file=sys.stderr,
                )
                continue

        confident_non_english = known_language != "en" and (
            language_source == "download metadata"
            or (
                language_confidence is not None
                and language_confidence >= args.language_confidence
            )
        )
        if confident_non_english:
            marker_path = write_language_skip_marker(
                audio_path, known_language, language_confidence, language_source
            )
            non_english += 1
            print(
                f"Skipped non-English audio ({known_language}): {audio_path.name}; "
                f"recorded in {marker_path.name}",
                flush=True,
            )
            continue

        caption_transcript = transcript_from_caption(audio_path)
        if caption_transcript is not None:
            completed += 1
            if not args.keep_audio:
                cleanup_completed_audio(audio_path)
            continue

        if backend is None:
            if args.backend == "mlx":
                model_name = args.model or "mlx-community/whisper-base-mlx"
                backend = MLXBackend(model_name)
            else:
                model_name = args.model or "base"
                backend = OpenAIBackend(model_name)

        print(f"Transcribing with {args.backend}: {audio_path.name}", flush=True)
        try:
            text = backend.transcribe(audio_path)
            if not text:
                raise RuntimeError("speech recognition returned an empty transcript")
            transcript_path.write_text(text + "\n", encoding="utf-8")
            completed += 1
            print(f"Transcript created: {transcript_path.name}", flush=True)
            if not args.keep_audio:
                cleanup_completed_audio(audio_path)
            if args.pause_seconds > 0:
                print(
                    f"Cooling for {args.pause_seconds:g} seconds after transcription...",
                    flush=True,
                )
                time.sleep(args.pause_seconds)
        except Exception as exc:
            failed += 1
            print(f"Transcription failed for {audio_path.name}: {exc}", file=sys.stderr)

    print(
        f"Batch complete: {completed} completed, {failed} failed, "
        f"{len(audio_files) - completed - failed - skipped - non_english} deferred, "
        f"{skipped} already complete, {non_english} non-English skipped.",
        flush=True,
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
