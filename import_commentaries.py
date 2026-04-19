from pathlib import Path
import sqlite3
import re
from datetime import datetime
import subprocess

BASE = Path("/Users/george/Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid")
DB_PATH = BASE / "99_Index" / "bible_study.db"
SOURCE_REGISTRY = Path(__file__).with_name("source_folders.tsv")

def load_local_source_dirs() -> list[Path]:
    dirs: list[Path] = []
    if not SOURCE_REGISTRY.exists():
        return dirs

    for raw_line in SOURCE_REGISTRY.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split("\t")
        if len(parts) < 2:
            continue

        key = parts[0].strip()
        source_path = parts[1].strip()

        if key in {"LFBI", "Sermon Notes", "Reference"} and source_path:
            dirs.append(Path(source_path))

    return dirs


SEARCH_FOLDERS = load_local_source_dirs() + [
    BASE / "05_Podcasts",
    BASE / "06_Blogs",
]

READABLE_SUFFIXES = {".txt", ".md", ".rtf", ".pdf", ".docx", ".pages"}

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
    path_str = str(path)
    if "/Users/george/Documents/Spiritual/Reference/" in path_str:
        return "commentary"
    if "/Users/george/Documents/Spiritual/Church/Sermon Notes/" in path_str:
        return "sermon_note"
    if "/Users/george/Documents/Spiritual/LFBI/" in path_str:
        return "lfbi"
    if "/05_Podcasts/" in path_str:
        return "podcast"
    if "/06_Blogs/" in path_str:
        return "blog"
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


def read_pdf_text(path: Path) -> str:
    text = ""

    try:
        import fitz
        doc = fitz.open(str(path))
        pieces = []
        for page in doc:
            page_text = page.get_text("text") or ""
            if page_text.strip():
                pieces.append(page_text)
        doc.close()
        text = "\n\n".join(pieces)
        if len(text.strip()) > 100:
            return text
    except Exception:
        pass

    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        pieces = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                pieces.append(page_text)
        text = "\n\n".join(pieces)
        if len(text.strip()) > 100:
            return text
    except Exception:
        pass

    try:
        from pdfminer.high_level import extract_text
        text = extract_text(str(path))
        if len(text.strip()) > 100:
            return text
    except Exception:
        pass

    return ""


def read_docx_text(path: Path) -> str:
    try:
        import docx
        document = docx.Document(str(path))
        paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except Exception:
        return ""


def read_pages_text(path: Path) -> str:
    applescript = f'''
    tell application "Pages"
        set docRef to open POSIX file "{path}"
        set paraList to every paragraph of body text of docRef
        set AppleScript's text item delimiters to linefeed
        set outText to paraList as text
        close docRef saving no
        quit
    end tell
    return outText
    '''

    try:
        completed = subprocess.run(
            ["osascript", "-e", applescript],
            capture_output=True,
            text=True,
            check=True,
        )
        return completed.stdout
    except Exception:
        return ""


def read_text(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return read_pdf_text(path)
    if suffix == ".docx":
        return read_docx_text(path)
    if suffix == ".pages":
        return read_pages_text(path)

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




# Helper functions for document management
def get_rel_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE))
    except Exception:
        return str(path)



def get_existing_document(conn: sqlite3.Connection, rel_path: str) -> tuple[int, float | None] | None:
    row = conn.execute(
        "SELECT id, modified_time FROM documents WHERE rel_path = ?",
        (rel_path,),
    ).fetchone()
    if row is None:
        return None
    return row[0], row[1]



def delete_document_by_id(conn: sqlite3.Connection, document_id: int) -> None:
    chunk_rows = conn.execute(
        "SELECT id FROM chunks WHERE document_id = ?",
        (document_id,),
    ).fetchall()
    chunk_ids = [row[0] for row in chunk_rows]

    for chunk_id in chunk_ids:
        conn.execute("DELETE FROM chunk_refs WHERE chunk_id = ?", (chunk_id,))
        conn.execute("DELETE FROM chunks_fts WHERE rowid = ?", (chunk_id,))

    conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
    conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))



def remove_stale_documents(conn: sqlite3.Connection, valid_rel_paths: set[str]) -> None:
    rows = conn.execute("SELECT id, rel_path FROM documents").fetchall()
    for document_id, rel_path in rows:
        if rel_path not in valid_rel_paths:
            delete_document_by_id(conn, document_id)


def index_file(conn: sqlite3.Connection, path: Path) -> None:
    rel_path = get_rel_path(path)
    title = path.stem
    source_type = guess_source_type(path)
    modified_time = path.stat().st_mtime
    indexed_at = datetime.now().isoformat(timespec="seconds")

    existing = get_existing_document(conn, rel_path)
    if existing is not None:
        existing_id, existing_modified_time = existing
        if existing_modified_time == modified_time:
            print(f"Skipped unchanged: {rel_path}")
            return
        delete_document_by_id(conn, existing_id)

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

        files = collect_files()
        valid_rel_paths = {get_rel_path(path) for path in files}
        remove_stale_documents(conn, valid_rel_paths)
        conn.commit()

        print(f"Found {len(files)} files to index.\n")

        for path in files:
            index_file(conn, path)

        print(f"\nIndex complete: {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()