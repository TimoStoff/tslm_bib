from pathlib import Path
import unittest

from bibtex_tools import first_author_surname, scan_blocks
from check_library import validate_text


ROOT = Path(__file__).resolve().parents[1]


class ValidatorTests(unittest.TestCase):
    def test_current_library_is_valid(self) -> None:
        macro_count, entry_count, problems = validate_text(
            (ROOT / "all.bib").read_text(encoding="utf-8")
        )
        self.assertGreater(macro_count, 0)
        self.assertGreater(entry_count, 0)
        self.assertEqual(problems, [])

    def test_reports_key_macro_month_and_repeated_field_errors(self) -> None:
        source = '''@STRING{known = "Venue with {braces}" }
@Article{Wrong20missing,
  author = {Markus L{\\"o}ning},
  title = {A Title},
  journal = missing,
  year = 2021,
  month = {jul},
  title = {A Second Title}
}
'''
        _, _, problems = validate_text(source)
        joined = "\n".join(problems)
        self.assertIn("repeated field 'title'", joined)
        self.assertIn("undefined macro 'missing'", joined)
        self.assertIn("month must be a bare BibTeX month macro", joined)
        self.assertIn("key year does not match year 2021", joined)
        self.assertIn("key surname does not match first author 'Loning'", joined)

    def test_scanner_ignores_braces_in_quoted_string_macro(self) -> None:
        blocks, problems = scan_blocks(
            '@STRING{x = "Venue {Name}"}\n@Misc{Key20x, title={T}}'
        )
        self.assertEqual(problems, [])
        self.assertEqual(
            [block.entry_type.lower() for block in blocks], ["string", "misc"]
        )

    def test_latex_accent_is_removed_from_surname(self) -> None:
        self.assertEqual(
            first_author_surname('{Markus L{\\"o}ning and A. Person}'), "Loning"
        )

    def test_tied_keys_use_each_entry_title(self) -> None:
        source = '''@STRING{arxiv = "arXiv"}
@Article{Doe24arxivBeta,
  author={Jane Doe}, title={Alpha Study}, journal=arxiv, year=2024
}
@Article{Doe24arxivAlpha,
  author={John Doe}, title={Beta Study}, journal=arxiv, year=2024
}
'''
        _, _, problems = validate_text(source)
        joined = "\n".join(problems)
        self.assertIn("expected citation key 'Doe24arxivAlpha'", joined)
        self.assertIn("expected citation key 'Doe24arxivBeta'", joined)


if __name__ == "__main__":
    unittest.main()
