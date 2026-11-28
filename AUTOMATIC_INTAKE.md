# Automatic Bible Study Aid intake

## Audit — November 19, 2026

Live repository: `~/Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid/98_Automation`.
The active updater is `update_bible_study_aid.sh`, not the legacy index scripts.
It already has a kernel lock in `~/Library/Caches/BibleStudyAid/update.flock`,
resumable download archives, capped downloader retries, transcript reuse,
per-stage error reporting, and safe incremental document replacement.
`import_commentaries.py` skips unchanged size/mtime entries and hashes changed
files before extraction. Failed extraction retains the previous searchable text.
Missing files are deliberately not pruned, because iCloud roots can disappear.
Scripture references are derived from stored chunks; the report is written only
when its content changes. These behaviors are retained.

The latest existing updater log ended with 11 failed stages, including an empty
Greater Hope transcript. Scheduling does not repair upstream HTTP restrictions
or corrupt source material, and those failures must remain visible.
The existing 09:15 catalog-discovery LaunchAgent remains installed. Its catalog
lock already serializes catalog refreshes, and its metadata/download discovery
is independent of the main database updater. No enrollment-wide Moodle inventory
is implied by the currently tracked course manifests.

## Schedule and limits

Two per-user launchd jobs check due state every 15 minutes, staggered by five
minutes. Local intake is due hourly. Public acquisition is due every two hours
from completion, initially at installation. RunAtLoad catches up at login;
calendar triggers catch up after sleep. The Mac must be on and the user logged
in; these jobs do not wake a powered-off Mac. Due timestamps survive restarts,
so missed time causes one catch-up run, not many accumulated runs.

- Local: file completed Moodle downloads, incrementally index source folders,
  build scripture index, write coverage, and refresh `moodle_pending.json`.
- Acquisition: existing updater in `backlog 5 all` mode; at most five new media
  items per source per attempt, five transcriptions, and a 10-minute transcription
  budget checked by the existing batch script. A recording can exceed that soft
  budget. The entire acquisition attempt has a two-hour hard timeout.
- Local stage timeouts: 10/30/5/5 minutes respectively. Later stages still run
  after earlier failures. Existing good index entries remain available.
- Failure delays: local 15 minutes, then 30, then 60; acquisition one hour,
  then two hours, then four hours for persistent errors. Due work runs at the next calendar tick.
  Existing source archives and fingerprints prevent reprocessing successes,
  although a retry can acquire another batch of new items per source. This is an aggregate
  retry of the updater, not a per-source retry queue.
- Both jobs share the manual updater lock. Busy jobs leave due state unchanged
  and try on a later tick. Long acquisition can delay local intake by up to its
  timeout. The runner terminates its child process group on timeout/shutdown.
  The inherited lock stays held by the updater if the scheduler crashes.
- Unattended runs suppress notifications and defer changed/new `.pages` files
  to manual runs, preserving their old index entries. No GUI apps are launched
  for Pages extraction in the background.

Before each acquisition batch, the scheduler checks for at least 20 GiB free on
the library volume. A low-space pause is logged and retried with backoff.
Already-running batches finish under their original limits; the next scheduler
invocation applies the new due-time policy, including to old completion state.

## Moodle acquisition

No Moodle password, cookies, browser automation, or authenticated media fetching
is added to launchd. Sign in through Safari, review each queued teaching resource,
and download it using the course download queues. The existing local importer
then files high-confidence matches without removing Downloads originals. Actual
quizzes, assignments, grades, and explicit assessment resources remain excluded
by the existing policy. Reviewed teaching material follows existing policy.

`~/Library/Application Support/BibleStudyAid/intake/moodle_pending.json` lists
pending resources and per-course queue paths from tracked manifests only. A queue
path may need regeneration if an old course export lacks `download_queue.html`.
Permission failures accessing Downloads/iCloud/Documents will be in the logs;
macOS permission approval may be necessary in System Settings for the background
Python process. A manually successful run alone does not prove launchd access.

## Status and logs

Runtime and durable state: `~/Library/Application Support/BibleStudyAid/intake/`.
Read `local.json` and `acquire.json` for status, exit codes, latest log path,
last success, failure count, and next due time (Unix timestamps).
`running` with no active job indicates an interrupted run; retry occurs after the
persisted recovery time. Invalid state is not silently reset: inspect it and
restore a valid backup or rename it while the job is stopped.

Per-run logs: `~/Library/Logs/BibleStudyAid/intake/run-*.log` (30-day retention).
Startup logs: `launch.out` / `launch.err` (truncated at 1 MiB by the next run).
The existing updater also retains its normal `98_Automation/logs/update_*.log`
files without deleting historical logs. Errors are recorded, not hidden behind
success notifications. No new messaging/reminder service is installed.

Status command:
```sh
/usr/local/bin/python3.14 "$HOME/Library/Application Support/BibleStudyAid/intake/scheduled_intake.py" local --status
launchctl print "gui/$(id -u)/org.biblestudyaid.intake-local"
```
Use `acquire` / `intake-acquire` for acquisition. A controlled manual catch-up can
use `local --force` or `acquire --force`; the shared lock still applies.

## Pause and rollback

```sh
launchctl bootout "gui/$(id -u)/org.biblestudyaid.intake-local"
launchctl bootout "gui/$(id -u)/org.biblestudyaid.intake-acquire"
```
Move the two `org.biblestudyaid.intake-*.plist` files out of `~/Library/LaunchAgents`
to keep them disabled across login. Do not remove the catalog-discovery job.
Restore the two original scripts from the backup path in `installation.json`
only after verifying neither updater owns the shared lock. The runtime, logs,
and new scheduler can be retained for diagnosis. No source documents or database
restore is needed to disable scheduling. Manual updater arguments are unchanged.

## Validation

Automated tests cover incremental no-op and touched-file handling, transactional
replacement and failed extraction retention, FTS/foreign-key consistency, lock
contention/crash recovery, retry backoff/reset, process-tree timeout cleanup,
continuation after a failed local stage, due-time skipping, and unattended Pages.
Installation checks live scripts against their audited originals before replacing
anything, saves backups, and validates generated plist files. Live launchd results
are recorded separately in the implementation workspace verification report.

Apple reference: https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html

## Runtime and recovery follow-up (November 27, 2026)

The updater now sources `select_python.sh`, checks intake imports before doing work and prefers the project's `.venv`. An explicit `BIBLE_STUDY_PYTHON` must pass the same preflight. Run `bash update_bible_study_aid.sh --check-runtime` to inspect it without updating the library. Install intake dependencies using `requirements-intake.txt`; speech recognition remains a separate heavier runtime and can be selected with `BIBLE_STUDY_TRANSCRIPTION_PYTHON`.

Each download source is bounded by `BIBLE_STUDY_SOURCE_TIMEOUT` (90 seconds by default). A timeout remains a reported failure but does not indefinitely prevent later sources and indexing. Downloads can be resumed using the existing archives. Longer sources can need a larger explicit budget. An entire acquisition lane still has its overall time limit.

Empty source files are preserved and recorded in `99_Index/index_pending.json`; they are not indexed as blank content, deleted or represented as successfully recovered. Scheduled local intake reports `ok_with_pending` when available files processed successfully but recovery remains. Actual extraction failures continue in `index_errors.json` and cause failure. The Update status page shows this distinction.

Successful updater transcription now preserves audio using `--keep-audio`. Storage retention needs deliberate management rather than automatic deletion of originals.
