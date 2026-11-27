import unittest
from scripture_references import extract_references
from build_scripture_index import parse_reference, BOOK_ORDER

class ScriptureTests(unittest.TestCase):
    def test_aliases_and_ranges(self):
        self.assertEqual(extract_references('Rom. 8:28–30; Ps 23; Psalm 23; I John 2:1; Jude 3'),
          ['1 John 2:1','Jude 1:3','Psalms 23','Romans 8:28-30'])
    def test_search_uses_the_same_canonical_references(self):
        from query_bible_study import extract_query_reference
        self.assertEqual(extract_query_reference('Jude 3'), 'Jude 1:3')
        self.assertEqual(extract_query_reference('I John 2:1'), '1 John 2:1')
        self.assertIsNone(extract_query_reference('John 99'))

    def test_invalid_and_multiword(self):
        self.assertEqual(extract_references('John 99; Romans 8:0; Rom 8:30-26; the numbers 3 and 4'),[])
        self.assertEqual(parse_reference('Song of Solomon 2:1')[:3],(BOOK_ORDER['Song of Solomon'],2,1))
