from pathlib import Path
import sqlite3
import sys
import re

BASE = Path("/Users/george/Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid")
DB_PATH = BASE / "99_Index" / "bible_study.db"

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

ABBREVIATION_MAP = {
    "gen": "Genesis", "ge": "Genesis",
    "exo": "Exodus", "ex": "Exodus",
    "lev": "Leviticus", "le": "Leviticus",
    "num": "Numbers", "nu": "Numbers",
    "deut": "Deuteronomy", "deu": "Deuteronomy",
    "josh": "Joshua", "jos": "Joshua",
    "judg": "Judges", "jdg": "Judges",
    "ruth": "Ruth",
    "1 sam": "1 Samuel", "2 sam": "2 Samuel",
    "1 kgs": "1 Kings", "2 kgs": "2 Kings",
    "1 chr": "1 Chronicles", "2 chr": "2 Chronicles",
    "ezra": "Ezra",
    "neh": "Nehemiah", "ne": "Nehemiah",
    "est": "Esther",
    "job": "Job",
    "ps": "Psalms", "psa": "Psalms",
    "prov": "Proverbs", "pro": "Proverbs",
    "eccl": "Ecclesiastes", "ecc": "Ecclesiastes",
    "song": "Song of Solomon",
    "isa": "Isaiah",
    "jer": "Jeremiah",
    "lam": "Lamentations",
    "ezek": "Ezekiel", "eze": "Ezekiel",
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
    "matt": "Matthew", "mt": "Matthew",
    "mk": "Mark", "mrk": "Mark", "mark": "Mark",
    "lk": "Luke", "lu": "Luke",
    "jn": "John", "joh": "John",
    "acts": "Acts", "act": "Acts",
    "rom": "Romans", "ro": "Romans",
    "1 cor": "1 Corinthians", "2 cor": "2 Corinthians",
    "gal": "Galatians",
    "eph": "Ephesians",
    "phil": "Philippians", "php": "Philippians",
    "col": "Colossians",
    "1 thess": "1 Thessalonians", "2 thess": "2 Thessalonians",
    "1 tim": "1 Timothy", "2 tim": "2 Timothy",
    "tit": "Titus",
    "philem": "Philemon", "phm": "Philemon",
    "heb": "Hebrews",
    "jas": "James", "jam": "James",
    "1 pet": "1 Peter", "2 pet": "2 Peter",
    "1 jn": "1 John", "2 jn": "2 John", "3 jn": "3 John",
    "jude": "Jude",
    "rev": "Revelation", "re": "Revelation",
}

STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "from", "have", "your",
    "about", "into", "they", "them", "then", "than", "were", "will", "what",
    "when", "where", "which", "their", "there", "would", "could", "should",
    "unto", "upon", "also", "only", "been", "being", "through", "some",
    "more", "does", "did", "not", "give", "information", "chapter", "verse"
}

TOPIC_EXPANSIONS = {
    "7 feasts of israel": [
        "passover",
        "unleavened bread",
        "firstfruits",
        "pentecost",
        "feast of trumpets",
        "trumpets",
        "day of atonement",
        "atonement",
        "tabernacles",
        "feast of tabernacles",
        "leviticus 23",
        "holy convocations",
        "feasts of the lord",
        "seven feasts",
    ],
    "seven feasts of israel": [
        "passover",
        "unleavened bread",
        "firstfruits",
        "pentecost",
        "feast of trumpets",
        "trumpets",
        "day of atonement",
        "atonement",
        "tabernacles",
        "feast of tabernacles",
        "leviticus 23",
        "holy convocations",
        "feasts of the lord",
        "seven feasts",
    ],
    "spiritual leadership": [
        "leadership",
        "leader",
        "elders",
        "bishop",
        "pastor",
        "overseer",
        "rule well",
        "servant leadership",
        "ministry leadership",
    ],
    "premillennial rapture": [
        "rapture",
        "caught up",
        "blessed hope",
        "pretribulation",
        "tribulation",
        "second coming",
        "millennial kingdom",
        "1 thessalonians 4",
        "1 corinthians 15",
        "titus 2:13",
    ],
    "nehemiah rebuilding the people": [
        "nehemiah",
        "rebuilding the people",
        "revival",
        "the people",
        "ezra",
        "the wall",
        "restore",
    ],
}

QUERY_REFERENCE_REGEX = re.compile(
    r"\b((?:[1-3]\s+)?[A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(\d+)(?::(\d+(?:-\d+)?))?\b",
    re.IGNORECASE,
)


def tokenize(text: str):
    return re.findall(r"[a-z0-9']+", text.lower())


def normalize_query_tokens(query: str):
    return [t for t in tokenize(query) if t not in STOP_WORDS and len(t) > 1]


def get_topic_expansion_terms(query: str):
    q = query.strip().lower()
    terms = []
    for topic, expansions in TOPIC_EXPANSIONS.items():
        if q == topic or topic in q or q in topic:
            terms.extend(expansions)
    return terms


def get_topic_anchor_rules(query: str):
    q = query.strip().lower()
    if q in {"7 feasts of israel", "seven feasts of israel"}:
        return {
            "required_any": {"leviticus 23", "holy convocations", "feasts of the lord"},
            "minimum_topic_matches": 2,
        }
    return None


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

    if verse:
        return f"{normalized_book} {chapter}:{verse}"
    return f"{normalized_book} {chapter}"


def make_fts_query(query: str, query_tokens, topic_terms):
    phrases = []
    if query.strip():
        phrases.append(f'"{query.strip()}"')

    for token in query_tokens:
        phrases.append(token)

    for term in topic_terms:
        if " " in term:
            phrases.append(f'"{term}"')
        else:
            phrases.append(term)

    seen = []
    for item in phrases:
        if item not in seen:
            seen.append(item)

    return " OR ".join(seen[:20])


