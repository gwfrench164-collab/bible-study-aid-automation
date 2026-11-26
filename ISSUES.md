# Bible Study Aid: development backlog

This is the central backlog. Issue IDs are permanent: they are never reused or renumbered. New issues get
new IDs; finished issues stay in the list with their results.

Last updated: November 26, 2026 (backlog version 3).

## How status is recorded

Every issue carries three separate marks, because they mean different things:

- **Code**: the change is written. `–` not started, `partial`, or `done`.
- **Tests**: automated tests pass (run on a Linux test machine with small or made-up data). `–` or `pass`.
- **Real**: it has been checked against your real library, database and Mac. `–` or `verified`.

Nothing is "finished" until all three marks say so. Work done so far is only ever marked as far as it has
actually been proven. Implementation details and verification results go in the **Work log** at the end.

Severity: **High**, **Med**, **Low**.

## Standing requirements (apply to every issue)

KJV only. Original source files are never altered; the database is an index. No doctrinal ranking or tiers of
authors. Quotations must be traceable to reliable, preferably primary, sources. Moodle passwords are never
stored or automated. Do not rewrite working code without a reason; do not duplicate capabilities that exist.
The search and reading interface must not depend on Mac-only ingestion tools (see A1).

---

## Audit of requested capabilities against the existing code

Found by searching and reading the code on `main`. "Not verified" means not run against your real library.

| Capability | What exists today | Gap | Issue |
|---|---|---|---|
| Automated database backups, tested restore | Only backups of the two launchd scripts (`installation.json`). Nothing backs up `bible_study.db`. | No database backup, no restore test. | K1 |
| Versioned migrations and rollback | None. Tables are made with `CREATE TABLE IF NOT EXISTS`, one `ALTER TABLE` adds columns, and one-time jobs are tracked by keys in `pipeline_metadata` (for example `fts_exact_delete_v1`). | No schema version number, no ordered steps, no rollback. | K2 |
| Database integrity checks | Only an FTS `integrity-check` inside a one-time repair (`repair_search_index.py`). | No `PRAGMA integrity_check`, no routine check, nothing reported. | K3 |
| Full rebuild from original files | The importer works incrementally from source files; `repair_search_index.py` rebuilds search data from stored text only. | No single documented "rebuild everything from the originals" command, and it is untested. | K4 |
| Installed application version detection | None. No version number, no build stamp. | Cannot tell what is installed. | K5 |
| Source-by-source completeness reporting | `report_library_status.py` writes `Library_Status.md/.json` after each run: documents by type, files awaiting indexing per source, podcast transcripts versus feed items, LFBI course counts. | No last-success time per source, no failure reasons, no pending-work list, and it is a Markdown file rather than a page in the app. | O10 |
| Persistent intake queues and recovery | Good base: per-lane state files (status, next due time, failure count, retry delays), a kernel lock, retry on the next tick, interrupted runs recorded before work starts; Moodle resources queued in `course_manifest_processed.json` and `download_queue.html`. | Pages files are skipped, not queued. No persistent per-item queue (what is pending, how many tries, why it failed). | O1, O11 |
| Original and corrected transcript preservation | Captions (`.vtt`/`.srt`) and `.info.json` are kept beside the audio. Whisper output becomes one `.txt`. | One text file only. Timestamps are discarded. Model, settings and confidence are not saved. No separate corrected version. | T9 |
| Consistent provenance | `documents` stores path, title, type, modified time, indexed time. Podcast `.info.json` and LFBI manifests hold some source details. | No common provenance fields (source URL, author, date, checksum, how obtained). | K9 |

Two further findings from the audit:

- **K8 (High):** the database lives inside iCloud Drive (`99_Index/bible_study.db`) and uses SQLite's
  write-ahead mode. iCloud syncs the main file and its side files separately and can sync a half-written
  state, which is a known way to corrupt SQLite. Not confirmed on your Mac, but it must be checked first.
