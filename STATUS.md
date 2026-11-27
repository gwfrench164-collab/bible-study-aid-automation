# Project status — November 27, 2026

## Recovered context
- HANDOFF.md: comprehensive November 26 handoff recovered from Downloads.
- ISSUES.md: Claude version 2 review recovered from Downloads, preserved beneath current audit notes.
- The conversation reader returned only recent setup messages with no older cursor. Missing: the separate revised development roadmap/development-package attachment from “Project Handoff Summary.”

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
- 25 regression tests passed; shell syntax check passed; packaged app built and signature verified.
- Verified SQLite backup created before maintenance at `~/Library/Application Support/Bible Study Aid/backups/library-20261127.sqlite` (subsequent snapshots use database-specific names).
- Locked reference-only rebuild completed: 114,358 rows. Original files, chunk text and FTS data were not rebuilt.
- Live search and protected reader returned HTTP 200 in the staged app; session tokens are present on links.
- Full macOS UI end-to-end security interaction and CI execution on GitHub remain to verify after deployment; unit tests do not substitute for those checks.
