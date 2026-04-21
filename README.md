# Bible Study Aid Automation

This project powers a local Bible Study Aid system that indexes study materials and makes them searchable through a local app.

## Current live workflow

The main active update flow is:

1. `update_bible_study_aid.sh`
2. `import_lff_blog.py`
3. podcast download and transcription
4. `import_commentaries.py`
5. `build_scripture_index.py`

## Main active files

These are the main files currently used in the working system:

- `update_bible_study_aid.sh`
- `import_commentaries.py`
- `import_lff_blog.py`
- `build_scripture_index.py`
- `query_bible_study.py`
- `bible_study_search_app.py`

## How local files are handled now

Local files already on the hard drive are indexed from their original locations.

This includes:

- LFBI
- Sermon Notes
- Reference

These paths are defined in `source_folders.tsv`.

## How generated content is handled

Some content is created or downloaded by the automation system and stored inside the `Bible_Study_Aid` folder.

This includes:

- podcast transcripts
- podcast text files
- downloaded blog content

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