"""Hold an advisory lock across the entire updater; no stale PID deletion."""
import fcntl
import os
from pathlib import Path
import subprocess
import sys

def main():
    # Compatibility with an old updater still running during rollout.
    if Path("/tmp/bible_study_aid_update.lock").exists():
        print("Legacy updater lock exists; verify that run before retrying.", flush=True)
        return 1
    path = Path.home() / "Library/Caches/BibleStudyAid/update.flock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Bible Study Aid updater is already running.", flush=True)
            return 1
        env = dict(os.environ, BIBLE_STUDY_LOCKED="1", PYTHONUNBUFFERED="1")
        # Child inherits the descriptor, retaining the lock if this parent dies.
        return subprocess.call(["/bin/bash", *sys.argv[1:]], env=env, pass_fds=(lock.fileno(),))

if __name__ == "__main__":
    raise SystemExit(main())
