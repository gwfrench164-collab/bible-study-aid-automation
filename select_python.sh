# Sourced by the updater; choose a Python with the actual intake dependencies.
python_ready() {
    [ -x "$1" ] && "$1" -c 'import sys, yt_dlp, bs4, requests, pypdf, docx, pptx, openpyxl; assert sys.version_info >= (3, 10)' >/dev/null 2>&1
}
if [ -n "${BIBLE_STUDY_PYTHON:-}" ]; then
    if ! python_ready "$BIBLE_STUDY_PYTHON"; then
        echo "Configured Python is missing intake dependencies: $BIBLE_STUDY_PYTHON" >&2
        echo "Install requirements-intake.txt with that interpreter." >&2
        exit 2
    fi
    PYTHON_BIN="$BIBLE_STUDY_PYTHON"
else
    PYTHON_BIN=""
    for candidate in "$SCRIPT_DIR/.venv/bin/python" /usr/local/bin/python3 "$(command -v python3)" /opt/homebrew/bin/python3 /usr/bin/python3; do
        if python_ready "$candidate"; then PYTHON_BIN="$candidate"; break; fi
    done
    if [ -z "$PYTHON_BIN" ]; then
        echo "No suitable Python found. Install requirements-intake.txt and set BIBLE_STUDY_PYTHON." >&2
        exit 2
    fi
fi
export BIBLE_STUDY_PYTHON="$PYTHON_BIN"
