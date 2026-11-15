"""Discover registered authors in the weekly catalog and import US public-domain texts."""
import csv
import fcntl
import hashlib
import html
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import urlopen

from discovery import BASE, HERE, REFERENCE, collect, load
sys.path.insert(0, str(BASE / "98_Automation"))
from pipeline_support import atomic_write_text
import import_commentaries as importer

FEED = "https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv"
MIRROR = "gutenberg.pglaf.org::gutenberg-epub"
ALIASES = {
    "Charles Spurgeon":"Spurgeon, C. H. (Charles Haddon)", "E. M. Bounds":"Bounds, Edward M. (Edward McKendree)",
    "Hudson Taylor":"Taylor, James Hudson", "John Calvin":"Calvin, Jean", "Bede":"Bede, the Venerable, Saint",
    "Augustine of Hippo":"Augustine, of Hippo, Saint", "R. A. Torrey":"Torrey, R. A. (Reuben Archer)",
    "C. T. Studd":"Studd, C. T. (Charles Thomas)", "G. K. Chesterton":"Chesterton, G. K. (Gilbert Keith)",
    "E. W. Bullinger":"Bullinger, E. W. (Ethelbert William)", "Polycarp":"Polycarp, Saint, Bishop of Smyrna",
    "Arno C. Gaebelein":"Gaebelein, Arno Clemens", "Philo of Alexandria":"Philo",
}
# Publisher edition numbers for specific works named in the local Church History handout.
CITED = {26134:("John William Burgon",30),38326:("Bede",18),45304:("Augustine of Hippo",12)}
NS = {"d":"http://purl.org/dc/terms/", "p":"http://www.gutenberg.org/2009/pgterms/",
      "r":"http://www.w3.org/1999/02/22-rdf-syntax-ns#"}

def norm(value):
    return " ".join(re.findall(r"[^\W_]+",unicodedata.normalize("NFKC",value).casefold()))

def candidates(feed, registry):
    names = {}
    for author in registry["authors"]:
        bits = author.rsplit(" ",1)
        form = ", ".join(reversed(bits))
        names[norm(form)] = author
        if author in ALIASES:
            names[norm(ALIASES[author])] = author
    records = {}
    with feed.open(encoding="utf-8-sig",newline="") as stream:
        for row in csv.DictReader(stream):
            if row["Type"] != "Text" or row["Language"].strip() != "en":
                continue
            for credit in row["Authors"].split("; "):
                if "[" in credit:
                    continue
                form = re.split(r", (?:-?\d|approximately|active|fl\.)",credit)[0]
                author = names.get(norm(form))
                if author:
                    number = int(row["Text#"])
                    records[number] = dict(author=author,credit=form,title=" ".join(row["Title"].split()),
                        subject=row["Subjects"],eligible=bool(re.search(r'biblical|bible|christian|theolog|sermons|church|missionar|prayer|religio|devotional',row["Subjects"],re.I)) or number in CITED)
                    break
    return records

def mirror_file(number, suffix, folder):
    name = f"pg{number}.{suffix}"
    subprocess.run(["/usr/bin/rsync","--contimeout=10","--timeout=30",f"{MIRROR}/{number}/{name}",str(folder)+"/"],check=True,timeout=60,capture_output=True)
    return folder/name

def import_one(number,record,folder,db,registry,index_now):
    rdf=mirror_file(number,"rdf",folder)
    book=ET.parse(rdf).getroot().find("p:ebook",NS)
    if book is None or book.get("{"+NS["r"]+"}about")!=f"ebooks/{number}":
        raise ValueError("Edition identifier mismatch")
    authors=[n.text for n in book.findall("d:creator/p:agent/p:name",NS)]
    if record["credit"] not in authors or book.findtext("d:rights",namespaces=NS)!="Public domain in the USA.":
        return "Rights or attribution requires review"
    source=mirror_file(number,"txt",folder)
    content=source.read_text(encoding="utf-8-sig")
    if not re.search(rf'(?:ebook|etext)\s*(?:no\.?\s*)?#?\s*{number}\b',content[:12000],re.I) or "END OF" not in content[-26000:]:
        raise ValueError("Text edition could not be verified")
    url=f"https://www.gutenberg.org/ebooks/{number}"
    work=dict(author=record["author"],title=record["title"],edition=f"Project Gutenberg #{number}",
              url=url,rights_evidence=url,permission="public domain in USA",catalog_credit=record["credit"],
              mirror_file=f"{MIRROR}/{number}/pg{number}.txt",rights_metadata_sha256=hashlib.sha256(rdf.read_bytes()).hexdigest())
    if number in CITED:
        work["handout_citations"]=[entry for entry in registry["handout_citations"].get(record["author"],[]) if entry["page"]==CITED[number][1]]
    result=collect(work,source,db,REFERENCE)
    if result.startswith("Already indexed"):
        return "Indexed"
    package=REFERENCE/"Web Sources"/hashlib.sha256(source.read_bytes()).hexdigest()
    path,=package.glob("*.txt")
    if not index_now:
        return "Collected for indexing"
    importer.index_file(db,path)
    return "Indexed"

