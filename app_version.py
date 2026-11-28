"""Identify the running bundle independently of the working-tree revision."""
import json,sys
from pathlib import Path


def build_info():
    root=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))
    try:
        data=json.loads((root/'BUILD_MANIFEST.json').read_text())
        return {'build':data.get('build_id','unidentified'), 'built_on':data.get('built_on','unknown'),
                'packaged':bool(getattr(sys,'frozen',False))}
    except (OSError,ValueError):
        return {'build':'unidentified','built_on':'unknown','packaged':bool(getattr(sys,'frozen',False))}
