"""Manage personal search preferences without changing library documents."""
from contextlib import closing
from pathlib import Path
import sqlite3
from flask import request, render_template_string, redirect, url_for, abort
import source_preferences as prefs

PAGE = '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Manage sources</title>
<style>body{font:17px/1.55 system-ui;background:#f6f7fb;color:#202c3d;max-width:850px;margin:2rem auto;padding:0 1rem}section{background:white;border:1px solid #d8dee7;border-radius:12px;padding:1.2rem;margin:1rem 0}h1,h2{line-height:1.2}article{border-top:1px solid #e1e6ee;padding:1rem 0;overflow-wrap:anywhere}button,input{font:inherit;padding:.55rem .75rem;max-width:100%;box-sizing:border-box}button{cursor:pointer;border:1px solid #b7c5d8;border-radius:7px;background:#f3f6fc;color:#193d72}input{border:1px solid #aebdce;border-radius:7px}small{display:block;color:#56667b;overflow-wrap:anywhere}form{margin:.6rem 0}a{color:#194e89}.notice{background:#e4f1e9;padding:.7rem;border-radius:7px}label{display:block}nav{display:flex;gap:1rem;flex-wrap:wrap}</style></head><body>
<nav><a href="/">Search library</a><a href="/saved">Saved passages</a></nav>
<h1>Manage sources</h1><p>Your preferences are saved on this Mac. They change search results, not the original materials.</p>
{% if changed %}<p class="notice" role="status">Preferences saved. They apply to your next search.</p>{% endif %}
<section><h2>Preferred sources</h2><p>Matching passages from these sources receive priority. Exact Scripture matches still take precedence.</p>
{% for item in favorites %}<article><strong>{{ item.title }}</strong><small>{{ item.detail }}</small><form method="post" action="/preferences/source"><input type="hidden" name="key" value="{{ item.key }}"><button name="action" value="remove">Remove preference</button></form></article>{% else %}<p>No preferred sources.</p>{% endfor %}
<details {% if find %}open{% endif %}><summary>Add a preferred source</summary><form method="get"><label for="find">Find a title or collection</label><input id="find" name="find" value="{{ find }}" placeholder="Title or folder name"><button>Find sources</button></form>
{% if find %}<p>{{ total }} matching sources{% if total > 50 %}; showing the first 50. Narrow the name to find others{% endif %}.</p>{% endif %}
{% for item in matches %}<article><strong>{{ item.title }}</strong><small>{{ item.detail }}</small>{% if item.preferred %}<span>Already preferred</span>{% else %}<form method="post" action="/preferences/source"><input type="hidden" name="path" value="{{ item.path }}"><input type="hidden" name="find" value="{{ find }}"><button name="action" value="add">Prefer this source</button></form>{% endif %}</article>{% endfor %}</details></section>
<section><h2>Excluded authors</h2><p>Their attributed works are omitted from normal searches. Use “Include excluded authors” in search when you want to consult them. Other authors’ discussions of their ideas remain searchable.</p>
{% for author in authors %}<article><strong>{{ author }}</strong><form method="post" action="/preferences/author"><input type="hidden" name="name" value="{{ author }}"><button name="action" value="remove">Remove exclusion</button></form></article>{% else %}<p>No excluded authors.</p>{% endfor %}
<form method="post" action="/preferences/author"><label for="author">Add an author to exclude</label><input id="author" name="name" required maxlength="120" placeholder="Author name"><button name="action" value="add">Exclude author</button><small>Use the author’s name as it appears before the work title or as an author folder. Names mentioned only inside a passage are not used.</small></form></section></body></html>'''


def register_management(app, qbs):
    def catalog():
        with closing(sqlite3.connect(qbs.DB_PATH.as_uri() + '?mode=ro', uri=True)) as db:
            return db.execute('SELECT title,rel_path FROM documents ORDER BY title COLLATE NOCASE').fetchall()

    @app.get('/preferences')
    def manage_sources():
        settings = prefs.load_preferences()
        sources = {}
        for title, path in catalog():
            key = prefs.source_key(path)
            collection = key.startswith('collection:')
            sources.setdefault(key, dict(key=key, title='52 Weeks of Pursuit' if collection else title,
                path=path, detail='Entire collection' if collection else str(Path(path).parent),
                preferred=prefs.is_preferred(path, settings)))
        for key, enabled in settings.items():
            if enabled and key not in sources and key.startswith('file:'):
                sources[key] = dict(key=key, title=Path(key[5:]).stem, detail='Not currently in the index', preferred=True)
        favorites = [s for s in sources.values() if s['preferred']]
        find = request.args.get('find', '').strip()
        words = find.casefold().split()
        matches = [s for s in sources.values() if 'path' in s and all(w in (s['title']+' '+s['path']).replace('_',' ').replace('+',' ').casefold() for w in words)] if words else []
        return render_template_string(PAGE, favorites=favorites, matches=matches[:50], total=len(matches),
            find=find, authors=prefs.load_excluded_authors(), changed=request.args.get('changed') == '1')

    @app.post('/preferences/source')
    def manage_source_change():
        action = request.form.get('action')
        if action == 'add':
            path = request.form.get('path','')
            if not any(p == path for _, p in catalog()):
                abort(404)
            prefs.set_preferred(path, True)
        elif action == 'remove':
            key = request.form.get('key','')
            if key == 'collection:52-weeks-of-pursuit':
                prefs.set_preferred('52 Weeks of Pursuit', False)
            elif key.startswith('file:') and key in prefs.load_preferences():
                prefs.set_preferred(key[5:], False)
            else:
                abort(404)
        else:
            abort(400)
        return redirect(url_for('manage_sources', changed='1', find=request.form.get('find','')), code=303)

    @app.post('/preferences/author')
    def manage_author_change():
        action = request.form.get('action')
        if action not in {'add','remove'}:
            abort(400)
        try:
            prefs.set_author_excluded(request.form.get('name',''), action == 'add')
        except ValueError as error:
            abort(400, str(error))
        return redirect(url_for('manage_sources', changed='1'), code=303)
