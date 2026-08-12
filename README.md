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
- Reference

These paths are defined in `source_folders.tsv`.

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

The latest intake report is written to:

- `99_Index/LFBI_Download_Intake.md`

## Coverage report

Every completed update writes both human-readable and machine-readable library
status reports:

- `99_Index/Library_Status.md`
- `99_Index/library_status.json`

These show indexed document counts, registered local sources, podcast backlog
estimates, feed errors, and LFBI course/resource status.

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
