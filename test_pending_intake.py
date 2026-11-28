import json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import closing
import import_commentaries as importer

class PendingTests(unittest.TestCase):
    def test_empty_source_is_persistent_pending_not_silent_success(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);empty=root/'empty.txt';empty.write_text('')
            good=root/'good.txt';good.write_text('Worship in Romans 8:28')
            with patch.object(importer,'DB_PATH',root/'index.sqlite'),patch.object(importer,'collect_files',return_value=[empty,good]):
                importer.main()
                pending=json.loads((root/'index_pending.json').read_text())
                self.assertEqual(pending[0]['path'],str(empty));self.assertEqual(empty.read_bytes(),b'')
                self.assertEqual(json.loads((root/'index_errors.json').read_text()),[])
                empty.write_text('Recovered original text about hope')
                importer.main()
                self.assertEqual(json.loads((root/'index_pending.json').read_text()),[])
