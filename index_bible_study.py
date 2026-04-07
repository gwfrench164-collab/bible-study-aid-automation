from pathlib import Path
import sqlite3
import re
from datetime import datetime

BASE = Path("/Users/george/Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid")
DB_PATH = BASE / "99_Index" / "bible_study.db"

SEARCH_FOLDERS = [
    "01_Bibles",
    "02_Originals",
    "03_Translations",
    "04_Commentaries",
    "05_Devotionals",
    "06_Theology",
    "07_History",
    "08_Language",
    "09_Maps",
]

READABLE_SUFFIXES = {".txt", ".md", ".rtf", ".pdf"}


def normalize_book_name(name: str) -> str:
    # Normalize book names to a standard form
    name = name.lower()
    name = re.sub(r"[^a-z0-9]", "", name)
    return name


def normalize_reference(ref: str) -> str:
    # Normalize references like "John 3:16" to a standard form
    ref = ref.strip()
    ref = re.sub(r"\s+", " ", ref)
    return ref


def guess_source_type(path: Path) -> str:
    # Guess source type based on folder name or filename
    for folder in SEARCH_FOLDERS:
        if folder in path.parts:
            return folder
    return "Other"


def collect_files(base_dir: Path):
    files = []
    for folder in SEARCH_FOLDERS:
        folder_path = base_dir / folder
        if not folder_path.exists():
            continue
        for path in folder_path.rglob("*"):
            if path.is_file() and path.suffix.lower() in READABLE_SUFFIXES:
                files.append(path)
    return files


def read_pdf_text(path: Path) -> str:
    # Read text from PDF file
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("PyMuPDF is required to read PDF files.")
        return ""
    try:
        doc = fitz.open(str(path))
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        print(f"Error reading PDF {path}: {e}")
        return ""


def read_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return read_pdf_text(path)
    else:
        try:
            with path.open("r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading text file {path}: {e}")
            return ""


def split_into_chunks(text: str, max_length: int = 1000):
    # Split text into chunks of max_length characters
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_length, len(text))
        chunks.append(text[start:end])
        start = end
    return chunks


def extract_references(text: str):
    # Extract Bible references from text using regex
    # This is a simplified example and may need improvement
    pattern = re.compile(
        r"\b(?:[1-3]\s)?(?:[A-Za-z]+)\s\d{1,3}:\d{1,3}(?:-\d{1,3})?(?:,\s*\d{1,3}:\d{1,3})*\b"
    )
    refs = pattern.findall(text)
    return [normalize_reference(ref) for ref in refs]


def init_db(conn: sqlite3.Connection):
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY,
            path TEXT UNIQUE,
            source_type TEXT,
            modified TIMESTAMP
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY,
            file_id INTEGER,
            chunk_index INTEGER,
            content TEXT,
            FOREIGN KEY(file_id) REFERENCES files(id)
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS references (
            id INTEGER PRIMARY KEY,
            chunk_id INTEGER,
            reference TEXT,
            FOREIGN KEY(chunk_id) REFERENCES chunks(id)
        )
        """
    )
    conn.commit()


def clear_db(conn: sqlite3.Connection):
    c = conn.cursor()
    c.execute("DELETE FROM references")
    c.execute("DELETE FROM chunks")
    c.execute("DELETE FROM files")
    conn.commit()


def index_file(conn: sqlite3.Connection, path: Path):
    c = conn.cursor()
    stat = path.stat()
    mtime = datetime.fromtimestamp(stat.st_mtime)
    source_type = guess_source_type(path)
    text = read_text(path)
    if not text.strip():
        print(f"Empty or unreadable file: {path}")
        return

    c.execute(
        "INSERT OR REPLACE INTO files (path, source_type, modified) VALUES (?, ?, ?)",
        (str(path), source_type, mtime),
    )
    file_id = c.lastrowid
    chunks = split_into_chunks(text)
    for i, chunk in enumerate(chunks):
        c.execute(
            "INSERT INTO chunks (file_id, chunk_index, content) VALUES (?, ?, ?)",
            (file_id, i, chunk),
        )
        chunk_id = c.lastrowid
        refs = extract_references(chunk)
        for ref in refs:
            c.execute(
                "INSERT INTO references (chunk_id, reference) VALUES (?, ?)",
                (chunk_id, ref),
            )
    conn.commit()
    print(f"Indexed {path} with {len(chunks)} chunks and {len(refs)} references.")


def main():
    BASE.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    init_db(conn)
    clear_db(conn)

    files = collect_files(BASE)
    print(f"Found {len(files)} files to index.")

    for path in files:
        index_file(conn, path)

    conn.close()
    print("Indexing complete.")


if __name__ == "__main__":
    main()