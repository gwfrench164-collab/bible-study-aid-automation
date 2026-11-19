from pathlib import Path
import sqlite3
import re
import hashlib
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
import subprocess
import json
import os
from pipeline_support import atomic_write_text

BASE = Path("/Users/george/Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid")
DB_PATH = BASE / "99_Index" / "bible_study.db"
SOURCE_REGISTRY = Path(__file__).with_name("source_folders.tsv")
LFF_CHURCH_REGISTRY = Path(__file__).with_name("lff_church_sources.tsv")
OCR_CACHE_DIR = Path(__file__).with_name("state") / "ocr_text"

SOURCE_TYPE_BY_KEY = {
    "LFBI": "lfbi",
    "LFBI Legacy": "lfbi",
    "Sermon Notes": "sermon_note",
    "Sermons": "sermon_note",
    "Reference": "commentary",
}

def load_local_sources() -> list[tuple[Path, str]]:
    sources: list[tuple[Path, str]] = []
    if not SOURCE_REGISTRY.exists():
        return sources

    for raw_line in SOURCE_REGISTRY.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split("\t")
        if len(parts) < 2:
            continue

        key = parts[0].strip()
        source_path = parts[1].strip()

        source_type = SOURCE_TYPE_BY_KEY.get(key)
        if source_type and source_path:
            sources.append((Path(source_path), source_type))

    return sources


LOCAL_SOURCES = load_local_sources()
EXISTING_LFF_CHURCH_FOLDERS = [
    "Harvest_Baptist_Church_Messages",
    "Harvest_Baptist_Church_Of_Blue_Springs",
    "Greater_Hope_Baptist_Church",
    "Faith_Fellowship_Sermons",
    "First_Baptist_Church_Of_New_Philadelphia",
    "Heartland_Baptist_Fellowship",
    "Whole_Heart_Fellowship_Sermons",
    "Life_Fellowship_Sermons",
    "Midtown_Baptist_Temple_Audio",
]


def load_lff_church_sources() -> list[tuple[Path, str]]:
    sources = [(BASE / "05_Podcasts" / folder, "church_sermon") for folder in EXISTING_LFF_CHURCH_FOLDERS]
    if not LFF_CHURCH_REGISTRY.exists():
        return sources
    for raw_line in LFF_CHURCH_REGISTRY.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) >= 4 and parts[3].strip():
            sources.append((BASE / parts[3].strip(), "church_sermon"))
    return sources


SEARCH_SOURCES = LOCAL_SOURCES + load_lff_church_sources() + [
    (BASE / "05_Podcasts", "podcast"),
    (BASE / "06_Blogs", "blog"),
]

READABLE_SUFFIXES = {".txt", ".md", ".rtf", ".pdf", ".docx", ".pptx", ".xlsx", ".pages"}

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
    resolved_path = path.resolve()
    for source_root, source_type in SEARCH_SOURCES:
        try:
            resolved_path.relative_to(source_root.resolve())
            return source_type
        except ValueError:
            continue
    return "unknown"


def collect_files() -> list[Path]:
    files = []
    seen = set()
    for folder, _source_type in SEARCH_SOURCES:
        if not folder.exists():
            print(f"WARNING: Source unavailable; retaining prior index: {folder}")
            continue
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() in READABLE_SUFFIXES and path.resolve() not in seen:
                files.append(path)
                seen.add(path.resolve())
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

    return read_pdf_text_with_ocr(path)


