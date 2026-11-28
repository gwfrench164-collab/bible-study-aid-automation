"""Read-only, plain-language reporting for scheduled intake."""
from pathlib import Path
import json
from flask import render_template_string


def read_state(path):
    if not path.exists(): return {'status':'not_run'}
    try:return json.loads(path.read_text())
    except (OSError,ValueError):return {'status':'unreadable'}


def describe(record):
    status=record.get('status') if isinstance(record,dict) else 'unreadable'
    if status == 'ok': return 'Last run completed successfully.'
    if status == 'running': return 'A run started; it may still be working. An interrupted run is retried on schedule.'
    if status == 'needs_attention': return 'Last run had failures. Successful stages may still have added material; the library is not fully up to date.'
    if status == 'unreadable':return 'The saved status could not be read. Inspect the intake log before restarting work.'
    return 'No scheduled run has been recorded.'


def register_health(app, qbs):
    @app.get('/intake-status')
    def intake_status():
        state=Path.home()/'Library/Application Support/BibleStudyAid/intake'
        lanes=[(label,describe(read_state(state/(lane+'.json')))) for lane,label in
               [('local','Local documents and LFBI downloads'),('acquire','Public downloads and transcription')]]
        errors=read_state(qbs.DB_PATH.parent/'index_errors.json')
        failures=[]
        if isinstance(errors,list):
            for item in errors:
                error=item.get('error','')
                reason=('No readable text was extracted. Any previously indexed version was retained.'
                        if 'Extraction empty' in error else
                        'Pages extraction needs an attended run.' if 'Pages extraction deferred' in error else
                        'This source failed to index. Review index_errors.json for details.')
                failures.append((Path(item.get('path','Unknown source')).name,reason))
        return render_template_string('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Library update status</title><style>body{font:17px/1.6 system-ui;max-width:760px;margin:2rem auto;padding:0 1rem;color:#202c3d}article{border:1px solid #ccd5df;padding:1rem;border-radius:10px;margin:1rem 0}h2{font-size:1.2rem}p{overflow-wrap:anywhere}</style><a href="/">Search library</a><h1>Library update status</h1>
<p>These are the most recently recorded results, not a guarantee that every source has been acquired.</p>
{% for label,message in lanes %}<article><h2>{{ label }}</h2><p>{{ message }}</p></article>{% endfor %}
<h2>Sources needing attention</h2>{% if not errors_known %}<p>The latest source-failure report is unavailable.</p>{% endif %}{% for name,reason in failures %}<article><strong>{{ name }}</strong><p>{{ reason }}</p></article>{% else %}{% if errors_known %}<p>No individual source failures are recorded in the latest index report.</p>{% endif %}{% endfor %}
<p>Updates require this Mac to be awake and logged in. Moodle resources may still require authorized access in Safari. Original materials and previous successful index entries are preserved when extraction fails.</p></html>''',lanes=lanes,failures=failures,errors_known=isinstance(errors,list))
