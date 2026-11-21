"""The local web app must not be steerable by other websites or open arbitrary files."""
from contextlib import closing
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bible_study_search_app as ui
import query_bible_study as search
import study_passages as shelf


class LocalGuardTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name)
        self.indexed = root / "lesson.pdf"
        self.indexed.write_bytes(b"%PDF-1.4 test")
        self.unindexed = root / "private.pdf"
        self.unindexed.write_bytes(b"%PDF-1.4 private")
        index = root / "index.sqlite"
        with closing(sqlite3.connect(index)) as db, db:
            db.executescript("""
                CREATE TABLE documents(id INTEGER PRIMARY KEY, rel_path TEXT, title TEXT, source_type TEXT);
                CREATE TABLE chunks(id INTEGER PRIMARY KEY, document_id INTEGER, chunk_index INTEGER, content TEXT);
            """)
            db.execute("INSERT INTO documents VALUES(1,?,'Lesson','lfbi')", (str(self.indexed),))
        for patcher in (patch.object(search, "DB_PATH", index),
                        patch.object(shelf, "SAVED", root / "saved.sqlite")):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.launched = []
        run = patch.object(ui.subprocess, "run", lambda command, **kw: self.launched.append(command))
        run.start()
        self.addCleanup(run.stop)
        self.client = ui.app.test_client()

    # --- opening files -------------------------------------------------
    def test_indexed_file_can_be_opened_and_revealed(self):
        self.assertEqual(self.client.get("/open", query_string={"path": str(self.indexed)}).status_code, 200)
        self.assertEqual(self.client.get("/reveal", query_string={"path": str(self.indexed)}).status_code, 200)
        self.assertEqual(self.launched, [["open", str(self.indexed)], ["open", "-R", str(self.indexed)]])

    def test_files_outside_the_index_are_refused(self):
        for path in (self.unindexed, Path("/etc/hosts"), Path("/usr/bin/true"), Path("/Applications")):
            for route in ("/open", "/reveal"):
                response = self.client.get(route, query_string={"path": str(path)})
                self.assertEqual(response.status_code, 404, (route, path))
        self.assertEqual(self.launched, [])

    def test_missing_index_refuses_instead_of_crashing(self):
        with patch.object(search, "DB_PATH", Path("/nonexistent/index.sqlite")):
            self.assertEqual(self.client.get("/open", query_string={"path": str(self.indexed)}).status_code, 404)

    # --- other websites ------------------------------------------------
    def test_requests_from_other_websites_are_refused(self):
        headers = {"Sec-Fetch-Site": "cross-site"}
        for route in ("/", "/open?path=" + str(self.indexed), "/reveal?path=" + str(self.indexed)):
            self.assertEqual(self.client.get(route, headers=headers).status_code, 403, route)
        self.assertEqual(self.launched, [])

    def test_own_pages_and_typed_addresses_still_work(self):
        for site in ("same-origin", "none", ""):
            headers = {"Sec-Fetch-Site": site} if site else {}
            self.assertEqual(self.client.get("/preferences", headers=headers).status_code, 200)

    def test_changes_must_come_from_the_apps_own_pages(self):
        data = {"name": "Custom Writer", "action": "add"}
        self.assertEqual(self.client.post("/preferences/author", data=data,
                                          headers={"Sec-Fetch-Site": "same-site"}).status_code, 403)
        self.assertEqual(self.client.post("/preferences/author", data=data,
                                          headers={"Origin": "https://evil.example"}).status_code, 403)
        self.assertEqual(self.client.post("/preferences/author", data=data,
                                          headers={"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"}).status_code, 303)

    # --- host names ----------------------------------------------------
    def test_only_this_computer_may_be_addressed(self):
        self.assertEqual(self.client.get("/preferences", base_url="http://evil.example").status_code, 400)
        for host in ("http://127.0.0.1:5055", "http://localhost:5055", "http://[::1]:5055"):
            self.assertEqual(self.client.get("/preferences", base_url=host).status_code, 200, host)

    def test_extra_hosts_can_be_allowed_for_phone_access(self):
        with patch.dict(os.environ, {"BIBLE_STUDY_ALLOWED_HOSTS": "my-mac.tail1234.ts.net"}):
            self.assertEqual(self.client.get("/preferences", base_url="http://my-mac.tail1234.ts.net:5055").status_code, 200)
        self.assertEqual(self.client.get("/preferences", base_url="http://my-mac.tail1234.ts.net:5055").status_code, 400)


if __name__ == "__main__":
    unittest.main()
