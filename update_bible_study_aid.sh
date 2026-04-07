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
LOG_DIR="$AUTOMATION_DIR/logs"
ARCHIVE_DIR="$AUTOMATION_DIR/archives"
LFBI_IMPORTER="$AUTOMATION_DIR/import_lfbi_files.py"
LFF_BLOG_IMPORTER="$AUTOMATION_DIR/import_lff_blog.py"
SERMON_NOTES_IMPORTER="$AUTOMATION_DIR/import_sermon_notes.py"
COMMENTARIES_IMPORTER="$AUTOMATION_DIR/import_commentaries.py"
DB_INDEXER="$AUTOMATION_DIR/index_bible_study.py"
SCRIPTURE_INDEXER="$AUTOMATION_DIR/build_scripture_index.py"

MODE="${1:-backlog}"
LIMIT="${2:-3}"

mkdir -p "$LOG_DIR" "$ARCHIVE_DIR"

LOG_FILE="$LOG_DIR/update_$(date +%Y%m%d_%H%M%S).log"

echo "Starting Bible Study Aid update..." | tee -a "$LOG_FILE"
echo "Mode: $MODE" | tee -a "$LOG_FILE"
echo "Limit per source: $LIMIT" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

if [ ! -f "$SOURCES_FILE" ]; then
    echo "Missing source file: $SOURCES_FILE" | tee -a "$LOG_FILE"
    exit 1
fi

echo "========================================" | tee -a "$LOG_FILE"
echo "Importing LFBI files..." | tee -a "$LOG_FILE"

if [ -f "$LFBI_IMPORTER" ]; then
    python3 "$LFBI_IMPORTER" >> "$LOG_FILE" 2>&1
    echo "LFBI import complete." | tee -a "$LOG_FILE"
else
    echo "LFBI importer not found: $LFBI_IMPORTER" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"

echo "========================================" | tee -a "$LOG_FILE"
echo "Importing LFF blog posts..." | tee -a "$LOG_FILE"

if [ -f "$LFF_BLOG_IMPORTER" ]; then
    python3 "$LFF_BLOG_IMPORTER" >> "$LOG_FILE" 2>&1
    echo "LFF blog import complete." | tee -a "$LOG_FILE"
else
    echo "LFF blog importer not found: $LFF_BLOG_IMPORTER" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"

echo "========================================" | tee -a "$LOG_FILE"
echo "Importing sermon notes..." | tee -a "$LOG_FILE"

if [ -f "$SERMON_NOTES_IMPORTER" ]; then
    python3 "$SERMON_NOTES_IMPORTER" >> "$LOG_FILE" 2>&1
    echo "Sermon notes import complete." | tee -a "$LOG_FILE"
else
    echo "Sermon notes importer not found: $SERMON_NOTES_IMPORTER" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"

echo "========================================" | tee -a "$LOG_FILE"
echo "Importing commentaries/reference files..." | tee -a "$LOG_FILE"

if [ -f "$COMMENTARIES_IMPORTER" ]; then
    python3 "$COMMENTARIES_IMPORTER" >> "$LOG_FILE" 2>&1
    echo "Commentaries/reference import complete." | tee -a "$LOG_FILE"
else
    echo "Commentaries importer not found: $COMMENTARIES_IMPORTER" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"

