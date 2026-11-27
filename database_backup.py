"""Verified SQLite snapshots made through the online backup API, never file copies."""
import argparse
import hashlib
from contextlib import closing
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
from library_settings import INDEX_PATH


def backup_database(source, directory):
    source, directory = Path(source), Path(directory)
    if not source.is_file():
        raise FileNotFoundError(source)
    directory.mkdir(parents=True, exist_ok=True)
    identity = hashlib.sha256(str(source.resolve()).encode()).hexdigest()[:10]
    destination = directory / (source.stem + '-' + identity + '-' + datetime.now(timezone.utc).strftime('%Y%m%d') + '.sqlite')
    if destination.exists():
        with closing(sqlite3.connect(destination.as_uri()+'?mode=ro',uri=True)) as previous:
            if previous.execute('PRAGMA quick_check').fetchone() != ('ok',):
                raise RuntimeError('Existing backup failed integrity check; preserve it for investigation')
        return destination
    if shutil.disk_usage(directory).free < source.stat().st_size * 2 + 100*1024**2:
        raise RuntimeError('Insufficient free space for a verified database backup')
    fd, temporary = tempfile.mkstemp(prefix='.library-',suffix='.sqlite',dir=directory)
    os.close(fd)
    try:
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as src, closing(sqlite3.connect(temporary)) as dst:
            src.backup(dst, pages=256, sleep=.05)
            if dst.execute('PRAGMA quick_check').fetchone() != ('ok',):
                raise RuntimeError('Backup failed integrity check')
        with open(temporary,'rb') as file:
            os.fsync(file.fileno())
        os.replace(temporary,destination)
        return destination
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def ensure_backup():
    return backup_database(INDEX_PATH, Path.home()/'Library/Application Support/Bible Study Aid/backups')

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path,default=INDEX_PATH)
    parser.add_argument('--directory',type=Path,default=Path.home()/'Library/Application Support/Bible Study Aid/backups')
    args=parser.parse_args()
    print('Verified backup:',backup_database(args.database,args.directory))
