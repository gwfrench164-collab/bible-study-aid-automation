#!/bin/bash

set -u

# A kernel lock survives crashes safely and serializes all current updater runs.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/select_python.sh"
if [ "${1:-}" = "--check-runtime" ]; then
    "$PYTHON_BIN" -c 'import sys,yt_dlp.version; print("Updater Python:",sys.executable); print("Downloader:",yt_dlp.version.__version__)'
    exit 0
fi
if [ "${BIBLE_STUDY_LOCKED:-}" != "1" ]; then
    exec "$PYTHON_BIN" "$SCRIPT_DIR/pipeline_lock.py" "$0" "$@"
fi

BASE="${BIBLE_STUDY_BASE:-$HOME/Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid}"
AUTOMATION_DIR="$BASE/98_Automation"
SOURCES_FILE="$AUTOMATION_DIR/podcast_sources.tsv"
LFF_SOURCES_FILE="$AUTOMATION_DIR/lff_church_sources.tsv"
LOG_DIR="$AUTOMATION_DIR/logs"
ARCHIVE_DIR="$AUTOMATION_DIR/archives"
LFF_BLOG_IMPORTER="$AUTOMATION_DIR/import_lff_blog.py"
COMMENTARIES_IMPORTER="$AUTOMATION_DIR/import_commentaries.py"
SCRIPTURE_INDEXER="$AUTOMATION_DIR/build_scripture_index.py"
COVERAGE_REPORTER="$AUTOMATION_DIR/report_library_status.py"
LFBI_DOWNLOAD_IMPORTER="$AUTOMATION_DIR/import_lfbi_downloads.py"
TRANSCRIBER="$AUTOMATION_DIR/transcribe_audio_batch.py"
export BIBLE_STUDY_PYTHON="$PYTHON_BIN"
YT_DLP=("$PYTHON_BIN" -m yt_dlp)

MODE="${1:-backlog}"
LIMIT="${2:-3}"
SOURCE_GROUP="${3:-all}"
PAUSE_SECONDS="${BIBLE_STUDY_COOLING_SECONDS:-${BIBLE_STUDY_PAUSE_SECONDS:-5}}"
TRANSCRIPTION_BACKEND="${BIBLE_STUDY_TRANSCRIBER:-auto}"
OPENAI_WHISPER_MODEL="${BIBLE_STUDY_WHISPER_MODEL:-base}"
MLX_WHISPER_MODEL="${BIBLE_STUDY_MLX_MODEL:-mlx-community/whisper-base-mlx}"
MLX_PYTHON="${BIBLE_STUDY_MLX_PYTHON:-$HOME/Library/Caches/BibleStudyAid/mlx-venv/bin/python}"
TRANSCRIPTION_LIMIT="${BIBLE_STUDY_TRANSCRIPTION_LIMIT:-0}"
TRANSCRIPTION_TIME_BUDGET="${BIBLE_STUDY_TRANSCRIPTION_TIME_BUDGET_MINUTES:-0}"
LANGUAGE_CONFIDENCE="${BIBLE_STUDY_LANGUAGE_CONFIDENCE:-0.75}"

mkdir -p "$LOG_DIR" "$ARCHIVE_DIR"

LOG_FILE="$LOG_DIR/update_$(date +%Y%m%d_%H%M%S)_$$.log"
FAILURES=0
run_stage() {
    local label="$1"
    shift
    echo "STAGE START: $label" | tee -a "$LOG_FILE"
    if "$@" >> "$LOG_FILE" 2>&1; then
        echo "STAGE OK: $label" | tee -a "$LOG_FILE"
        return 0
    else
        local status=$?
        echo "STAGE FAILED: $label (exit $status)" | tee -a "$LOG_FILE"
        FAILURES=$((FAILURES + 1))
        return "$status"
    fi
}


echo "Starting Bible Study Aid update..." | tee -a "$LOG_FILE"
echo "Mode: $MODE" | tee -a "$LOG_FILE"
echo "Limit per source: $LIMIT" | tee -a "$LOG_FILE"
echo "Source group: $SOURCE_GROUP" | tee -a "$LOG_FILE"
echo "Cooling pause after speech recognition: ${PAUSE_SECONDS}s" | tee -a "$LOG_FILE"
echo "Transcription backend: $TRANSCRIPTION_BACKEND" | tee -a "$LOG_FILE"
echo "Transcription limit: $TRANSCRIPTION_LIMIT" | tee -a "$LOG_FILE"
echo "Transcription time budget: ${TRANSCRIPTION_TIME_BUDGET} minutes" | tee -a "$LOG_FILE"
echo "Non-English skip confidence: $LANGUAGE_CONFIDENCE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

