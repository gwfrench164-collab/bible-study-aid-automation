from collections import Counter
from contextlib import closing
from pathlib import Path
import sqlite3

from flask import abort, redirect, render_template_string, request, url_for

SAVED = Path.home() / "Library/Application Support/Bible Study Aid/saved-passages.sqlite"
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
<form method="get"><label for="find">Search saved passages and notes</label><br>
<input type="search" id="find" name="find" value="{{ find }}"><button>Search</button>
{% if find %}<a href="/saved">Clear search</a>{% endif %}</form>
{% if find %}<p>{{ rows|length }} of {{ total }} saved passages</p>{% endif %}
{% for row in rows %}<article id="passage-{{ row.id }}"><h2>{{ row.title }}</h2>
<blockquote>{{ row.excerpt }}</blockquote>
{% if row.note %}<p class="note"><strong>My note</strong><br>{{ row.note }}</p>{% endif %}
<details><summary>{{ 'Edit note' if row.note else 'Add a note' }}</summary>
<form method="post" action="{{ url_for('save_note', key=row.id) }}">
<label for="note-{{ row.id }}">My study note</label>
<textarea rows="3" id="note-{{ row.id }}" name="note">{{ row.note }}</textarea>
<input type="hidden" name="find" value="{{ find }}"><button>Save note</button></form></details>
<a href="{{ url_for('saved_open', key=row.id) }}">Read in context</a>
<form class="inline" method="post" action="{{ url_for('saved_remove', key=row.id) }}">
<input type="hidden" name="find" value="{{ find }}"><button>Remove from saved</button></form>
</article>{% else %}<p>{% if find %}No saved passages match your search.{% else %}Choose Save passage beside a search excerpt to keep it here.{% endif %}</p>{% endfor %}</html>"""


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
        return db

    @app.get("/saved")
    def saved():
        find = request.args.get("find", "").strip()
        words = find.casefold().split()
        with closing(database()) as db:
            rows = db.execute("""SELECT p.id, p.title, p.excerpt, p.body, coalesce(n.note,'') AS note
                FROM passages p LEFT JOIN study_notes n ON n.passage_id=p.id ORDER BY p.id DESC""").fetchall()
        total = len(rows)
        if words:
            matches = []
            for row in rows:
                text = " ".join((row["title"], row["body"], row["note"])).casefold()
                if all(word in text for word in words):
                    matches.append(row)
            rows = matches
        return render_template_string(SHELF, rows=rows, find=find, total=total)

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
        return redirect(url_for("saved", find=request.form.get("find") or None,
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
            return redirect(url_for("open_source", path=row["path"], chunk=found[0], q=row["query"], shelf=1))
        return render_template_string("""<a href="/saved">Saved passages</a><h1>{{ row.title }}</h1>
            <p>The original passage is unavailable. Here is your saved copy.</p>
            <article style="white-space:pre-wrap;max-width:70ch;font:19px/1.6 Georgia">{{ row.body }}</article>""", row=row)

    @app.post("/saved/<int:key>/remove")
    def saved_remove(key):
        with closing(database()) as db, db:
            db.execute("DELETE FROM passages WHERE id=?", (key,))
        return redirect(url_for("saved", find=request.form.get("find") or None), code=303)
