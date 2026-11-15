"""Refresh verified passages and a weekly, metadata-only Internet Archive queue."""
import hashlib
import html
import json
import sqlite3
import sys
import time
from pathlib import Path
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

from discovery import BASE, HERE, load, report
sys.path.insert(0, str(BASE / "98_Automation"))
from pipeline_support import atomic_write_text

AUTHORS = {
    "Clarence Larkin": ["Clarence Larkin", "Larkin, Clarence"],
    "Charles Spurgeon": ["Charles Haddon Spurgeon", "Spurgeon, Charles Haddon"],
    "E. M. Bounds": ["Edward McKendree Bounds", "Bounds, Edward McKendree"],
}


def link_passages(db, data):
    for work in data["works"]:
        if not work.get("passages"):
            continue
        source = Path(work["local_path"])
        if hashlib.sha256(source.read_bytes()).hexdigest() != work["sha256"]:
            raise ValueError(f"Edition changed: {source}")
        chunks = db.execute("SELECT c.id,c.content FROM chunks c JOIN documents d ON c.document_id=d.id WHERE d.rel_path=?", (str(source),)).fetchall()
        for passage in work["passages"]:
            ids = [i for i, text in chunks if passage["anchor"] in " ".join(text.split())]
            if len(ids) != 1:
                raise ValueError(f"Recheck indexed passage: {passage['anchor']}")
            key = (ids[0], passage["reference"])
            db.execute("INSERT INTO chunk_refs(chunk_id,scripture_ref) SELECT ?,? WHERE NOT EXISTS (SELECT 1 FROM chunk_refs WHERE chunk_id=? AND scripture_ref=?)", key + key)


def fetch(names):
    creators = " OR ".join(f'creator:"{name}"' for name in names)
    params = {"q": f"mediatype:texts AND ({creators})", "sort[]": "addeddate desc", "fl[]": ["identifier","title","date","creator"], "rows": 25, "output":"json"}
    url = "https://archive.org/advancedsearch.php?" + urlencode(params, doseq=True)
    req = Request(url, headers={"User-Agent":"BibleStudyAid/1.0 (personal catalog discovery)"})
    with urlopen(req, timeout=20) as response:
        return json.load(response)["response"]["docs"]


def refresh(folder, lookup=fetch, authors=None):
    import fcntl
    authors = list(dict.fromkeys(load()["authors"] if authors is None else authors))
    with (folder/"catalog.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        _refresh_locked(folder, authors, lookup)


def _refresh_locked(folder, authors, lookup):
    state_path = folder / "catalog.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {"checked":0,"records":{}}
    checked = state.setdefault("author_checks", {a:state["checked"] for a in AUTHORS if state["checked"]})
    day = time.strftime("%Y-%m-%d")
    if state.get("batch_day") != day:
        state.update(batch_day=day, attempted=[], daily_changes=[])
    now = time.time()
    due = sorted((a for a in authors if now-checked.get(a,0) >= 7*86400 and a not in state["attempted"]), key=lambda a:checked.get(a,0))
    errors = state.setdefault("errors",{})
    for author in due[:max(0,6-len(state["attempted"]))]:
        state["attempted"].append(author)
        parts = author.rsplit(" ",1)
        aliases = AUTHORS.get(author,[author] + ([parts[1]+", "+parts[0]] if len(parts)==2 else []))
        try:
            items = lookup(aliases)
            for item in items:
                key = item["identifier"]
                previous = state["records"].get(key,{})
                matches = list(dict.fromkeys(previous.get("matched_authors",[previous.get("search_author",author)])+[author]))
                record = dict(item, search_author=matches[0], matched_authors=matches)
                if {k:v for k,v in previous.items() if k!="matched_authors"} != {k:v for k,v in record.items() if k!="matched_authors"} or author not in previous.get("matched_authors",[previous.get("search_author")]):
                    if key not in state["daily_changes"]:
                        state["daily_changes"].append(key)
                state["records"][key]=record
            checked[author]=now
            errors.pop(author,None)
        except (OSError,ValueError,KeyError) as exc:
            errors[author]=str(exc)
        atomic_write_text(state_path,json.dumps(state,ensure_ascii=False,indent=2))
    esc = html.escape
    rows = ['<!doctype html><meta charset="utf-8"><title>Catalog review</title><h1>Catalog review</h1>',
            f'<p>{sum(a in checked for a in authors)} of {len(authors)} authors checked · {len(state["records"])} catalog records · {day}</p>',
            '<p>Up to six author searches per day. Each search checks the 25 newest Internet Archive text listings. Review local holdings, identity and edition rights before collection.</p>']
    def row(key):
        item = state["records"][key]
        names = ", ".join(item.get("matched_authors",[item["search_author"]]))
        return f'<li>{esc(names)} · <a href="https://archive.org/details/{quote(key,safe="")}">{esc(str(item["title"]))}</a> · {esc(str(item.get("date","Undated")))}</li>'
    rows.append('<h2>Added or changed today</h2><ul>')
    rows.extend(row(key) for key in state["daily_changes"])
    if not state["daily_changes"]:
        rows.append('<li>No catalog changes recorded today.</li>')
    rows.append('</ul>')
    if errors:
        rows.append('<p>Pending retry: '+esc(", ".join(sorted(errors)))+'</p>')
    rows.append('<details><summary>All catalog records</summary><ul>')
    rows.extend(row(key) for key in sorted(state["records"],key=lambda k:(state["records"][k]["search_author"],k)))
    rows.append('</ul></details>')
    atomic_write_text(folder/"Catalog review.html","\n".join(rows))


def main():
    data = load()
    with sqlite3.connect((BASE/"99_Index/bible_study.db").as_uri()+"?mode=rw",uri=True,timeout=30) as db:
        link_passages(db,data)
        paths = [row[0] for row in db.execute("SELECT rel_path FROM documents")]
    atomic_write_text(HERE/"Web Source Discovery.html",report(data,paths))
    refresh(HERE)


if __name__ == "__main__":
    if sys.argv[1:] == ["--catalog-only"]:
        refresh(HERE)
    else:
        main()
