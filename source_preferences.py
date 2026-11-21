"""Personal source preferences, separate from the search index."""
from contextlib import closing
from pathlib import Path
import re
import sqlite3
from library_settings import STUDIES_PATH


def source_key(path):
    if re.search(r'\b52[ _+]+weeks[ _+]+of[ _+]+pursuit\b', path, re.I):
        return 'collection:52-weeks-of-pursuit'
    return 'file:' + path


def load_preferences():
    if not STUDIES_PATH.exists():
        return {}
    with closing(sqlite3.connect(STUDIES_PATH.as_uri() + '?mode=ro', uri=True)) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='source_preferences'").fetchone():
            return {}
        return dict(db.execute('SELECT source_key,preferred FROM source_preferences'))


def is_preferred(path, preferences):
    key = source_key(path)
    return bool(preferences.get(key, key == 'collection:52-weeks-of-pursuit'))


def set_preferred(path, enabled):
    STUDIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(STUDIES_PATH)) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS source_preferences(source_key TEXT PRIMARY KEY, preferred INTEGER NOT NULL)')
        db.execute('INSERT INTO source_preferences VALUES(?,?) ON CONFLICT(source_key) DO UPDATE SET preferred=excluded.preferred',
                   (source_key(path), int(enabled)))
