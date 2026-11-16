from collections import Counter
from contextlib import closing
from pathlib import Path
import sqlite3

from flask import abort, redirect, render_template_string, request, url_for

SAVED = Path.home() / "Library/Application Support/Bible Study Aid/saved-passages.sqlite"
COPY_SCRIPT = """<script>
document.addEventListener('click', async event => {
    const button = event.target.closest('[data-copy]');
    if (!button) return;
    const passage = button.closest('[data-passage]');
    const parts = [passage.querySelector('[data-excerpt]').textContent,
                   'Source: ' + button.dataset.copy];
    if (passage.querySelector('[data-include-note]:checked'))
        parts.push('My note: ' + passage.querySelector('[data-note]').textContent);
    const text = parts.join('\\n\\n');
    const status = passage.querySelector('[role=status]');
    try {
        await navigator.clipboard.writeText(text);
        status.textContent = 'Copied';
    } catch {
        const field = document.createElement('textarea');
        field.value = text;
        field.setAttribute('aria-label', 'Excerpt with source');
        status.replaceChildren(field);
        field.select();
        if (document.execCommand('copy')) status.textContent = 'Copied';
        else field.focus();
    }
});
</script>"""


def source_line(title, path):
    parts = Path(path).parts
    details = []
    if "02_LFBI" in parts:
        start = parts.index("02_LFBI") + 1
        details = [part.replace("_", " ") for part in parts[start:-1][:2]]
    return " · ".join([title, *details])


