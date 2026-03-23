from pathlib import Path
import sqlite3
import re
from datetime import datetime

BASE = Path("/Users/george/Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid")
DB_PATH = BASE / "99_Index" / "bible_study.db"

SEARCH_FOLDERS = [
    BASE / "02_LFBI",
    BASE / "03_Sermon_Notes",
    BASE / "04_Commentaries",
    BASE / "05_Podcasts",
    BASE / "06_Blogs",
]

READABLE_SUFFIXES = {".txt", ".md", ".rtf"}

BOOK_PATTERNS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
    "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
    "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah",
    "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel",
    "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah",
    "Haggai", "Zechariah", "Malachi", "Matthew", "Mark", "Luke", "John",
    "Acts", "Romans", "1 Corinthians", "2 Corinthians", "Galatians",
    "Ephesians", "Philippians", "Colossians", "1 Thessalonians",
    "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon",
    "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John",
    "3 John", "Jude", "Revelation"
]

BOOK_REGEX = "|".join(re.escape(book) for book in BOOK_PATTERNS)
REFERENCE_REGEX = re.compile(
    rf"\b({BOOK_REGEX})\s+(\d+)(?::(\d+(?:-\d+)?))?\b",
    re.IGNORECASE,
)


def normalize_book_name(book: str) -> str:
    for b in BOOK_PATTERNS:
        if b.lower() == book.lower():
            return b
    return book


def normalize_reference(match: re.Match) -> str:
    book = normalize_book_name(match.group(1))
    chapter = match.group(2)
    verse = match.group(3)
    if verse:
        return f"{book} {chapter}:{verse}"
    return f"{book} {chapter}"


def guess_source_type(path: Path) -> str:
    parts = set(path.parts)
    if "04_Commentaries" in parts:
        return "commentary"
    if "05_Podcasts" in parts:
        return "podcast"
    if "06_Blogs" in parts:
        return "blog"
    if "03_Sermon_Notes" in parts:
        return "sermon_note"
    if "02_LFBI" in parts:
        return "lfbi"
    return "unknown"


def collect_files() -> list[Path]:
    files = []
    for folder in SEARCH_FOLDERS:
        if not folder.exists():
            continue
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() in READABLE_SUFFIXES:
                files.append(path)
    return files


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def split_into_chunks(text: str, chunk_size: int = 1800, overlap: int = 250) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= chunk_size:
            current = f"{current}\n\n{para}".strip()
        else:
            if current:
                chunks.append(current)
            if len(para) <= chunk_size:
                current = para
            else:
                start = 0
                while start < len(para):
                    end = min(start + chunk_size, len(para))
                    piece = para[start:end].strip()
                    if piece:
                        chunks.append(piece)
                    if end == len(para):
                        break
                    start = max(end - overlap, start + 1)
                current = ""

    if current:
        chunks.append(current)

    return chunks


def extract_references(text: str) -> list[str]:
    refs = set()
    for match in REFERENCE_REGEX.finditer(text):
        refs.add(normalize_reference(match))
    return sorted(refs)


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rel_path TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            source_type TEXT NOT NULL,
            modified_time REAL,
            indexed_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunk_refs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chunk_id INTEGER NOT NULL,
            scripture_ref TEXT NOT NULL,
            FOREIGN KEY(chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
        )
    """)

    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            content,
            title,
            rel_path,
            source_type,
            content='',
            tokenize='porter unicode61'
        )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_rel_path ON documents(rel_path)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chunk_refs_ref ON chunk_refs(scripture_ref)")
    conn.commit()


def clear_db(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM chunk_refs")
    conn.execute("DELETE FROM chunks")
    conn.execute("DELETE FROM documents")
    conn.execute("DELETE FROM chunks_fts")
    conn.commit()


def index_file(conn: sqlite3.Connection, path: Path) -> None:
    rel_path = str(path.relative_to(BASE))
    title = path.stem
    source_type = guess_source_type(path)
    modified_time = path.stat().st_mtime
    indexed_at = datetime.now().isoformat(timespec="seconds")

    text = read_text(path)
    if not text.strip():
        return

    chunks = split_into_chunks(text)
    if not chunks:
        return

    cur = conn.cursor()
    cur.execute("""
        INSERT INTO documents (rel_path, title, source_type, modified_time, indexed_at)
        VALUES (?, ?, ?, ?, ?)
    """, (rel_path, title, source_type, modified_time, indexed_at))
    document_id = cur.lastrowid

    for idx, chunk in enumerate(chunks):
        cur.execute("""
            INSERT INTO chunks (document_id, chunk_index, content)
            VALUES (?, ?, ?)
        """, (document_id, idx, chunk))
        chunk_id = cur.lastrowid

        cur.execute("""
            INSERT INTO chunks_fts (rowid, content, title, rel_path, source_type)
            VALUES (?, ?, ?, ?, ?)
        """, (chunk_id, chunk, title, rel_path, source_type))

        refs = extract_references(chunk)
        for ref in refs:
            cur.execute("""
                INSERT INTO chunk_refs (chunk_id, scripture_ref)
                VALUES (?, ?)
            """, (chunk_id, ref))

    conn.commit()
    print(f"Indexed: {rel_path} ({len(chunks)} chunks)")


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        init_db(conn)
        clear_db(conn)

        files = collect_files()
        print(f"Found {len(files)} files to index.\n")

        for path in files:
            index_file(conn, path)

        print(f"\nIndex complete: {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()