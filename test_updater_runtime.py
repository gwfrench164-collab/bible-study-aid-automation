import os,subprocess,sys,unittest,tempfile
from pathlib import Path
from bounded_command import run

class RuntimeTests(unittest.TestCase):
    def test_missing_override_fails_before_updates(self):
        result=subprocess.run(['/bin/bash','update_bible_study_aid.sh','--check-runtime'],env=dict(os.environ,BIBLE_STUDY_PYTHON='/not/a/python'),capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
        self.assertIn('missing intake dependencies',result.stderr)
    def test_bound_and_exit_code(self):
        self.assertEqual(run([sys.executable,'-c','raise SystemExit(7)'],5),7)
        self.assertEqual(run([sys.executable,'-c','import time;time.sleep(20)'],.05),124)
