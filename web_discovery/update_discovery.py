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


def refresh(folder, lookup=fetch):
    state_path = folder / "catalog.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {"checked":0,"records":{}}
    now = time.time()
    if now - state["checked"] >= 7 * 86400:
        changes = []
        for author, names in AUTHORS.items():
            for item in lookup(names):
                key = item["identifier"]
                record = dict(item, search_author=author)
                if state["records"].get(key) != record:
                    changes.append(key)
                    state["records"][key] = record
        state.update(checked=now, changes=changes)
        atomic_write_text(state_path,json.dumps(state,ensure_ascii=False,indent=2))
        if changes:
            print(f"{len(changes)} catalog records added or changed")
    esc = html.escape
    rows = ['<!doctype html><meta charset="utf-8"><title>Catalog review</title><h1>Catalog review</h1><p>Internet Archive, 25 newest text records per author search. Check attribution, edition, local holdings and permissions before collection.</p>']
    for key, record in sorted(state["records"].items(),key=lambda pair:(pair[1]["search_author"],str(pair[1]["title"]))):
        label = " · New or changed at last check" if key in state['changes'] else ""
        rows.append(f'<p>{esc(record["search_author"])} · <a href="https://archive.org/details/{quote(key,safe="")}">{esc(str(record["title"]))}</a> · {esc(str(record.get("date","Undated")))}{label}</p>')
    atomic_write_text(folder/"Catalog review.html","\n".join(rows))


def main():
    data = load()
    with sqlite3.connect((BASE/"99_Index/bible_study.db").as_uri()+"?mode=rw",uri=True,timeout=30) as db:
        link_passages(db,data)
        paths = [row[0] for row in db.execute("SELECT rel_path FROM documents")]
    atomic_write_text(HERE/"Web Source Discovery.html",report(data,paths))
    refresh(HERE)


if __name__ == "__main__":
    main()
