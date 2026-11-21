"""Personal source preferences, separate from the search index."""
from contextlib import closing
from pathlib import Path
import re
from functools import lru_cache
import sqlite3
from library_settings import STUDIES_PATH


@lru_cache(maxsize=16384)
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


DEFAULT_EXCLUDED = ('John Calvin', 'Origen', 'Augustine')


def load_excluded_authors():
    authors = set(DEFAULT_EXCLUDED)
    if STUDIES_PATH.exists():
        with closing(sqlite3.connect(STUDIES_PATH.as_uri() + '?mode=ro', uri=True)) as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='author_preferences'").fetchone():
                for name, excluded in db.execute('SELECT name,excluded FROM author_preferences'):
                    if excluded:
                        authors.add(name)
                    else:
                        authors.discard(name)
    return tuple(sorted(authors))


def set_author_excluded(name, excluded):
    name = ' '.join(name.split())
    if not name or len(name) > 120:
        raise ValueError('Enter an author name of 1–120 characters.')
    aliases = {'calvin':'John Calvin', 'john calvin':'John Calvin', 'origen':'Origen',
               'augustine':'Augustine', 'augustine of hippo':'Augustine', 'agustine':'Augustine'}
    name = aliases.get(name.casefold(), name)
    STUDIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(STUDIES_PATH)) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS author_preferences(name TEXT PRIMARY KEY COLLATE NOCASE, excluded INTEGER NOT NULL)')
        db.execute('INSERT INTO author_preferences VALUES(?,?) ON CONFLICT(name) DO UPDATE SET excluded=excluded.excluded',
                   (name, int(excluded)))
