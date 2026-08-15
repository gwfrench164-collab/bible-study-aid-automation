#!/bin/bash

set -u

# Prevent multiple updater runs at the same time
LOCK_FILE="/tmp/bible_study_aid_update.lock"

if [ -f "$LOCK_FILE" ]; then
    echo "Bible Study Aid updater is already running. Exiting."
    osascript -e 'display notification "Another Bible Study Aid update is already running." with title "Bible Study Aid" sound name "Glass"'
    exit 1
fi

touch "$LOCK_FILE"

# Ensure lock file is removed when script exits
trap 'rm -f "$LOCK_FILE"' EXIT

BASE="$HOME/Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid"
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
PYTHON_BIN="/usr/local/bin/python3.14"
YT_DLP=("$PYTHON_BIN" -m yt_dlp)

MODE="${1:-backlog}"
LIMIT="${2:-3}"
SOURCE_GROUP="${3:-all}"
PAUSE_SECONDS="${BIBLE_STUDY_COOLING_SECONDS:-${BIBLE_STUDY_PAUSE_SECONDS:-5}}"
TRANSCRIPTION_BACKEND="${BIBLE_STUDY_TRANSCRIBER:-auto}"
OPENAI_WHISPER_MODEL="${BIBLE_STUDY_WHISPER_MODEL:-base}"
MLX_WHISPER_MODEL="${BIBLE_STUDY_MLX_MODEL:-mlx-community/whisper-base.en-mlx}"
MLX_PYTHON="${BIBLE_STUDY_MLX_PYTHON:-$HOME/Library/Caches/BibleStudyAid/mlx-venv/bin/python}"
TRANSCRIPTION_LIMIT="${BIBLE_STUDY_TRANSCRIPTION_LIMIT:-0}"
TRANSCRIPTION_TIME_BUDGET="${BIBLE_STUDY_TRANSCRIPTION_TIME_BUDGET_MINUTES:-0}"

mkdir -p "$LOG_DIR" "$ARCHIVE_DIR"

LOG_FILE="$LOG_DIR/update_$(date +%Y%m%d_%H%M%S).log"

echo "Starting Bible Study Aid update..." | tee -a "$LOG_FILE"
echo "Mode: $MODE" | tee -a "$LOG_FILE"
echo "Limit per source: $LIMIT" | tee -a "$LOG_FILE"
echo "Source group: $SOURCE_GROUP" | tee -a "$LOG_FILE"
echo "Cooling pause after speech recognition: ${PAUSE_SECONDS}s" | tee -a "$LOG_FILE"
echo "Transcription backend: $TRANSCRIPTION_BACKEND" | tee -a "$LOG_FILE"
echo "Transcription limit: $TRANSCRIPTION_LIMIT" | tee -a "$LOG_FILE"
echo "Transcription time budget: ${TRANSCRIPTION_TIME_BUDGET} minutes" | tee -a "$LOG_FILE"
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

if [ "$MODE" != "index" ]; then
echo "========================================" | tee -a "$LOG_FILE"
echo "Importing LFF blog posts..." | tee -a "$LOG_FILE"

if [ -f "$LFF_BLOG_IMPORTER" ]; then
    /usr/local/bin/python3.14 "$LFF_BLOG_IMPORTER" >> "$LOG_FILE" 2>&1
    echo "LFF blog import complete." | tee -a "$LOG_FILE"
else
    echo "LFF blog importer not found: $LFF_BLOG_IMPORTER" | tee -a "$LOG_FILE"
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
        "${YT_DLP[@]}" "${DOWNLOAD_ARGS[@]}" "$URL" >> "$LOG_FILE" 2>&1
    else
        echo "Downloading new episodes..." | tee -a "$LOG_FILE"
        "${YT_DLP[@]}" "${DOWNLOAD_ARGS[@]}" "$URL" >> "$LOG_FILE" 2>&1
    fi
    echo "" | tee -a "$LOG_FILE"
done < <(emit_selected_sources)

echo "========================================" | tee -a "$LOG_FILE"
echo "Processing downloaded captions and audio as one resumable batch..." | tee -a "$LOG_FILE"

if [ ! -f "$TRANSCRIBER" ]; then
    echo "Batch transcriber not found: $TRANSCRIBER" | tee -a "$LOG_FILE"
else
    TRANSCRIBE_ARGS=(
        "$TRANSCRIBER"
        --pause-seconds "$PAUSE_SECONDS"
        --limit "$TRANSCRIPTION_LIMIT"
        --time-budget-minutes "$TRANSCRIPTION_TIME_BUDGET"
    )

    TRANSCRIBE_PYTHON="$PYTHON_BIN"
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
        "$PYTHON_BIN" "${TRANSCRIBE_ARGS[@]}" \
            --backend openai \
            --model "$OPENAI_WHISPER_MODEL" \
            "${TRANSCRIPTION_DIRS[@]}" >> "$LOG_FILE" 2>&1
    fi
fi
else
    echo "Index-only mode: skipping blog, media download, and transcription." | tee -a "$LOG_FILE"
fi

echo "========================================" | tee -a "$LOG_FILE"
echo "Importing completed LFBI browser downloads..." | tee -a "$LOG_FILE"

if [ -f "$LFBI_DOWNLOAD_IMPORTER" ]; then
    /usr/local/bin/python3.14 "$LFBI_DOWNLOAD_IMPORTER" >> "$LOG_FILE" 2>&1
    echo "LFBI browser-download intake complete." | tee -a "$LOG_FILE"
else
    echo "LFBI download importer not found: $LFBI_DOWNLOAD_IMPORTER" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"

echo "========================================" | tee -a "$LOG_FILE"
echo "Building searchable index..." | tee -a "$LOG_FILE"

if [ -f "$COMMENTARIES_IMPORTER" ]; then
    /usr/local/bin/python3.14 "$COMMENTARIES_IMPORTER" >> "$LOG_FILE" 2>&1
    echo "Searchable index build complete." | tee -a "$LOG_FILE"
else
    echo "Indexer not found: $COMMENTARIES_IMPORTER" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"

echo "========================================" | tee -a "$LOG_FILE"
echo "Building scripture index..." | tee -a "$LOG_FILE"

if [ -f "$SCRIPTURE_INDEXER" ]; then
    /usr/local/bin/python3.14 "$SCRIPTURE_INDEXER" >> "$LOG_FILE" 2>&1
    echo "Scripture index complete." | tee -a "$LOG_FILE"
else
    echo "Scripture indexer not found: $SCRIPTURE_INDEXER" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"

echo "========================================" | tee -a "$LOG_FILE"
echo "Writing library coverage report..." | tee -a "$LOG_FILE"

if [ -f "$COVERAGE_REPORTER" ]; then
    /usr/local/bin/python3.14 "$COVERAGE_REPORTER" >> "$LOG_FILE" 2>&1
    echo "Library coverage report complete." | tee -a "$LOG_FILE"
else
    echo "Coverage reporter not found: $COVERAGE_REPORTER" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"

echo "Update complete." | tee -a "$LOG_FILE"
echo "Log saved to: $LOG_FILE"
osascript -e 'display notification "Bible Study Aid update finished." with title "Bible Study Aid" subtitle "See the latest log file for details." sound name "Glass"'