- The repository itself is ordinary and clean of passwords or keys (see H1).

---

## Prioritized implementation plan

| Phase | Work | Issues |
|---|---|---|
| 0. Know what you have | Version check script; a baseline backup; run the tests on every change; dependency list | K5, K8, K1 (baseline), K6, K7, O9 |
| 1. Security and privacy | Close S1 to S3 with tests; privacy recommendation; no remote access until done | S1, S2, S3, H1 |
| 2. Safe data foundation | Backups and restore test, integrity checks, migrations, rebuild-from-sources, provenance fields; **Bible reference parsing and numeric verse IDs** | K1 to K4, K9, B1 to B6 |
| 3. Reliable unattended intake | Pages documents, persistent queue, retries, recovery, and the library status page | O1, O11, O2, O10 |
| 4. One complete LFBI course | Verify the Acts course end to end before any other course | L1 to L6 |
| 5. Transcription quality | Comparative tests, original and corrected versions kept apart | T1 to T10 |
| 6. Phone access | Tailscale first, only after phase 1; keep offline access possible | P1 to P5 |
| 7. Reading and search | Titles and metadata, reader, filters, highlighting, speed | R1 to R12, A1 |
| 8. Bible-first app, authors | KJV, Strong's, TSK, Nave's, Webster | F1 to F8 |
| 9. Exploratory and housekeeping | reMarkable (separate from phone); clean-up | P6, C1 to C7, H2 to H7 |

Phases overlap where they do not depend on each other. Phase 0 items that need your Mac (K5, K8, O9, L5) are
blocked until you run a short check I will give you.

---

## K. Reliability foundation (new)

| ID | Sev | Issue | Depends on | Acceptance criteria | Code | Tests | Real |
|---|---|---|---|---|---|---|---|
| K1 | High | No automated database backups or tested restore. | K8 | A backup of the database is made safely (SQLite online backup, not a file copy) before every update and once a day; the last N are kept outside the live iCloud folder; a restore command works; a test restores a backup and confirms searches return the same results; backup age appears on the status page. | – | – | – |
| K2 | High | No versioned database migrations or rollback. | K1 | The database carries a schema version; changes are numbered steps that run once, in order; each step is preceded by an automatic backup; a failed step leaves the database unchanged; a test upgrades an old-shape database and rolls one step back. Existing one-time jobs are brought under this system, not duplicated. | – | – | – |
| K3 | Med | No database integrity checks. | – | A routine check (SQLite integrity and foreign-key checks plus FTS check) runs in each update and on demand; failures stop automatic runs, trigger a backup restore recommendation, and appear on the status page. | – | – | – |
| K4 | Med | No tested full rebuild from original files. | K1, K2 | One command rebuilds a new database from the source folders without touching the old one, then reports differences (documents, chunks, references) before it is swapped in; saved passages and notes survive; a test builds a small library twice and gets identical results. | – | – | – |
| K5 | High | The installed app version cannot be detected. | – | A version and build stamp is created by the packaging step; a check compares GitHub `main`, the iCloud project folder, the database schema version and the packaged app, and prints "all match" or exactly what differs; shown on the status page. | – | – | – |
| K6 | Med | No dependency management. | – | A complete `requirements.txt` with exact versions taken from the Mac, a documented Python version, and a check that the app and updater use the same Python (O3). | partial | – | – |
| K7 | High | Regression testing is partial and not automatic (H5, T-series). | – | One command runs all tests; GitHub runs them on every change; there is a small fixed set of your real searches with expected results (R4); a whole-pipeline test on a tiny sample library. | partial | – | – |
| K8 | High | The database sits in iCloud with WAL mode. | – | Confirm where the database really is and how it is configured on your Mac; if at risk, either keep the live database outside iCloud with backups inside it, or change the journal mode; document the choice. | – | – | – |
| K9 | Med | Provenance is inconsistent across collections. | K2 | Every document records source collection, original path or URL, how and when obtained, a content checksum, and where known author, date and title; podcast, LFBI, sermon, blog and commentary collections all fill the same fields; a status check reports documents missing provenance. | – | – | – |

