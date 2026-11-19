"""Bounded launchd intake; shares the manual updater's kernel lock.

Only this scheduler's state/logs live outside iCloud. No credentials are stored.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

BASE = Path.home() / 'Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid'
AUTOMATION = BASE / '98_Automation'
STATE = Path.home() / 'Library/Application Support/BibleStudyAid/intake'
LOGS = Path.home() / 'Library/Logs/BibleStudyAid/intake'
LOCK = Path.home() / 'Library/Caches/BibleStudyAid/update.flock'
POLICY = {'local': (3600, [900, 1800, 3600]),
          'acquire': (7200, [3600, 7200, 14400])}


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('w') as out:
        json.dump(value, out, indent=2)
        out.flush()
        os.fsync(out.fileno())
    tmp.replace(path)


def record_result(record, success, now):
    interval, retries = POLICY[record['lane']]
    failures = 0 if success else record.get('failures', 0) + 1
    record.update(status='ok' if success else 'needs_attention', failures=failures,
                  finished=now, next_due=now + (interval if success else retries[min(failures-1, len(retries)-1)]))
    if success:
        record['last_success'] = now


def stop_group(child):
    # Include grandchildren (downloaders/transcribers), even if the shell exited.
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    child.wait()


def run_command(command, log, lock_fd, timeout, env):
    print('START ' + json.dumps(command), file=log, flush=True)
    child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, env=env,
                             start_new_session=True, pass_fds=(lock_fd,))
    try:
        code = child.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        stop_group(child)
        code = 124
    except BaseException:
        stop_group(child)
        raise
    print(f'END exit={code}', file=log, flush=True)
    return code


def moodle_queue():
    sys.path.insert(0, str(AUTOMATION))
    from pipeline_support import excluded_resource
    courses = []
    for manifest in sorted((BASE / '02_LFBI').rglob('course_manifest_processed.json')):
        data = json.loads(manifest.read_text())
        resources = [r for r in data.get('queued_resources', []) if not excluded_resource(r)]
        if resources:
            courses.append({'manifest': str(manifest), 'pending': len(resources),
                            'download_queue': str(manifest.parent / 'download_queue.html'),
                            'resources': resources})
    atomic_json(STATE / 'moodle_pending.json', {
        'checked': time.time(), 'status': 'requires_authenticated_browser' if courses else 'no_tracked_pending_resources',
        'note': 'Tracked manifests only, not a complete enrollment inventory. Sign into Moodle in Safari and review teaching resources. No automatic login or quiz/grade acquisition.',
        'courses': courses})


def run_lane(lane, log, fd, env):
    if lane == 'acquire':
        if shutil.disk_usage(BASE).free < 20 * 1024**3:
            print('Acquisition paused: less than 20 GiB free on the library volume.', file=log, flush=True)
            return [75]
        return [run_command(['/bin/bash', str(AUTOMATION / 'update_bible_study_aid.sh'), 'backlog', '5', 'all'], log, fd, 7200, env)]
    results = []
    for script, timeout in [('import_lfbi_downloads.py', 600), ('import_commentaries.py', 1800),
                            ('build_scripture_index.py', 300), ('report_library_status.py', 300)]:
        results.append(run_command([sys.executable, '-B', str(AUTOMATION / script)], log, fd, timeout, env))
    try:
        moodle_queue()
    except Exception as exc:
        print(f'MOODLE QUEUE ERROR: {exc}', file=log, flush=True)
        results.append(1)
    return results


def interrupted(signum, frame):
    raise KeyboardInterrupt(f'signal {signum}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('lane', choices=POLICY)
    parser.add_argument('--force', action='store_true', help='Ignore due time, but never ignore locks')
    parser.add_argument('--status', action='store_true', help='Read state without running intake')
    args = parser.parse_args()
    path = STATE / (args.lane + '.json')
    if args.status:
        print(path.read_text() if path.exists() else 'No scheduled run yet.')
        return 0
    os.umask(0o077)
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Busy: manual or scheduled intake owns the lock; retry next calendar tick.')
            return 0
        if Path('/tmp/bible_study_aid_update.lock').exists():
            print('Legacy updater lock requires inspection; not removing it automatically.')
            return 1
        record = json.loads(path.read_text()) if path.exists() else {'lane': args.lane}
        # Apply the current policy even when an older, already-running runner
        # finishes after this file is upgraded and writes its old due time.
        if args.lane == 'acquire' and 'finished' in record and record.get('status') != 'running':
            interval, retries = POLICY['acquire']
            failures = record.get('failures', 0)
            delay = interval if failures == 0 else retries[min(failures-1, len(retries)-1)]
            record['next_due'] = record['finished'] + delay
            atomic_json(path, record)
        if args.lane == 'acquire' and record.get('status') == 'running':
            record['next_due'] = min(record.get('next_due', 0), record.get('started', 0) + 7200)
        if not args.force and time.time() < record.get('next_due', 0):
            return 0
        if not (BASE / '99_Index/bible_study.db').is_file():
            print('Library/database unavailable; retry next calendar tick.')
            return 1
        LOGS.mkdir(parents=True, exist_ok=True)
        for old in LOGS.glob('run-*.log'):
            if old.stat().st_mtime < time.time() - 30*86400:
                old.unlink()
        # launchd opens these only for startup/uncaught errors; bound their growth.
        for name in ('launch.out', 'launch.err'):
            target = LOGS / name
            if target.exists() and target.stat().st_size > 1024*1024:
                target.write_text('Previous startup output truncated at 1 MiB.\n')
        now = time.time()
        logfile = LOGS / f'run-{args.lane}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{os.getpid()}.log'
        # Persist recovery time BEFORE work; a crash cannot cause a tight retry loop.
        record.update(status='running', started=now, log=str(logfile),
                      next_due=now + (3600 if args.lane == 'local' else 7200))
        atomic_json(path, record)
        env = dict(os.environ, BIBLE_STUDY_LOCKED='1', BIBLE_STUDY_UNATTENDED='1',
                   BIBLE_STUDY_PYTHON=sys.executable, PYTHONUNBUFFERED='1', PYTHONDONTWRITEBYTECODE='1',
                   BIBLE_STUDY_TRANSCRIPTION_LIMIT='5', BIBLE_STUDY_TRANSCRIPTION_TIME_BUDGET_MINUTES='10',
                   PATH='/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin')
        with logfile.open('w') as log:
            try:
                results = run_lane(args.lane, log, lock.fileno(), env)
            except (Exception, KeyboardInterrupt) as exc:
                print(f'RUN ERROR: {exc}', file=log, flush=True)
                results = [1]
            record['exit_codes'] = results
            record_result(record, all(code == 0 for code in results), time.time())
            atomic_json(path, record)
        return 0 if record['status'] == 'ok' else 1


if __name__ == '__main__':
    raise SystemExit(main())
