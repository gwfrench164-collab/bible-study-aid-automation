# Database recovery and full rebuilding

## Verify a backup without touching the live library
Run `python database_restore.py BACKUP NEW_DESTINATION` with the project's Python. The destination must not exist. This uses SQLite's online backup API, then full SQLite, foreign-key and FTS integrity checks. It refuses replacement of an existing database and preserves the backup. Inspect the restored copy with read-only queries and representative searches before considering a live switch.

A real recovery drill passed on November 27, 2026. The restored database remains separate; the live database was not rolled back. To switch after a genuine incident, first stop app/readers and scheduled writers, obtain the shared updater lock, retain the current database plus its WAL/SHM state, and use a reviewed maintenance operation. Do not replace a live SQLite file while processes have it open. This tool intentionally does not automate live replacement yet.

## Rebuild only Scripture references
`python rebuild_scripture_refs.py --apply` takes the updater lock and a verified backup, then transactionally rebuilds derived references from existing chunk text. Original files and transcript text remain untouched.

## Full index rebuild
Build into a NEW location rather than deleting the existing index:

1. Obtain the shared updater lock using the existing locking wrapper or an attended maintenance process. Do not run concurrently with intake.
2. Make and verify a backup. Ensure all configured source roots are locally available; unavailable iCloud files are not deletions.
3. Set `BIBLE_STUDY_INDEX_PATH` to a new absolute SQLite path, and run `import_commentaries.py` with the project's dependency environment. The source registry still determines which original files are read. Do not copy or modify originals.
4. Inspect `index_errors.json` and `index_pending.json` in the new index directory. Unattended Pages extraction remains deferred; use an attended run for complete Pages coverage. A run with pending/error items is not a complete rebuild.
5. Run the same integrity checks as the restore tool, compare document/source counts and real queries, and confirm supported file types and references. Test using the app with `BIBLE_STUDY_INDEX_PATH` pointing at the new index.
6. Retain both databases until a separately reviewed switch is complete. Never treat lower counts as permission to delete missing documents or originals.

## Schema migrations
`database_migrations.py` records numbered changes in `schema_migrations`. Index initialization applies missing migrations inside one immediate transaction; failure rolls back schema changes and ledger entries. An unknown newer schema version is rejected. Backups are required before live maintenance. Do not repurpose migration numbers after deployment.