while IFS='|' read -r NAME TYPE URL DEST_REL; do
    [ -z "$NAME" ] && continue

    DEST_DIR="$BASE/$DEST_REL"
    ARCHIVE_FILE="$ARCHIVE_DIR/${NAME}_downloaded.txt"

    mkdir -p "$DEST_DIR"

    echo "========================================" | tee -a "$LOG_FILE"
    echo "Processing source: $NAME" | tee -a "$LOG_FILE"
    echo "Destination: $DEST_DIR" | tee -a "$LOG_FILE"
    echo "Source URL: $URL" | tee -a "$LOG_FILE"

    if [ "$TYPE" != "rss" ]; then
        echo "Skipping non-rss source: $NAME" | tee -a "$LOG_FILE"
        echo "" | tee -a "$LOG_FILE"
        continue
    fi

    if [ "$MODE" = "backlog" ]; then
        echo "Downloading up to $LIMIT new episodes..." | tee -a "$LOG_FILE"

        yt-dlp \
            --download-archive "$ARCHIVE_FILE" \
            --max-downloads "$LIMIT" \
            -x \
            --audio-format mp3 \
            -o "$DEST_DIR/%(title)s.%(ext)s" \
            "$URL" >> "$LOG_FILE" 2>&1
    else
        echo "Downloading new episodes..." | tee -a "$LOG_FILE"

        yt-dlp \
            --download-archive "$ARCHIVE_FILE" \
            -x \
            --audio-format mp3 \
            -o "$DEST_DIR/%(title)s.%(ext)s" \
            "$URL" >> "$LOG_FILE" 2>&1
    fi

    echo "Looking for untranscribed MP3 files..." | tee -a "$LOG_FILE"
    shopt -s nullglob
    MP3_FILES=("$DEST_DIR"/*.mp3)

    if [ ${#MP3_FILES[@]} -eq 0 ]; then
        echo "No MP3 files to transcribe for $NAME." | tee -a "$LOG_FILE"
        echo "" | tee -a "$LOG_FILE"
        continue
    fi

    for file in "${MP3_FILES[@]}"; do
        TXT_FILE="${file%.mp3}.txt"

        if [ -f "$TXT_FILE" ]; then
            echo "Transcript already exists, deleting leftover MP3: $(basename "$file")" | tee -a "$LOG_FILE"
            [ -f "$file" ] && rm "$file"
            continue
        fi

        echo "Transcribing: $(basename "$file")" | tee -a "$LOG_FILE"

        whisper "$file" \
            --model base \
            --output_dir "$DEST_DIR" >> "$LOG_FILE" 2>&1

        if [ -f "$TXT_FILE" ]; then
            echo "Transcript created successfully." | tee -a "$LOG_FILE"

            SRT_FILE="${file%.mp3}.srt"
            TSV_FILE="${file%.mp3}.tsv"
            VTT_FILE="${file%.mp3}.vtt"

            [ -f "$SRT_FILE" ] && rm "$SRT_FILE"
            [ -f "$TSV_FILE" ] && rm "$TSV_FILE"
            [ -f "$VTT_FILE" ] && rm "$VTT_FILE"
            [ -f "$file" ] && rm "$file"

            echo "Deleted MP3 and extra subtitle files." | tee -a "$LOG_FILE"
            echo "Pausing 10 seconds before next file..." | tee -a "$LOG_FILE"
            sleep 10
        else
            echo "Transcript failed for: $(basename "$file")" | tee -a "$LOG_FILE"
        fi
    done

    echo "" | tee -a "$LOG_FILE"
done < "$SOURCES_FILE"

echo "========================================" | tee -a "$LOG_FILE"
echo "Rebuilding searchable database..." | tee -a "$LOG_FILE"

if [ -f "$DB_INDEXER" ]; then
    python3 "$DB_INDEXER" >> "$LOG_FILE" 2>&1
    echo "Search database rebuild complete." | tee -a "$LOG_FILE"
else
    echo "Database indexer not found: $DB_INDEXER" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"

echo "========================================" | tee -a "$LOG_FILE"
echo "Building scripture index..." | tee -a "$LOG_FILE"

if [ -f "$SCRIPTURE_INDEXER" ]; then
    python3 "$SCRIPTURE_INDEXER" >> "$LOG_FILE" 2>&1
    echo "Scripture index complete." | tee -a "$LOG_FILE"
else
    echo "Scripture indexer not found: $SCRIPTURE_INDEXER" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"

echo "Update complete." | tee -a "$LOG_FILE"
echo "Log saved to: $LOG_FILE"
osascript -e 'display notification "Bible Study Aid update finished." with title "Bible Study Aid" subtitle "See the latest log file for details." sound name "Glass"'

