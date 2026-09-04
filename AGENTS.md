# Agent instructions

These instructions apply to the complete repository.

## Protect the library

- Treat `all.bib` as the authoritative shared library.
- Change only the entries or macros required by the task.
- Do not reformat, re-key, or reorder unrelated entries.
- Never edit `IEEEtran.bst`.
- Do not invent missing metadata. Report uncertainty and request a reliable source.

Confirm metadata against the publisher record. Use these primary sources:

- PMLR for ICML and AISTATS.
- `proceedings.neurips.cc` for NeurIPS.
- OpenReview for ICLR.
- The ACL Anthology for ACL, EMNLP, and NAACL.

## Available tools

| Command | Purpose |
| --- | --- |
| `./check_library.py` | Validate `all.bib`. |
| `./check_library.py PATH` | Validate another BibTeX file. |
| `./doi2bib.py DOI` | Fetch, clean, and append a Crossref record. |
| `./export_bibliography.py PAPER OUTPUT` | Create a reduced bibliography for a paper. |
| `./format_library.sh` | Normalize the full library with BibTool, then validate it. |
| `make check` | Run the library validator. |
| `make test` | Run the Python test suite. |
| `make all` | Build the PDF that displays every entry. |
| `make clean` | Remove normal LaTeX build files. |
| `make cleanall` | Remove all generated LaTeX files, including the PDF. |
| `uv sync` | Create the dependency-free managed Python environment. |

The Python tools use only the standard library. BibTool and LaTeX are separate system tools.

GitHub Actions checks the current tree and every commit in each pull request.
Local checks remain required because each commit must be valid before it is pushed.

## Add an entry

Read nearby entries and the `@STRING` header before you edit `all.bib`.
Keep the existing layout:

- Group venue macros under the existing field comments.
- Keep entries sorted by citation key.
- Indent fields with two spaces.
- Pad field names so each equals sign starts in column 17.
- Wrap at 80 columns when possible.
- Indent continuation text to column 19.

Use `LastnameYYvenue` for every citation key:

- Use the surname of the first listed author.
- Remove LaTeX accents and convert the surname to capitalized ASCII.
- Use the final two digits of the publication year.
- Use the exact `@STRING` macro name from `journal` or `booktitle`.
- For a duplicate base key, append the capitalized first word of the title.

Author order can be alphabetical. Always use the first listed author, even when another author is better known.

Write authors in one braced value. Separate authors with `and`.
Use bare BibTeX month macros from `jan` through `dec`.
Brace-protect acronyms, model names, dataset names, and intentional capitals in titles.
Unprotected names can render in lowercase with `IEEEtran.bst`.

Use one of these forms for every field value:

- A string inside balanced braces.
- A bare integer.
- A bare macro name.

Define each macro used by `journal`, `booktitle`, or `publisher` in the header.
Do not repeat a field within one entry.

Use the required fields for common entry types:

- `@Article`: `author`, `title`, `journal`, and `year`.
- `@InProceedings`: `author`, `title`, `booktitle`, and `year`.

For an arXiv preprint, use `@Article` with `journal = arxiv`.
Include `month`, `primaryclass`, `url`, and `arxivid`.
Derive the month from the arXiv identifier.
For example, identifier `2510.02410` uses `year = 2025` and `month = oct`.

Prefer a published record over its preprint. Keep `arxivid` on the published record.

For a new venue, complete both changes together:

1. Add an `@STRING` macro in the correct header group.
2. Add `macro=Full Crossref Venue Name` to `crossref_abbreviation_map.txt`.

The citation-key suffix must use the new macro name exactly.

After `doi2bib.py` appends a record, review every field against the publisher.
Add missing conference page numbers. Resolve any `TODO(VENUE)` comment and move the entry into key order.

## Validate a change

Run these commands after every library edit:

```sh
./check_library.py
python3 -m unittest discover -s tests -v
```

For a visual metadata change, also inspect the rendered bibliography:

```sh
make all
```

Review the complete diff before committing. Confirm that `all.bib` contains only the intended changes.

## Use the formatter carefully

`format_library.sh` changes the complete library. It is not a routine validation command.
The current file contains deliberate manual wrapping that BibTool does not preserve byte for byte.

Do not run the formatter in the middle of a stacked change.
Its full-file sorting can conflict with every branch above the current branch.

If a task requires normalization, create a safe commit first. Then inspect every formatter change before committing it.

## Commit and submit changes

Keep commits small and atomic. Run `./check_library.py` before every commit.
Each commit in a stack must leave the library valid because reviewers assess it alone.

Use the repository stack workflow:

```sh
gh stack init NAME
gh stack add NAME
gh stack submit
gh stack sync
gh stack merge
```

Enable recorded conflict resolution for repeated stack rebases:

```sh
git config rerere.enabled true
```

Add tests for new parser, validator, importer, or exporter behavior.
Use realistic input and protect a distinct failure mode with each test.
