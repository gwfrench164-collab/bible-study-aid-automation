# Project status — November 27, 2026

## Recovered context
- HANDOFF.md: comprehensive November 26 handoff recovered from Downloads.
- ISSUES.md: Claude version 2 review recovered from Downloads, preserved beneath current audit notes.
- The conversation reader returned only recent setup messages with no older cursor. The user subsequently supplied the revised roadmap in this chat; it is now incorporated into ROADMAP.md.

## Implemented this milestone
- Loopback Host checks, session tokens, cross-site request rejection, protected source actions, indexed supported-file validation and security headers.
- Verified daily SQLite online backups before updater work; fail closed on backup failure. Existing sources and transcript content are not rewritten.
- Portable updater Python selection; regression tests for retry/timeout/backup and incremental extraction failure preservation.
- Expanded Scripture extraction and corrected Song of Solomon report grouping; reference-only rebuild tool with backup and updater lock.
- Automated test workflow and permanent project guidance.

## Live baseline
- SQLite quick_check returned ok; database approximately 507 MiB.
- Documents: LFBI 793, sermon notes 246, church sermons 1,858, podcasts 849, commentaries 121, blogs 164. These are indexed documents, not proof of complete courses or successful acquisition.
- Shared updater lock was idle at initial inspection; maintenance rechecks the lock before writing.
- Git contained three generated discovery-file changes before development; preserve and sync separately.

## Remaining / limitations
- Unattended Pages extraction remains deferred. Do not silently enable GUI automation in launchd.
- Complete Acts course acquisition and transcription-quality evaluation are not yet verified.
- Reference extraction does not yet validate each chapter's verse count or fully handle lists/cross-chapter references.
- Local security is not a sign-in system. Keep the server on loopback; no phone/public exposure yet.
- Backups retain one verified snapshot per UTC day without pruning. A disk-full condition stops protected intake; add visible retention management later.
- Deployment and final verification results are appended below after execution.

## Verification results
- 26 regression tests passed; shell syntax check passed; packaged app built and signature verified.
- Verified SQLite backup created before maintenance at `~/Library/Application Support/Bible Study Aid/backups/library-20261127.sqlite` (subsequent snapshots use database-specific names).
- Locked reference-only rebuild completed: 114,358 rows. Original files, chunk text and FTS data were not rebuilt.
- Live search and protected reader returned HTTP 200 in the staged app; session tokens are present on links.
- The initial 25-test suite also passed on GitHub Actions (run 46082681039). Full macOS UI end-to-end security interaction remains to verify after restarting the installed app.

- Installed the rebuilt app with a rollback copy retained in Applications. Live post-rebuild quick_check was ok; a Jude 3 query returned 275 matching sources (broad mode, not all exact verse citations).
- Added an Update status page for scheduled intake and per-source failures. Current saved state reports local/acquisition failures: latest index report has one empty transcript; acquisition logs include provider download failures. These underlying acquisition errors remain open, not silently reclassified as success.
- Core milestone commit: c55c91e; original generated discovery updates separately committed as 040ab90. Both verified pushed before the health-page follow-up.

## Recovery and updater repair follow-up
- A real backup was restored to `/tmp/bsa-recovery/recovery-drill.sqlite`, not over the live database. Verified 4,031 documents, 195,477 chunks and 73,229 reference rows from that older snapshot; SQLite/foreign-key/FTS integrity passed. Its older reference count is expected, not a claim about current live references.
- Added migration ledger v1 for existing fingerprint/index schema; rollback and idempotence tested. The real local updater adopted it successfully.
- Fixed the manual updater selecting Homebrew Python without yt-dlp. Dependency preflight now selects `.venv`; installed declared intake dependencies and yt-dlp 2026.11.23.
- Added 90-second per-source acquisition budgets (configurable) and child-process cleanup. Whole acquisition run still requires verification; external-provider errors are not declared fixed.
- Latest forced local run returned all four exit codes zero, reset failure count to zero and recorded `ok_with_pending`, with one zero-byte sermon source preserved in the recovery queue. Its recorded YouTube source supplied no captions; no replacement transcript was fabricated.
- Update status now includes indexed collection counts, pending source recovery and embedded build identity. Counts are indexed documents, not full collection completeness.
- 31 local regression tests passed before final packaging. Full Mac GUI and final GitHub run results are tracked separately.
- Real manual updater verified with Homebrew-first PATH: `index 2 all` completed with exit 0; LFBI intake, indexing, Scripture report, discovery and coverage stages passed. One pending source remains explicit. This does not prove a full backlog download run succeeds.
- Live schema_migrations contains v1; post-run SQLite quick_check returned ok.
- Speech recognition retains its separately installed Whisper runtime when intake uses the isolated environment. Updater now passes `--keep-audio` so successful transcription does not remove original audio.
