# Current issue tracking

Updated November 27, 2026. Original review is preserved below. Its “every item is open” statement refers to November 26, not current status.

| Review IDs | Verified status |
|---|---|
| S1–S3 | Implemented: indexed supported-file allowlist, symlink rejection, per-session tokens for file actions and mutations, origin/fetch-site checks, strict loopback Host validation. Covered by regression tests. Not remote authentication. |
| O3 | Removed fixed Python version; explicit override or PATH interpreter. Dependency availability remains an operational prerequisite. |
| O4 / H5 | Repository tests now cover backup/WAL, timeout, retries, incremental preservation, Moodle assessment exclusion, security, references and existing UI behavior; CI workflow added. Lock contention and real sleep/iCloud behavior remain to test. |
| B1 / B2 / B3 | Index extraction supports common abbreviations, singular Psalm, Roman numeral books, long-dash verse ranges, single-chapter verses and chapter limits. Multi-word Scripture report grouping fixed. Per-book verse limits and ambiguous prose need more work. |
| B4–B6 | Still open: cross-chapter ranges, lists, contextual verse references, numeric verse identities, consolidation of all older parser copies. |
| R11 | Already implemented: source/author management. Defaults remain built in but are overridable. |
| R3 / R6 / R9 | Review partly stale: exact phrase mode, reading controls and grouped/filterable results already exist. Further improvements remain. |
| O1 / L1–L3 / T1–T8 | Open: unattended Pages, complete authenticated Acts intake, transcription comparison and quality improvements. Do not claim completion from unit tests. |
| P1–P3 | Open; Mac-independent phone service is the user's requirement. The review's Mac-tunnel recommendation does not meet it. |

Database protection added: verified daily snapshots outside iCloud before scheduled/local updater work; reference-only rebuild uses the shared lock and a backup. Snapshots are retained without automatic deletion; monitor disk space. Direct legacy entry points still need a complete lock/backup audit.

---

## Original Claude review (unaltered)

# Bible Study Aid: issues list (version 2)

Rewritten November 26, 2026. This list describes the project **as it is on `main` in GitHub**. No fixes are
applied; every item is open. It combines my first review of the repository with the ChatGPT handoff.

Severity: **High** = do first, **Med** = important, **Low** = tidy-up.

Your priorities, in order: (1) automatic, reliable updates; (2) LFBI course ingestion; (3) reading and
search experience, including transcript quality; (4) searching from your phone; (5) the Bible-first,
e-Sword-style app and external authors; (6) reMarkable tablet (exploratory, and separate from the phone work).
Safety and housekeeping items are listed last but some (S1, S2) are quick and worth doing early.

---

## 1. Automatic updates (O)

Already built: two launchd jobs every 15 minutes, shared lock, retries, disk-space check
(`AUTOMATIC_INTAKE.md`). They run only while the Mac is on and you are logged in.

| ID | Sev | Issue | Why it matters |
|---|---|---|---|
| O1 | High | Pages documents (most of your sermon notes) are skipped by automatic runs; only manual runs read them. | Sermon notes go stale in search unless you remember to update by hand. |
| O2 | Med | No plain-language "what worked, what failed, why" report. The last log showed 11 failed stages. | Problems stay buried in logs. |
| O3 | Med | The update script points to `/usr/local/bin/python3.14` (override: `BIBLE_STUDY_PYTHON`). | Breaks if Python moves or upgrades. |
| O4 | Med | `AUTOMATIC_INTAKE.md` says tests cover locks, retries, timeouts and incremental updates; those tests are not in the project. | Protection that cannot be checked. |
| O5 | Low | About 30 places catch every error and carry on quietly. | Real problems may never be reported. |
| O6 | Low | Files that disappear are never removed from the index (deliberate). | Deleted material still appears; needs a clean-up tool. |
| O7 | Low | Generated `web_discovery/` reports (with local paths) are saved in the project history. | Clutter and personal details. |
| O8 | Med | Not verified: iCloud "optimized storage" removing local copies, Mac sleep, and overlapping runs on real data. | Silent gaps in the library. |
| O9 | Med | Unknown which version is installed on the Mac, in iCloud and in the packaged app. | Fixes may not reach the app you actually use. |

## 2. LFBI course ingestion (L)

I only skimmed these importers in my first review; they need a proper review next.

| ID | Sev | Issue | Why it matters |
|---|---|---|---|
| L1 | High | Moodle downloads (Microsoft 365 sign-in, `cookies.txt`) are coded but have never been shown to work end to end. A manual `download_queue.html` fallback exists. | Handouts, slides and PDFs may be missing. |
| L2 | High | The duplicate checker was corrected in code (generic names like "Handout", "Acts 1" vs "Acts 10") but never tried on real Moodle files. | Real handouts could be hidden, or repeats let in. |
| L3 | High | No complete course (Acts) has been verified from lesson page to search result. | Expanding before one course works end to end multiplies errors. |
| L4 | Med | LFBI intake is not part of the normal update; it takes separate commands. | You must remember them. |
| L5 | Med | Unknown: how much LFBI material is indexed, and what has succeeded, failed or is queued. | Needs your database and `report_library_status.py`. |
| L6 | Med | Coverage of lessons is uncertain (for example, whether Acts 15 material is all there). | Gaps would go unnoticed. |
| L7 | Info | Moodle passwords are correctly never stored or automated. | Keep it that way. |

