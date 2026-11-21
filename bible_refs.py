"""One shared home for Bible book names, abbreviations and reference parsing.

Every script that needs to recognise a Bible reference imports it from here, so a
fix or addition only has to be made once.
"""
import re

# Canonical book names, in Bible order.
BOOK_PATTERNS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua",
    "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
    "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
    "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah",
    "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah",
    "Haggai", "Zechariah", "Malachi", "Matthew", "Mark", "Luke",
    "John", "Acts", "Romans", "1 Corinthians", "2 Corinthians", "Galatians",
    "Ephesians", "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians", "1 Timothy",
    "2 Timothy", "Titus", "Philemon", "Hebrews", "James", "1 Peter",
    "2 Peter", "1 John", "2 John", "3 John", "Jude", "Revelation",
]

# Number of chapters in each book.
BOOK_CHAPTER_LIMITS = {
    "Genesis": 50, "Exodus": 40, "Leviticus": 27, "Numbers": 36,
    "Deuteronomy": 34, "Joshua": 24, "Judges": 21, "Ruth": 4,
    "1 Samuel": 31, "2 Samuel": 24, "1 Kings": 22, "2 Kings": 25,
    "1 Chronicles": 29, "2 Chronicles": 36, "Ezra": 10, "Nehemiah": 13,
    "Esther": 10, "Job": 42, "Psalms": 150, "Proverbs": 31,
    "Ecclesiastes": 12, "Song of Solomon": 8, "Isaiah": 66, "Jeremiah": 52,
    "Lamentations": 5, "Ezekiel": 48, "Daniel": 12, "Hosea": 14,
    "Joel": 3, "Amos": 9, "Obadiah": 1, "Jonah": 4,
    "Micah": 7, "Nahum": 3, "Habakkuk": 3, "Zephaniah": 3,
    "Haggai": 2, "Zechariah": 14, "Malachi": 4, "Matthew": 28,
    "Mark": 16, "Luke": 24, "John": 21, "Acts": 28,
    "Romans": 16, "1 Corinthians": 16, "2 Corinthians": 13, "Galatians": 6,
    "Ephesians": 6, "Philippians": 4, "Colossians": 4, "1 Thessalonians": 5,
    "2 Thessalonians": 3, "1 Timothy": 6, "2 Timothy": 4, "Titus": 3,
    "Philemon": 1, "Hebrews": 13, "James": 5, "1 Peter": 5,
    "2 Peter": 3, "1 John": 5, "2 John": 1, "3 John": 1,
    "Jude": 1, "Revelation": 22,
}

# Short forms accepted when someone types a search (lower-case keys).
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

# ---------------------------------------------------------------------------
# Finding references inside documents (sermons, notes, commentaries ...)
# ---------------------------------------------------------------------------

# Spellings that are safe to read as a book name when a chapter number follows.
_FULL_NAMES = {book.lower(): book for book in BOOK_PATTERNS}
_FULL_NAMES.update({
    "psalm": "Psalms",
    "song of songs": "Song of Solomon",
    "song of solomon": "Song of Solomon",
    "revelations": "Revelation",
})

# Short forms writers commonly use. These are only trusted when written with a
# period ("Rom. 8") or with a verse ("Rom 8:28"), so ordinary words are not
# mistaken for Bible books.
_SHORT_FORMS = {
    "gen": "Genesis", "gn": "Genesis", "exod": "Exodus", "ex": "Exodus",
    "lev": "Leviticus", "num": "Numbers", "deut": "Deuteronomy", "dt": "Deuteronomy",
    "josh": "Joshua", "judg": "Judges", "jdg": "Judges",
    "1 sam": "1 Samuel", "2 sam": "2 Samuel",
    "1 kgs": "1 Kings", "2 kgs": "2 Kings", "1 ki": "1 Kings", "2 ki": "2 Kings",
    "1 chr": "1 Chronicles", "2 chr": "2 Chronicles",
    "neh": "Nehemiah", "esth": "Esther", "est": "Esther",
    "ps": "Psalms", "pss": "Psalms", "psa": "Psalms", "prov": "Proverbs",
    "eccl": "Ecclesiastes", "eccles": "Ecclesiastes", "song": "Song of Solomon",
    "isa": "Isaiah", "jer": "Jeremiah", "lam": "Lamentations",
    "ezek": "Ezekiel", "eze": "Ezekiel", "dan": "Daniel", "hos": "Hosea",
    "obad": "Obadiah", "mic": "Micah", "nah": "Nahum", "hab": "Habakkuk",
    "zeph": "Zephaniah", "hag": "Haggai", "zech": "Zechariah", "mal": "Malachi",
    "matt": "Matthew", "mt": "Matthew", "mk": "Mark", "lk": "Luke", "jn": "John",
    "rom": "Romans", "1 cor": "1 Corinthians", "2 cor": "2 Corinthians",
    "gal": "Galatians", "eph": "Ephesians", "phil": "Philippians", "php": "Philippians",
    "col": "Colossians", "1 thess": "1 Thessalonians", "2 thess": "2 Thessalonians",
    "1 tim": "1 Timothy", "2 tim": "2 Timothy", "tit": "Titus",
    "philem": "Philemon", "phm": "Philemon", "heb": "Hebrews", "jas": "James",
    "1 pet": "1 Peter", "2 pet": "2 Peter", "1 jn": "1 John", "2 jn": "2 John",
    "3 jn": "3 John", "rev": "Revelation",
}

