# Bible Study Aid: issues list

Written November 21, 2026 after a full review of the project.
**Status** is *Fixed* (done in the first batch of changes), *Partly* or *Open*.
Severity: **High** = fix before anything else, **Med** = important, **Low** = tidy-up.

Your stated first priority is reliably searching the supplemental material (sermons, podcasts, LFBI,
blogs, commentaries) from both your computer and your phone. Group **P** is that priority.

---

## S. Safety of the local app

| ID | Sev | Issue | Why it matters | Status |
|---|---|---|---|---|
| S1 | High | The "Open Source" and "Show in Finder" links could open **any** file or program on the Mac, and a link on any web page could trigger them while the app was running. | A booby-trapped web page could launch programs on your Mac. | **Fixed**: only files in your library index can be opened, and requests from other sites are refused. |
| S2 | High | Other web pages could silently send changes to the app (saved notes, source preferences, excluded authors). | Your notes and settings could be altered without you knowing. | **Fixed**: changes must come from the app's own pages. |
| S3 | Med | The app answered to any address, not just this computer. | A known trick (DNS rebinding) uses this to reach local apps. | **Fixed**: only this computer is accepted; extra addresses can be allowed on purpose (needed for phone access). |
| S4 | Low | The desktop window program adds an unprotected `/shutdown` address that probably does nothing on current software. | Dead code that looks like a control. | Open |
| S5 | Med | There is no sign-in. | Fine on one computer; **not fine** the moment the app can be reached from a phone or the internet. Anyone who can reach it could read your library and notes. | Open (do alongside P1) |

## P. Searching from your phone (first priority)

| ID | Sev | Issue | Why it matters | Status |
|---|---|---|---|---|
| P1 | High | The app only runs on the Mac and only listens to that Mac. | No phone access at all today. **Needs your decision**, see "Phone options" below. | Open |
| P2 | Med | "Open Source" and "Show in Finder" use Mac-only commands, and only text/Markdown files show in the app's reader. PDFs, Word, PowerPoint and Pages files open in Mac programs. | On a phone these buttons would do nothing; PDF and Word results would be unreadable. The app needs to serve those files itself. | Open |
| P3 | Med | The Mac must be on and awake, and iCloud may have "optimized" (removed) local copies of files. | Phone searches would fail or show missing files at random times. | Open |
| P4 | Med | The page layout adapts to narrow screens but has never been checked on a real phone. | Likely small annoyances (buttons, long titles, reader controls). | Open |
| P5 | Med | Audio is kept, but results cannot play it or jump to the spot in the recording; timestamps from captions are thrown away. | For sermons and podcasts, "play from here" is the most useful phone feature. | Open |

## Q. Search quality and speed