if [ "$MODE" != "backlog" ] && [ "$MODE" != "latest" ] && [ "$MODE" != "index" ]; then
    echo "Unknown mode '$MODE'; expected backlog, latest, or index." | tee -a "$LOG_FILE"
    exit 2
fi

for REGISTRY_FILE in "$SOURCES_FILE" "$LFF_SOURCES_FILE"; do
    if [ ! -f "$REGISTRY_FILE" ]; then
        echo "Missing source file: $REGISTRY_FILE" | tee -a "$LOG_FILE"
        exit 1
    fi
done

if [ "$SOURCE_GROUP" != "all" ] && [ "$SOURCE_GROUP" != "podcasts" ] && [ "$SOURCE_GROUP" != "churches" ]; then
    echo "Unknown source group '$SOURCE_GROUP'; expected all, podcasts, or churches." | tee -a "$LOG_FILE"
    exit 2
fi

if [ "$TRANSCRIPTION_BACKEND" != "openai" ] && [ "$TRANSCRIPTION_BACKEND" != "mlx" ] && [ "$TRANSCRIPTION_BACKEND" != "auto" ]; then
    echo "Unknown transcription backend '$TRANSCRIPTION_BACKEND'; expected openai, mlx, or auto." | tee -a "$LOG_FILE"
    exit 2
fi

emit_selected_sources() {
    if [ "$SOURCE_GROUP" = "podcasts" ]; then
        cat "$SOURCES_FILE"
    elif [ "$SOURCE_GROUP" = "churches" ]; then
        cat "$LFF_SOURCES_FILE"
    else
        cat "$SOURCES_FILE" "$LFF_SOURCES_FILE"
    fi
}

if ! run_stage "Verified database backup" "$PYTHON_BIN" "$AUTOMATION_DIR/database_backup.py"; then
    echo "Update stopped before changing the library: backup could not be verified." | tee -a "$LOG_FILE"
    exit 1
fi

if [ "$MODE" != "index" ]; then
echo "========================================" | tee -a "$LOG_FILE"
echo "Importing LFF blog posts..." | tee -a "$LOG_FILE"

if [ -f "$LFF_BLOG_IMPORTER" ]; then
    run_stage "LFF blog import" "$PYTHON_BIN" "$LFF_BLOG_IMPORTER"
else
    echo "LFF blog importer not found: $LFF_BLOG_IMPORTER" | tee -a "$LOG_FILE"
    FAILURES=$((FAILURES + 1))
fi

echo "" | tee -a "$LOG_FILE"

TRANSCRIPTION_DIRS=()

