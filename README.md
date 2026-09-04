# TSLM BibTeX library

This repository contains a shared bibliography for time-series language model research.
It also contains small tools that keep the library consistent.

## Use the library in a paper

Reference the library by its path when the paper and this repository have a stable relative layout:

```tex
\bibliography{../tslm_bib/all}
```

BibTeX also reads paths from `BIBINPUTS`.
The final colon retains the default BibTeX search path.

```make
BIB_LIBRARY := $(abspath ../tslm_bib)
export BIBINPUTS := $(BIB_LIBRARY):

paper.pdf: paper.tex
	latexmk -pdf paper.tex
```

A conference submission usually requires a self-contained source tree.
Copy `all.bib` into that tree before submission instead of using an external path.

## Repository files

| File | Purpose |
| --- | --- |
| `all.bib` | Stores the venue macros and bibliography entries. |
| `IEEEtran.bst` | Renders the bibliography in the IEEE style. |
| `AGENTS.md` | Gives coding agents the repository rules and safe commands. |
| `options.rsc` | Defines the BibTool normalization and field order. |
| `check_library.py` | Validates BibTeX syntax, keys, fields, macros, months, and entry order. |
| `bibtex_tools.py` | Provides the parser used by the Python tools. |
| `format_library.sh` | Runs BibTool safely and then validates the result. |
| `doi2bib.py` | Gets and cleans a DOI record, maps its venue, creates its key, and appends it. |
| `export_bibliography.py` | Creates a standalone bibliography with only the entries that a paper cites. |
| `crossref_abbreviation_map.txt` | Maps Crossref venue names to local macro names. |
| `all_bib_doc.tex` | Renders every entry for visual review. |
| `Makefile` | Provides the build, validation, formatting, and cleanup targets. |
| `pyproject.toml` and `uv.lock` | Define a dependency-free Python environment for `uv`. |
| `tests/` | Covers the parser, validator, DOI importer, and bibliography exporter. |
| `.gitignore` | Excludes LaTeX output and local scratch files. |
| `.github/workflows/library.yml` | Validates the current tree and every commit in a pull request. |

The Python tools use only the Python standard library.
If you want a managed environment, run `uv sync`.

## Citation keys

Use `LastnameYYvenue` for each citation key.
The surname comes from the first listed author, in ASCII, with an initial capital.
The year uses its final two digits.
The venue suffix must equal the `@STRING` macro name exactly.

Real examples include:

| Key | Parts |
| --- | --- |
| `Alexandrov20jmlr` | Alexandrov, 2020, `journal = jmlr` |
| `Deng09cvpr` | Deng, 2009, `booktitle = cvpr` |
| `Loning19arxiv` | `L{\"o}ning` becomes Loning, 2019, `journal = arxiv` |

If two entries have the same base key, append the capitalized first title word.
Some papers list authors alphabetically.
Therefore, the first listed author is not always the author associated with the paper in informal discussion.

Write authors as a braced list, and separate names with `and`:

```bibtex
author        = {Given Family and Given Middle Family}
```

Use a bare BibTeX macro for a month, such as `month = jul`.
Do not write `{jul}`, `July`, or `7`.

## arXiv entries

Store a preprint as `@Article` with `journal = arxiv`.
Derive the month from the two digits after the year in the arXiv identifier.
For example, `2510.02410` gives `oct`.

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

If a published version exists, prefer it to the preprint.
Keep `arxivid` on that published entry so readers can find the preprint.
For example, `Goswami24icml` is the published ICML entry and retains its arXiv identifier.

## Protect capitals in titles

Brace-protect every acronym, model name, dataset name, product name, and intentional capital.
The bibliography style can lowercase an unprotected word.

```bibtex
title         = {{OpenTSLM}: Reasoning with {ECG} and {UCR} Data}
```

This rule is especially important in this library.
Nearly every entry contains a model name or dataset name, so an unprotected title usually renders incorrectly.

## Validate metadata at the source

Use a publisher record instead of a search-engine result.
Search engines often contain incomplete or preprint metadata.

- Use [PMLR](https://proceedings.mlr.press/) for ICML and AISTATS papers.
- Use the [NeurIPS proceedings](https://proceedings.neurips.cc/) for NeurIPS papers.
- Use [OpenReview](https://openreview.net/venue?id=ICLR.cc) for ICLR papers.
- Use the [ACL Anthology](https://aclanthology.org/) for ACL, EMNLP, and NAACL papers.

Prefer the page numbers, author order, title, and publication year from these records.

## Add or update an entry

Run the validator from the repository root:

```sh
/path/to/tslm_bib/check_library.py
```

If you need to validate another file, pass its path:

```sh
./check_library.py path/to/library.bib
```

Import a DOI with the helper:

```sh
./doi2bib.py 10.1038/s41597-024-03960-3
```

The importer uses [DOI content negotiation](https://www.crossref.org/documentation/retrieve-metadata/content-negotiation/) and the local Crossref map.
Read the new record carefully after import.
Crossref usually omits conference page numbers.

If a venue is missing, add its `@STRING` definition to the correct group in `all.bib`.
Use the new macro name as the citation-key suffix.
At the same time, add `macro=Full Crossref Venue Name` to `crossref_abbreviation_map.txt`.

Commit the valid hand-edited file before you run the formatter.
This commit gives you a safe point before BibTool changes line wrapping or order.

```sh
./check_library.py
./format_library.sh
```

The formatter requires BibTool.
Install it with `brew install bib-tool` on macOS or `apt-get install bibtool` on Debian.
The resource options come from the [BibTool manual](https://ctan.org/pkg/bibtool).

Build the rendered review document with:

```sh
make
```

The command uses `latexmk -pdf` and writes `all_bib_doc.pdf`.

## Create a submission bibliography

Create a reduced bibliography before an arXiv or conference submission:

```sh
./export_bibliography.py ../paper/main.tex ../paper/submission.bib
```

The exporter follows local `\input`, `\include`, and `\subfile` commands.
It reads common LaTeX, natbib, and biblatex citation commands.
It ignores citations in LaTeX comments.

The output contains the cited entries and the venue macros that those entries use.
The exporter also includes entries referenced through `crossref`, `xref`, or `xdata` fields.
It stops if a citation key or an included source file is missing.

The exporter does not replace an existing output file by default.
Use `--force` to replace a previous export:

```sh
./export_bibliography.py --force ../paper/main.tex ../paper/submission.bib
```

Use `--library` for another library that obeys the rules of this repository:

```sh
./export_bibliography.py --library path/to/library.bib main.tex submission.bib
```

The exporter scans source text and does not expand custom LaTeX macros.
Inspect the reduced file and build the submission after each export.

## Stacked pull requests

This repository uses the `gh stack` extension for stacked pull requests.
Install GitHub CLI 2.90.0 or later and Git 2.20 or later.
Then install the extension:

```sh
gh extension install github/gh-stack
```

GitHub documents the feature in its [stacked pull request guide](https://docs.github.com/en/pull-requests/how-tos/stacked-pull-requests).

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
GitHub Actions also validates each commit in every pull request.

WARNING: Never run `format_library.sh` in the middle of a stack.
BibTool sorts the full library and can create a whole-file diff.
That diff conflicts with every branch above the changed branch.

Enable Git conflict reuse before stack work:

```sh
git config rerere.enabled true
```

Stack operations frequently rebase branches against one sorted file.
Recorded conflict resolutions can make repeated rebases easier.