def run():
    folder=HERE
    feed=folder/"pg_catalog.csv"
    if not feed.exists() or time.time()-feed.stat().st_mtime>7*86400:
        with urlopen(FEED,timeout=45) as response:
            raw=response.read().decode("utf-8-sig")
        if not raw.startswith("Text#,Type,") or len(raw)<1000000:
            raise ValueError("Incomplete Gutenberg catalog")
        atomic_write_text(feed,raw)
    registry=load()
    records=candidates(feed,registry)
    status_file=folder/"gutenberg_status.json"
    state=json.loads(status_file.read_text()) if status_file.exists() else {}
    day=time.strftime("%Y-%m-%d")
    prior=state.setdefault("items",{})
    if state.get("day")!=day:
        state.update(day=day,attempted=[])
    known_urls={w["url"] for w in registry["works"] if w.get("local_path")}
    lockpath=Path.home()/"Library/Caches/BibleStudyAid/update.flock"
    with lockpath.open("a+") as lock:
        index_now = True
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            index_now = False
        with sqlite3.connect(importer.DB_PATH.as_uri()+"?mode=rw",uri=True,timeout=30) as db:
            local={norm(row[0]) for row in db.execute("SELECT title FROM documents")}
            ranked=sorted(records,key=lambda n:(n not in CITED,prior.get(str(n),{}).get("tries",0),n))
            for n in ranked:
                key=str(n);r=records[n];entry=prior.get(key,{})
                if f"https://www.gutenberg.org/ebooks/{n}" in known_urls:
                    prior[key]={"status":"Already in library"};continue
                if entry.get("status") == "Collected for indexing":
                    for receipt in (REFERENCE/"Web Sources").glob("*/provenance.json"):
                        metadata=json.loads(receipt.read_text())
                        if metadata.get("url")==f"https://www.gutenberg.org/ebooks/{n}":
                            path,=receipt.parent.glob("*.txt")
                            if index_now:
                                importer.index_file(db,path)
                            if db.execute("SELECT 1 FROM documents WHERE rel_path=?", (str(path),)).fetchone():
                                prior[key]={"status":"Indexed"}
                            break
                    continue
                if entry.get("status") in {"Indexed","Rights or attribution requires review"}:
                    continue
                if norm(r["title"]) in local:
                    prior[key]={"status":"Possible local copy"};continue
                if not r["eligible"] or len(state["attempted"])>=10 or n in state["attempted"]:
                    continue
                state["attempted"].append(n)
                atomic_write_text(status_file,json.dumps(state,indent=2))
                try:
                    with tempfile.TemporaryDirectory() as tmp:
                        status=import_one(n,r,Path(tmp),db,registry,index_now)
                except (OSError,ValueError,ET.ParseError,subprocess.SubprocessError,RuntimeError) as exc:
                    db.rollback()
                    status=f"Pending retry: {exc}"
                prior[key]={"status":status,"tries":entry.get("tries",0)+1}
                atomic_write_text(status_file,json.dumps(state,indent=2))
    atomic_write_text(status_file,json.dumps(state,indent=2))
    rows=['<!doctype html><meta charset="utf-8"><title>Gutenberg resources</title><h1>Gutenberg resources</h1>',
          f'<p>{len(records)} English-language edition matches. Updated {day}. Each indexed download has an edition and rights record alongside the original text.</p><ul>']
    for n,r in sorted(records.items(),key=lambda pair:(pair[0] not in CITED,pair[1]["author"],pair[1]["title"])):
        status=prior.get(str(n),{}).get("status","Awaiting collection" if r["eligible"] else "Catalog only")
        flag=" · LFBI handout title" if n in CITED else ""
        rows.append(f'<li>{html.escape(r["author"])} · <a href="https://www.gutenberg.org/ebooks/{n}">{html.escape(r["title"])}</a> · {html.escape(status)}{flag}</li>')
    atomic_write_text(folder/"Gutenberg resources.html","\n".join(rows)+"</ul>")
