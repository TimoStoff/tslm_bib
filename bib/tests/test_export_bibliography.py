from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest

from export_bibliography import main


LIBRARY = '''@STRING{arxiv = "arXiv" }
@STRING{jmlr = "J. Mach. Learn. Res." }
@STRING{nips = "Conf. Neural Inf. Process. Syst." }

@Article{Doe24arxiv,
  author        = {Jane Doe},
  title         = {First Study},
  journal       = arxiv,
  year          = 2024
}

@Article{Roe23jmlr,
  author        = {Richard Roe},
  title         = {Second Study},
  journal       = jmlr,
  year          = 2023
}

@InProceedings{Smith22nips,
  author        = {Alex Smith},
  title         = {Unused Study},
  booktitle     = nips,
  year          = 2022
}
'''


class ExporterTests(unittest.TestCase):
    def test_exports_citations_from_main_and_included_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sections = root / "sections"
            sections.mkdir()
            (root / "all.bib").write_text(LIBRARY, encoding="utf-8")
            (root / "main.tex").write_text(
                r'''\documentclass{article}
% \cite{Smith22nips}
\begin{document}
\citep[see][p.~4]{Doe24arxiv}
\input{sections/results}
\end{document}
''',
                encoding="utf-8",
            )
            (sections / "results.tex").write_text(
                r"Results follow \textcite{Roe23jmlr}.", encoding="utf-8"
            )
            output = root / "submission.bib"

            with redirect_stdout(io.StringIO()):
                result = main(
                    [
                        str(root / "main.tex"),
                        str(output),
                        "--library",
                        str(root / "all.bib"),
                    ]
                )

            self.assertEqual(result, 0)
            exported = output.read_text(encoding="utf-8")
            self.assertIn("@STRING{arxiv", exported)
            self.assertIn("@STRING{jmlr", exported)
            self.assertNotIn("@STRING{nips", exported)
            self.assertIn("@Article{Doe24arxiv", exported)
            self.assertIn("@Article{Roe23jmlr", exported)
            self.assertNotIn("Smith22nips", exported)

    def test_missing_citation_fails_without_writing_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "all.bib").write_text(LIBRARY, encoding="utf-8")
            (root / "main.tex").write_text(
                r"\cite{Missing24venue}", encoding="utf-8"
            )
            output = root / "submission.bib"
            errors = io.StringIO()

            with redirect_stderr(errors):
                result = main(
                    [
                        str(root / "main.tex"),
                        str(output),
                        "--library",
                        str(root / "all.bib"),
                    ]
                )

            self.assertEqual(result, 1)
            self.assertIn("Missing24venue", errors.getvalue())
            self.assertFalse(output.exists())

    def test_missing_included_source_fails_without_partial_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "all.bib").write_text(LIBRARY, encoding="utf-8")
            (root / "main.tex").write_text(
                r"\cite{Doe24arxiv}\input{missing-section}", encoding="utf-8"
            )
            output = root / "submission.bib"
            errors = io.StringIO()

            with redirect_stderr(errors):
                result = main(
                    [
                        str(root / "main.tex"),
                        str(output),
                        "--library",
                        str(root / "all.bib"),
                    ]
                )

            self.assertEqual(result, 1)
            self.assertIn("missing-section.tex", errors.getvalue())
            self.assertFalse(output.exists())

    def test_nocite_star_exports_every_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "all.bib").write_text(LIBRARY, encoding="utf-8")
            (root / "main.tex").write_text(r"\nocite{*}", encoding="utf-8")
            output = root / "submission.bib"

            with redirect_stdout(io.StringIO()):
                result = main(
                    [
                        str(root / "main.tex"),
                        str(output),
                        "--library",
                        str(root / "all.bib"),
                    ]
                )

            self.assertEqual(result, 0)
            exported = output.read_text(encoding="utf-8")
            self.assertIn("Doe24arxiv", exported)
            self.assertIn("Roe23jmlr", exported)
            self.assertIn("Smith22nips", exported)

    def test_exports_a_single_member_of_a_tied_key_group(self) -> None:
        library = '''@STRING{arxiv = "arXiv" }

@Article{Doe24arxivAlpha,
  author        = {Jane Doe},
  title         = {Alpha Study},
  journal       = arxiv,
  year          = 2024
}

@Article{Doe24arxivBeta,
  author        = {John Doe},
  title         = {Beta Study},
  journal       = arxiv,
  year          = 2024
}
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "all.bib").write_text(library, encoding="utf-8")
            (root / "main.tex").write_text(
                r"\cite{Doe24arxivAlpha}", encoding="utf-8"
            )
            output = root / "submission.bib"

            with redirect_stdout(io.StringIO()):
                result = main(
                    [
                        str(root / "main.tex"),
                        str(output),
                        "--library",
                        str(root / "all.bib"),
                    ]
                )

            self.assertEqual(result, 0)
            exported = output.read_text(encoding="utf-8")
            self.assertIn("Doe24arxivAlpha", exported)
            self.assertNotIn("Doe24arxivBeta", exported)

    def test_includes_an_entry_required_by_crossref(self) -> None:
        library = '''@STRING{nips = "Conf. Neural Inf. Process. Syst." }

@Proceedings{Roe23nips,
  editor        = {Richard Roe},
  title         = {Conference Proceedings},
  booktitle     = nips,
  year          = 2023
}

@InProceedings{Smith24nips,
  author        = {Alex Smith},
  title         = {A Study},
  booktitle     = nips,
  year          = 2024,
  crossref      = {Roe23nips}
}
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "all.bib").write_text(library, encoding="utf-8")
            (root / "main.tex").write_text(
                r"\cite{Smith24nips}", encoding="utf-8"
            )
            output = root / "submission.bib"

            with redirect_stdout(io.StringIO()):
                result = main(
                    [
                        str(root / "main.tex"),
                        str(output),
                        "--library",
                        str(root / "all.bib"),
                    ]
                )

            self.assertEqual(result, 0)
            exported = output.read_text(encoding="utf-8")
            self.assertIn("Roe23nips", exported)
            self.assertIn("Smith24nips", exported)

    def test_existing_output_requires_force(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "all.bib").write_text(LIBRARY, encoding="utf-8")
            (root / "main.tex").write_text(r"\cite{Doe24arxiv}", encoding="utf-8")
            output = root / "submission.bib"
            output.write_text("keep this\n", encoding="utf-8")

            with redirect_stderr(io.StringIO()):
                result = main(
                    [
                        str(root / "main.tex"),
                        str(output),
                        "--library",
                        str(root / "all.bib"),
                    ]
                )

            self.assertEqual(result, 1)
            self.assertEqual(output.read_text(encoding="utf-8"), "keep this\n")


if __name__ == "__main__":
    unittest.main()
