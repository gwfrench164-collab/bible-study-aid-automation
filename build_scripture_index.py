from pathlib import Path
import re
import sys
import sqlite3
import io
from pipeline_support import atomic_write_text
from library_settings import LIBRARY_ROOT
from collections import defaultdict, Counter

BASE = LIBRARY_ROOT  # set BIBLE_STUDY_LIBRARY_ROOT to use a different library folder
INDEX_DIR = BASE / "99_Index"
INDEX_FILE = INDEX_DIR / "scripture_index.txt"

SEARCH_FOLDERS = [
    BASE / "02_LFBI",
    BASE / "03_Sermon_Notes",
    BASE / "04_Commentaries",
    BASE / "05_Podcasts",
    BASE / "06_Blogs",
]

from bible_refs import BOOK_PATTERNS, BOOK_CHAPTER_LIMITS, ABBREVIATION_MAP

BOOK_ORDER = {book: i for i, book in enumerate(BOOK_PATTERNS)}
BOOK_REGEX = "|".join(re.escape(book) for book in BOOK_PATTERNS)
REFERENCE_REGEX = re.compile(rf"\b({BOOK_REGEX})\s+(\d+)(?::(\d+(?:-\d+)?))?\b", re.IGNORECASE)

QUERY_REFERENCE_REGEX = re.compile(
    r"\b((?:[1-3]\s+)?[A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(\d+)(?::(\d+(?:-\d+)?))?\b",
    re.IGNORECASE,
)

READABLE_SUFFIXES = {".txt", ".md", ".rtf"}

SNIPPET_LENGTH = 220
MAX_RESULTS = 12
STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "from", "have", "your",
    "about", "into", "they", "them", "then", "than", "were", "will", "what",
    "when", "where", "which", "their", "there", "would", "could", "should",
    "unto", "upon", "also", "only", "been", "being", "through", "some",
    "more", "does", "did", "not", "give", "information", "chapter", "verse"
}


def normalize_book_name(book: str) -> str:
    for b in BOOK_PATTERNS:
        if b.lower() == book.lower():
            return b
    return book


def is_valid_reference(book: str, chapter: str) -> bool:
    try:
        chapter_num = int(chapter)
    except ValueError:
        return False
    return 1 <= chapter_num <= BOOK_CHAPTER_LIMITS.get(book, 999)


def normalize_reference(match):
    book = normalize_book_name(match.group(1))
    chapter = match.group(2)
    verse = match.group(3)

    if not is_valid_reference(book, chapter):
        return None

    if verse:
        return f"{book} {chapter}:{verse}"
    return f"{book} {chapter}"


def extract_query_reference(query: str):
    q = query.strip()
    match = QUERY_REFERENCE_REGEX.search(q)
    if not match:
        return None

    raw_book = match.group(1).strip().lower()
    chapter = match.group(2)
    verse = match.group(3)

    normalized_book = None

    for alias, full_book in sorted(ABBREVIATION_MAP.items(), key=lambda item: -len(item[0])):
        if raw_book == alias:
            normalized_book = full_book
            break

    if normalized_book is None:
        for full_book in BOOK_PATTERNS:
            if raw_book == full_book.lower():
                normalized_book = full_book
                break

    if normalized_book is None:
        return None

    if not is_valid_reference(normalized_book, chapter):
        return None

    if verse:
        return f"{normalized_book} {chapter}:{verse}"
    return f"{normalized_book} {chapter}"


def parse_reference(ref: str):
    """Sort key for a stored reference such as 'Song of Solomon 2:1' or '1 John 3:16-18'."""
    match = re.match(r"^(.+?)\s+(\d+)(?::(\d+))?", ref)
    if not match:
        return 999, 999, 0, ref
    book, chapter, verse = match.groups()
    return BOOK_ORDER.get(book, 999), int(chapter), int(verse or 0), ref


def scan_file(path: Path):
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return set()

    refs = set()
    for match in REFERENCE_REGEX.finditer(text):
        normalized = normalize_reference(match)
        if normalized:
            refs.add(normalized)
    return refs


def tokenize(text: str):
    return re.findall(r"[a-z0-9']+", text.lower())


def normalize_query_tokens(query: str):
    raw_tokens = tokenize(query)
    tokens = [t for t in raw_tokens if t not in STOP_WORDS and len(t) > 1]
    return tokens


def expand_token_forms(token: str):
    forms = {token}

    if token.endswith("ies") and len(token) > 4:
        forms.add(token[:-3] + "y")
    if token.endswith("y") and len(token) > 3:
        forms.add(token[:-1] + "ies")

    if token.endswith("es") and len(token) > 4:
        forms.add(token[:-2])
    if token.endswith("s") and len(token) > 3:
        forms.add(token[:-1])
    else:
        forms.add(token + "s")

    if token.endswith("ing") and len(token) > 5:
        forms.add(token[:-3])
    if token.endswith("ed") and len(token) > 4:
        forms.add(token[:-2])

    return {f for f in forms if len(f) > 1}


def collect_searchable_files():
    files = []
    for folder in SEARCH_FOLDERS:
        if not folder.exists():
            continue
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() in READABLE_SUFFIXES:
                files.append(path)
    return files


