from pathlib import Path
import re
from collections import defaultdict

BASE = Path("/Users/george/Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid")
INDEX_DIR = BASE / "99_Index"
INDEX_FILE = INDEX_DIR / "scripture_index.txt"

SEARCH_FOLDERS = [
    BASE / "02_LFBI",
    BASE / "03_Sermon_Notes",
    BASE / "05_Podcasts",
    BASE / "06_Blogs",
]

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
REFERENCE_REGEX = re.compile(rf"\b({BOOK_REGEX})\s+(\d+)(?::(\d+(?:-\d+)?))?\b", re.IGNORECASE)


def normalize_reference(match):
    book = match.group(1)
    chapter = match.group(2)
    verse = match.group(3)

    # normalize capitalization for matching book names
    for b in BOOK_PATTERNS:
        if b.lower() == book.lower():
            book = b
            break

    if verse:
        return f"{book} {chapter}:{verse}"
    return f"{book} {chapter}"


def scan_file(path: Path):
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return set()

    refs = set()
    for match in REFERENCE_REGEX.finditer(text):
        refs.add(normalize_reference(match))
    return refs


def main():
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    scripture_map = defaultdict(list)

    for folder in SEARCH_FOLDERS:
        if not folder.exists():
            continue
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".txt", ".md", ".json", ".rtf"}:
                refs = scan_file(path)
                rel_path = path.relative_to(BASE)
                for ref in refs:
                    scripture_map[ref].append(str(rel_path))

    with INDEX_FILE.open("w", encoding="utf-8") as f:
        for ref in sorted(scripture_map.keys()):
            f.write(ref + "\n")
            for file_path in sorted(set(scripture_map[ref])):
                f.write(f"  - {file_path}\n")
            f.write("\n")

    print(f"Scripture index written to: {INDEX_FILE}")


if __name__ == "__main__":
    main()