# Bible Study Aid Automation

This project powers a local Bible Study Aid system that indexes study materials and makes them searchable through a local app.

## Current live workflow

The main active update flow is:

1. `update_bible_study_aid.sh`
2. `import_lff_blog.py`
3. podcast download and transcription
4. `import_lfbi_downloads.py`
5. `import_commentaries.py`
6. `build_scripture_index.py`
7. `report_library_status.py`

## Main active files

These are the main files currently used in the working system:

- `update_bible_study_aid.sh`
- `transcribe_audio_batch.py`
- `import_commentaries.py`
- `import_lff_blog.py`
- `build_scripture_index.py`
- `query_bible_study.py`
- `bible_study_search_app.py`
- `import_lfbi_downloads.py`
- `report_library_status.py`

## How local files are handled now

Local files already on the hard drive are indexed from their original locations.

This includes:

- current LFBI course output
- the legacy LFBI collection under `Documents/Spiritual/LFBI`
- Sermon Notes
- the separate local Sermons folder
- Reference

These paths are defined in `source_folders.tsv`.

Podcast and church updates now request English captions alongside YouTube audio.
Caption files are converted directly to transcripts; speech recognition runs only
when captions are unavailable. Downloaded audio is processed as one resumable
batch so the Whisper model is loaded once instead of once per recording.

Only English-language recordings are processed. The updater first uses reliable
download metadata when available; otherwise Whisper checks the recording's
language before captions are imported or full transcription begins. A confidently
non-English recording is left untouched and receives a small
`skipped-language.json` audit marker so later updates ignore it without spending
transcription resources again.

The default five-second cooling pause remains in place after speech recognition
and does not run after fast caption imports. Set `BIBLE_STUDY_COOLING_SECONDS`
to a larger value if the computer needs more cooling time. The older
`BIBLE_STUDY_PAUSE_SECONDS` name remains supported.

Transcription controls:

- `BIBLE_STUDY_TRANSCRIBER=openai|mlx|auto` selects the backend. `auto` is the
  default: it uses the faster Apple MLX backend when available and falls back
  to OpenAI Whisper if MLX cannot complete a recording.
- `BIBLE_STUDY_WHISPER_MODEL` defaults to the already-cached `base` model.
- `BIBLE_STUDY_MLX_MODEL` defaults to the multilingual
  `mlx-community/whisper-base-mlx`, which supports the English-language gate.
- `BIBLE_STUDY_LANGUAGE_CONFIDENCE` controls the non-English rejection threshold
  and defaults to `0.75`.
- `BIBLE_STUDY_TRANSCRIPTION_LIMIT` caps completed items in one run; zero is
  unlimited.
- `BIBLE_STUDY_TRANSCRIPTION_TIME_BUDGET_MINUTES` stops before starting another
  recording once the elapsed transcription budget has been reached; zero is
  unlimited.

## Living Faith Fellowship churches

`lff_church_directory.tsv` records the churches listed by the official Living
Faith Fellowship directory. `discover_lff_church_sermons.py` audits their public
websites and writes `99_Index/LFF_Church_Sermon_Audit.md` plus a machine-readable
JSON report. Verified church feeds and video channels are registered separately
in `lff_church_sources.tsv`; the normal updater processes both RSS and YouTube
sources while using the same archive and transcript safeguards.

Directory-church transcripts are classified as `church_sermon` in the search
index and appear under the app's separate **Church Sermons** filter instead of
being mixed into general podcasts.

The updater's optional third argument selects `all`, `podcasts`, or `churches`.
For example, `update_bible_study_aid.sh backlog 1 churches` takes one new sermon
from each registered LFF church source without first working through the other
podcast feeds.

Use `update_bible_study_aid.sh index` to import completed LFBI downloads and
rebuild the searchable and scripture indexes without waiting for any podcast or
church-media work. Registry comment/header rows are ignored automatically.

High Plains Christian Fellowship is intentionally excluded from online sermon
intake because the owner's sermon notes are already indexed as the authoritative
local source.

## How generated content is handled

Some content is created or downloaded by the automation system and stored inside the `Bible_Study_Aid` folder.

This includes:

- podcast transcripts
- podcast text files
- downloaded blog content

## LFBI browser downloads

Authenticated Moodle files may be downloaded through Safari using a course's
`download_queue.html`. On the next update, `import_lfbi_downloads.py` scans the
Downloads folder and safely copies unique, high-confidence matches into the
correct LFBI course and week folders. It never deletes the original download.

LFBI retakes are treated as another enrollment in the same canonical class.
Matching resources are reused, and an existing week transcript is referenced
instead of transcribing the same lecture again. Material that does not confidently
match an earlier resource remains separate for review.

The latest intake report is written to:

- `99_Index/LFBI_Download_Intake.md`

## Coverage report

Every completed update writes both human-readable and machine-readable library
status reports:

- `99_Index/Library_Status.md`
- `99_Index/library_status.json`

These show indexed document counts, registered local sources, podcast backlog
estimates, feed errors, and LFBI course/resource status.

Scanned PDFs that contain no embedded text use a cached OCR fallback during
indexing. Ordinary text PDFs continue through the faster native extractors.

## Search and reading

The local search app returns one ranked card per document, supports source and
match-mode filters, and expands several common study topics. Source-count pills
can be clicked to narrow the current search. Text and Markdown results open in a
built-in reading view with highlighted matches, adjustable text size, and a link
back to the search results; other document formats open in their normal Mac app.

## Legacy files

Some older files are still in the repo but are no longer part of the main live update flow.

These include:

- `index_bible_study.py`
- `import_lfbi_files.py`
- `import_sermon_notes.py`

These are kept for reference but should not be treated as the main active pipeline.

## Notes

- The live index is currently built through `import_commentaries.py`
- The updater script is `update_bible_study_aid.sh`
- The local search app uses the current database built by the active workflow
