import unittest
from unittest.mock import patch
import bible_study_search_app as ui
from test_support import client

class SecurityTests(unittest.TestCase):
    def setUp(self):
        import tempfile,sqlite3
        from pathlib import Path
        from contextlib import closing
        self.folder=tempfile.TemporaryDirectory(); self.addCleanup(self.folder.cleanup)
        db=Path(self.folder.name)/'index.sqlite'
        with closing(sqlite3.connect(db)) as conn, conn:
            conn.execute('CREATE TABLE documents(title TEXT,rel_path TEXT)')
        p=patch.object(ui.qbs,'DB_PATH',db);p.start();self.addCleanup(p.stop)

    def test_host_and_cross_site_requests(self):
        c=ui.app.test_client()
        self.assertEqual(c.get('/',headers={'Host':'evil.example'}).status_code,400)
        self.assertEqual(c.post('/studies',data={'name':'Injected'}).status_code,403)
        self.assertEqual(c.get('/open?path=/etc/passwd').status_code,403)
        good=client(ui.app)
        self.assertEqual(good.post('/studies',data={'name':'Injected'},headers={'Origin':'https://evil.example'}).status_code,403)
        with patch.object(ui,'resolve_result_path') as resolve:
            self.assertEqual(good.get('/reveal?path=test',headers={'Sec-Fetch-Site':'cross-site'}).status_code,403)
            resolve.assert_not_called()

    def test_tokens_on_forms_and_links(self):
        html=ui.app.test_client().get('/preferences').get_data(as_text=True)
        self.assertIn('name="_csrf"',html)
        self.assertNotIn('name="_csrf" value=""',html)

    def test_generated_redirect_links_carry_session_token(self):
        from flask import url_for, session
        with ui.app.test_request_context('/'):
            session['_csrf']='protected'
            self.assertIn('_csrf=protected',url_for('open_source',path='lesson.txt'))

    def test_unindexed_path_never_opens(self):
        with patch.object(ui.subprocess,'run') as run:
            response=client(ui.app).get('/reveal?path=/etc/passwd')
            self.assertEqual(response.status_code,404)
            run.assert_not_called()
