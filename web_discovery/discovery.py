"""Discover works and stage individually reviewed local editions for the existing updater."""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from urllib.parse import urlencode, urlsplit

HERE = Path(__file__).resolve().parent
BASE = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid"
REFERENCE = Path.home() / "Documents/Spiritual/Reference"


def load():
    data = json.loads((HERE / "registry.json").read_text())
    seen = set()
    for work in data["works"]:
        url = work["url"]
        if url in seen or urlsplit(url).scheme != "https" or not urlsplit(url).hostname:
            raise ValueError(f"Invalid or repeated edition URL: {url}")
        seen.add(url)
    return data


def report(data, documents):
    esc = html.escape
    rows = []
    rows.append('<h2>From MyLFBI Library Resources</h2><p>Check collection rights on the individual edition.</p><ul>')
    for directory in data["directories"]:
        rows.append(f'<li><a href="{esc(directory["url"])}">{esc(directory["name"])}</a></li>')
    rows.append("</ul>")
    for author in dict.fromkeys(data["authors"] + [w["author"] for w in data["works"]]):
        surname = author.split()[-1]
        links = []
        for label, base, query in [
            ("Open Library", "https://openlibrary.org/search", {"author": author}),
            ("Project Gutenberg", "https://www.gutenberg.org/ebooks/search/", {"query": surname})
        ]:
            links.append(f'<a href="{base}?{esc(urlencode(query))}">{label}</a>')
        works = [w for w in data["works"] if w["author"] == author]
        matches = []
        for path in documents:
            normalized = re.sub(r"[\W_]+", " ", path.casefold())
            if surname.casefold() in normalized or any(w.get("match_phrase") and w["match_phrase"].casefold() in normalized for w in works):
                matches.append(path)
        rows.append(f'<section><h2>{esc(author)}</h2>{" · ".join(links)}')
        for w in works:
            rows.append(f'<p><a href="{esc(w["url"])}">{esc(w["title"])}</a> · {esc(w["permission"])}<br>{esc(w["edition"])}</p>')
            if w.get("local_path"):
                rows.append(f'<p>Verified local edition: {esc(w["local_path"])}</p>')
            for passage in w.get("passages", []):
                rows.append(f'<p>{esc(passage["reference"])} · {esc(passage["use"])}</p>')
        if matches:
            rows.append(f'<details><summary>{len(matches)} possible local matches</summary><ul>')
            rows.extend(f'<li>{esc(p)}</li>' for p in sorted(matches))
            rows.append('</ul></details>')
        rows.append('</section>')
    return """<!doctype html><meta charset="utf-8"><title>Bible Study Aid · Web sources</title>
<style>body{font:17px system-ui;max-width:58rem;margin:3rem auto;padding:0 1rem;color:#272922}section{padding:1rem 0;border-top:1px solid #ccc}a{color:#185346}li{overflow-wrap:anywhere}</style>
<h1>Web source discovery</h1><p><a href="Catalog review.html">Review catalog discoveries</a> · <a href="Gutenberg resources.html">Gutenberg resources</a> · <a href="Library of Congress matches.html">Library of Congress matches</a> · <a href="Handout title matches.html">Handout title matches</a> · <a href="LFBI Handout Authors.html">LFBI handout author references</a></p><p>Search an author’s catalogs, check local matches, and record the exact edition and its permissions in registry.json.</p>""" + "\n".join(rows)


def collect(work, source, db, reference):
    if work["permission"] not in {"public domain in USA", "licensed for local indexing"} or not work.get("rights_evidence"):
        raise ValueError("This edition needs documented permission for local indexing.")
    if source.suffix.lower() not in {".pdf", ".txt", ".docx"}:
        raise ValueError("Select a PDF, text file, or Word document.")
    content = source.read_bytes()
    if not content:
        raise ValueError("The selected file is empty.")
    digest = hashlib.sha256(content).hexdigest()
    existing = db.execute("SELECT rel_path FROM documents WHERE content_sha256=? LIMIT 1", (digest,)).fetchone()
    if existing:
        return f"Already indexed: {existing[0]}"
    root = reference / "Web Sources"
    root.mkdir(parents=True, exist_ok=True)
    final = root / digest
    if final.exists():
        return f"Already staged: {final}"
    name = re.sub(r'[^\w .-]', '', work['author'] + ' - ' + work['title'])[:130] + source.suffix.lower()
    # Prepare outside the scanned tree, then publish the file and citation together.
    with tempfile.TemporaryDirectory(dir=reference.parent) as temporary:
        package = Path(temporary) / digest
        package.mkdir()
        (package / name).write_bytes(content)
        (package / "provenance.json").write_text(json.dumps(dict(work, sha256=digest, original_filename=source.name), ensure_ascii=False, indent=2))
        try:
            package.rename(final)
        except OSError:
            if not final.is_dir():
                raise
    return f"Staged for the next library update: {final}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collect", metavar="EDITION_URL")
    parser.add_argument("--file", type=Path)
    args = parser.parse_args()
    if bool(args.collect) != bool(args.file):
        parser.error("--collect and --file must be used together")
    data = load()
    path = BASE / "99_Index/bible_study.db"
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
        if args.collect:
            work = next((w for w in data["works"] if w["url"] == args.collect), None)
            if work is None:
                parser.error("Record the edition in registry.json first.")
            print(collect(work, args.file, db, REFERENCE))
        else:
            paths = [r[0] for r in db.execute("SELECT rel_path FROM documents")]
            output = HERE / "Web Source Discovery.html"
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=HERE, delete=False) as f:
                f.write(report(data, paths))
            os.replace(f.name, output)
            print(output)


if __name__ == "__main__":
    main()
