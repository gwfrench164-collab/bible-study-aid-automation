"""Rebuild only derived reference rows from stored text, under the updater lock."""
from contextlib import closing
from pathlib import Path
import argparse, fcntl, sqlite3
from library_settings import INDEX_PATH
from database_backup import ensure_backup
from scripture_references import extract_references


def rebuild(conn):
    count=0
    with conn:
        conn.execute('DELETE FROM chunk_refs')
        for key, text in conn.execute('SELECT id,content FROM chunks'):
            refs=extract_references(text)
            conn.executemany('INSERT INTO chunk_refs(chunk_id,scripture_ref) VALUES(?,?)',[(key,ref) for ref in refs])
            count += len(refs)
    return count

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    if not args.apply:
        parser.exit(message='Use --apply to rebuild derived references after a verified backup. Original texts are unchanged.\n')
    lock=Path.home()/'Library/Caches/BibleStudyAid/update.flock'
    lock.parent.mkdir(parents=True,exist_ok=True)
    with lock.open('a+') as handle:
        try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:parser.exit(1,'Updater is active; try again after it finishes.\n')
        print('Backup:',ensure_backup(),flush=True)
        with closing(sqlite3.connect(INDEX_PATH)) as conn:
            conn.execute('PRAGMA busy_timeout=30000')
            print('Reference rows rebuilt:',rebuild(conn),flush=True)
