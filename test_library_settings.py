"""Ensure a relocated library can reuse old index entries and saved passages."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class LibrarySettingsTests(unittest.TestCase):
    def test_relocated_sources_and_independent_storage(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            env = dict(os.environ, BIBLE_STUDY_LIBRARY_ROOT=str(root/"library"),
                       BIBLE_STUDY_LEGACY_LIBRARY_ROOT=str(root/"old"),
                       BIBLE_STUDY_INDEX_PATH=str(root/"index.sqlite"),
                       BIBLE_STUDY_STUDIES_PATH=str(root/"private"/"studies.sqlite"))
            code = """
import library_settings as s
import query_bible_study as q
import study_passages as shelf
import bible_study_search_app as app
assert q.DB_PATH == s.INDEX_PATH
assert shelf.SAVED == s.STUDIES_PATH
target = s.LIBRARY_ROOT / '02_LFBI/test.txt'
target.parent.mkdir(parents=True)
target.write_text('Study passage')
old = str(s.LEGACY_LIBRARY_ROOT / '02_LFBI/test.txt')
assert s.source_path(old) == target
assert s.source_path('02_LFBI/test.txt') == target
assert shelf.source_path(old).is_file()
assert s.source_path('/external/source.txt') == s.Path('/external/source.txt')
for bad in ('../escape.txt', ''):
    try: s.source_path(bad)
    except FileNotFoundError: pass
    else: raise AssertionError(bad)
assert not s.INDEX_PATH.exists()
assert not s.STUDIES_PATH.exists()
"""
            subprocess.run([sys.executable,"-c",code],env=env,check=True)

    def test_default_locations_preserve_current_install(self):
        env = {k:v for k,v in os.environ.items() if not k.startswith("BIBLE_STUDY_")}
        code = """
from pathlib import Path
import library_settings as s
assert s.LIBRARY_ROOT == Path.home()/'Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid'
assert s.STUDIES_PATH == Path.home()/'Library/Application Support/Bible Study Aid/saved-passages.sqlite'
"""
        subprocess.run([sys.executable,"-c",code],env=env,check=True)


if __name__ == "__main__":
    unittest.main()