| ID | Sev | Issue | Why it matters | Status |
|---|---|---|---|---|
| Q1 | High | Every matching passage is pulled out of the database and scored one at a time, with no cap. | A common word ("God", "love") will get slower as the library grows. Measured on made-up test libraries: a broad three-word search took about 2.5 seconds at 20,000 passages and about 12 seconds at 100,000. Real text is less repetitive, so real searches should be faster, but the time still grows in step with the library. | **Partly**: the scoring work was trimmed (about 25-30% faster, results proven identical on thousands of test cases). The remaining cost needs a decision: scoring only the best few thousand matches would make searches fast at any size, but the result counts shown in the page would become approximate. |
| Q2 | Med | Search understands word forms (love/loved/loving) but highlighting does not. | Matches look like they have nothing highlighted. | Open |
| Q3 | Med | Topic searches ("7 feasts of Israel" etc.) work for only five topics typed into the code. | A real topical index (Nave's) would cover every topic. | Open |
| Q4 | Med | Ranking uses hand-tuned bonus numbers and there is no way to tell whether a change made searches better or worse. | Easy to break good results by accident. Needs a small list of your real searches with the results you expect. | Open |
| Q5 | Low | No exact-phrase or wildcard syntax, no spelling suggestions, and no Strong's-number search. | Features you use in e-Sword. | Open |
| Q6 | Low | Your preferences (excluded authors Calvin/Origen/Augustine, the "52 Weeks of Pursuit" collection) are built into the code as defaults. | Fine for you; should be plain settings before anyone else uses it. | Open |

## R. Finding Bible references inside documents

| ID | Sev | Issue | Why it matters | Status |
|---|---|---|---|---|
| R1 | High | Indexing only recognized full book names. "Rom. 8:28", "Ps 23", "Psalm 23" (singular), and ranges written with a long dash were missed. | Searching by passage missed material that cites it in the most common ways. | **Fixed**: one shared finder (`bible_refs.py`). Existing material is refreshed automatically by the next update (see notes). |
| R2 | Med | Everyday words became false references ("the numbers 3 and 4"), impossible references were stored ("John 99"), and "Jude 3" (verse 3) was misread. | Noise in results and in the Scripture index. | **Fixed** |
| R3 | Med | The Scripture index silently left out Song of Solomon (and any multi-word book name). | Missing section of the index. | **Fixed** |
| R4 | Med | Not recognized yet: ranges across chapters ("8:28–9:3"), lists ("3:16, 18"), "verse 28", "vv. 3–4", "I John". | More missed citations. | Open |
| R5 | Med | References are stored as text and matched by text patterns. | Slow, and it blocks easy links between your KJV text, cross-references and commentary. Should become numbers (e.g. verse 43003016 = John 3:16). | Open |

## D. How the information is stored

| ID | Sev | Issue | Why it matters | Status |
|---|---|---|---|---|
| D1 | Med | A document's title is just its file name. There is no speaker, series, date or web address. | Can't sort sermons by date or group them by series. | Open |
| D2 | Med | Saved passages are tied to file locations. | Moving or renaming a file can orphan a saved passage. Permanent IDs are on your own roadmap. | Open |
| D3 | Low | Database changes are made by ad-hoc commands rather than numbered upgrade steps. | Risky as the app grows and ships to other devices. | Open |
| D4 | Low | Duplicate content (same lecture in several places) is only hidden in the display, not in the index. | Inflated counts and slower searches. | Open |

## O. The automatic update pipeline

| ID | Sev | Issue | Why it matters | Status |
|---|---|---|---|---|
| O1 | Med | The update script points to `/usr/local/bin/python3.14`. | Breaks if Python moves or upgrades (it can be overridden with `BIBLE_STUDY_PYTHON`). | Open |
| O2 | Med | Failures are logged, but there is no plain-language "what failed and why" page. The last log recorded 11 failed stages. | Problems stay buried in log files. | Open |
| O3 | Med | Pages documents are skipped by the automatic runs and only refreshed by manual runs. | Edited Pages documents go stale in search until a manual update. | Open |
| O4 | Low | About 30 places catch every error and carry on quietly. | Some real problems may never be reported. | Open |
| O5 | Low | Files that disappear are never removed from the index (a deliberate safety choice). | Deleted or renamed material still shows up in results. Needs an explicit "clean up" tool. | Open |
| O6 | Low | Two overlapping source lists (`sources.txt` and `podcast_sources.tsv`) disagreed. | Confusing; one was out of date. | **Fixed**: the unused `sources.txt` was removed. |
| O7 | Low | Generated reports in `web_discovery/` (with your local file paths) are saved into the project history. | Clutter and personal details in history. | Open |
| O8 | Med | Moodle (Microsoft 365 sign-in) downloads using an exported `cookies.txt` have never been shown to work end to end on the real course; the manual `download_queue.html` fallback exists. | LFBI handouts and slides may be missing from the library. Verify one full course (Acts) before adding others. | Open |
| O9 | Med | The duplicate checker was corrected in code but has not been run against the real Moodle files. | Wrong matches could hide real handouts, or let repeats in. | Open |

## C. Code organization

| ID | Sev | Issue | Why it matters | Status |
|---|---|---|---|---|
| C1 | Med | The list of Bible books and abbreviations was copied into four files. | A fix in one place missed the others. | Partly: three files now share `bible_refs.py`. Old copies remain in `search_bible_study.py` and `index_bible_study.py`. |
| C2 | Med | About 40 scripts sit in one folder, including retired ones (`import_lfbi_pilot.py`, `import_lfbi_files.py`, `import_sermon_notes.py`, `index_bible_study.py`, and probably `search_bible_study.py`). | Hard to tell what matters. Moving them to a `legacy` folder or deleting them is safe, because the project history keeps them. | Open |
| C3 | Med | The main app file is 1,100+ lines with page designs written inside the code. | Hard to change the look, especially for a phone layout. | Open |
| C4 | Med | Two different programs open the desktop window (`bible_study_desktop_app.py` and the one inside the search app). | Confusing; only one is packaged. Pick one. | Open |
| C5 | Med | Your personal folder path was written into several scripts. | The project couldn't run on any other computer or location. | Partly: fixed in three scripts. Still in `source_folders.tsv`, the retired scripts and `search_bible_study.py`. |
| C6 | Low | Many steps use Mac-only commands (`open`, `osascript`, `textutil`, Pages, launchd, MLX). | Fine for the pipeline on your Mac; must not be needed by phone or Windows versions. | Open |

## H. Project housekeeping

| ID | Sev | Issue | Why it matters | Status |
|---|---|---|---|---|
| H1 | Low | Editor settings (`.idea/`) were saved in the project even though they were meant to be ignored. | Clutter and tool-specific data. | **Fixed** |
| H2 | Med | No list of required software. | Rebuilding on a new computer would be guesswork. | Partly: `requirements.txt` added without exact versions; record versions from your Mac. |
| H3 | Low | No license file. | Others have no stated permission, and you have not chosen your terms. | Open |
| H4 | Low | The whole history is one entry, and generated files are mixed with your own work. | Can't see or undo individual changes. | Open |
| H5 | Med | The repository is **public** and shows your computer user name, LFBI course and handout names, and the church list. | Personal details visible to anyone. Consider making it private. | Open (your choice) |
| H6 | Low | Nothing runs the tests automatically when changes are made. | Mistakes can slip in unnoticed. The tests run fine on a normal Linux computer. | Open |

## L. Permissions and privacy

| ID | Sev | Issue | Why it matters | Status |
|---|---|---|---|---|
| L1 | High, before sharing | LFBI course materials, church sermons, scraped blogs and commentaries each have their own terms. | Personal use is one thing; letting other people search or download them is another. Record permission for each source before anyone else gets access, or before any public app. A private connection to your own Mac stays personal use. | Open |
| L2 | Info | The project correctly avoids storing Moodle passwords or automating sign-in. | Keep it that way. | OK |

## T. Tests and documents

| ID | Sev | Issue | Why it matters | Status |
|---|---|---|---|---|
| T1 | Med | `AUTOMATIC_INTAKE.md` says automated tests cover locks, retries, timeouts and incremental updates. Those tests are not in the project. | Claimed protection that can't be checked or re-run. | Open (bring the tests over from the other workspace) |
| T2 | Med | Coverage was 13 tests, now 38, but nothing tests a whole small library from start to finish. | Part-by-part tests can pass while the whole thing breaks. | Partly |
| T3 | Low | The documents refer to an "audit report in the task workspace" that is not in the project. | Information that exists only elsewhere. | Open |

## B. Future: the Bible-first (e-Sword-style) part

You use only the KJV, with word and phrase searches, Strong's numbers and definitions, the TSK
cross-references, Nave's Topical Bible and Webster's 1828 Dictionary. All of these are old enough to be
public domain in some form, but file formats and exact editions differ, and e-Sword's own module files may
have their own terms. Check each source before copying it in.

| ID | What | Notes |
|---|---|---|
| B1 | KJV text and a chapter-by-chapter reader | The foundation; every other item links to verses. Needs R5 (numeric verse IDs). |
| B2 | KJV word and phrase search, with Strong's tagging | Strong's-tagged KJV data exists in open collections. Check the license of any copy. |
| B3 | Strong's numbers and definitions (Hebrew and Greek) | Click a word to see its number and meaning. |
| B4 | TSK cross-references | Appears beside each verse. |
| B5 | Nave's Topical Bible | Also replaces the hard-coded topics in Q3. |
| B6 | Webster's 1828 Dictionary | Look up a word from anywhere in the app. |
| B7 | Link everything together | A verse shows KJV text, cross-references, your sermon notes, LFBI lessons and podcast passages in one place. |
| B8 | External authors library (Spurgeon, McGee, Bounds, etc.) | Record only practical details: author, title, source, copyright status. No doctrinal rankings or tiers. Public-domain text only unless permission is obtained. Not started. |
| B9 | Traceable quotations | Any quotation shown must link to a reliable, preferably primary, source with citation details. Never present unverified popular attributions as established. |
| B10 | reMarkable tablet (exploratory) | You want to look up and search Scripture on a reMarkable. Whether it can run an interactive search is unverified; static exported pages are the likely fallback. Settle the phone approach (P1) first, then check the tablet's actual abilities before buying anything. |

---

## Phone options (decision needed for P1)

1. **Private connection to your own Mac (recommended first step).** A free private-network service such as
   Tailscale lets your phone reach the app running on your Mac from anywhere, with nothing public and no
   copies of your material elsewhere. Needs: the Mac on and awake, a sign-in (S5), and a small change to let
   the app listen on that connection. Fastest route, lowest legal risk.
2. **A hosted copy on a cloud server.** Works when the Mac is off, but costs money, copies all material to
   someone else's computer (see L1), and needs a complete sign-in system.
3. **A copy of the search database stored on the phone.** Works offline and is the long-term goal for a
   stand-alone phone app. It's the most work, so it comes after the Bible part exists.

## Suggested order

1. Apply the first batch (done here), then run an update so existing material gets the new reference finder.
2. Decide on P1, then S5, P2, P4.
3. Q1 (speed), R4 and R5, then D1 and P5.
4. Tidy: C2, C4, C5, H2, H3, H5, T1.
5. Bible-first features B1 to B7, once supplemental search is reliable on both devices.
