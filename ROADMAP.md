# Development roadmap

This working roadmap is based on the recovered HANDOFF.md, Claude's review, current code and the user's November 27 authorization. The separately revised roadmap from “Project Handoff Summary” has not been recovered; reconcile it when supplied.

1. Security and recoverability: local request boundaries, safe source actions, backups, regression tests and CI. First implementation delivered; review all legacy writers and restore procedures next.
2. Reliable automatic intake: runtime/version reporting, readable per-stage status, lock contention/crash tests, recoverable Pages extraction without disruptive unattended GUI automation. Preserve originals and previous successful index rows.
3. LFBI: audit existing Acts manifests/downloads and coverage, prove one complete course from source to reader, then expand. Keep quizzes/grades excluded and use authorized Safari access only.
4. Scripture indexing: complete canonical parser consolidation and verse validation, reference lists/cross-chapter ranges, numeric verse ranges and incremental parser-version migrations.
5. Transcription: retain timestamps/confidence metadata, add a vocabulary prompt, compare models against corrected sermon samples before changing defaults, preserve originals during selective retranscription.
6. Search/reading: real-query ranking benchmark, bounded rendering of long result sets, metadata/date filters, highlighting inflections, in-app document/audio reading.
7. Mac-independent phone access: decide hosting/storage after measuring collection size and permissions. Authentication and per-user access precede deployment. Installable web app can precede native iPhone/Android clients.
8. KJV-first study tools: licensed KJV data, Strong's, TSK, Nave's, Webster's, traceable source-linked quotations. reMarkable remains a separate feasibility investigation.

Do not equate implementation tests with live acquisition completeness or remote deployment.