def build_snippet(text: str, query: str, topic_terms=None, query_reference=None):
    if topic_terms is None:
        topic_terms = []

    lower_text = text.lower()
    search_terms = []

    if query_reference:
        search_terms.append(query_reference.lower())

    search_terms.extend(term.lower() for term in topic_terms)
    search_terms.append(query.lower())

    best_pos = None
    for term in search_terms:
        if not term:
            continue
        pos = lower_text.find(term)
        if pos != -1 and (best_pos is None or pos < best_pos):
            best_pos = pos

    if best_pos is None:
        snippet = text[:350].replace("\n", " ").strip()
        return snippet

    start = max(0, best_pos - 120)
    end = min(len(text), best_pos + 350)
    snippet = text[start:end].replace("\n", " ").strip()

    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet += "..."

    return snippet


def run_query(query: str, limit: int = 20):
    query_tokens = normalize_query_tokens(query)
    query_reference = extract_query_reference(query)
    topic_terms = get_topic_expansion_terms(query)
    topic_rules = get_topic_anchor_rules(query) or {}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        results = []

        if query_reference:
            ref_rows = conn.execute(
                """
                SELECT
                    c.id AS chunk_id,
                    d.title,
                    d.rel_path,
                    d.source_type,
                    c.content,
                    COUNT(cr.scripture_ref) AS ref_hits
                FROM chunk_refs cr
                JOIN chunks c ON c.id = cr.chunk_id
                JOIN documents d ON d.id = c.document_id
                WHERE cr.scripture_ref = ?
                GROUP BY c.id, d.title, d.rel_path, d.source_type, c.content
                ORDER BY
                    CASE d.source_type
                        WHEN 'commentary' THEN 1
                        WHEN 'sermon_note' THEN 2
                        WHEN 'blog' THEN 3
                        WHEN 'podcast' THEN 4
                        ELSE 5
                    END,
                    d.title
                LIMIT ?
                """,
                (query_reference, limit)
            ).fetchall()

            for row in ref_rows:
                results.append({
                    "score": 1000,
                    "title": row["title"],
                    "path": row["rel_path"],
                    "source_type": row["source_type"],
                    "snippet": build_snippet(row["content"], query, topic_terms, query_reference),
                })

        fts_query = make_fts_query(query, query_tokens, topic_terms)
        if fts_query:
            fts_rows = conn.execute(
                """
                SELECT
                    c.id AS chunk_id,
                    d.title,
                    d.rel_path,
                    d.source_type,
                    c.content,
                    bm25(chunks_fts, 10.0, 5.0, 3.0, 2.0) AS rank
                FROM chunks_fts
                JOIN chunks c ON c.id = chunks_fts.rowid
                JOIN documents d ON d.id = c.document_id
                WHERE chunks_fts MATCH ?
                ORDER BY rank
                LIMIT 100
                """,
                (fts_query,)
            ).fetchall()

            for row in fts_rows:
                text = row["content"]
                lower_text = text.lower()
                lower_path = row["rel_path"].lower()

                bonus = 0
                topic_match_count = 0

                if query.lower() in lower_path:
                    bonus += 80
                if query.lower() in lower_text:
                    bonus += 40

                if query_reference:
                    if query_reference.lower() in lower_text:
                        bonus += 150
                    if query_reference.lower() in lower_path:
                        bonus += 180

                for term in topic_terms:
                    term_lower = term.lower()
                    matched_this_term = False

                    if term_lower in lower_text:
                        bonus += 40
                        matched_this_term = True
                    if term_lower in lower_path:
                        bonus += 60
                        matched_this_term = True

                    if matched_this_term:
                        topic_match_count += 1

                if topic_match_count >= 3:
                    bonus += 120
                elif topic_match_count >= 2:
                    bonus += 60

                required_any = {term.lower() for term in topic_rules.get("required_any", set())}
                minimum_topic_matches = topic_rules.get("minimum_topic_matches")

                if required_any:
                    anchor_hit = any(term in lower_text or term in lower_path for term in required_any)
                    if not anchor_hit and topic_match_count < 2:
                        bonus -= 120

                if minimum_topic_matches is not None and topic_match_count < minimum_topic_matches:
                    bonus -= 80

                score = int(500 - row["rank"] * 100 + bonus)

                results.append({
                    "score": score,
                    "title": row["title"],
                    "path": row["rel_path"],
                    "source_type": row["source_type"],
                    "snippet": build_snippet(text, query, topic_terms, query_reference),
                })

        deduped = []
        seen = set()
        for item in sorted(results, key=lambda x: (-x["score"], x["path"])):
            key = (item["path"], item["snippet"])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)

        final_results = []
        path_counts = {}

        for item in deduped:
            count = path_counts.get(item["path"], 0)
            if count >= 2:
                continue

            final_results.append(item)
            path_counts[item["path"]] = count + 1

            if len(final_results) >= limit:
                break

        return final_results

    finally:
        conn.close()


def main():
    if len(sys.argv) < 2:
        print('Usage: python3 query_bible_study.py "your search here"')
        return

    query = " ".join(sys.argv[1:]).strip()
    results = run_query(query)

    print()
    print(f"Query: {query}")
    print(f"Results: {len(results)}")
    print()

    for i, item in enumerate(results, start=1):
        print(f"{i}. [{item['score']}] ({item['source_type']}) {item['path']}")
        print(f"   {item['snippet']}")
        print()


if __name__ == "__main__":
    main()