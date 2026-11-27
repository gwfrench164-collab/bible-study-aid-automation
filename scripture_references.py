"""Shared canonical book names and explicit reference extraction."""
import re
BOOK_PATTERNS = ['Genesis', 'Exodus', 'Leviticus', 'Numbers', 'Deuteronomy', 'Joshua', 'Judges', 'Ruth', '1 Samuel', '2 Samuel', '1 Kings', '2 Kings', '1 Chronicles', '2 Chronicles', 'Ezra', 'Nehemiah', 'Esther', 'Job', 'Psalms', 'Proverbs', 'Ecclesiastes', 'Song of Solomon', 'Isaiah', 'Jeremiah', 'Lamentations', 'Ezekiel', 'Daniel', 'Hosea', 'Joel', 'Amos', 'Obadiah', 'Jonah', 'Micah', 'Nahum', 'Habakkuk', 'Zephaniah', 'Haggai', 'Zechariah', 'Malachi', 'Matthew', 'Mark', 'Luke', 'John', 'Acts', 'Romans', '1 Corinthians', '2 Corinthians', 'Galatians', 'Ephesians', 'Philippians', 'Colossians', '1 Thessalonians', '2 Thessalonians', '1 Timothy', '2 Timothy', 'Titus', 'Philemon', 'Hebrews', 'James', '1 Peter', '2 Peter', '1 John', '2 John', '3 John', 'Jude', 'Revelation']
BOOK_CHAPTER_LIMITS = {'Genesis': 50, 'Exodus': 40, 'Leviticus': 27, 'Numbers': 36, 'Deuteronomy': 34, 'Joshua': 24, 'Judges': 21, 'Ruth': 4, '1 Samuel': 31, '2 Samuel': 24, '1 Kings': 22, '2 Kings': 25, '1 Chronicles': 29, '2 Chronicles': 36, 'Ezra': 10, 'Nehemiah': 13, 'Esther': 10, 'Job': 42, 'Psalms': 150, 'Proverbs': 31, 'Ecclesiastes': 12, 'Song of Solomon': 8, 'Isaiah': 66, 'Jeremiah': 52, 'Lamentations': 5, 'Ezekiel': 48, 'Daniel': 12, 'Hosea': 14, 'Joel': 3, 'Amos': 9, 'Obadiah': 1, 'Jonah': 4, 'Micah': 7, 'Nahum': 3, 'Habakkuk': 3, 'Zephaniah': 3, 'Haggai': 2, 'Zechariah': 14, 'Malachi': 4, 'Matthew': 28, 'Mark': 16, 'Luke': 24, 'John': 21, 'Acts': 28, 'Romans': 16, '1 Corinthians': 16, '2 Corinthians': 13, 'Galatians': 6, 'Ephesians': 6, 'Philippians': 4, 'Colossians': 4, '1 Thessalonians': 5, '2 Thessalonians': 3, '1 Timothy': 6, '2 Timothy': 4, 'Titus': 3, 'Philemon': 1, 'Hebrews': 13, 'James': 5, '1 Peter': 5, '2 Peter': 3, '1 John': 5, '2 John': 1, '3 John': 1, 'Jude': 1, 'Revelation': 22}
ABBREVIATION_MAP = {'gen': 'Genesis', 'ge': 'Genesis', 'exo': 'Exodus', 'ex': 'Exodus', 'lev': 'Leviticus', 'le': 'Leviticus', 'num': 'Numbers', 'nu': 'Numbers', 'deut': 'Deuteronomy', 'deu': 'Deuteronomy', 'josh': 'Joshua', 'jos': 'Joshua', 'judg': 'Judges', 'jdg': 'Judges', 'ruth': 'Ruth', '1 sam': '1 Samuel', '2 sam': '2 Samuel', '1 kgs': '1 Kings', '2 kgs': '2 Kings', '1 chr': '1 Chronicles', '2 chr': '2 Chronicles', 'ezra': 'Ezra', 'neh': 'Nehemiah', 'ne': 'Nehemiah', 'est': 'Esther', 'job': 'Job', 'ps': 'Psalms', 'psa': 'Psalms', 'prov': 'Proverbs', 'pro': 'Proverbs', 'eccl': 'Ecclesiastes', 'ecc': 'Ecclesiastes', 'song': 'Song of Solomon', 'isa': 'Isaiah', 'jer': 'Jeremiah', 'lam': 'Lamentations', 'ezek': 'Ezekiel', 'eze': 'Ezekiel', 'dan': 'Daniel', 'hos': 'Hosea', 'joe': 'Joel', 'amos': 'Amos', 'obad': 'Obadiah', 'jon': 'Jonah', 'mic': 'Micah', 'nah': 'Nahum', 'hab': 'Habakkuk', 'zeph': 'Zephaniah', 'hag': 'Haggai', 'zech': 'Zechariah', 'mal': 'Malachi', 'matt': 'Matthew', 'mt': 'Matthew', 'mk': 'Mark', 'mrk': 'Mark', 'mark': 'Mark', 'lk': 'Luke', 'lu': 'Luke', 'jn': 'John', 'joh': 'John', 'acts': 'Acts', 'act': 'Acts', 'rom': 'Romans', 'ro': 'Romans', '1 cor': '1 Corinthians', '2 cor': '2 Corinthians', 'gal': 'Galatians', 'eph': 'Ephesians', 'phil': 'Philippians', 'php': 'Philippians', 'col': 'Colossians', '1 thess': '1 Thessalonians', '2 thess': '2 Thessalonians', '1 tim': '1 Timothy', '2 tim': '2 Timothy', 'tit': 'Titus', 'philem': 'Philemon', 'phm': 'Philemon', 'heb': 'Hebrews', 'jas': 'James', 'jam': 'James', '1 pet': '1 Peter', '2 pet': '2 Peter', '1 jn': '1 John', '2 jn': '2 John', '3 jn': '3 John', 'jude': 'Jude', 'rev': 'Revelation', 're': 'Revelation'}
NAMES = {book.casefold(): book for book in BOOK_PATTERNS}
NAMES.update(ABBREVIATION_MAP)
NAMES['psalm'] = 'Psalms'
for name, book in list(NAMES.items()):
    if name[:2] in {'1 ', '2 ', '3 '}:
        NAMES[{'1':'i','2':'ii','3':'iii'}[name[0]] + name[1:]] = book
PATTERN = re.compile(r"(?<!\w)(" + '|'.join(re.escape(n) for n in sorted(NAMES,key=len,reverse=True)) +
    r")\.?\s+(\d+)(?:\s*:\s*(\d+)(?:\s*[-–—]\s*(\d+))?)?(?!\d)", re.I)


def extract_references(text):
    refs=set()
    for match in PATTERN.finditer(text):
        name, chapter, first, last=match.groups()
        book=NAMES[name.casefold()]; chapter=int(chapter)
        if BOOK_CHAPTER_LIMITS[book] == 1 and not first and chapter != 1:
            first=str(chapter);chapter=1
        if not 1 <= chapter <= BOOK_CHAPTER_LIMITS[book]: continue
        if first and (int(first) < 1 or int(first) > 176): continue
        if last and (int(last) < int(first) or int(last) > 176): continue
        # Lowercase common nouns without a verse are ambiguous prose.
        if name in {'numbers','job','acts','mark'} and not first: continue
        ref=f'{book} {chapter}'
        if first: ref += ':'+str(int(first)) + ('-'+str(int(last)) if last else '')
        refs.add(ref)
    return sorted(refs)
