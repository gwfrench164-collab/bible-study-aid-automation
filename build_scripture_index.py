from pathlib import Path
import re
import sys
from collections import defaultdict, Counter

BASE = Path("/Users/george/Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid")
INDEX_DIR = BASE / "99_Index"
INDEX_FILE = INDEX_DIR / "scripture_index.txt"

SEARCH_FOLDERS = [
    BASE / "02_LFBI",
    BASE / "03_Sermon_Notes",
    BASE / "04_Commentaries",
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

BOOK_CHAPTER_LIMITS = {
    "Genesis": 50, "Exodus": 40, "Leviticus": 27, "Numbers": 36, "Deuteronomy": 34,
    "Joshua": 24, "Judges": 21, "Ruth": 4, "1 Samuel": 31, "2 Samuel": 24,
    "1 Kings": 22, "2 Kings": 25, "1 Chronicles": 29, "2 Chronicles": 36,
    "Ezra": 10, "Nehemiah": 13, "Esther": 10, "Job": 42, "Psalms": 150,
    "Proverbs": 31, "Ecclesiastes": 12, "Song of Solomon": 8, "Isaiah": 66,
    "Jeremiah": 52, "Lamentations": 5, "Ezekiel": 48, "Daniel": 12,
    "Hosea": 14, "Joel": 3, "Amos": 9, "Obadiah": 1, "Jonah": 4, "Micah": 7,
    "Nahum": 3, "Habakkuk": 3, "Zephaniah": 3, "Haggai": 2, "Zechariah": 14,
    "Malachi": 4, "Matthew": 28, "Mark": 16, "Luke": 24, "John": 21,
    "Acts": 28, "Romans": 16, "1 Corinthians": 16, "2 Corinthians": 13,
    "Galatians": 6, "Ephesians": 6, "Philippians": 4, "Colossians": 4,
    "1 Thessalonians": 5, "2 Thessalonians": 3, "1 Timothy": 6, "2 Timothy": 4,
    "Titus": 3, "Philemon": 1, "Hebrews": 13, "James": 5, "1 Peter": 5,
    "2 Peter": 3, "1 John": 5, "2 John": 1, "3 John": 1, "Jude": 1,
    "Revelation": 22,
}

BOOK_ORDER = {book: i for i, book in enumerate(BOOK_PATTERNS)}
BOOK_REGEX = "|".join(re.escape(book) for book in BOOK_PATTERNS)
REFERENCE_REGEX = re.compile(rf"\b({BOOK_REGEX})\s+(\d+)(?::(\d+(?:-\d+)?))?\b", re.IGNORECASE)

QUERY_REFERENCE_REGEX = re.compile(
    r"\b((?:[1-3]\s+)?[A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(\d+)(?::(\d+(?:-\d+)?))?\b",
    re.IGNORECASE,
)

ABBREVIATION_MAP = {
    "gen": "Genesis",
    "ge": "Genesis",
    "exo": "Exodus",
    "ex": "Exodus",
    "lev": "Leviticus",
    "le": "Leviticus",
    "num": "Numbers",
    "nu": "Numbers",
    "deut": "Deuteronomy",
    "deu": "Deuteronomy",
    "josh": "Joshua",
    "jos": "Joshua",
    "judg": "Judges",
    "jdg": "Judges",
    "ruth": "Ruth",
    "1 sam": "1 Samuel",
    "2 sam": "2 Samuel",
    "1 kgs": "1 Kings",
    "2 kgs": "2 Kings",
    "1 chr": "1 Chronicles",
    "2 chr": "2 Chronicles",
    "ezra": "Ezra",
    "neh": "Nehemiah",
    "ne": "Nehemiah",
    "est": "Esther",
    "job": "Job",
    "ps": "Psalms",
    "psa": "Psalms",
    "prov": "Proverbs",
    "pro": "Proverbs",
    "eccl": "Ecclesiastes",
    "ecc": "Ecclesiastes",
    "song": "Song of Solomon",
    "isa": "Isaiah",
    "jer": "Jeremiah",
    "lam": "Lamentations",
    "ezek": "Ezekiel",
    "eze": "Ezekiel",
    "dan": "Daniel",
    "hos": "Hosea",
    "joe": "Joel",
    "amos": "Amos",
    "obad": "Obadiah",
    "jon": "Jonah",
    "mic": "Micah",
    "nah": "Nahum",
    "hab": "Habakkuk",
    "zeph": "Zephaniah",
    "hag": "Haggai",
    "zech": "Zechariah",
    "mal": "Malachi",
    "matt": "Matthew",
    "mt": "Matthew",
    "mk": "Mark",
    "mrk": "Mark",
    "mark": "Mark",
    "lk": "Luke",
    "lu": "Luke",
    "jn": "John",
    "joh": "John",
    "acts": "Acts",
    "act": "Acts",
    "rom": "Romans",
    "ro": "Romans",
    "1 cor": "1 Corinthians",
    "2 cor": "2 Corinthians",
    "gal": "Galatians",
    "eph": "Ephesians",
    "phil": "Philippians",
    "php": "Philippians",
    "col": "Colossians",
    "1 thess": "1 Thessalonians",
    "2 thess": "2 Thessalonians",
    "1 tim": "1 Timothy",
    "2 tim": "2 Timothy",
    "tit": "Titus",
    "philem": "Philemon",
    "phm": "Philemon",
    "heb": "Hebrews",
    "jas": "James",
    "jam": "James",
    "1 pet": "1 Peter",
    "2 pet": "2 Peter",
    "1 jn": "1 John",
    "2 jn": "2 John",
    "3 jn": "3 John",
    "jude": "Jude",
    "rev": "Revelation",
    "re": "Revelation",
}

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
    parts = ref.split(" ", 1)
    book = parts[0]
    rest = parts[1] if len(parts) > 1 else ""

    if book in {"1", "2", "3"} and rest:
        parts2 = rest.split(" ", 1)
        book = f"{book} {parts2[0]}"
        rest = parts2[1] if len(parts2) > 1 else ""

    if ":" in rest:
        chapter_str, verse_str = rest.split(":", 1)
    else:
        chapter_str, verse_str = rest, ""

    try:
        chapter_num = int(chapter_str)
    except ValueError:
        chapter_num = 999

    verse_num = 0
    if verse_str:
        first_verse = verse_str.split("-", 1)[0]
        try:
            verse_num = int(first_verse)
        except ValueError:
            verse_num = 0

    return BOOK_ORDER.get(book, 999), chapter_num, verse_num, ref


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

    for folder in SEARCH_FOLDERS:
        if not folder.exists():
            continue
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() in READABLE_SUFFIXES:
                refs = scan_file(path)
                rel_path = path.relative_to(BASE)
                for ref in refs:
                    scripture_map[ref].add(str(rel_path))

    grouped = defaultdict(list)
    for ref in scripture_map:
        book_index, _, _, _ = parse_reference(ref)
        if book_index < len(BOOK_PATTERNS):
            grouped[BOOK_PATTERNS[book_index]].append(ref)

    with INDEX_FILE.open("w", encoding="utf-8") as f:
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

    print(f"Scripture index written to: {INDEX_FILE}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:]).strip()
        run_search(query)
    else:
        build_scripture_index()