## 3. Transcription quality (T)

| ID | Sev | Issue | Why it matters |
|---|---|---|---|
| T1 | High | The default speech-recognition model is Whisper **"base"**, the second-smallest size, both in the Mac-native route (`whisper-base-mlx`) and the fallback. | Likely the main cause of unintelligible or wrong words. Larger models are far more accurate on accents, speed and background noise; the Mac can run them, just more slowly. |
| T2 | High | Names, books of the Bible and church words (Strong's, Thessalonians, Melchizedek, LFBI) are not given to the transcriber as hints. | Whisper accepts a vocabulary prompt; today it is not used, so proper names are commonly misspelled. |
| T3 | Med | No clean-up step after transcribing: no correction of Bible book names, no spelling pass against your own documents, no paragraphs. | Wrong words also damage search, because the index sees them. |
| T4 | Med | No marking of low-confidence passages. | Unintelligible sections look the same as good ones. |
| T5 | Med | Timestamps are thrown away. | Needed for "play from here" (R5) and for finding bad spots. |
| T6 | Med | Existing transcripts are not re-done when the method improves. | Old poor transcripts stay poor. A "re-transcribe the worst ones" process is needed. |
| T7 | Med | Captions are used first when they exist; their quality varies, especially auto-captions. | Poor captions can be worse than a good Whisper pass; they should be checked. |
| T8 | Low | No way to measure accuracy. | Needs a small set of sample sermons with correct text to compare models against. |

Plan: test a few real sermons with larger models and a vocabulary prompt, compare against a corrected sample,
then choose the default and set up re-transcription of the weakest ones.

## 4. Reading and search experience (R)

| ID | Sev | Issue | Why it matters |
|---|---|---|---|
| R1 | Med | Titles are just file names; no speaker, series, date or web address. | Cannot sort sermons by date or group by series. |
| R2 | Med | Highlighting ignores word forms (love/loved/loving) though search matches them. | Hits look unhighlighted. |
| R3 | Med | No exact-phrase or wildcard syntax, no spelling suggestions, no Strong's-number search. | Features you use in e-Sword. |
| R4 | Med | Ranking uses hand-tuned numbers with no way to tell if a change helped or hurt. | Needs a small list of your real searches with expected results. |
| R5 | Med | Audio is kept but cannot be played from the matching spot. | Most useful sermon and podcast feature (depends on T5). |
| R6 | Med | The transcript reader shows text as HTML but has no adjustable size, paragraphs, long-document navigation or consistent look. | Hard to read for long periods; screens strain your eyes. |
| R7 | Med | Only text and Markdown show in the app. PDF, Word, PowerPoint and Pages open in Mac programs. | A phone could not read them. |
| R8 | Med | Topic search works for only five topics typed into the code. | A real topical index (Nave's) would cover every topic. |
| R9 | Med | Search results are hard to sort and scan (filters, excerpts, context, grouping). | Handoff item. |
| R10 | Low | Duplicate content is hidden in the display but still indexed. | Inflated counts. |
| R11 | Low | Preferences (excluded authors, "52 Weeks of Pursuit") are built into the code. | Should be settings. |
| R12 | High | Broad searches ("God", "love") slow down as the library grows: about 2.5 s at 20,000 passages and 12 s at 100,000 on test data. | Needs a decision about approximate counts. |

## 5. Bible references (B)

| ID | Sev | Issue | Why it matters |
|---|---|---|---|
| B1 | High | Only full book names are recognized. "Rom. 8:28", "Ps 23", "Psalm 23" and long-dash ranges are missed. | Searching by passage misses most common citations. |
| B2 | Med | Everyday words become false references ("the numbers 3 and 4"), impossible ones are stored ("John 99"), and "Jude 3" is misread. | Noise in results. |
| B3 | Med | The Scripture index silently drops Song of Solomon and other multi-word book names. | Missing section. |
| B4 | Med | Not recognized: cross-chapter ranges, lists ("3:16, 18"), "vv. 3-4", "I John". | More missed citations. |
| B5 | Med | References are stored as text, not numbers (John 3:16 = 43003016). | Slow, and blocks linking KJV text, TSK and commentary. |
| B6 | Med | The list of books is copied into four files. | A fix in one place misses the others. |

## 6. Phone and tablet access (P) — higher priority than reMarkable

| ID | Sev | Issue | Why it matters |
|---|---|---|---|
| P1 | High | The app runs only on the Mac and listens only to that Mac. **Needs your decision** (options below). | No phone access today. |
| P2 | High | No sign-in (was S5). | Not safe once the app can be reached from a phone. |
| P3 | Med | Mac must be on and awake; iCloud may remove local copies. | Phone searches would fail at random times. |
| P4 | Med | Layout adapts to small screens but was never checked on a real phone. | Small annoyances. |
| P5 | Med | See R7 (PDF/Word in app) and R5 (play audio from here). | Phone must not rely on Mac programs. |

reMarkable (P6, exploratory, after P1 to P4): whether it can run an interactive search is unverified; exported
pages are the likely fallback. Do not buy one for this until that is checked. The phone work is the base.

## 7. Bible-first app and external authors (F)

| ID | What | Notes |
|---|---|---|
| F1 | KJV text, chapter reader, word and phrase search | Foundation; needs B5. |
| F2 | Strong's numbers and definitions, KJV tagging | Check the license of any data. |
| F3 | TSK cross-references | A separate tab, as in your e-Sword workflow. |
| F4 | Nave's Topical Bible | Also replaces hard-coded topics (R8). |
| F5 | Webster's 1828 Dictionary | Opens in a side window. |
| F6 | Link everything by verse | KJV, TSK, sermon notes, LFBI lessons, podcast passages (example: Acts 15). |
| F7 | External authors library (Spurgeon, McGee, Bounds, etc.) | Author, title, source, copyright status only. **No doctrinal rankings.** Public domain only unless permission is obtained. Not started. |
| F8 | Traceable quotations | Any quotation links to a reliable, preferably primary, source with citation details. |

## 8. Safety (S)

| ID | Sev | Issue | Why it matters |
|---|---|---|---|
| S1 | High | "Open Source" and "Show in Finder" can open **any** file or program on the Mac, and a link on any web page can trigger them. | A booby-trapped page could launch programs. |
| S2 | High | Other web pages can silently send changes to the app (notes, preferences, excluded authors). | Settings altered without your knowledge. |
| S3 | Med | The app answers to any address. | Enables DNS-rebinding attacks. |
| S4 | Low | The desktop window adds an unprotected `/shutdown` address that probably does nothing now. | Dead code. |

## 9. Code, housekeeping, permissions (C, H)

| ID | Sev | Issue |
|---|---|---|
| C1 | Med | About 40 scripts in one folder, including retired ones (`import_lfbi_pilot.py`, `import_lfbi_files.py`, `import_sermon_notes.py`, `index_bible_study.py`, probably `search_bible_study.py`). |
| C2 | Med | The main app file is 1,100+ lines with page designs inside the code (blocks a good phone layout). |
| C3 | Med | Two programs open the desktop window; only one is packaged. |
| C4 | Med | Your personal folder path is written into several scripts and `source_folders.tsv`. |
| C5 | Low | Many steps are Mac-only (`open`, `osascript`, `textutil`, Pages, launchd, MLX); phone versions must not need them. |
| C6 | Low | Database changes are ad-hoc, not numbered upgrade steps. |
| C7 | Low | Saved passages are tied to file locations; moving a file orphans them. |
| H1 | Med | The repository is **public** and shows your computer user name, LFBI course and handout names, and the church list. |
| H2 | Med | No requirements list (no `requirements.txt`). |
| H3 | Low | No license file. |
| H4 | Low | The whole history is one entry; editor settings (`.idea/`) and the unused `sources.txt` are tracked. |
| H5 | Low | Nothing runs the tests automatically. |
| H6 | High, before sharing | LFBI, sermon and blog materials have their own terms. Personal use is fine; record permission for each source before anyone else gets access. |
| H7 | Low | The docs refer to an "audit report in the task workspace" that is not in the project. |

## Phone options (decision needed for P1)

1. **Private connection to your own Mac (recommended first).** A free service such as Tailscale lets your
   phone reach the app on your Mac, with nothing public and no copies elsewhere. Needs the Mac on and awake,
   a sign-in (P2), and a small change to let the app listen on that connection.
2. **Hosted copy on a cloud server.** Works when the Mac is off, but costs money, copies your material to
   someone else's computer (see H6), and needs a full sign-in system.
3. **A copy of the search database on the phone.** Works offline; the long-term goal for a stand-alone app, and the most work.

## Suggested order

1. Quick safety fixes (S1 to S3) and bring in a version-checked copy of the project (O9).
2. Updater reliability (O1 to O4), then one full LFBI course end to end (L1 to L3).
3. Transcription quality test with real sermons (T1, T2, T8), then re-transcribe the weakest.
4. Phone access (P1, P2, then R7, P4) and the reading experience (R1, R6, R9).
5. Search and reference improvements (B1 to B5, R2 to R4, R12).
6. Bible-first features (F1 to F8), then reMarkable (P6) and housekeeping.
