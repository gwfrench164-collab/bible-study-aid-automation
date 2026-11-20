# Mobile and desktop direction

Build a shared search and document service, with personal accounts and synchronized studies.
An installable phone website is the first mobile client. Retain the standalone Mac interface.
Future native iPhone and Android clients should use the same service.

## Storage configuration

The desktop defaults use the existing iCloud library and Application Support studies database.
Set these environment variables before starting the application to use another deployment.

| Variable | Purpose |
| --- | --- |
| BIBLE_STUDY_LIBRARY_ROOT | Root folder containing library source materials |
| BIBLE_STUDY_INDEX_PATH | Search SQLite file, defaulting to 99_Index/bible_study.db beneath the library |
| BIBLE_STUDY_STUDIES_PATH | Personal saved-passages SQLite file |
| BIBLE_STUDY_LEGACY_LIBRARY_ROOT | Original root recorded in absolute index paths when relocating a library |

Relative source paths resolve beneath the configured library root. Absolute paths beneath the
legacy root map to the new root. Absolute external-library paths still refer to their original
location and require separate migration planning. Configuration does not move files.

These settings apply to the search app and saved studies. Existing ingestion scripts have their
own storage configuration. A hosted deployment needs a defined ingestion and publishing workflow.

## Next implementation milestones

1. Assign durable source and passage identifiers and preserve existing saved links during migration.
2. Expose authenticated search, reading, and study operations through a versioned service interface.
3. Store notes and studies per account, with authorization on every operation, backup, and restore.
4. Deploy a private test library independent of the Mac. Select hosting after estimating storage,
   document access, indexing needs, and monthly costs.
5. Build the phone navigation, sign-in, synchronized studies, and offline downloads.
6. Validate iPhone and Android behavior with a small invited group.

## Hosting readiness

The current Flask app is a local desktop application. Hosting requires user authentication,
per-user authorization, request protections for write operations, opaque document identifiers,
and document access controls. Local path and Finder actions need desktop-specific handling.
Distribution permissions must be recorded before including sources in a shared library.

## Verification

Run the storage and search regressions with:

    python3 -m unittest test_library_settings test_search_coverage

The relocation test uses a temporary library and an old absolute source path, checks independent
index/study locations, and checks relative path containment. Default-path tests cover the existing
desktop installation.
