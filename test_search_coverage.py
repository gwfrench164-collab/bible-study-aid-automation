"""Regression coverage for library-wide search and Scripture ranges."""
from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import query_bible_study as search


class SearchCoverageTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.db_path = Path(self.folder.name) / "index.sqlite"
        with closing(sqlite3.connect(self.db_path)) as db, db:
            db.executescript("""
                CREATE TABLE documents(id INTEGER PRIMARY KEY,title TEXT,rel_path TEXT,source_type TEXT);
                CREATE TABLE chunks(id INTEGER PRIMARY KEY,document_id INTEGER,chunk_index INTEGER,content TEXT);
                CREATE TABLE chunk_refs(chunk_id INTEGER,scripture_ref TEXT);
                CREATE VIRTUAL TABLE chunks_fts USING fts5(content,title,rel_path,source_type);
            """)
            for key in range(1, 132):
                title = f"Lesson {key}"
                path = f"02_LFBI/Course_{key}/lesson.txt"
                content = "resurrection and hope"
                db.execute("INSERT INTO documents VALUES(?,?,?,?)", (key,title,path,"lfbi"))
                db.execute("INSERT INTO chunks VALUES(?,?,0,?)", (key,key,content))
                db.execute("INSERT INTO chunks_fts(rowid,content,title,rel_path,source_type) VALUES(?,?,?,?,?)",
                           (key,content,title,path,"lfbi"))
                db.execute("INSERT INTO chunk_refs VALUES(?,?)",
                           (key,"Romans 8:26-30" if key == 131 else "John 11:25"))
        self.patch = patch.object(search, "DB_PATH", self.db_path)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_source_beyond_previous_cap_is_found(self):
        rows = search.run_query("resurrection", limit=None)
        self.assertEqual(len(rows), 131)
        self.assertEqual(len(search.run_query("resurrection", limit=20)), 20)

    def test_filters_search_the_whole_library(self):
        for kwargs in ({"book":"Romans"}, {"course":"Course_131"}, {"book":"Romans","course":"Course_131"}):
            rows = search.run_query("resurrection", **kwargs)
            self.assertEqual([row["title"] for row in rows], ["Lesson 131"])
        self.assertEqual(search.run_query("resurrection", course="Course_13")[0]["title"],"Lesson 13")

    def test_range_finds_passage_without_matching_words(self):
        for query in ("Rom. 8:28", "Romans 8:28–32", "Romans 8"):
            rows = search.run_query(query)
            self.assertEqual(rows[0]["title"], "Lesson 131")
            self.assertIn("Romans 8:26-30", rows[0]["passages"][0]["evidence"])
        self.assertFalse(search.references_overlap("Romans 8:31","Romans 8:26-30"))
        self.assertFalse(search.references_overlap("Romans 9:28","Romans 8:26-30"))

    def test_author_opt_in_applies_to_words_and_references(self):
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE documents SET title='John Calvin - Institutes' WHERE id=131")
        for query in ('resurrection', 'Romans 8:28'):
            ordinary = search.run_query(query, limit=None)
            included = search.run_query(query, limit=None, include_excluded=True)
            self.assertFalse(any('Calvin' in r['title'] for r in ordinary))
            self.assertTrue(any('Calvin' in r['title'] for r in included))
        for title in ('Episode 240: Augustinian-Calvinism', 'Not Calvinist Not Arminian', 'A discussion of Origen'):
            self.assertFalse(search.excluded_author(title, '05_Podcasts/episode.txt'))
        for title in ('Origen - Writings', 'Augustine of Hippo - Confessions', 'John Calvin - Institutes'):
            self.assertTrue(search.excluded_author(title, '/Reference/work.txt'))

    def test_preferred_collection_is_visible_without_filters(self):
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE documents SET title='Week+5-8', rel_path='/Reference/52 weeks of pursuit/Week+5-8.pdf' WHERE id=130")
        rows = search.run_query('resurrection')
        self.assertTrue(rows[0]['preferred_source'])
        self.assertEqual(rows[0]['title'], '52 Weeks of Pursuit — Week 5-8')
        self.assertEqual(search.run_query('Romans 8:28 resurrection')[0]['title'], 'Lesson 131')
        self.assertEqual(search.run_query('nonexistentword'), [])

    def test_abbreviations_and_modes(self):
        self.assertEqual(search.extract_query_reference("Explain 1 Cor. 15:3–4"), "1 Corinthians 15:3-4")
        self.assertEqual(search.extract_query_reference("Rom. 8:28"), "Romans 8:28")
        self.assertIsNone(search.extract_query_reference("Romans 8:30-26"))
        self.assertEqual(search.run_query("resurrection hope", search_mode="exact"),[])
        self.assertEqual(len(search.run_query("resurrection hope",search_mode="all",limit=None)),131)


if __name__ == "__main__":
    unittest.main()
