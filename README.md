# TSLM BibTeX library

A shared BibTeX library for time-series language model research.

## Use the library

Copy `all.bib` into your paper:

```sh
cp ../tslm_bib/all.bib .
```

For shared updates, add this repository as a Git submodule:

```sh
git submodule add https://github.com/TimoStoff/tslm_bib.git tslm_bib
```

Then reference it from the paper:

```tex
\bibliography{tslm_bib/all}
```

A conference submission needs a self-contained source archive.
Use the cleanup tool below.
You can also copy `all.bib` into the archive.

For a new paper, open a pull request.

## Tools that come with this repo

The Python tools use only the standard library.
If you want a managed Python environment, run `uv sync`.

### Convert a DOI to a reference

```sh
./doi2bib.py 10.1038/s41597-024-03960-3
```

This tool gets the Crossref record and appends a local BibTeX entry.
Review the entry because Crossref often omits conference page numbers.

### Validate the library

```sh
./check_library.py
```

This tool validates the syntax, citation keys, fields, macros, months, and entry order.
GitHub Actions runs the same validation for every commit in a pull request.

### Format the library

```sh
./format_library.sh
```

This tool uses BibTool to normalize and sort the full library.
Before you run this tool, commit your work.
Never run it in the middle of a stack.

Install BibTool with `brew install bib-tool` on macOS.
On Debian, use `apt-get install bibtool`.
The options follow the [BibTool manual](https://ctan.org/pkg/bibtool).

### Clean your bibliography before publication

```sh
./export_bibliography.py ../paper/main.tex ../paper/submission.bib
```

This tool scans the paper and its local LaTeX source files.
It copies only the cited entries and their required macros and dependencies.

A missing citation or source file stops the export.
The tool keeps an existing output file unchanged.
Use `--force` to replace that file.
It does not expand custom LaTeX macros.

### Review every reference

```sh
make
```

This command builds `all_bib_doc.pdf` with every entry in the library.
Use the PDF to find title, author, and layout problems.

### Run the tests

```sh
make test
```

The tests cover the parser, validator, DOI importer, and bibliography exporter.

## Citation keys

Use `LastnameYYvenue` for each citation key.
Use the surname of the first listed author in ASCII, with an initial capital.
Use the final two digits of the year.
The venue suffix must match the `@STRING` macro name exactly.

Real examples include:

| Key | Parts |
| --- | --- |
| `Alexandrov20jmlr` | Alexandrov, 2020, `journal = jmlr` |
| `Deng09cvpr` | Deng, 2009, `booktitle = cvpr` |
| `Loning19arxiv` | `L{\"o}ning` becomes Loning, 2019, `journal = arxiv` |

For a duplicate base key, append the capitalized first word of the title.
Some papers list authors alphabetically.
Therefore, the first listed author is not always the best-known author.

Write authors as one braced list. Separate names with `and`:

```bibtex
author        = {Given Family and Given Middle Family}
```

Use a bare BibTeX month macro, such as `month = jul`.
Do not write `{jul}`, `July`, or `7`.

## arXiv entries

Store a preprint as `@Article` with `journal = arxiv`.
Include `month`, `primaryclass`, `url`, and `arxivid`.

Derive the month from the two digits after the year in the arXiv identifier.
For example, `2510.02410` uses `oct`.

```bibtex
@Article{Lastname25arxiv,
  author        = {Given Lastname and Another Author},
  title         = {{ModelName}: A Brace-Protected Title},
  journal       = arxiv,
  year          = 2025,
  month         = oct,
  primaryclass  = {cs.LG},
  url           = {https://arxiv.org/abs/2510.02410},
  arxivid       = {2510.02410}
}
```

Prefer a published version over its preprint.
Keep `arxivid` on the published entry.
For example, `Goswami24icml` is the published ICML entry and retains its arXiv identifier.

## Protect capitals in titles

Brace-protect every acronym, model name, dataset name, product name, and intentional capital.
The bibliography style can lowercase an unprotected word.

```bibtex
title         = {{OpenTSLM}: Reasoning with {ECG} and {UCR} Data}
```

Nearly every entry contains a model name or dataset name.
An unprotected title will usually render incorrectly.

## Validate metadata at the source

Use a publisher record instead of a search-engine result.
Search engines often contain incomplete or preprint metadata.

- Use [PMLR](https://proceedings.mlr.press/) for ICML and AISTATS papers.
- Use the [NeurIPS proceedings](https://proceedings.neurips.cc/) for NeurIPS papers.
- Use [OpenReview](https://openreview.net/venue?id=ICLR.cc) for ICLR papers.
- Use the [ACL Anthology](https://aclanthology.org/) for ACL, EMNLP, and NAACL papers.

Use the page numbers, author order, title, and year from these records.

## Add a venue macro

Add a missing `@STRING` definition to the correct group in `all.bib`.
Use the macro name as the citation-key suffix.

Add the Crossref venue name to `crossref_abbreviation_map.txt` in the same change:

```text
macro=Full Crossref Venue Name
```

## Repository files

| File | Purpose |
| --- | --- |
| `all.bib` | Stores the venue macros and bibliography entries. |
| `IEEEtran.bst` | Renders the bibliography in the IEEE style. |
| `LICENSE` | Contains the MIT license for the original repository work. |
| `AGENTS.md` | Gives coding agents the repository rules and safe commands. |
| `options.rsc` | Defines the BibTool normalization and field order. |
| `check_library.py` | Validates the library. |
| `bibtex_tools.py` | Provides the parser used by the Python tools. |
| `format_library.sh` | Runs BibTool and validates its result. |
| `doi2bib.py` | Converts a DOI record into a local entry. |
| `export_bibliography.py` | Creates a reduced bibliography for publication. |
| `crossref_abbreviation_map.txt` | Maps Crossref venue names to local macros. |
| `all_bib_doc.tex` | Defines the document for visual review. |
| `Makefile` | Provides build, validation, formatting, and cleanup commands. |
| `pyproject.toml` and `uv.lock` | Define the dependency-free Python environment. |
| `tests/` | Contains the tool tests. |
| `.gitignore` | Excludes generated and local files. |
| `.github/workflows/library.yml` | Validates the current tree and each pull request commit. |

## License

The original work in this repository uses the [MIT License](LICENSE).
`IEEEtran.bst` is a third-party file and retains the license notice inside that file.

## Contribute with stacked pull requests

This repository uses the `gh stack` extension.
Install GitHub CLI 2.90.0 or later and Git 2.20 or later.

```sh
gh extension install github/gh-stack
```

Read the [GitHub stacked pull request guide](https://docs.github.com/en/pull-requests/how-tos/stacked-pull-requests) for more information.

Use this loop:

```sh
gh stack init first-change
# Edit files, validate them, and commit the first layer.
gh stack add second-change
# Edit files, validate them, and commit the next layer.
gh stack submit
gh stack sync
gh stack merge
```

Run `./check_library.py` before every commit in a stack.
Reviewers assess each pull request alone, so every layer must leave `all.bib` valid.

WARNING: Never run `format_library.sh` in the middle of a stack.
BibTool sorts the full library and can create a full-file diff.
That diff conflicts with every branch above the changed branch.

Enable recorded conflict resolution:

```sh
git config rerere.enabled true
```

Stack operations frequently rebase branches against one sorted file.
Recorded conflict resolutions can make repeated rebases easier.
