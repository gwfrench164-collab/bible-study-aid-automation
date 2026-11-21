"""Re-find Bible references in text that is already indexed.

The reference finder (bible_refs.py) now understands more ways of writing a
reference, such as "Rom. 8:28", "Ps 23" and "Psalm 119". Documents indexed
before that only have the references the old finder could see. This reads the
text already stored in the search database (it never reopens your original
files) and refreshes the stored references to match the new finder.

It runs by itself once, as part of the normal update. It saves its place every
few thousand passages, so if an update is stopped part-way the next update picks
up where it left off.

To preview what it would change without changing anything:

    python3 backfill_references.py /path/to/bible_study.db

Add --apply to run it by hand.
"""
import argparse
import sqlite3
from pathlib import Path

from bible_refs import extract_references

DONE_KEY = "chunk_refs_v2"
PROGRESS_KEY = "chunk_refs_v2_progress"
BATCH = 2000


def _metadata(conn, key):
    row = conn.execute("SELECT value FROM pipeline_metadata WHERE key=?", (key,)).fetchone()
    return row[0] if row else None


def _set_metadata(conn, key, value):
    conn.execute("INSERT INTO pipeline_metadata(key,value) VALUES(?,?) "
                 "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))


def refresh(conn, apply=True, max_chunks=None, report=None):
    """Refresh stored references. Returns counts. Resumable and safe to stop at any time."""
    conn.execute("CREATE TABLE IF NOT EXISTS pipeline_metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    if apply and _metadata(conn, DONE_KEY):
        return None
    last_id = int(_metadata(conn, PROGRESS_KEY) or 0) if apply else 0
    stats = {"passages_checked": 0, "passages_changed": 0, "references_added": 0, "references_removed": 0}
    finished = True
    while True:
        batch = conn.execute("SELECT id, content FROM chunks WHERE id>? ORDER BY id LIMIT ?",
                             (last_id, BATCH)).fetchall()
        if not batch:
            break
        ids = [row[0] for row in batch]
        old = {}
        for start in range(0, len(ids), 500):
            part = ids[start:start + 500]
            marks = ",".join("?" for _ in part)
            for chunk_id, reference in conn.execute(
                    f"SELECT chunk_id, scripture_ref FROM chunk_refs WHERE chunk_id IN ({marks})", part):
                old.setdefault(chunk_id, set()).add(reference)
        for chunk_id, content in batch:
            new = set(extract_references(content))
            before = old.get(chunk_id, set())
            stats["passages_checked"] += 1
            if new == before:
                continue
            stats["passages_changed"] += 1
            stats["references_added"] += len(new - before)
            stats["references_removed"] += len(before - new)
            if apply:
                for reference in before - new:
                    conn.execute("DELETE FROM chunk_refs WHERE chunk_id=? AND scripture_ref=?",
                                 (chunk_id, reference))
                for reference in sorted(new - before):
                    conn.execute("INSERT INTO chunk_refs(chunk_id, scripture_ref) VALUES(?,?)",
                                 (chunk_id, reference))
        last_id = ids[-1]
        if apply:
            _set_metadata(conn, PROGRESS_KEY, last_id)
            conn.commit()
        if report:
            report(stats)
        if max_chunks is not None and stats["passages_checked"] >= max_chunks:
            finished = False
            break
    if apply and finished:
        _set_metadata(conn, DONE_KEY, "1")
        conn.commit()
    stats["finished"] = finished
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("database", type=Path)
    parser.add_argument("--apply", action="store_true", help="actually change the database")
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error("database does not exist")
    conn = sqlite3.connect(args.database)
    try:
        stats = refresh(conn, apply=args.apply,
                        report=lambda s: print(f"  checked {s['passages_checked']} passages...", flush=True))
    finally:
        conn.close()
    if stats is None:
        print("Already done; nothing to change.")
        return
    mode = "Changed" if args.apply else "Preview (nothing was changed)"
    print(f"{mode}: {stats['passages_changed']} of {stats['passages_checked']} passages; "
          f"{stats['references_added']} references added, {stats['references_removed']} removed.")


if __name__ == "__main__":
    main()