while IFS='|' read -r NAME TYPE URL DEST_REL; do
    [ -z "$NAME" ] && continue
    [[ "$NAME" == \#* ]] && continue

    DEST_DIR="$BASE/$DEST_REL"
    ARCHIVE_FILE="$ARCHIVE_DIR/${NAME}_downloaded.txt"

    mkdir -p "$DEST_DIR"
    TRANSCRIPTION_DIRS+=("$DEST_DIR")

    echo "========================================" | tee -a "$LOG_FILE"
    echo "Processing source: $NAME" | tee -a "$LOG_FILE"
    echo "Destination: $DEST_DIR" | tee -a "$LOG_FILE"
    echo "Source URL: $URL" | tee -a "$LOG_FILE"

    if [ "$TYPE" != "rss" ] && [ "$TYPE" != "youtube" ]; then
        echo "Skipping unsupported source type '$TYPE': $NAME" | tee -a "$LOG_FILE"
        echo "" | tee -a "$LOG_FILE"
        continue
    fi

    DOWNLOAD_ARGS=(
        --download-archive "$ARCHIVE_FILE"
        -x
        --audio-format mp3
        --socket-timeout 30
        --retries 2
        --fragment-retries 2
        --write-info-json
        -o "$DEST_DIR/%(title)s.%(ext)s"
    )
    if [ "$TYPE" = "youtube" ]; then
        DOWNLOAD_ARGS+=(
            --write-auto-subs
            --write-subs
            --sub-langs "en.*,en"
            --convert-subs vtt
        )
    fi

    if [ "$MODE" = "backlog" ]; then
        echo "Downloading up to $LIMIT new episodes..." | tee -a "$LOG_FILE"
        DOWNLOAD_ARGS+=(--max-downloads "$LIMIT")
        "$PYTHON_BIN" "$AUTOMATION_DIR/bounded_command.py" --timeout "${BIBLE_STUDY_SOURCE_TIMEOUT:-90}" -- "${YT_DLP[@]}" "${DOWNLOAD_ARGS[@]}" "$URL" >> "$LOG_FILE" 2>&1
    else
        echo "Downloading new episodes..." | tee -a "$LOG_FILE"
        "$PYTHON_BIN" "$AUTOMATION_DIR/bounded_command.py" --timeout "${BIBLE_STUDY_SOURCE_TIMEOUT:-90}" -- "${YT_DLP[@]}" "${DOWNLOAD_ARGS[@]}" "$URL" >> "$LOG_FILE" 2>&1
    fi
    DOWNLOAD_STATUS=$?
    if [ "$DOWNLOAD_STATUS" -ne 0 ] && { [ "$DOWNLOAD_STATUS" -ne 101 ] || [ "$MODE" != "backlog" ]; }; then
        echo "STAGE FAILED: download $NAME (exit $DOWNLOAD_STATUS)" | tee -a "$LOG_FILE"
        FAILURES=$((FAILURES + 1))
    fi
    echo "" | tee -a "$LOG_FILE"
done < <(emit_selected_sources)

echo "========================================" | tee -a "$LOG_FILE"
echo "Processing downloaded captions and audio as one resumable batch..." | tee -a "$LOG_FILE"

if [ ! -f "$TRANSCRIBER" ]; then
    echo "Batch transcriber not found: $TRANSCRIBER" | tee -a "$LOG_FILE"
    FAILURES=$((FAILURES + 1))
else
    TRANSCRIBE_ARGS=(
        "$TRANSCRIBER"
        --keep-audio
        --pause-seconds "$PAUSE_SECONDS"
        --limit "$TRANSCRIPTION_LIMIT"
        --time-budget-minutes "$TRANSCRIPTION_TIME_BUDGET"
        --language-confidence "$LANGUAGE_CONFIDENCE"
    )

    # Speech recognition has heavier dependencies than intake. Preserve the
    # installed working speech runtime when the intake venv has no Whisper.
    OPENAI_PYTHON="${BIBLE_STUDY_TRANSCRIPTION_PYTHON:-$PYTHON_BIN}"
    if [ -z "${BIBLE_STUDY_TRANSCRIPTION_PYTHON:-}" ] && ! "$OPENAI_PYTHON" -c 'import whisper, numpy' >/dev/null 2>&1; then
        for candidate in /usr/local/bin/python3 "$(command -v python3)"; do
            if [ -x "$candidate" ] && "$candidate" -c 'import whisper, numpy' >/dev/null 2>&1; then OPENAI_PYTHON="$candidate"; break; fi
        done
    fi
    TRANSCRIBE_PYTHON="$OPENAI_PYTHON"
    TRANSCRIBE_MODEL="$OPENAI_WHISPER_MODEL"
    EFFECTIVE_BACKEND="$TRANSCRIPTION_BACKEND"
    if [ "$TRANSCRIPTION_BACKEND" = "mlx" ] || [ "$TRANSCRIPTION_BACKEND" = "auto" ]; then
        if [ -x "$MLX_PYTHON" ]; then
            TRANSCRIBE_PYTHON="$MLX_PYTHON"
            TRANSCRIBE_MODEL="$MLX_WHISPER_MODEL"
            EFFECTIVE_BACKEND="mlx"
        elif [ "$TRANSCRIPTION_BACKEND" = "mlx" ]; then
            echo "MLX environment is unavailable; falling back to OpenAI Whisper." | tee -a "$LOG_FILE"
            EFFECTIVE_BACKEND="openai"
        else
            EFFECTIVE_BACKEND="openai"
        fi
    fi

    "$TRANSCRIBE_PYTHON" "${TRANSCRIBE_ARGS[@]}" \
        --backend "$EFFECTIVE_BACKEND" \
        --model "$TRANSCRIBE_MODEL" \
        "${TRANSCRIPTION_DIRS[@]}" >> "$LOG_FILE" 2>&1
    TRANSCRIBE_STATUS=$?

    if [ $TRANSCRIBE_STATUS -ne 0 ] && [ "$EFFECTIVE_BACKEND" = "mlx" ]; then
        echo "MLX transcription had a problem; retrying unfinished audio with OpenAI Whisper." | tee -a "$LOG_FILE"
        "$OPENAI_PYTHON" "${TRANSCRIBE_ARGS[@]}" \
            --backend openai \
            --model "$OPENAI_WHISPER_MODEL" \
            "${TRANSCRIPTION_DIRS[@]}" >> "$LOG_FILE" 2>&1
        TRANSCRIBE_STATUS=$?
    fi
    if [ "$TRANSCRIBE_STATUS" -ne 0 ]; then
        FAILURES=$((FAILURES + 1))
    fi
fi
else
    echo "Index-only mode: skipping blog, media download, and transcription." | tee -a "$LOG_FILE"
fi

echo "========================================" | tee -a "$LOG_FILE"
echo "Importing completed LFBI browser downloads..." | tee -a "$LOG_FILE"

if [ -f "$LFBI_DOWNLOAD_IMPORTER" ]; then
    run_stage "LFBI browser-download intake" "$PYTHON_BIN" "$LFBI_DOWNLOAD_IMPORTER"
else
    echo "LFBI download importer not found: $LFBI_DOWNLOAD_IMPORTER" | tee -a "$LOG_FILE"
    FAILURES=$((FAILURES + 1))
fi

echo "" | tee -a "$LOG_FILE"

echo "========================================" | tee -a "$LOG_FILE"
echo "Building searchable index..." | tee -a "$LOG_FILE"

if [ -f "$COMMENTARIES_IMPORTER" ]; then
    run_stage "Searchable index build" "$PYTHON_BIN" "$COMMENTARIES_IMPORTER"
else
    echo "Indexer not found: $COMMENTARIES_IMPORTER" | tee -a "$LOG_FILE"
    FAILURES=$((FAILURES + 1))
fi

echo "" | tee -a "$LOG_FILE"

echo "========================================" | tee -a "$LOG_FILE"
echo "Building scripture index..." | tee -a "$LOG_FILE"

if [ -f "$SCRIPTURE_INDEXER" ]; then
    run_stage "Scripture index" "$PYTHON_BIN" "$SCRIPTURE_INDEXER"
else
    echo "Scripture indexer not found: $SCRIPTURE_INDEXER" | tee -a "$LOG_FILE"
    FAILURES=$((FAILURES + 1))
fi

echo "" | tee -a "$LOG_FILE"

if [ -f "$AUTOMATION_DIR/web_discovery/update_discovery.py" ]; then
    run_stage "Web source discovery" "$PYTHON_BIN" "$AUTOMATION_DIR/web_discovery/update_discovery.py"
fi

if [ "$FAILURES" -ne 0 ]; then
    echo "Update completed with $FAILURES failed stages; review this log." | tee -a "$LOG_FILE"
    [ "${BIBLE_STUDY_UNATTENDED:-0}" = "1" ] || osascript -e 'display notification "Bible Study Aid update has errors. See the latest log." with title "Bible Study Aid"' || true
    run_stage "Library coverage report" "$PYTHON_BIN" "$COVERAGE_REPORTER"
    exit 1
fi
PENDING_COUNT=$("$PYTHON_BIN" -c 'import json,sys,pathlib; p=pathlib.Path(sys.argv[1]); print(len(json.loads(p.read_text())) if p.exists() else 0)' "$BASE/99_Index/index_pending.json")
if [ "$PENDING_COUNT" -gt 0 ]; then
    echo "Available files updated; $PENDING_COUNT sources still need recovery. See Update status." | tee -a "$LOG_FILE"
else
    echo "Update complete." | tee -a "$LOG_FILE"
fi
if ! run_stage "Library coverage report" "$PYTHON_BIN" "$COVERAGE_REPORTER"; then
    echo "Update completed with $FAILURES failed stages; coverage report failed." | tee -a "$LOG_FILE"
    exit 1
fi
echo "Log saved to: $LOG_FILE"
[ "${BIBLE_STUDY_UNATTENDED:-0}" = "1" ] || osascript -e 'display notification "Bible Study Aid update finished." with title "Bible Study Aid" subtitle "See the latest log file for details." sound name "Glass"'