# Everyday words that are also book names: only count them when capitalised
# ("Numbers 3:5", not "the numbers 3 and 4").
_NEEDS_CAPITAL = {"numbers", "mark", "job", "acts", "judges"}

# Books with a single chapter: "Jude 3" means verse 3.
_SINGLE_CHAPTER = {book for book, chapters in BOOK_CHAPTER_LIMITS.items() if chapters == 1}

MAX_VERSE = 176  # Psalm 119 is the longest chapter


def _squash(name):
    """'1 Cor.' / '1Cor' / '1  cor' all become '1cor'."""
    return re.sub(r"[\s.]", "", name).lower()


_LOOKUP = {}  # squashed spelling -> (canonical book, needs period or verse)
for _name, _book in _FULL_NAMES.items():
    _LOOKUP[_squash(_name)] = (_book, False)
for _name, _book in _SHORT_FORMS.items():
    _LOOKUP.setdefault(_squash(_name), (_book, True))


def _spelling_pattern(name):
    """Allow '1 John', '1John' and '1  John'; other spaces may stretch."""
    words = name.split()
    if words and words[0].isdigit():
        return re.escape(words[0]) + r"\s*" + r"\s+".join(re.escape(w) for w in words[1:])
    return r"\s+".join(re.escape(w) for w in words)


_ALL_SPELLINGS = sorted({*_FULL_NAMES, *_SHORT_FORMS}, key=len, reverse=True)
REFERENCE_PATTERN = re.compile(
    r"(?<!\w)(?P<book>" + "|".join(_spelling_pattern(n) for n in _ALL_SPELLINGS) + r")"
    r"(?P<dot>\.)?\s*(?P<chapter>\d{1,3})"
    r"(?::(?P<start>\d{1,3})(?:\s*[-–—]\s*(?P<end>\d{1,3}))?)?(?!\d)",
    re.IGNORECASE,
)


def normalize_match(match):
    """Turn one regex match into 'Romans 8', 'Romans 8:28' or 'Romans 8:26-30', or None."""
    raw = match.group("book")
    book, short_form = _LOOKUP[_squash(raw)]
    chapter, start, end = match.group("chapter"), match.group("start"), match.group("end")
    if short_form and not (match.group("dot") or start):
        return None
    if _squash(raw) in _NEEDS_CAPITAL and not raw[0].isupper():
        return None
    chapter = int(chapter)
    if book in _SINGLE_CHAPTER and not start:
        chapter, start = 1, chapter  # "Jude 3" -> Jude 1:3
    if not 1 <= chapter <= BOOK_CHAPTER_LIMITS[book]:
        return None
    if start is None:
        return f"{book} {chapter}"
    start = int(start)
    if not 1 <= start <= MAX_VERSE:
        return None
    reference = f"{book} {chapter}:{start}"
    if end is not None and start < int(end) <= MAX_VERSE:
        reference += f"-{int(end)}"
    return reference


def extract_references(text):
    """Every distinct, valid single-chapter reference in the text, sorted."""
    found = set()
    for match in REFERENCE_PATTERN.finditer(text):
        reference = normalize_match(match)
        if reference:
            found.add(reference)
    return sorted(found)
