# Bible Study Aid development

## Authority and preservation
- This is the live automation repository; the ChatGPT project sources mirror is read-only.
- Preserve original documents, audio, transcripts, provenance and existing features. Never prune missing iCloud sources automatically.
- Review current code and live status before treating historical review statements as facts.
- Keep desktop functionality primary. Phone access must eventually work independently of the Mac; no network exposure before authentication and source permissions.
- KJV only for future Bible text. No doctrinal rankings of authors; personal preferences remain user-controlled.

## Implementation and validation
- Make routine safe changes directly; test and document actual results.
- Keep database access in the search app read-only. Mutations belong to the intake pipeline, protected by the shared updater lock.
- Use verified SQLite online backups before maintenance; never copy a live database file as a backup. Preserve failed backups for investigation.
- No credentials in source control, logs or generated reports. Do not automate Moodle login or acquire quizzes/grades.
- Never weaken request protection to make tests pass. Test clients must obtain a valid session token; include negative security tests.
- Run `python3 -m unittest discover -v` and `bash -n update_bible_study_aid.sh`. Tests use disposable fixtures and do not modify the live library.
- Update ISSUES.md, ROADMAP.md and STATUS.md after each milestone. Distinguish tested code, deployed app and verified remote state.
- Rebuild the packaged Mac app after GUI changes, verify its signature, retain a rollback copy and verify local/remote commit IDs before claiming GitHub synchronization.
- Keep generated catalog changes separate from code commits. Do not rewrite history or remove user files.