## S. Security (do first; no remote access until done)

| ID | Sev | Issue | Depends on | Acceptance criteria | Code | Tests | Real |
|---|---|---|---|---|---|---|---|
| S1 | High | "Open Source" and "Show in Finder" can open any file or program on the Mac, and a link on any web page can trigger them. | – | Only files recorded in the library index can be opened or revealed; paths outside the library are refused; tests cover paths with `..`, absolute paths, and a file not in the index. | done | pass | – |
| S2 | High | Other web pages can send changes (notes, preferences, excluded authors) to the app. | – | State-changing requests are accepted only from the app's own pages; cross-site requests are refused; tests cover each changing address. | done | pass | – |
| S3 | Med | The app answers to any host name (DNS-rebinding risk). | – | Only expected host names are accepted, extendable on purpose for phone access (S3 supports P1); tests cover wrong host names. | done | pass | – |
| S4 | Low | Unprotected `/shutdown` address in the desktop window program. | – | Removed or protected. | – | – | – |
| S5 | High | No sign-in. | S1 to S3 | Required before P1 is turned on; design chosen with the phone work. | – | – | – |
| H1 | Med | Repository privacy. | – | See "Repository privacy review" below; the recommendation is decided by the owner and carried out. | – | n/a | – |

## O. Unattended intake and reporting

