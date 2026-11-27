# Bible Study Aid — Comprehensive Project Handoff

Updated November 26, 2026. Intended for Claude or another development agent.

**Status caveat:** This is a conversation-derived handoff, not a fresh audit of the repository, local files, database or installed application. Previously reported functionality must be verified against the current implementation. Do not assume proposed changes were implemented.

## 1. Project overview

Build a comprehensive, searchable, locally maintained Bible study environment combining personal study materials, LFBI coursework, sermon notes, reference works, podcasts, blogs, and selected external Christian writings with Bible study tools familiar from e-Sword. It should become the central environment for Bible study, sermon preparation, research, and retrieval of previously studied material, not merely a document store.

### Guiding principles

- King James Version exclusively for Bible text.
- Scripture is the authority against which outside writings are evaluated.
- Do not assign doctrinal rankings, theological tiers, or classifications to authors. The user will evaluate their writings against Scripture.
- Preserve original files and index them in place; avoid unnecessary duplication.
- Preserve verifiable source attribution and provenance.
- Prefer automation, repeatable processes, reliability, data integrity, maintainability and thorough testing.
- Prioritize a comfortable reading experience and efficient sermon preparation.
- Retain compatibility with macOS, Safari and iCloud; do not require Chrome.
- Reuse existing software and resources where practical rather than reinventing functionality.
- The user values quality over speed and expects the development agent to make and test actual changes wherever possible rather than repeatedly assigning manual edits.

## 2. Repository and technical environment

- GitHub: https://github.com/gwfrench164-collab/bible-study-aid-automation.git (main branch historically used)
- Local project directory: `/Users/george/Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid`
- Database relative to project: `99_Index/bible_study.db`
- Source configuration: `source_folders.tsv`

| Component       | Technology                                                  |
|-----------------|-------------------------------------------------------------|
| Language        | Python                                                      |
| Database        | SQLite                                                      |
| Application     | Flask                                                       |
| Word extraction | python-docx                                                 |
| PDF extraction  | PyMuPDF                                                     |
| Transcripts     | Python ingestion pipeline; captions first, Whisper fallback |
| Packaging       | macOS .app bundle                                           |
| Browser         | Safari                                                      |
| Synchronization | iCloud Drive                                                |
| Version control | Git/GitHub                                                  |

Primary computer: 2023 15-inch MacBook Air. Older 2015 iMac running Monterey 12.7.6 also available. User also uses an iPhone.

### Source categories

LFBI coursework, Sermon Notes, Reference, `05_Podcasts`, `06_Blogs`. Previously identified original paths:

- `/Users/george/Documents/Spiritual/Church/Sermon Notes`
- `/Users/george/Documents/Spiritual/Reference`

Index original locations using source configuration rather than copying everything into the project.

## 3. Database and indexing

Reported working: configured directory indexing, PDF and DOCX extraction, plain-text transcript indexing, content search, incremental indexing skipping unchanged files, original source links, Flask database querying. Tests returned LFBI results involving Simon and Saul of Tarsus.

Outstanding: Apple Pages extraction (most sermon notes are .pages, with some DOCX/PDF); verify incremental handling of changed files and new sources, especially Moodle downloads. Audit duplicate records, stale/missing references, document identity, source paths, changed-file detection, extraction failure recovery, interrupted runs, logging, search quality and performance. A comprehensive review of everything used to update the database was requested October 17, 2026; completion is not established.

## 4. LFBI coursework ingestion — major unfinished workstream

Capture course videos, transcripts, PDFs, handouts, slides and other substantive Moodle instructional materials. Skip quizzes, grades and administrative content.

Intended flow: Moodle course/week/lesson pages → page parser, resource collector, transcript collector and duplicate checker → extraction and metadata → incremental SQLite indexing → search and reading interface.

### Reported accomplishments

- Parsing Safari .webarchive files, extracting and cleaning week information.
- Extracting embedded YouTube links.
- Generating/retrieving and indexing some lesson transcripts.
- Extracting Moodle resource references and creating a download queue.
- Beginning duplicate detection and integration with the project.
- Acts course used for testing; backlog updater ran and found Week 1–2 material, with later-week search results also reported.

### Unfinished items

**Authenticated downloads:** Moodle uses Microsoft 365 Connect authentication. Investigate authorized Safari session/cookie-based downloads of handouts, slides, PDFs and other protected resources. No end-to-end success established. Provide `download_queue.html` fallback for resources that require manual retrieval. Do not expose credentials or bypass access controls.

**Duplicate checker:** Generic names such as Handout or Slides were overmatched. Distinguish course, lesson, week, specific title and content identity where available. Examples: Acts 1, Appendix 3, Week 5. Final correction unverified. Account for resources already downloaded by the user.

**Multi-course processing:** Verify one entire course end-to-end before expanding to multiple courses. Do not assume all Acts material is available; an Acts 15 retrieval request exposed uncertainty about coverage.

**Main updater integration:** Make LFBI intake part of the normal update pipeline, not a separate set of commands the user must remember.

