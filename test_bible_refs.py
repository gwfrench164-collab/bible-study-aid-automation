"""Tests for the shared Bible reference finder."""
import unittest

import bible_refs
from bible_refs import extract_references


class ExtractReferencesTests(unittest.TestCase):
    def test_full_names_still_work(self):
        self.assertEqual(extract_references("Read Romans 8:28 and John 3:16-18 today."),
                         ["John 3:16-18", "Romans 8:28"])
        self.assertEqual(extract_references("The whole of Romans 8 matters."), ["Romans 8"])

    def test_numbered_books(self):
        self.assertEqual(extract_references("1 John 3:16 and 2 Timothy 3:16, also 1Cor. 13"),
                         ["1 Corinthians 13", "1 John 3:16", "2 Timothy 3:16"])

    def test_short_forms_with_period_or_verse(self):
        self.assertEqual(extract_references("See Rom. 8:28, Ps 23:1 and Heb. 11."),
                         ["Hebrews 11", "Psalms 23:1", "Romans 8:28"])
        self.assertEqual(extract_references("Gal. 2:20; Phil 4:13; 1 Thess. 4:16-17"),
                         ["1 Thessalonians 4:16-17", "Galatians 2:20", "Philippians 4:13"])

    def test_short_forms_without_period_or_verse_are_ignored(self):
        # "dan 3", "col 4" or "ex 5" alone could be anything.
        self.assertEqual(extract_references("Call dan 3 times, row col 4, item ex 5"), [])

    def test_psalm_singular_and_song_of_songs(self):
        self.assertEqual(extract_references("Psalm 119:105 and Song of Songs 2:1"),
                         ["Psalms 119:105", "Song of Solomon 2:1"])

    def test_dash_styles_in_ranges(self):
        self.assertEqual(extract_references("Romans 8:26–30 and Romans 12:1—2"),
                         ["Romans 12:1-2", "Romans 8:26-30"])

    def test_single_chapter_books(self):
        self.assertEqual(extract_references("Jude 3 and Philemon 6, but also Jude 1:24"),
                         ["Jude 1:24", "Jude 1:3", "Philemon 1:6"])

    def test_impossible_references_are_dropped(self):
        self.assertEqual(extract_references("Romans 99:1, John 3:0, Genesis 51"), [])

    def test_backwards_range_keeps_first_verse_only(self):
        self.assertEqual(extract_references("Romans 8:30-26"), ["Romans 8:30"])

    def test_everyday_words_need_a_capital(self):
        self.assertEqual(extract_references("the numbers 3 and 4, mark 5 minutes, job 2 of 3"), [])
        self.assertEqual(extract_references("Numbers 3:5, Mark 5:3, Job 2:10, Acts 2:38"),
                         ["Acts 2:38", "Job 2:10", "Mark 5:3", "Numbers 3:5"])

    def test_all_capitals_headings(self):
        self.assertEqual(extract_references("ROMANS 8:28"), ["Romans 8:28"])

    def test_not_fooled_by_words_that_contain_a_book_name(self):
        self.assertEqual(extract_references("Index 3, Standard 4, Jordan 5:1"), [])

    def test_constants_cover_every_book(self):
        self.assertEqual(set(bible_refs.BOOK_CHAPTER_LIMITS), set(bible_refs.BOOK_PATTERNS))
        self.assertEqual(len(bible_refs.BOOK_PATTERNS), 66)
        self.assertTrue(set(bible_refs.ABBREVIATION_MAP.values()) <= set(bible_refs.BOOK_PATTERNS))


if __name__ == "__main__":
    unittest.main()
