"""Tests for refreshing stored Bible references."""
from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path

import backfill_references as backfill
import build_scripture_index as scripture_index


class BackfillTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "index.sqlite"
        with closing(sqlite3.connect(self.path)) as db, db:
            db.executescript("""
                CREATE TABLE documents(id INTEGER PRIMARY KEY, rel_path TEXT, title TEXT, source_type TEXT);
                CREATE TABLE chunks(id INTEGER PRIMARY KEY, document_id INTEGER, chunk_index INTEGER, content TEXT);
                CREATE TABLE chunk_refs(id INTEGER PRIMARY KEY AUTOINCREMENT, chunk_id INTEGER, scripture_ref TEXT);
            """)
            db.execute("INSERT INTO documents VALUES(1,'a.txt','A','sermon_note')")
            rows = [
                (1, "We turn to Rom. 8:28 and Psalm 23 today.", ["Romans 8"]),      # old finder missed two
                (2, "Nothing about the Bible here.", []),
                (3, "Genesis 99 is not real but Genesis 1:1 is.", ["Genesis 99", "Genesis 1:1"]),
                (4, "Already correct: John 3:16.", ["John 3:16"]),
            ]
            for chunk_id, text, refs in rows:
                db.execute("INSERT INTO chunks VALUES(?,1,?,?)", (chunk_id, chunk_id, text))
                for ref in refs:
                    db.execute("INSERT INTO chunk_refs(chunk_id,scripture_ref) VALUES(?,?)", (chunk_id, ref))

    def refs(self, db):
        found = {}
        for chunk_id, ref in db.execute("SELECT chunk_id, scripture_ref FROM chunk_refs ORDER BY id"):
            found.setdefault(chunk_id, set()).add(ref)
        return found

    def test_preview_changes_nothing(self):
        with closing(sqlite3.connect(self.path)) as db:
            before = self.refs(db)
            stats = backfill.refresh(db, apply=False)
            self.assertEqual(self.refs(db), before)
        self.assertEqual((stats["passages_changed"], stats["references_added"], stats["references_removed"]), (2, 2, 2))

    def test_apply_fixes_references_once(self):
        with closing(sqlite3.connect(self.path)) as db:
            stats = backfill.refresh(db)
            self.assertTrue(stats["finished"])
            self.assertEqual(self.refs(db), {1: {"Romans 8:28", "Psalms 23"}, 3: {"Genesis 1:1"}, 4: {"John 3:16"}})
            self.assertIsNone(backfill.refresh(db))  # already done

    def test_can_be_stopped_and_resumed(self):
        with closing(sqlite3.connect(self.path)) as db:
            original = backfill.BATCH
            backfill.BATCH = 1
            self.addCleanup(setattr, backfill, "BATCH", original)
            first = backfill.refresh(db, max_chunks=2)
            self.assertFalse(first["finished"])
            self.assertEqual(first["passages_checked"], 2)
            second = backfill.refresh(db)
            self.assertEqual(second["passages_checked"], 2)  # only chunks 3 and 4 remained
            self.assertTrue(second["finished"])
            self.assertEqual(self.refs(db)[3], {"Genesis 1:1"})

    def test_scripture_index_sorts_multiword_books(self):
        self.assertLess(scripture_index.parse_reference("Song of Solomon 2:1")[0], 999)
        order = sorted(["Song of Solomon 2:1", "Psalms 23", "Isaiah 1:1"], key=scripture_index.parse_reference)
        self.assertEqual(order, ["Psalms 23", "Song of Solomon 2:1", "Isaiah 1:1"])


if __name__ == "__main__":
    unittest.main()