### User workflow

User navigates Moodle week by week in Safari, views/saves pages and prints handouts. Safari Save As options previously discussed include page source, webarchive and PNG. Minimize manual steps.

## 5. Transcripts

Acquisition priority: existing captions/transcripts first, Whisper fallback. Preserve lesson, course, video and source associations; index transcripts for search.

Original reader displayed massive single-spaced text. Rendering TXT as HTML reportedly improved readability. Full integrated transcript reader requested November 2026; implementation not verified.

Desired: paragraph formatting, comfortable spacing/margins, adjustable text size, long-document navigation, search-term highlighting, clear provenance, links to associated sermon/lesson and consistent application integration. Avoid a separate unrelated utility.

## 6. Bible interface and e-Sword-inspired features

Reference: e-Sword X macOS version 9.6 (44); user also uses e-Sword on iPhone. Reproduce the useful workflow rather than every feature.

| Feature                | Expected behavior                                       |
|------------------------|---------------------------------------------------------|
| Navigation             | Book, chapter, verse selection                          |
| Bible                  | KJV exclusively                                         |
| Search                 | Words and exact phrases                                 |
| Copy                   | Selected Scripture into other applications              |
| Strong’s               | Hebrew/Greek numbers and definitions                    |
| Translation renderings | Other KJV renderings of the same original-language word |
| Occurrences            | Other passages using that Hebrew/Greek word             |
| Cross-references       | Treasury of Scripture Knowledge (TSK)                   |
| Dictionaries/reference | Webster’s 1828 and Nave’s Topical Bible                 |
| Library integration    | Link verses/topics to personal study materials          |

### Interface and study workflow

Most of the time only the Bible is visible. TSK is a separate main-area tab, not simultaneously visible with Bible; dictionaries open in a side window when needed. Avoid crowded permanent panels. User reads and rereads, compares Scripture with Scripture, investigates words and handwrites passages/notes, often returning to a printed Bible. Bright screens strain the user’s eyes; favor readable typography and a clean interface. User dislikes ASCII layout diagrams and prefers actual visual examples.

Example: Acts 15 should provide access to KJV text, Strong’s, TSK, relevant LFBI lessons, sermon notes, reference documents and external writings without distracting from Scripture.

Determine legal and technical sources for KJV, Strong’s, TSK, Webster’s 1828 and Nave’s. Evaluate a Flask-native interface versus integration of existing Bible software components. User requested a hybrid approach after discussing NotebookLM and existing alternatives; avoid unnecessary reinvention. Implementation not confirmed.

## 7. External Christian writings

Initial requested authors (not exhaustive): Oliver B. Greene, J. Vernon McGee, E. M. Bounds, George Müller, Charles H. Spurgeon, H. A. Ironside, C. T. Studd, J. Frank Norris, Peter S. Ruckman, John Phillips, Warren Wiersbe, Clarence Larkin, C. I. Scofield, John Nelson Darby, George Whitefield, Hudson Taylor, Adoniram Judson, William Carey, David Brainerd.

An earlier tiered conservative-library proposal was superseded by the user’s explicit rejection of doctrinal classification. Use only practical metadata: author, title, publication information, source URL/original document, copyright/reuse status, document type, relevant passages/topics, duplicate identifiers. No doctrinal tiers or rankings.

Prioritize legitimate accessible sources. Public-domain material may be appropriate for local indexing; copyrighted material requires appropriate permissions and access restrictions. Public visibility does not establish permission to permanently copy. User authorized beginning implementation, but acquisition pipeline and actual collection are unverified.

## 8. Application usability

Reported fixes: packaged macOS app opens its own window; closing window stops app; Open in Finder and Open source repaired; podcasts, sermon notes and commentaries open; TXT transcripts rendered as HTML.

Outstanding: search results difficult to sort and read. Improve document titles, source types, excerpts, highlighted search terms (including preview), context, filters and sorting by meaningful metadata. Provide consistent reading views for transcripts, PDF previews, notes and references. Make navigation between results, sources, Bible passages and related study materials straightforward. Verify packaged app includes latest changes.

## 9. Automated intake and updates — current priority

November 19, 2026: user raised the problem of having to remember to run the updater manually. Significant backlog remains.

Desired: detect new/modified local files; automatically run incremental updates; collect eligible LFBI resources and transcripts; avoid repeat work; log failures, retry recoverable errors and report outcomes; retain manual Update Now option.

Recommended but not approved/verified implementation: macOS launchd background task, periodic schedule and potentially filesystem triggers. Updater should not require Flask app to be open. Account for iCloud synchronization, Mac sleep, authenticated Moodle sessions, and overlapping runs. A previous updater encountered a lock condition; investigate before scheduling. Implement robust locking, recovery and clear logs; prevent duplicate records, database corruption and simultaneous updater processes. Automatic scheduling not confirmed implemented.

## 10. Other requirements

