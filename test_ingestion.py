from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import sqlite3, unittest
import import_commentaries as indexer
from pipeline_support import excluded_resource
from rebuild_scripture_refs import rebuild

class IngestionTests(unittest.TestCase):
    def test_unchanged_and_failed_extraction_preserve_text(self):
        with TemporaryDirectory() as folder, closing(sqlite3.connect(':memory:')) as db:
            path=Path(folder)/'lesson.txt';path.write_text('Rom. 8:28; worship and hope.')
            indexer.init_db(db);indexer.index_file(db,path)
            before=db.execute('SELECT content FROM chunks').fetchall()
            with patch.object(indexer,'read_text',side_effect=AssertionError('should skip')):
                indexer.index_file(db,path)
            path.write_text('Changed source contents; extraction will fail.')
            with patch.object(indexer,'read_text',return_value=''):
                with self.assertRaises(RuntimeError):indexer.index_file(db,path)
            self.assertEqual(db.execute('SELECT content FROM chunks').fetchall(),before)
            self.assertGreater(rebuild(db),0)
            self.assertEqual(db.execute('SELECT content FROM chunks').fetchall(),before)
            self.assertIn(('Romans 8:28',),db.execute('SELECT scripture_ref FROM chunk_refs').fetchall())

    def test_moodle_assessments_and_reviewed_teaching(self):
        self.assertTrue(excluded_resource({'url':'https://mylfbi.org/mod/quiz/view.php?id=1','reviewed_teaching_material':True}))
        self.assertFalse(excluded_resource({'title':'Examining Acts','url':'https://mylfbi.org/mod/resource/view.php?id=1'}))
        self.assertFalse(excluded_resource({'title':'Exam review teaching','reviewed_teaching_material':True}))
