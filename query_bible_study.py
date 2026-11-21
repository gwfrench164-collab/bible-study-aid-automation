from pathlib import Path
import sqlite3
import hashlib
import sys
import re

from library_settings import LIBRARY_ROOT as BASE, INDEX_PATH as DB_PATH

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


def focus_words(query):
    """Drop common question framing while keeping meaningful verbs in short searches."""
    words = normalize_query_tokens(query)
    if re.match(r"^(what|how|why|who|where|when|does|do|can|should)\b", query.strip(), re.I):
        framing = {"how", "why", "who", "can", "do", "we", "us", "is", "are", "in",
                   "of", "to", "on", "an", "say", "says", "teach", "teaches", "tell",
                   "me", "bible", "scripture"}
        focused = [word for word in words if word not in framing]
        if focused:
            return list(dict.fromkeys(focused))
    return list(dict.fromkeys(words))


def passage_focus(text, words):
    """Prefer distinct terms occurring together within a readable excerpt."""
    if not words:
        return 0, None
    pattern = r"\b(?:" + "|".join(map(re.escape, words)) + r")\b"
    hits = list(re.finditer(pattern, text, re.I))
    counts = {}
    left = 0
    best_score, position = 0, None
    for hit in hits:
        word = hit.group().lower()
        counts[word] = counts.get(word, 0) + 1
        while hit.start() - hits[left].start() > 200 or counts[hits[left].group().lower()] > 1:
            first = hits[left].group().lower()
            counts[first] -= 1
            if not counts[first]:
                del counts[first]
            left += 1
        span = hit.start() - hits[left].start()
        score = 120 * len(counts) + (max(0, 80 - span // 3) if len(counts) > 1 else 0)
        if score > best_score:
            best_score, position = score, hits[left].start()
    return best_score, position


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
    names = {book.lower(): book for book in BOOK_PATTERNS}
    names.update(ABBREVIATION_MAP)
    names["psalm"] = "Psalms"
    pattern = r"(?<!\w)(" + "|".join(re.escape(name) for name in sorted(names, key=len, reverse=True))
    pattern += r")\.?\s*(\d+)(?:\s*:\s*(\d+)(?:\s*[-–—]\s*(\d+))?)?(?!\d)"
    match = re.search(pattern, query, re.I)
    if not match:
        return None
    book, chapter, start, end = match.groups()
    if int(chapter) < 1 or (start and int(start) < 1) or (end and int(end) < int(start)):
        return None
    reference = f"{names[book.lower()]} {int(chapter)}"
    if start:
        reference += f":{int(start)}"
        if end:
            reference += f"-{int(end)}"
    return reference


def references_overlap(left, right):
    """Compare indexed single-chapter references, including verse ranges."""
    left_chapter, _, left_verses = left.partition(":")
    right_chapter, _, right_verses = right.partition(":")
    if left_chapter != right_chapter:
        return False
    if not left_verses or not right_verses:
        return True
    try:
        a = [int(v) for v in left_verses.split("-")]
        b = [int(v) for v in right_verses.split("-")]
    except ValueError:
        return False
    return a[0] <= b[-1] and b[0] <= a[-1]


def fts_phrase(value: str) -> str:
    return f'"{value.strip().replace(chr(34), chr(34) * 2)}"'


def make_fts_query(query: str, query_tokens, topic_terms, search_mode: str = "balanced"):
    if search_mode == "exact":
        return fts_phrase(query) if query.strip() else ""

    if search_mode == "all":
        required = [token for token in query_tokens if token]
        return " AND ".join(fts_phrase(token) for token in required[:20])

    phrases = []
    if query.strip():
        phrases.append(fts_phrase(query))

    for token in query_tokens:
        phrases.append(fts_phrase(token))

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

    if not query_reference and query.lower() not in lower_text:
        _, focus = passage_focus(text, focus_words(query))
        if focus is not None:
            best_pos = focus
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


def passage_anchor(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def resolve_passage_id(path, chunk_id, anchor=""):
    """Keep a source passage addressable when an index rebuild changes row IDs."""
    conn = sqlite3.connect(DB_PATH.as_uri() + "?mode=ro", uri=True)
    try:
        rows = conn.execute("""SELECT c.id,c.content FROM chunks c JOIN documents d
            ON d.id=c.document_id WHERE d.rel_path=?
            ORDER BY (c.id=?) DESC,c.chunk_index""", (path,chunk_id))
        for found_id, text in rows:
            if anchor:
                if passage_anchor(text) == anchor:
                    return found_id
            elif found_id == chunk_id:
                return found_id
        return None
    finally:
        conn.close()


def read_passage(path, chunk_id):
    """Read the selected indexed passage and its immediate neighbors in source order."""
    conn = sqlite3.connect(DB_PATH.as_uri() + "?mode=ro", uri=True)
    try:
        return conn.execute("""
            SELECT context.id, context.content FROM chunks selected
            JOIN documents d ON d.id = selected.document_id
            JOIN chunks context ON context.document_id = d.id
             AND context.chunk_index BETWEEN selected.chunk_index - 1 AND selected.chunk_index + 1
            WHERE selected.id = ? AND d.rel_path = ? ORDER BY context.chunk_index
        """, (chunk_id, path)).fetchall()
    finally:
        conn.close()


def related_phrases(query):
    words = set(focus_words(query))
    if words & {"pastor", "pastors", "elder", "elders"} and words & {"care", "church", "shepherd"}:
        return ["feed the flock", "shepherd the flock", "tend the flock", "shepherding"]
    return []


def run_query(query: str, limit: int = 20, source_types=None, search_mode: str = "balanced", related=True, book="", course=""):
    query_tokens = focus_words(query) if search_mode == "balanced" else normalize_query_tokens(query)
    query_reference = extract_query_reference(query)
    equivalents = related_phrases(query) if related and search_mode == "balanced" else []
    topic_terms = (get_topic_expansion_terms(query) if related else []) + equivalents
    books = [book.lower() for book in BOOK_PATTERNS if re.search(r"\b" + re.escape(book) + r"\b", query, re.I)]
    topic_rules = get_topic_anchor_rules(query) or {}
    selected_source_types = []
    for source_type in source_types or []:
        if source_type and source_type not in selected_source_types:
            selected_source_types.append(source_type)
    source_clause = ""
    source_params = []
    if selected_source_types:
        placeholders = ", ".join("?" for _ in selected_source_types)
        source_clause = f" AND d.source_type IN ({placeholders})"
        source_params = selected_source_types

    if book:
        source_clause += " AND EXISTS (SELECT 1 FROM chunk_refs br WHERE br.chunk_id=c.id AND (br.scripture_ref=? OR br.scripture_ref GLOB ?))"
        source_params.extend([book, book + " [0-9]*"])
    if course:
        course_path = "02_LFBI/" + course + "/"
        source_clause += " AND d.source_type='lfbi' AND (instr(d.rel_path,?)=1 OR instr(d.rel_path,?)>0)"
        source_params.extend([course_path, "/" + course_path])

    conn = sqlite3.connect(DB_PATH.as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    try:
        results = []

        if query_reference:
            conn.create_function("reference_overlap", 2, references_overlap)
            chapter = query_reference.partition(":")[0]
            ref_rows = conn.execute(
                f"""
                SELECT c.id AS chunk_id, d.title, d.rel_path, d.source_type, c.content
                FROM chunks c JOIN documents d ON d.id=c.document_id
                WHERE EXISTS (SELECT 1 FROM chunk_refs cr WHERE cr.chunk_id=c.id
                    AND (cr.scripture_ref=? OR cr.scripture_ref GLOB ?)
                    AND reference_overlap(cr.scripture_ref,?)){source_clause}
                ORDER BY d.rel_path,c.id
                """, (chapter, chapter + ":[0-9]*", query_reference, *source_params)
            )

            for row in ref_rows:
                results.append({
                    "score": 100000,
                    "chunk_id": row["chunk_id"],
                    "title": row["title"],
                    "path": row["rel_path"],
                    "source_type": row["source_type"],
                    "anchor": passage_anchor(row["content"]),
                    "snippet": build_snippet(row["content"], query, topic_terms, query_reference),
                })

        fts_query = make_fts_query(query, query_tokens, topic_terms, search_mode)
        if fts_query:
            fts_rows = conn.execute(
                f"""
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
                WHERE chunks_fts MATCH ?{source_clause}
                ORDER BY rank
                """,
                (fts_query, *source_params)
            )

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

                if search_mode == "balanced" and not query_reference and len(query_tokens) > 1:
                    proximity, _ = passage_focus(text, query_tokens)
                    bonus += proximity
                    if any(book in lower_path or book in row["title"].lower() for book in books):
                        bonus += 200
                rank_value = row["rank"] if row["rank"] is not None else 0.0
                score = int(500 - rank_value * 100 + bonus)

                results.append({
                    "score": score,
                    "chunk_id": row["chunk_id"],
                    "title": row["title"],
                    "path": row["rel_path"],
                    "source_type": row["source_type"],
                    "related_hits": [phrase for phrase in equivalents if phrase in lower_text],
                    "anchor": passage_anchor(text),
                    "snippet": build_snippet(text, query, topic_terms, query_reference),
                })

        refs_by_chunk = {}
        if results:
            ids = sorted({item["chunk_id"] for item in results})
            for start in range(0, len(ids), 500):
                batch = ids[start:start + 500]
                placeholders = ",".join("?" for _ in batch)
                for chunk_id, ref in conn.execute(
                    f"SELECT chunk_id, scripture_ref FROM chunk_refs WHERE chunk_id IN ({placeholders})", batch
                ):
                    refs_by_chunk.setdefault(chunk_id, set()).add(ref)

        if query_reference:
            for item in results:
                refs = refs_by_chunk.get(item["chunk_id"], set())
                if query_reference in refs:
                    item["score"] += 300000
                elif any(":" in ref and references_overlap(query_reference, ref) for ref in refs):
                    item["score"] += 200000
        sources = {}
        seen_chunks = set()
        for item in sorted(results, key=lambda x: (-x["score"], x["path"], x["chunk_id"])):
            chunk_id = item["chunk_id"]
            if chunk_id in seen_chunks:
                continue
            seen_chunks.add(chunk_id)
            refs = refs_by_chunk.get(chunk_id, set())
            chapter = (query_reference or "").partition(":")[0]
            if query_reference in refs:
                evidence = f"Cites {query_reference}"
            elif query_reference and any(references_overlap(query_reference, ref) for ref in refs):
                matching = sorted(ref for ref in refs if references_overlap(query_reference, ref))
                evidence = "Cites " + ", ".join(matching)
            elif chapter and any(ref.partition(":")[0] == chapter for ref in refs):
                evidence = f"Mentions {chapter}"
            else:
                evidence = "Search-word match" if query_reference else ""
            passage = {"anchor": item["anchor"], "chunk_id": chunk_id, "snippet": item["snippet"], "evidence": evidence}
            passage["books"] = sorted({ref.rsplit(" ", 1)[0] for ref in refs})
            if item.get("related_hits"):
                passage["evidence"] = "Related wording: " + ", ".join(item["related_hits"])
            if item["path"] in sources:
                sources[item["path"]]["passages"].append(passage)
            elif limit is None or len(sources) < limit:
                sources[item["path"]] = {**item, "passages": [passage]}
        return list(sources.values())

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