- Quotations must be genuinely traceable to reliable sources, preferably primary sources, with bibliographic information sufficient for citation. Do not present unverified popular attributions as established quotations.
- Preserve original source files intact; database is an index and retrieval system.
- Unified search across supported collections with optional scope restrictions.
- Test, document, log and maintain predictable behavior. Avoid unnecessary standalone scripts where functionality belongs in the existing pipeline.
- Keep legally obtained local material usable offline. Network required for external acquisition and authenticated course downloads.

### reMarkable tablet exploration (November 25, 2026)

User likes the reMarkable display and simplicity, would prefer it to an iPad, and wants to search Scripture from the tablet. Wife owns one; user has considered purchasing one. Explore feasibility of integrating Bible Study Aid with reMarkable, especially actual interactive Scripture lookup/search rather than only exporting static documents. Exact model, connectivity, supported integration methods and architecture remain undetermined. This is exploratory, not an approved implementation or a verified capability. Preserve existing Mac workflow; evaluate limitations before recommending hardware or committing to an approach.

## 11. Consolidated status

| Workstream               | Reported status     | Next requirement             |
|--------------------------|---------------------|------------------------------|
| SQLite database          | Working             | Integrity and coverage audit |
| Incremental indexer      | Working in testing  | Reliability review           |
| PDF/DOCX extraction      | Working             | Regression tests             |
| Apple Pages extraction   | Uncertain           | Verify coverage              |
| Flask search application | Working             | Usability improvements       |
| macOS packaging          | Working             | Verify current build         |
| Source opening           | Previously repaired | Regression tests             |
| Moodle parsing           | Partially working   | End-to-end verification      |
| YouTube link extraction  | Working in testing  | Course-wide validation       |
| Transcript ingestion     | Partially working   | Complete coverage            |
| Moodle downloads         | Incomplete          | Authenticated downloads      |
| Duplicate checker        | Needs correction    | Context-aware matching       |
| Transcript reader        | Basic improvement   | Complete integration         |
| External author library  | Planned             | Acquisition                  |
| e-Sword-like interface   | Planned             | Architecture/implementation  |
| Automatic updater        | Planned             | Background scheduling        |
| Search usability         | Needs improvement   | Interface redesign           |
| reMarkable integration   | Exploratory         | Feasibility assessment       |

## 12. Recommended development priorities

1.  **Audit repository and database:** inspect actual code, configuration, logs, schema, source material, working tree and packaged app. Establish implemented, partial, missing and broken features. Do not assume previous plans were executed.
2.  **Stabilize and automate updater:** correct duplicate detection, validate incremental indexing and Pages coverage, implement locking/recovery and appropriate background scheduling.
3.  **Complete LFBI ingestion:** authenticated resource downloads, transcript acquisition and one full course end-to-end before expansion.
4.  **Improve reading/search:** integrated transcript reader, result presentation, highlighting, filtering, consistent document views.
5.  **Expand study environment:** KJV interface and study tools, Scripture-linked personal library, external-source acquisition. Explore hybrid reuse and reMarkable feasibility.

Phases may overlap where practical, particularly interface design and source research while ingestion runs. This ordering is a recommendation, not a user-mandated schedule.

## 13. Instructions for Claude or the next development agent

You are continuing the Bible Study Aid project. Use the repository and paths in section 2. Respect the requirements in section 1 and throughout this handoff. Begin by inspecting the actual repository and local project state. Review indexing pipeline, update scripts, database schema, source configuration, Moodle ingestion, duplicate checker, logs, Flask application and macOS packaging. Produce a concise implementation audit and prioritized action plan, then begin making the highest-value improvements within your available permissions.

Do not assume a feature is complete merely because it was discussed. Do not unnecessarily replace functioning code. Preserve existing work, use version control and test changes. Make actual code changes where possible. If local files or credentials are unavailable, clearly identify the blocker rather than claiming completion.

Current priority: make intake and database updates substantially more automatic so the user does not have to remember to run the updater. Long-term goal: unified Bible study environment with the familiar e-Sword workflow and searchable personal library.

## 14. Questions to resolve in the audit

- How much LFBI material is actually indexed? Which resources succeeded, failed or remain queued?
- Is the duplicate checker correction in current code?
- Which updater scripts are active and how are they invoked?
- Is background scheduling already present?
- Does Apple Pages extraction work for the sermon-note collection?
- Which transcript reader improvements are present?
- Have external author materials already been downloaded/indexed?
- Has Bible interface implementation begun?
- Are GitHub, local iCloud files and packaged application synchronized to the same version?

## Final assessment

The project has progressed beyond concept: database, indexer, functional application, document retrieval and parts of LFBI ingestion were reported working. The largest remaining obstacle is incomplete and insufficiently automated acquisition and maintenance of the underlying library. Audit and stabilize existing code, complete LFBI intake and automate updates so subsequent Bible interface and reference-library work rests on a trustworthy collection.

This handoff preserves the substantive content of the prior summary and adds the recent reMarkable discussion. It is not a live technical audit; implementation status and recommendations require verification.