| ID | Sev | Issue | Depends on | Acceptance criteria | Code | Tests | Real |
|---|---|---|---|---|---|---|---|
| O1 | High | Apple Pages files are skipped by unattended runs. | O11 | New or changed `.pages` files are recorded as pending and handled by a safe unattended method (for example reading the file's built-in preview or text without opening Pages, or a quiet single-file conversion), or are shown on the status page as waiting; never silently ignored; tested on sample `.pages` files. | – | – | – |
| O11 | High | No persistent per-item queue. | K2 | A small database table lists each pending item (type, path, tries, last error, next try); interrupted runs resume where they stopped; retries back off; failed items stay visible with the reason; tests simulate a crash mid-run. Builds on the existing lane state files and Moodle queue rather than replacing them. | – | – | – |
| O2 | Med | No plain-language report of what failed and why (11 failed stages in the last log). | O11 | Failures are grouped and explained on the status page. | – | – | – |
| O10 | High | No integrated library and intake status page. | O11, K1, K3, K5 | A page in the app shows, per source: files found, indexed, pending, failed (with reasons), last successful update; plus last backup, integrity result, app version, scheduled-job state and LFBI course coverage. Replaces nothing: it extends `report_library_status.py`. | – | – | – |
| O3 | Med | Hard-coded Python path `/usr/local/bin/python3.14`. | K6 | One configured Python, checked at the start of a run. | – | – | – |
| O4 | Med | Documented tests for locks, retries, timeouts and incremental updates are not in the project. | K7 | Tests exist and pass. | – | – | – |
| O5 | Low | About 30 places swallow errors. | O11 | Failures are recorded, not hidden. | – | – | – |
| O6 | Low | Deleted files are never removed from the index (deliberate). | K4 | An explicit, reversible clean-up tool. | – | – | – |
| O7 | Low | `web_discovery/` generated reports are in the repository history. | H1 | Stop tracking generated reports. | – | – | – |
| O8 | Med | iCloud optimized storage, Mac sleep and overlapping runs not verified on real data. | K8 | Documented behavior and tested handling of "file not downloaded yet". | – | – | – |
| O9 | High | Which version is installed and running is unknown. | K5 | See K5. | – | – | – |

## B. Bible references (moved early: foundation for linking the library to the Bible)

| ID | Sev | Issue | Depends on | Acceptance criteria | Code | Tests | Real |
|---|---|---|---|---|---|---|---|
| B1 | High | Only full book names are recognized ("Rom. 8:28", "Ps 23", "Psalm 23", long-dash ranges missed). | – | One shared parser recognizes abbreviations, numbered books, single-chapter books and ranges; a test file of real citation forms passes. | – | – | – |
| B2 | Med | False references ("the numbers 3 and 4"), impossible ones ("John 99"), "Jude 3" misread. | B1 | Rejected by tests. | – | – | – |
| B3 | Med | Song of Solomon (and other multi-word book names) dropped from the Scripture index. | B1 | All 66 books appear. | – | – | – |
| B4 | Med | Cross-chapter ranges, lists, "vv. 3-4", "I John" unrecognized. | B1 | Recognized and tested. | – | – | – |
| B5 | High | References are text, not canonical verse identifiers. | B1, K2 | Every reference is stored as a numeric verse (or verse range) such as 43003016 = John 3:16, with a single book table; a migration converts existing data; searching a passage uses the numbers; a test confirms old and new results match. | – | – | – |
| B6 | Med | The book list is copied into four files. | B1 | One shared module; the old copies removed. | – | – | – |

## L. LFBI courses (verify one entire course before scaling)

| ID | Sev | Issue | Depends on | Acceptance criteria | Code | Tests | Real |
|---|---|---|---|---|---|---|---|
| L1 | High | Moodle downloads (Microsoft 365 sign-in, `cookies.txt`) never shown to work end to end. | S1 to S3 | One real handout downloaded using your own signed-in session, or the manual queue page proven usable; credentials never stored. | partial | – | – |
| L2 | High | Duplicate checker corrected in code, untested on real files. | – | Tests for generic names and "Acts 1" versus "Acts 10"; run on your real Acts files with results shown to you. | partial | – | – |
| L3 | High | No course checked from lesson page to search result. | L1, L2, O1 | The Acts course: every week's lessons, transcripts, handouts and slides accounted for in a coverage table (present, missing, why) and findable in search. Only then is a second course started. | – | – | – |
| L4 | Med | LFBI intake is not part of the normal update. | L3 | One update does everything. | – | – | – |
| L5 | Med | Amount of LFBI material indexed and pending is unknown. | O10 | Visible on the status page. | – | – | – |
| L6 | Med | Coverage uncertain (e.g., Acts 15). | L3 | Missing lessons listed. | – | – | – |
| L7 | Info | No Moodle passwords are stored or automated. | – | Stays true. | done | n/a | n/a |

## T. Transcription quality (comparative testing, originals preserved)

| ID | Sev | Issue | Depends on | Acceptance criteria | Code | Tests | Real |
|---|---|---|---|---|---|---|---|
| T1 | High | Default model is Whisper "base" (smallest practical size). | T8 | Models compared on the same real sermons; default chosen from the results, with speed noted. | – | – | – |
| T2 | High | No vocabulary hints (names, Bible books, church terms). | T8 | Tested with and without hints; kept only if error counts fall. Hints must never insert wording into a transcript. | – | – | – |
| T3 | Med | No clean-up step. | T9 | Clean-up creates a **separate corrected reading version** and never changes Scripture quotations or a speaker's theological statements without showing a before-and-after; uncertain spots are flagged, not silently changed. | – | – | – |
| T4 | Med | Low-confidence passages not marked. | T9 | Confidence stored where the model provides it and shown in the reader. | – | – | – |
| T5 | Med | Timestamps discarded. | T9 | Segment times saved. | – | – | – |
| T6 | Med | Old transcripts are not redone when the method improves. | T9 | Worst transcripts re-run without losing the originals. | – | – | – |
| T7 | Med | Caption quality varies. | T8 | Captions checked against Whisper on samples; the better source chosen per case and recorded. | – | – | – |
| T8 | High | No way to measure accuracy. | – | A few real sermons and podcasts (your choice, with a short corrected passage from each) used as a fixed test set with a word-error score. Needs audio from you. | – | – | – |
| T9 | High | Original and corrected transcripts are not kept apart; model, settings and provenance not saved. | K2, K9 | The raw transcript is stored unchanged with model name, settings, date, source audio and checksum; corrected versions are separate files linked to the raw one; search can use either, and the reader shows which. | – | – | – |
| T10 | High | Rule: never silently alter a speaker's theological statements or Scripture quotations. | – | Built into T3 and tested: any corrector that changes quoted Scripture or doctrinal wording must show the change for approval. | – | – | – |

## P. Phone and tablet access (Tailscale first, after S1 to S5)

| ID | Sev | Issue | Depends on | Acceptance criteria | Code | Tests | Real |
|---|---|---|---|---|---|---|---|
| P1 | High | No phone access. Tailscale is the leading candidate; no remote access is configured until security is finished. | S1 to S5, K1 | Phone searches the library over the private connection; no public exposure; documented set-up and a way to switch it off. | – | – | – |
| P2 | High | See S5 (sign-in). | S1 to S3 | See S5. | – | – | – |
| P3 | Med | Mac must be on and awake; iCloud may remove local copies. | O8 | Behavior documented and shown on the status page. | – | – | – |
| P4 | Med | Phone layout never checked on a real phone. | P1 | Checked and fixed. | – | – | – |
| P5 | Med | PDF, Word and Pages results open in Mac programs; audio not playable from the match. | A1, T5 | The app serves and displays these itself. | – | – | – |
| P7 | Med | Future offline access must stay possible. | A1, B5 | Search and reading code works from a copy of the database without the ingestion tools (see A1). | – | – | – |
| P6 | Low | reMarkable: exploratory and separate from phone access. | P1 | Feasibility report on what a reMarkable can and cannot run; no purchase advice before that. | – | n/a | – |

## A. Architecture

| ID | Sev | Issue | Depends on | Acceptance criteria | Code | Tests | Real |
|---|---|---|---|---|---|---|---|
| A1 | High | The search and reading interface must not depend on Mac-specific ingestion tools (`open`, `osascript`, `textutil`, Pages, launchd, MLX). | – | Ingestion and the app are separated by the database; a test starts the app on Linux without any Mac tools; Mac-only code lives only in the ingestion side. | – | – | – |

## R. Reading and search

| ID | Sev | Issue | Depends on |
|---|---|---|---|
| R1 | Med | Titles are file names; no speaker, series, date, URL. | K9 |
| R2 | Med | Highlighting ignores word forms (love/loved). | – |
| R3 | Med | No exact-phrase or wildcard search, spelling suggestions or Strong's search. | F2 |
| R4 | Med | No fixed set of real searches to detect regressions. | K7 |
| R5 | Med | Audio cannot play from the matching spot. | T5 |
| R6 | Med | Transcript reader lacks adjustable size, paragraphs, navigation, calm styling. | T9 |
| R7 | Med | PDF, Word and Pages cannot be read in the app. | A1 |
| R8 | Med | Only five hard-coded topics. | F4 |
| R9 | Med | Results hard to sort and scan. | R1 |
| R10 | Low | Duplicate content still indexed. | K9 |
| R11 | Low | Personal preferences built into code. | – |
| R12 | High | Broad searches slow with library size (about 2.5 s at 20,000 passages and 12 s at 100,000 on made-up data). Needs your decision on approximate counts. | K7 |

(Acceptance criteria for R-items are written when each is started; the status marks are Code –, Tests –, Real – for all.)

## F. Bible-first app and external authors

| ID | What | Depends on |
|---|---|---|
| F1 | KJV text, chapter reader, word and phrase search | B5 |
| F2 | Strong's numbers and definitions | F1 |
| F3 | TSK cross-references (separate tab) | F1, B5 |
| F4 | Nave's Topical Bible | F1 |
| F5 | Webster's 1828 Dictionary (side window) | – |
| F6 | Link everything by verse (Acts 15 example) | B5, F1 |
| F7 | External authors library: practical metadata only, no ranking, public domain unless permission | K9 |
| F8 | Traceable quotations with citations | K9 |

All F-items: Code –, Tests –, Real –. Each source's license and edition are checked before any data is copied.

## C and H. Code and housekeeping

| ID | Sev | Issue |
|---|---|---|
| C1 | Med | About 40 scripts in one folder, including retired ones. |
| C2 | Med | Main app file is 1,100+ lines with page designs inside. |
| C3 | Med | Two programs open the desktop window. |
| C4 | Med | Personal folder paths in several scripts and `source_folders.tsv`. |
| C5 | Low | Mac-only steps (see A1). |
| C6 | Low | Saved passages tied to file locations. |
| C7 | Low | (reserved) |
| H2 | Med | See K6. |
| H3 | Low | No license file. |
| H4 | Low | History is three entries; `.idea/` editor files and the unused `sources.txt` are tracked. |
| H5 | Low | Tests not run automatically (see K7). |
| H6 | High | LFBI, sermon and blog materials have their own terms; record permission before anyone else gets access. |
| H7 | Low | Docs refer to an audit report that is not in the project. |

---

## Repository privacy review (H1)

Found in the tracked files of `main` (61 files, 3 commits):

- **No passwords, keys, tokens or email addresses.** The only hits were ordinary words in the code.
- **Your Mac user name** (`/Users/george/...`) appears in 7 code files, `source_folders.tsv` and in about 435
  lines across five generated `web_discovery/` reports and data files.
- **LFBI course and handout names** and author lists are in `web_discovery/` and `source_folders.tsv`.
- **The list of Living Faith Fellowship-connected churches and their web addresses** is in
  `lff_church_directory.tsv` and `lff_church_sources.tsv`.
- **Editor settings** (`.idea/`).

Recommendation, in order:

1. **Make the repository private now** (GitHub: Settings, then Danger Zone, then Change visibility). History is
   only three entries, so the personal details are in the history too; making it private is the fix that works
   regardless of what is removed later. Private repositories are free, and nothing in this project needs to be
   public. Anyone who has already copied it keeps the copy; the contents are not sensitive in the way a password
   is, so this is limited exposure.
2. Then stop tracking the generated files (`web_discovery/` reports and data, `.idea/`) and move the folder path
   into one settings file (C4, O7, H4). This keeps new history clean.
3. Settle source permissions (H6) before ever sharing the repository.

Status: recommendation only. The visibility change is yours to make.

---

## Work log

Entries are added as work happens: date, issue ID, what changed, which tests passed, and whether anything was
checked on real data.

- **Nov 26, 2026 (H1):** privacy scan completed; recommendation above. Nothing changed in the repository.
- **Nov 26, 2026 (K-audit):** all nine requested capabilities checked against the code; findings are in the audit
  table above. Nothing was duplicated; K1 to K9 work will extend `pipeline_metadata`, `scheduled_intake.py`
  state files and `report_library_status.py`. Not run on real data.
- **Nov 26, 2026 (S1, S2, S3):** added `local_guard.py` (registered in `bible_study_search_app.py`) and a check
  that `/open` and `/reveal` accept only files listed in the index. Cross-site requests, changes not coming from
  the app's own pages, and unexpected host names are refused. Older browsers that send no fetch-metadata headers
  are checked by the linking page instead. `BIBLE_STUDY_ALLOWED_HOSTS` allows a phone address later on purpose.
  **Code done. Tests: 23 pass (13 existing, 10 new) on Linux with a scratch database.** Not yet checked on the Mac:
  open a result's "Open Source" and "Show in Finder", save a note, and use the desktop window; all should still
  work. Residual risk: an old browser with no fetch-metadata headers and no referrer could still trigger "Open
  Source" for a file that is in the index (it cannot reach any file outside it).
