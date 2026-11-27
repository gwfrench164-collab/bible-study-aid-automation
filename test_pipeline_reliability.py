import tempfile, sqlite3, unittest, sys, os
from pathlib import Path
from contextlib import closing
from database_backup import backup_database
from scheduled_intake import record_result, run_command

class ReliabilityTests(unittest.TestCase):
    def test_backup_captures_committed_wal_and_is_readable(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source.sqlite'
            with closing(sqlite3.connect(source)) as db:
                db.execute('PRAGMA journal_mode=WAL')
                db.execute('CREATE TABLE notes(body TEXT)');db.execute("INSERT INTO notes VALUES('preserve me')");db.commit()
                destination=backup_database(source,root/'backups')
                with closing(sqlite3.connect(destination)) as backup:
                    self.assertEqual(backup.execute('SELECT body FROM notes').fetchone(),('preserve me',))
                self.assertEqual(backup_database(source,root/'backups'), destination)
                self.assertEqual(db.execute('SELECT count(*) FROM notes').fetchone(),(1,))

    def test_health_report_preserves_partial_failure_uncertainty(self):
        from intake_health import describe
        self.assertIn('not fully up to date', describe({'status':'needs_attention'}))
        self.assertIn('may still',describe({'status':'running'}))
        self.assertIn('No scheduled run',describe({}))

    def test_retry_backoff_and_recovery(self):
        record={'lane':'local'}
        for delay in (900,1800,3600,3600):
            record_result(record,False,100);self.assertEqual(record['next_due'],100+delay)
        record_result(record,True,200);self.assertEqual(record['failures'],0);self.assertEqual(record['last_success'],200)

    def test_timeout_and_success(self):
        with tempfile.TemporaryFile(mode='w+') as log, tempfile.TemporaryFile() as lock:
            self.assertEqual(run_command([sys.executable,'-c','import time;time.sleep(30)'],log,lock.fileno(),.05,dict(os.environ)),124)
            self.assertEqual(run_command([sys.executable,'-c','print("ok")'],log,lock.fileno(),5,dict(os.environ)),0)
