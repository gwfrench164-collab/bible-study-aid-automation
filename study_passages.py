from collections import Counter
from contextlib import closing
from pathlib import Path
import sqlite3

from flask import abort, redirect, render_template_string, request, url_for

SAVED = Path.home() / "Library/Application Support/Bible Study Aid/saved-passages.sqlite"
SHELF = """<!doctype html><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Saved passages</title><style>body{font:18px/1.5 system-ui;max-width:72ch;margin:2rem auto;padding:0 1rem}
article{padding:1rem 0;border-bottom:1px solid #ccc}blockquote{font-family:Georgia,serif;margin:1rem 0;white-space:pre-wrap}
button,a{font:inherit}form{display:inline}</style><a href="/">Search library</a><h1>Saved passages</h1>
{% for row in rows %}<article><h2>{{ row.title }}</h2><blockquote>{{ row.excerpt }}</blockquote>
<a href="{{ url_for('saved_open', key=row.id) }}">Read in context</a>
<form method="post" action="{{ url_for('saved_remove', key=row.id) }}"><button>Remove from saved</button></form>
</article>{% else %}<p>Choose Save passage beside a search excerpt to keep it here.</p>{% endfor %}"""


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
        return db

    @app.get("/saved")
    def saved():
        with closing(database()) as db:
            return render_template_string(SHELF, rows=db.execute("SELECT * FROM passages ORDER BY id DESC").fetchall())

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
        return redirect(url_for("saved"), code=303)