SHELF = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Saved passages</title>
<style>
body{font:17px/1.5 system-ui;color:#202833;max-width:72ch;margin:2rem auto;padding:0 1rem}
article{padding:1rem 0 1.5rem;border-bottom:1px solid #cbd5df}
h2{line-height:1.3;overflow-wrap:anywhere}
blockquote{font:1.12rem/1.65 Georgia,serif;margin:1rem 0;white-space:pre-wrap}
button,input,textarea{font:inherit}input,textarea{padding:.4rem;max-width:100%;box-sizing:border-box}
textarea{width:100%;display:block;margin:.4rem 0}button,summary{cursor:pointer}
.note{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f6fa;padding:.75rem}
details{margin:.75rem 0}a{color:#194e89}.inline{display:inline-block;margin-left:.75rem}
</style><a href="/">Search library</a><h1>Saved passages</h1>
<nav><a href="/saved">All saved passages</a>
{% for group in studies %} · <a href="{{ url_for('saved',study=group.id) }}">{{ group.name }}</a>{% endfor %}</nav>
<details><summary>Create a study</summary><form method="post" action="/studies">
<label>Study name <input required name="name" maxlength="160"></label><button>Create study</button></form></details>
{% if current %}<h2>{{ current.name }}</h2>{% endif %}
<form method="get">{% if current %}<input type="hidden" name="study" value="{{ current.id }}">{% endif %}<label for="find">Search saved passages and notes</label><br>
<input type="search" id="find" name="find" value="{{ find }}"><button>Search</button>
{% if find %}<a href="{{ url_for('saved', study=study) }}">Clear search</a>{% endif %}</form>
{% if find %}<p>{{ rows|length }} of {{ total }} saved passages</p>{% endif %}
{% for row in rows %}<article data-passage id="passage-{{ row.id }}"><h2>{{ row.title }}</h2>
<blockquote data-excerpt>{{ row.excerpt }}</blockquote>
{% if row.note %}<p class="note"><strong>My note</strong><br><span data-note>{{ row.note }}</span></p>{% endif %}
<button type="button" data-copy="{{ source_line(row.title,row.path) }}">Copy excerpt with source</button>
{% if row.note %}<label><input type="checkbox" data-include-note>Include my note</label>{% endif %} <span role="status"></span>
{% if studies %}<details><summary>Organize in studies</summary>
<form method="post" action="{{ url_for('membership', key=row.id) }}">
<input type="hidden" name="view" value="{{ study or '' }}">
<label>Study <select name="study">{% for group in studies %}<option value="{{ group.id }}">{{ group.name }}</option>{% endfor %}</select></label>
<button name="action" value="add">Add to study</button></form></details>{% endif %}
{% if current %}<form method="post" action="{{ url_for('membership', key=row.id) }}">
<input type="hidden" name="study" value="{{ study }}"><input type="hidden" name="view" value="{{ study }}">
<button name="action" value="up">Move up</button> <button name="action" value="down">Move down</button>
<button name="action" value="remove">Remove from this study</button></form>{% endif %}
<details><summary>{{ 'Edit note' if row.note else 'Add a note' }}</summary>
<form method="post" action="{{ url_for('save_note', key=row.id) }}">
<label for="note-{{ row.id }}">My study note</label>
<textarea rows="3" id="note-{{ row.id }}" name="note">{{ row.note }}</textarea>
<input type="hidden" name="study" value="{{ study or '' }}"><input type="hidden" name="find" value="{{ find }}"><button>Save note</button></form></details>
<a href="{{ url_for('saved_open', key=row.id, study=study, find=find or none) }}">Read in context</a>
<form class="inline" method="post" action="{{ url_for('saved_remove', key=row.id) }}">
<input type="hidden" name="study" value="{{ study or '' }}"><input type="hidden" name="find" value="{{ find }}"><button>Remove from saved</button></form>
</article>{% else %}<p>{% if find %}No saved passages match your search.{% elif current %}Add passages from All saved passages using Organize in studies.{% else %}Choose Save passage beside a search excerpt to keep it here.{% endif %}</p>{% endfor %}""" + COPY_SCRIPT + "</html>"


def course_name(item):
    parts = Path(item["path"]).parts
    if item["source_type"] == "lfbi" and "02_LFBI" in parts:
        rest = parts[parts.index("02_LFBI") + 1:-1]
        if rest:
            return rest[0]
    return ""


def narrow_results(rows, book, course):
    books, courses = Counter(), Counter()
    visible = []
    canonical = {}
    for row in rows:
        name = course_name(row)
        cited = {b for passage in row["passages"] for b in passage["books"]}
        if not course or name == course:
            books.update(cited)
        if name and (not book or book in cited):
            courses[name] += 1
        if course and name != course:
            continue
        kept = []
        for p in row["passages"]:
            if book and book not in p["books"]:
                continue
            key = " ".join(p["snippet"].split())
            if key in canonical and len(key) >= 80:
                canonical[key]["copies"].append((row["title"], row["path"], p["chunk_id"]))
            else:
                passage = dict(p, copies=[])
                canonical[key] = passage
                kept.append(passage)
        if kept:
            visible.append(dict(row, passages=kept))
    return visible, sorted(books.items()), sorted(courses.items())


def register_shelf(app, qbs):
    def database():
        SAVED.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(SAVED)
        db.row_factory = sqlite3.Row
        db.execute("""CREATE TABLE IF NOT EXISTS passages(id INTEGER PRIMARY KEY, path TEXT,
                   title TEXT, chunk INTEGER, body TEXT, excerpt TEXT, query TEXT, UNIQUE(path,body,excerpt))""")
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("""CREATE TABLE IF NOT EXISTS study_notes(
            passage_id INTEGER PRIMARY KEY REFERENCES passages(id) ON DELETE CASCADE, note TEXT NOT NULL)""")
        db.execute("CREATE TABLE IF NOT EXISTS studies(id INTEGER PRIMARY KEY, name TEXT UNIQUE COLLATE NOCASE)")
        db.execute("""CREATE TABLE IF NOT EXISTS study_items(
            study INTEGER REFERENCES studies ON DELETE CASCADE,
            passage INTEGER REFERENCES passages ON DELETE CASCADE,
            position INTEGER NOT NULL, PRIMARY KEY(study,passage))""")
        return db

    @app.get("/saved")
    def saved():
        find = request.args.get("find", "").strip()
        words = find.casefold().split()
        study = request.args.get("study", type=int)
        with closing(database()) as db:
            studies = db.execute("SELECT * FROM studies ORDER BY name COLLATE NOCASE").fetchall()
            current = next((group for group in studies if group["id"] == study), None)
            if study is not None and current is None:
                abort(404)
            rows = db.execute("""SELECT p.*, coalesce(n.note,'') AS note FROM passages p
                LEFT JOIN study_notes n ON n.passage_id=p.id
                LEFT JOIN study_items i ON i.passage=p.id AND i.study=?
                WHERE ? IS NULL OR i.passage IS NOT NULL ORDER BY i.position,p.id DESC""",
                (study,study)).fetchall()
        total = len(rows)
        if words:
            matches = []
            for row in rows:
                text = " ".join((row["title"], row["body"], row["note"])).casefold()
                if all(word in text for word in words):
                    matches.append(row)
            rows = matches
        return render_template_string(SHELF, rows=rows, find=find, total=total, studies=studies,
                                      current=current, study=study, source_line=source_line)

    @app.post("/studies")
    def create_study():
        name = request.form["name"].strip()
        if not name or len(name) > 160:
            abort(400)
        with closing(database()) as db, db:
            db.execute("INSERT OR IGNORE INTO studies(name) VALUES(?)", (name,))
            study = db.execute("SELECT id FROM studies WHERE name=?", (name,)).fetchone()[0]
        return redirect(url_for("saved", study=study), code=303)

    @app.post("/saved/<int:key>/study")
    def membership(key):
        study = request.form.get("study", type=int)
        action = request.form["action"]
        with closing(database()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            if not db.execute("SELECT 1 FROM studies WHERE id=?", (study,)).fetchone() or not db.execute(
                    "SELECT 1 FROM passages WHERE id=?", (key,)).fetchone():
                abort(404)
            if action == "add":
                db.execute("""INSERT OR IGNORE INTO study_items(study,passage,position)
                    SELECT ?,?,coalesce(max(position),0)+1 FROM study_items WHERE study=?""", (study,key,study))
            elif action == "remove":
                db.execute("DELETE FROM study_items WHERE study=? AND passage=?", (study,key))
            elif action in {"up","down"}:
                order = db.execute("SELECT passage,position FROM study_items WHERE study=? ORDER BY position",
                                   (study,)).fetchall()
                for i, row in enumerate(order):
                    if row["passage"] == key:
                        j = i + (-1 if action == "up" else 1)
                        if 0 <= j < len(order):
                            neighbor = order[j]
                            db.executemany("UPDATE study_items SET position=? WHERE study=? AND passage=?",
                                [(neighbor["position"],study,key),(row["position"],study,neighbor["passage"])])
                        break
            else:
                abort(400)
        return redirect(url_for("saved", study=study, _anchor=f"passage-{key}"), code=303)

    @app.post("/saved/<int:key>/note")
    def save_note(key):
        note = request.form["note"].strip()
        with closing(database()) as db, db:
            if not db.execute("SELECT 1 FROM passages WHERE id=?", (key,)).fetchone():
                abort(404)
            if note:
                db.execute("""INSERT INTO study_notes(passage_id,note) VALUES(?,?)
                    ON CONFLICT(passage_id) DO UPDATE SET note=excluded.note""", (key,note))
            else:
                db.execute("DELETE FROM study_notes WHERE passage_id=?", (key,))
        return redirect(url_for("saved", study=request.form.get("study",type=int), find=request.form.get("find") or None,
                                _anchor=f"passage-{key}"), code=303)

    @app.post("/saved")
    def save_passage():
        path = request.form["path"]
        chunk = request.form.get("chunk", type=int)
        query = request.form.get("q", "")
        with closing(sqlite3.connect(qbs.DB_PATH.as_uri() + "?mode=ro", uri=True)) as index:
            row = index.execute("""SELECT d.title,c.content FROM chunks c JOIN documents d ON d.id=c.document_id
                                  WHERE c.id=? AND d.rel_path=?""", (chunk, path)).fetchone()
        if not row:
            abort(404, "Search again to refresh this passage.")
        terms = qbs.get_topic_expansion_terms(query) if request.form.get("related") != "off" else []
        if request.form.get("related") != "off" and request.form.get("mode", "balanced") == "balanced":
            terms += qbs.related_phrases(query)
        excerpt = qbs.build_snippet(row[1], query, terms, qbs.extract_query_reference(query))
        with closing(database()) as db, db:
            db.execute("INSERT OR IGNORE INTO passages(path,title,chunk,body,excerpt,query) VALUES(?,?,?,?,?,?)",
                       (path,row[0],chunk,row[1],excerpt,query))
        return redirect(url_for("saved"), code=303)

    @app.get("/saved/<int:key>")
    def saved_open(key):
        with closing(database()) as db:
            row = db.execute("SELECT * FROM passages WHERE id=?", (key,)).fetchone()
        if not row:
            abort(404)
        with closing(sqlite3.connect(qbs.DB_PATH.as_uri() + "?mode=ro", uri=True)) as index:
            found = index.execute("""SELECT c.id FROM chunks c JOIN documents d ON d.id=c.document_id
                WHERE d.rel_path=? AND c.content=? ORDER BY (c.id=?) DESC,c.chunk_index LIMIT 1""",
                (row["path"],row["body"],row["chunk"])).fetchone()
        if found and (qbs.BASE / row["path"]).is_file():
            return redirect(url_for("open_source", path=row["path"], chunk=found[0], q=row["query"], shelf=key, study=request.args.get("study",type=int), find=request.args.get("find") or None))
        return render_template_string("""<a href="/saved">Saved passages</a><h1>{{ row.title }}</h1>
            <p>The original passage is unavailable. Here is your saved copy.</p>
            <article style="white-space:pre-wrap;max-width:70ch;font:19px/1.6 Georgia">{{ row.body }}</article>""", row=row)

    @app.post("/saved/<int:key>/remove")
    def saved_remove(key):
        with closing(database()) as db, db:
            db.execute("DELETE FROM passages WHERE id=?", (key,))
        return redirect(url_for("saved", study=request.form.get("study",type=int), find=request.form.get("find") or None), code=303)
