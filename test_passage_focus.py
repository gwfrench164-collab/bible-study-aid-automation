"""The passage-focus score picks the excerpt shown for a hit, so it must not drift."""
import unittest

import query_bible_study as search


class PassageFocusTests(unittest.TestCase):
    def test_no_words_or_no_hits(self):
        self.assertEqual(search.passage_focus("anything at all", []), (0, None))
        self.assertEqual(search.passage_focus("nothing relevant here", ["grace"]), (0, None))

    def test_single_word_scores_once_at_first_hit(self):
        self.assertEqual(search.passage_focus("Grace and more grace", ["grace"]), (120, 0))

    def test_distinct_words_close_together_beat_a_lone_word(self):
        text = "x " * 300 + "the love of God is great" + " y" * 300
        score, position = search.passage_focus(text, ["love", "god"])
        self.assertGreater(score, 240)
        self.assertEqual(position, text.index("love"))

    def test_words_far_apart_do_not_combine(self):
        text = "love " + "filler " * 80 + "God"
        score, _ = search.passage_focus(text, ["love", "god"])
        self.assertEqual(score, 120)

    def test_whole_words_only_and_case_is_ignored(self):
        self.assertEqual(search.passage_focus("Beloved GRACE", ["love", "grace"]), (120, 8))

    def test_same_answer_when_asked_twice(self):
        text = "faith, hope and love"
        words = ["faith", "love"]
        self.assertEqual(search.passage_focus(text, words), search.passage_focus(text, list(words)))


if __name__ == "__main__":
    unittest.main()