def build_snippet(text: str, matched_forms, query_reference=None):
    lower_text = text.lower()
    best_pos = None

    if query_reference:
        pos = lower_text.find(query_reference.lower())
        if pos != -1:
            best_pos = pos

    if best_pos is None:
        for form in matched_forms:
            pos = lower_text.find(form.lower())
            if pos != -1 and (best_pos is None or pos < best_pos):
                best_pos = pos

    if best_pos is None:
        snippet = text[:SNIPPET_LENGTH]
        return snippet.replace("\n", " ").strip()

    start = max(0, best_pos - 80)
    end = min(len(text), best_pos + SNIPPET_LENGTH)
    snippet = text[start:end].replace("\n", " ").strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


def score_file(text: str, query: str, query_tokens, query_reference=None):
    lower_text = text.lower()
    token_counter = Counter(tokenize(text))

    score = 0
    matched_forms = set()

    if query_reference:
        query_reference_lower = query_reference.lower()
        if query_reference_lower in lower_text:
            score += 140
            matched_forms.add(query_reference_lower)

        ref_parts = query_reference.split(" ", 1)
        book_name = ref_parts[0]
        remainder = ref_parts[1] if len(ref_parts) > 1 else ""
        if book_name in {"1", "2", "3"} and remainder:
            remainder_parts = remainder.split(" ", 1)
            book_name = f"{book_name} {remainder_parts[0]}"
            remainder = remainder_parts[1] if len(remainder_parts) > 1 else ""

        chapter_only = remainder.split(":", 1)[0] if remainder else ""
        book_phrase = book_name.lower()
        chapter_phrase = f"{book_name.lower()} {chapter_only}".strip()
        chapter_words = f"{book_name.lower()} chapter {chapter_only}".strip()

        if book_phrase and book_phrase in lower_text:
            score += 20
            matched_forms.add(book_phrase)
        if chapter_phrase and chapter_phrase in lower_text:
            score += 40
            matched_forms.add(chapter_phrase)
        if chapter_words and chapter_words in lower_text:
            score += 40
            matched_forms.add(chapter_words)

    if query.lower() in lower_text:
        score += 30
        matched_forms.add(query.lower())

    phrase_parts = [part.strip() for part in re.split(r"[:,;]", query.lower()) if part.strip()]
    for part in phrase_parts:
        if len(part) >= 4 and part in lower_text:
            score += 12
            matched_forms.add(part)

    matched_token_count = 0
    for token in query_tokens:
        forms = expand_token_forms(token)
        token_score = 0
        found_form = None

        for form in forms:
            count = token_counter.get(form, 0)
            if count > 0:
                token_score = max(token_score, min(count, 4))
                found_form = form

        if found_form:
            matched_token_count += 1
            score += token_score + 2
            matched_forms.add(found_form)

    if query_tokens and matched_token_count == len(query_tokens):
        score += 12
    elif len(query_tokens) >= 3 and matched_token_count >= 2:
        score += 4

    return score, matched_forms


def run_search(query: str):
    query_tokens = normalize_query_tokens(query)
    query_reference = extract_query_reference(query)

    if not query_tokens and not query_reference:
        print("Please enter a more specific search.")
        return

    results = []

    for path in collect_searchable_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        score, matched_forms = score_file(text, query, query_tokens, query_reference=query_reference)
        if score <= 0:
            continue

        rel_path = path.relative_to(BASE)
        snippet = build_snippet(text, matched_forms, query_reference=query_reference)
        results.append((score, str(rel_path), snippet))

    results.sort(key=lambda item: (-item[0], item[1]))

    print()
    print(f"Search query: {query}")
    if query_reference:
        print(f"Recognized reference: {query_reference}")
    print(f"Results found: {len(results)}")
    print()

    if not results:
        print("No matching results found.")
        return

    for idx, (score, rel_path, snippet) in enumerate(results[:MAX_RESULTS], start=1):
        print(f"{idx}. [{score}] {rel_path}")
        print(f"   {snippet}")
        print()


def build_scripture_index():
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    scripture_map = defaultdict(set)

    database = INDEX_DIR / "bible_study.db"
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as conn:
        for ref, path in conn.execute("SELECT DISTINCT r.scripture_ref,d.rel_path FROM chunk_refs r JOIN chunks c ON c.id=r.chunk_id JOIN documents d ON d.id=c.document_id"):
            match = REFERENCE_REGEX.fullmatch(ref)
            if match and normalize_reference(match):
                scripture_map[ref].add(path)

    grouped = defaultdict(list)
    for ref in scripture_map:
        book_index, _, _, _ = parse_reference(ref)
        if book_index < len(BOOK_PATTERNS):
            grouped[BOOK_PATTERNS[book_index]].append(ref)

    with io.StringIO() as f:
        for book in BOOK_PATTERNS:
            refs = grouped.get(book, [])
            if not refs:
                continue

            f.write(book + "\n")
            f.write("=" * len(book) + "\n\n")

            for ref in sorted(refs, key=parse_reference):
                paths = sorted(scripture_map[ref])
                f.write(f"{ref} ({len(paths)})\n")
                for file_path in paths:
                    f.write(f"  - {file_path}\n")
                f.write("\n")

        output = f.getvalue()
    if not INDEX_FILE.exists() or INDEX_FILE.read_text(encoding="utf-8") != output:
        atomic_write_text(INDEX_FILE, output)

    print(f"Scripture index written to: {INDEX_FILE}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:]).strip()
        run_search(query)
    else:
        build_scripture_index()