def read_pdf_text_with_ocr(path: Path) -> str:
    """OCR scanned PDFs only after the normal text extractors find nothing."""
    try:
        stat = path.stat()
        cache_key = hashlib.sha256(
            f"{path.resolve()}|{stat.st_size}|{stat.st_mtime_ns}".encode("utf-8")
        ).hexdigest()
        OCR_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path = OCR_CACHE_DIR / f"{cache_key}.txt"
        if cache_path.exists():
            return cache_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""

    print(f"OCR fallback: {path}")
    pieces = []
    try:
        with tempfile.TemporaryDirectory(prefix="bible_study_ocr_") as temp_dir:
            image_prefix = Path(temp_dir) / "page"
            rendered = subprocess.run(
                ["pdftoppm", "-jpeg", "-r", "160", str(path), str(image_prefix)],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if rendered.returncode != 0:
                return ""

            for image_path in sorted(Path(temp_dir).glob("page-*.jpg")):
                result = subprocess.run(
                    ["tesseract", str(image_path), "stdout", "-l", "eng", "--psm", "6"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode == 0 and result.stdout.strip():
                    pieces.append(result.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return ""

    text = "\n\n".join(pieces).strip()
    if text:
        cache_path.write_text(text + "\n", encoding="utf-8")
    return text


def read_docx_text(path: Path) -> str:
    """Include tables/text boxes, selecting modern OOXML over duplicate fallback."""
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    mc = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    for alternate in root.iter(mc + "AlternateContent"):
        choices = alternate.findall(mc + "Choice")
        fallback = alternate.find(mc + "Fallback")
        selected = choices[0] if choices else fallback
        for child in list(alternate):
            if child is not selected:
                alternate.remove(child)
    def paragraph_text(element):
        pieces = []
        for child in element:
            if child.tag == w + "p":
                continue
            if child.tag == w + "t":
                pieces.append(child.text or "")
            elif child.tag in {w + "br", w + "tab"}:
                pieces.append(" ")
            else:
                pieces.append(paragraph_text(child))
        return "".join(pieces)
    return "\n".join(text for p in root.iter(w + "p") if (text := paragraph_text(p).strip()))


def read_pptx_text(path: Path) -> str:
    namespace = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    try:
        with zipfile.ZipFile(path) as archive:
            slide_names = sorted(
                (name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)),
                key=lambda name: int(re.search(r"\d+", Path(name).stem).group()),
            )
            slides = []
            for slide_number, name in enumerate(slide_names, start=1):
                root = ET.fromstring(archive.read(name))
                text = [node.text.strip() for node in root.findall(".//a:t", namespace) if node.text and node.text.strip()]
                if text:
                    slides.append(f"Slide {slide_number}\n" + "\n".join(text))
            return "\n\n".join(slides)
    except Exception:
        return ""


def read_xlsx_text(path: Path) -> str:
    namespace = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    try:
        with zipfile.ZipFile(path) as archive:
            shared_strings = []
            if "xl/sharedStrings.xml" in archive.namelist():
                shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
                for item in shared_root.findall("s:si", namespace):
                    shared_strings.append("".join(node.text or "" for node in item.findall(".//s:t", namespace)))

            workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
            sheet_names = [node.attrib.get("name", "Sheet") for node in workbook_root.findall(".//s:sheet", namespace)]
            worksheet_names = sorted(
                (name for name in archive.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name)),
                key=lambda name: int(re.search(r"\d+", Path(name).stem).group()),
            )
            sheets = []
            for index, name in enumerate(worksheet_names):
                root = ET.fromstring(archive.read(name))
                rows = []
                for row in root.findall(".//s:row", namespace):
                    values = []
                    for cell in row.findall("s:c", namespace):
                        cell_type = cell.attrib.get("t")
                        if cell_type == "inlineStr":
                            value = "".join(node.text or "" for node in cell.findall(".//s:t", namespace))
                        else:
                            value_node = cell.find("s:v", namespace)
                            value = value_node.text if value_node is not None and value_node.text else ""
                            if cell_type == "s" and value.isdigit() and int(value) < len(shared_strings):
                                value = shared_strings[int(value)]
                        if value.strip():
                            values.append(f"{cell.attrib.get('r', '')}: {value.strip()}")
                    if values:
                        rows.append(" | ".join(values))
                if rows:
                    sheet_title = sheet_names[index] if index < len(sheet_names) else f"Sheet {index + 1}"
                    sheets.append(f"Worksheet: {sheet_title}\n" + "\n".join(rows))
            return "\n\n".join(sheets)
    except Exception:
        return ""


def read_pages_text(path: Path) -> str:
    if os.environ.get("BIBLE_STUDY_UNATTENDED") == "1":
        raise RuntimeError("Pages extraction deferred to a manual updater run; previous index retained")
    escaped_path = str(path).replace("\\", "\\\\").replace('"', '\\"')
    applescript = f'''
    tell application "Pages"
        set docRef to open POSIX file "{escaped_path}"
        set paraList to every paragraph of body text of docRef
        set AppleScript's text item delimiters to linefeed
        set outText to paraList as text
        close docRef saving no
    end tell
    return outText
    '''

    try:
        completed = subprocess.run(
            ["osascript", "-e", applescript],
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )
        return completed.stdout
    except Exception:
        return ""


def read_text(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix == ".rtf":
        return subprocess.run(["textutil", "-convert", "txt", "-stdout", str(path)], capture_output=True, text=True, check=True, timeout=60).stdout
    if suffix == ".pdf":
        return read_pdf_text(path)
    if suffix == ".docx":
        return read_docx_text(path)
    if suffix == ".pptx":
        return read_pptx_text(path)
    if suffix == ".xlsx":
        return read_xlsx_text(path)
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
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=30000;")
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
    columns = {row[1] for row in conn.execute("PRAGMA table_info(documents)")}
    for name, kind in (("file_size", "INTEGER"), ("modified_ns", "INTEGER"), ("content_sha256", "TEXT")):
        if name not in columns:
            conn.execute(f"ALTER TABLE documents ADD COLUMN {name} {kind}")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chunk_refs_chunk ON chunk_refs(chunk_id)")
    conn.commit()


# Helper functions for document management
def get_rel_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE))
    except Exception:
        return str(path)



def get_existing_document(conn: sqlite3.Connection, rel_path: str) -> tuple[int, float | None, str] | None:
    row = conn.execute(
        "SELECT id, modified_time, source_type FROM documents WHERE rel_path = ?",
        (rel_path,),
    ).fetchone()
    if row is None:
        return None
    return row[0], row[1], row[2]



def delete_document_by_id(conn: sqlite3.Connection, document_id: int) -> None:
    rows = conn.execute("""
        SELECT c.id, c.content, d.title, d.rel_path, d.source_type
        FROM chunks c JOIN documents d ON d.id=c.document_id WHERE d.id=?
    """, (document_id,)).fetchall()
    for row in rows:
        # Contentless FTS5 requires exactly the original indexed values.
        conn.execute("INSERT INTO chunks_fts(chunks_fts,rowid,content,title,rel_path,source_type) VALUES('delete',?,?,?,?,?)", row)
        conn.execute("DELETE FROM chunk_refs WHERE chunk_id=?", (row[0],))
    conn.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
    conn.execute("DELETE FROM documents WHERE id=?", (document_id,))


def remove_stale_documents(conn: sqlite3.Connection, valid_rel_paths: set[str]) -> None:
    rows = conn.execute("SELECT id, rel_path FROM documents").fetchall()
    for document_id, rel_path in rows:
        if rel_path not in valid_rel_paths:
            delete_document_by_id(conn, document_id)


def index_file(conn: sqlite3.Connection, path: Path) -> None:
    rel_path = get_rel_path(path)
    title = path.stem
    source_type = guess_source_type(path)
    stat = path.stat()
    modified_time = stat.st_mtime
    indexed_at = datetime.now().isoformat(timespec="seconds")
    existing = get_existing_document(conn, rel_path)
    fingerprint = conn.execute("SELECT file_size, modified_ns, content_sha256 FROM documents WHERE rel_path=?", (rel_path,)).fetchone()
    if existing and existing[2] == source_type:
        if fingerprint[0] == stat.st_size and fingerprint[1] == stat.st_mtime_ns:
            return
        # Adopt metadata for pre-migration entries without reopening unchanged Pages.
        if fingerprint[0] is None and existing[1] == modified_time:
            conn.execute("UPDATE documents SET file_size=?,modified_ns=? WHERE id=?", (stat.st_size,stat.st_mtime_ns,existing[0]))
            conn.commit()
            return
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if existing and existing[2] == source_type and fingerprint[2] == digest:
        conn.execute("UPDATE documents SET modified_time=?,file_size=?,modified_ns=? WHERE id=?", (modified_time,stat.st_size,stat.st_mtime_ns,existing[0]))
        conn.commit()
        return
    text = read_text(path)
    if not text.strip():
        raise RuntimeError(f"Extraction empty or failed; previous index retained: {path}")
    after = path.stat()
    if (after.st_size,after.st_mtime_ns) != (stat.st_size,stat.st_mtime_ns):
        raise RuntimeError(f"File changed during extraction; retry next run: {path}")
    chunks = split_into_chunks(text)
    # All writes below are one transaction; caller rolls back on any failure.
    if existing:
        delete_document_by_id(conn, existing[0])

    cur = conn.cursor()
    cur.execute("""
        INSERT INTO documents (rel_path, title, source_type, modified_time, indexed_at)
        VALUES (?, ?, ?, ?, ?)
    """, (rel_path, title, source_type, modified_time, indexed_at))
    document_id = cur.lastrowid
    cur.execute("UPDATE documents SET file_size=?,modified_ns=?,content_sha256=? WHERE id=?", (stat.st_size,stat.st_mtime_ns,digest,document_id))

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
        from repair_search_index import repair
        if repair(conn):
            print("Repaired full-text index from stored chunks; source files were not reopened.", flush=True)

        files = collect_files()
        valid_rel_paths = {get_rel_path(path) for path in files}
        # Do not automatically prune: an unavailable iCloud root is not a deletion.
        # Missing paths remain searchable pending an explicit reconciliation.
        conn.commit()

        print(f"Found {len(files)} files to index.\n")

        failures = []
        for path in files:
            try:
                index_file(conn, path)
            except Exception as exc:
                conn.rollback()
                failures.append({"path": str(path), "error": str(exc)})
                print(f"ERROR: {path}: {exc}", flush=True)
        atomic_write_text(DB_PATH.parent / "index_errors.json", json.dumps(failures, indent=2))
        if failures:
            raise RuntimeError(f"{len(failures)} files failed; see index_errors.json")

        print(f"\nIndex complete: {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
