"""Numbered, transactional upgrades of the existing search-index schema."""
from datetime import datetime, timezone


def fingerprints(conn):
    columns={r[1] for r in conn.execute('PRAGMA table_info(documents)')}
    for name,kind in (('file_size','INTEGER'),('modified_ns','INTEGER'),('content_sha256','TEXT')):
        if name not in columns:conn.execute(f'ALTER TABLE documents ADD COLUMN {name} {kind}')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_chunk_refs_chunk ON chunk_refs(chunk_id)')

MIGRATIONS=((1,'Incremental document fingerprints',fingerprints),)


def migrate(conn, migrations=MIGRATIONS):
    if conn.in_transaction:raise RuntimeError('Migrations require a clean transaction boundary')
    conn.execute('BEGIN IMMEDIATE')
    try:
        conn.execute('CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY,name TEXT NOT NULL,applied_at TEXT NOT NULL)')
        applied={r[0] for r in conn.execute('SELECT version FROM schema_migrations')}
        known={m[0] for m in migrations}
        if applied-known:raise RuntimeError('Database has newer migrations than this program')
        for version,name,upgrade in migrations:
            if version in applied:continue
            upgrade(conn)
            conn.execute('INSERT INTO schema_migrations VALUES(?,?,?)',(version,name,datetime.now(timezone.utc).isoformat()))
        conn.commit()
    except BaseException:
        conn.rollback();raise
