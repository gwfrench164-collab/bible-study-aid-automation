import sqlite3,unittest,tempfile
from pathlib import Path
from contextlib import closing
from database_restore import restore_to_new
from database_migrations import migrate
from import_commentaries import init_db,index_file
from database_backup import backup_database

class RecoveryTests(unittest.TestCase):
    def test_restore_preserves_search_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.sqlite';text=root/'source.txt';text.write_text('Worship in Romans 8:28')
            with closing(sqlite3.connect(source)) as db:
                init_db(db);index_file(db,text)
                backup=backup_database(source,root/'backups')
            target=root/'restored.sqlite';counts=restore_to_new(backup,target)
            self.assertEqual(counts['documents'],1)
            with closing(sqlite3.connect(target)) as db:
                self.assertEqual(db.execute("SELECT count(*) FROM chunks_fts WHERE chunks_fts MATCH 'worship'").fetchone(),(1,))
            with self.assertRaises(FileExistsError):restore_to_new(backup,target)
            bad=root/'bad.sqlite';bad.write_text('not sqlite')
            with self.assertRaises(sqlite3.DatabaseError):restore_to_new(bad,root/'failed.sqlite')
            self.assertFalse((root/'failed.sqlite').exists())

    def test_migration_rollback_and_repetition(self):
        with closing(sqlite3.connect(':memory:')) as db:
            db.execute('CREATE TABLE documents(id INTEGER PRIMARY KEY)')
            db.execute('CREATE TABLE chunks(id INTEGER,document_id INTEGER)')
            db.execute('CREATE TABLE chunk_refs(chunk_id INTEGER)');db.commit()
            migrate(db);migrate(db)
            self.assertEqual(db.execute('SELECT count(*) FROM schema_migrations').fetchone(),(1,))
            def fail(c):
                c.execute('CREATE TABLE must_rollback(x)');raise RuntimeError('injected failure')
            from database_migrations import MIGRATIONS
            with self.assertRaises(RuntimeError):migrate(db,(*MIGRATIONS,(2,'failure',fail)))
            self.assertFalse(db.execute("SELECT 1 FROM sqlite_master WHERE name='must_rollback'").fetchone())
            self.assertEqual(db.execute('SELECT count(*) FROM schema_migrations').fetchone(),(1,))
