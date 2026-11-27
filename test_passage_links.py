from test_support import client as protected_client
from contextlib import closing
import sqlite3
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory

import query_bible_study as search
import study_passages as shelf
import bible_study_search_app as ui


class PassageLinksTests(unittest.TestCase):
    def test_rebuild_preserves_reader_and_save_but_replaced_text_is_rejected(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "lesson.txt"
            source.write_text("A passage about hope.")
            index = root / "index.sqlite"
            with closing(sqlite3.connect(index)) as db, db:
                db.executescript("""
                CREATE TABLE documents(id INTEGER PRIMARY KEY,rel_path TEXT,title TEXT);
                CREATE TABLE chunks(id INTEGER PRIMARY KEY,document_id INTEGER,chunk_index INTEGER,content TEXT);
                """)
                db.execute("INSERT INTO documents VALUES(1,?,'Lesson')",(str(source),))
                db.execute("INSERT INTO chunks VALUES(7,1,0,?)",(source.read_text(),))
            with patch.object(search,"DB_PATH",index), patch.object(shelf,"SAVED",root/"saved.sqlite"):
                anchor=search.passage_anchor(source.read_text())
                args=dict(path=str(source),chunk=7,anchor=anchor,q="hope")
                client=protected_client(ui.app)
                self.assertEqual(client.get("/open",query_string=args).status_code,200)
                with closing(sqlite3.connect(index)) as db, db:
                    db.execute("UPDATE chunks SET id=19")
                    db.execute("INSERT INTO chunks VALUES(7,1,1,'Different teaching')")
                self.assertEqual(search.resolve_passage_id(str(source),7,anchor),19)
                reader=client.get("/open",query_string=args)
                self.assertEqual(reader.status_code,200)
                self.assertIn('id="selected-passage"',reader.text)
                self.assertEqual(client.post("/saved",data=args).status_code,303)
                with closing(sqlite3.connect(root/"saved.sqlite")) as db:
                    self.assertEqual(db.execute("SELECT body FROM passages").fetchone()[0],source.read_text())
                with closing(sqlite3.connect(index)) as db, db:
                    db.execute("DELETE FROM chunks WHERE id=19")
                self.assertEqual(client.get("/open",query_string=args).status_code,404)
                self.assertEqual(client.post("/saved",data=args).status_code,404)


if __name__ == "__main__":
    unittest.main()
