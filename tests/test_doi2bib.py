import unittest

from bibtex_tools import Block, parse_entry
from doi2bib import convert_entry


class ImporterTests(unittest.TestCase):
    def test_converts_known_venue_and_removes_crossref_fields(self) -> None:
        block = Block(
            "article",
            '''crossref-key,
  author = {Doe, Jane and Roe, Richard},
  title = {A Paper},
  journal = {Journal of Machine Learning Research},
  year = {2024},
  month = {jul},
  publisher = {Example},
  url = {https://example.test}''',
            1,
        )
        entry, problems = parse_entry(block)
        self.assertEqual(problems, [])
        assert entry is not None
        converted, comment = convert_entry(
            entry, [("jmlr", "Journal of Machine Learning Research")]
        )
        self.assertIsNone(comment)
        self.assertIn("@Article{Doe24jmlr,", converted)
        self.assertIn("journal       = jmlr,", converted)
        self.assertIn("month         = jul", converted)
        self.assertNotIn("publisher", converted)
        self.assertNotIn("url", converted)

    def test_unknown_venue_gets_placeholder_and_comment(self) -> None:
        block = Block(
            "inproceedings",
            "key, author={Jane Doe}, title={A Paper}, booktitle={New Venue}, year={2025}",
            1,
        )
        entry, _ = parse_entry(block)
        assert entry is not None
        converted, comment = convert_entry(entry, [])
        self.assertIn("@InProceedings{Doe25VENUE,", converted)
        self.assertIn("TODO(VENUE)", comment or "")

    def test_short_venue_name_does_not_match_a_longer_unrelated_name(self) -> None:
        block = Block(
            "article",
            "key, author={Henry Frank}, title={Water}, journal={Science}, year={1970}",
            1,
        )
        entry, _ = parse_entry(block)
        assert entry is not None
        converted, _ = convert_entry(
            entry,
            [
                ("pnas", "Proceedings of the National Academy of Sciences"),
                ("science", "Science"),
            ],
        )
        self.assertIn("@Article{Frank70science,", converted)


if __name__ == "__main__":
    unittest.main()
