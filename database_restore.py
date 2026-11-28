"""Restore and verify a backup into a NEW database; never overwrite a live index."""
import argparse
from contextlib import closing
from pathlib import Path
import os, sqlite3, tempfile, shutil


def validate_database(db):
    if db.execute('PRAGMA integrity_check').fetchone() != ('ok',):
        raise RuntimeError('Database integrity check failed')
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {'documents','chunks','chunk_refs','chunks_fts'} <= tables:
        raise RuntimeError('Not a complete Bible Study Aid index')
    if db.execute('PRAGMA foreign_key_check').fetchone():
        raise RuntimeError('Database has broken foreign-key references')
    # FTS has its own integrity check, separate from SQLite page integrity.
    with db:
        db.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('integrity-check')")
    return {table:db.execute('SELECT count(*) FROM '+table).fetchone()[0]
            for table in ('documents','chunks','chunk_refs')}


def restore_to_new(backup, destination):
    backup,destination=Path(backup).resolve(),Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Restore destination must be new; the live database is never overwritten')
    if not backup.is_file(): raise FileNotFoundError(backup)
    destination.parent.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(destination.parent).free < backup.stat().st_size*2+100*1024**2:
        raise RuntimeError('Insufficient disk space for a verified restore')
    fd,temporary=tempfile.mkstemp(prefix='.restore-',suffix='.sqlite',dir=destination.parent);os.close(fd)
    try:
        with closing(sqlite3.connect(backup.as_uri()+'?mode=ro',uri=True)) as source, closing(sqlite3.connect(temporary)) as target:
            source.backup(target,pages=256,sleep=.05)
            counts=validate_database(target)
            target.execute('PRAGMA journal_mode=DELETE')
        with open(temporary,'rb') as file:os.fsync(file.fileno())
        # Hard-link publication fails atomically if a destination appears meanwhile.
        os.link(temporary,destination)
        return counts
    finally:
        for suffix in ('','-wal','-shm','-journal'):
            path=Path(temporary+suffix)
            if path.exists():path.unlink()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('backup',type=Path);parser.add_argument('destination',type=Path)
    args=parser.parse_args()
    print('Verified restored copy:',args.destination,restore_to_new(args.backup,args.destination))
