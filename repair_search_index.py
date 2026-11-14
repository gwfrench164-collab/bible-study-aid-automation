"""Rebuild derived FTS data from stored chunks; never reads source documents."""
import argparse
import sqlite3
from pathlib import Path

def repair(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS pipeline_metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    if conn.execute("SELECT value FROM pipeline_metadata WHERE key='fts_exact_delete_v1'").fetchone():
        return False
    with conn:
        conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('delete-all')")
        conn.execute("""INSERT INTO chunks_fts(rowid,content,title,rel_path,source_type)
            SELECT c.id,c.content,d.title,d.rel_path,d.source_type
            FROM chunks c JOIN documents d ON d.id=c.document_id""")
        conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('integrity-check')")
        conn.execute("INSERT INTO pipeline_metadata(key,value) VALUES('fts_exact_delete_v1','1')")
    return True

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database',type=Path)
    args=parser.parse_args()
    if not args.database.is_file():parser.error('database does not exist')
    with sqlite3.connect(args.database) as conn:
        print('FTS rebuilt from stored chunks.' if repair(conn) else 'FTS repair already applied.')
