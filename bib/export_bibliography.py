#!/usr/bin/env python3
"""Create a BibTeX file that contains only entries cited by a LaTeX paper."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

from bibtex_tools import (
    Block,
    IDENTIFIER_RE,
    ParsedEntry,
    parse_entry,
    scan_blocks,
    split_assignment,
    unwrap_value,
)
from check_library import validate_text


CITE_COMMANDS = {
    "autocite",
    "autocites",
    "avolcite",
    "avolcites",
    "cite",
    "citealp",
    "citealps",
    "citealt",
    "citealts",
    "citeauthor",
    "citeauthors",
    "citep",
    "citeps",
    "cites",
    "citet",
    "citets",
    "citeyear",
    "citeyearpar",
    "citeyears",
    "footcite",
    "footcites",
    "footcitetext",
    "footfullcite",
    "fullcite",
    "fvolcite",
    "fvolcites",
    "nocite",
    "notecite",
    "parencite",
    "parencites",
    "pvolcite",
    "pvolcites",
    "smartcite",
    "smartcites",
    "supercite",
    "textcite",
    "textcites",
    "tvolcite",
    "tvolcites",
    "volcite",
    "volcites",
}
MULTI_CITE_COMMANDS = {name for name in CITE_COMMANDS if name.endswith("s")}
INPUT_COMMANDS = {"include", "input", "subfile"}
MONTH_MACROS = {
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec",
}


class ExportError(Exception):
    """Report an input error that prevents a safe export."""


def strip_comments(text: str) -> str:
    """Remove unescaped LaTeX comments and retain line boundaries."""
    result: list[str] = []
    cursor = 0
    while cursor < len(text):
        character = text[cursor]
        if character != "%":
            result.append(character)
            cursor += 1
            continue

        backslashes = 0
        previous = cursor - 1
        while previous >= 0 and text[previous] == "\\":
            backslashes += 1
            previous -= 1
        if backslashes % 2 == 1:
            result.append(character)
            cursor += 1
            continue

        newline = text.find("\n", cursor)
        if newline < 0:
            break
        result.append("\n")
        cursor = newline + 1
    return "".join(result)


def _skip_space(text: str, cursor: int) -> int:
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    return cursor


def _read_group(text: str, cursor: int, opener: str, closer: str) -> tuple[str, int]:
    if cursor >= len(text) or text[cursor] != opener:
        raise ExportError(f"expected {opener!r} at character {cursor + 1}")
    depth = 1
    start = cursor + 1
    cursor += 1
    while cursor < len(text):
        character = text[cursor]
        if character == opener:
            depth += 1
        elif character == closer:
            depth -= 1
            if depth == 0:
                return text[start:cursor], cursor + 1
        cursor += 1
    raise ExportError(f"unclosed {opener!r} group at character {start}")


def _command_arguments(text: str, cursor: int, multiple: bool) -> list[str]:
    arguments: list[str] = []
    while True:
        cursor = _skip_space(text, cursor)
        while cursor < len(text) and text[cursor] == "[":
            _, cursor = _read_group(text, cursor, "[", "]")
            cursor = _skip_space(text, cursor)
        if cursor >= len(text) or text[cursor] != "{":
            if arguments:
                return arguments
            raise ExportError(
                f"citation command has no key group at character {cursor + 1}"
            )
        argument, cursor = _read_group(text, cursor, "{", "}")
        arguments.append(argument)
        if not multiple:
            return arguments
        next_cursor = _skip_space(text, cursor)
        if next_cursor >= len(text) or text[next_cursor] not in "[{":
            return arguments
        cursor = next_cursor


def find_commands(text: str) -> tuple[set[str], list[str]]:
    """Return citation keys and local source paths from uncommented LaTeX."""
    citations: set[str] = set()
    includes: list[str] = []
    text = strip_comments(text)
    command_re = re.compile(r"\\([A-Za-z@]+)\*?")

    for match in command_re.finditer(text):
        preceding_slashes = 0
        previous = match.start() - 1
        while previous >= 0 and text[previous] == "\\":
            preceding_slashes += 1
            previous -= 1
        if preceding_slashes % 2 == 1:
            continue

        command = match.group(1).lower()
        if command in CITE_COMMANDS:
            arguments = _command_arguments(
                text, match.end(), command in MULTI_CITE_COMMANDS
            )
            for argument in arguments:
                citations.update(
                    key.strip() for key in argument.split(",") if key.strip()
                )
        elif command in INPUT_COMMANDS:
            cursor = _skip_space(text, match.end())
            if cursor < len(text) and text[cursor] == "{":
                include, _ = _read_group(text, cursor, "{", "}")
                if include.strip():
                    includes.append(include.strip())
    return citations, includes


def collect_citations(paper: Path) -> tuple[set[str], int]:
    """Read one LaTeX source tree and return its citation keys."""
    pending = [paper.resolve()]
    visited: set[Path] = set()
    citations: set[str] = set()

    while pending:
        source = pending.pop()
        if source in visited:
            continue
        try:
            text = source.read_text(encoding="utf-8")
        except FileNotFoundError as error:
            raise ExportError(f"LaTeX source does not exist: {source}") from error
        except (OSError, UnicodeError) as error:
            raise ExportError(f"cannot read LaTeX source {source}: {error}") from error
        visited.add(source)

        try:
            found, includes = find_commands(text)
        except ExportError as error:
            raise ExportError(f"cannot parse LaTeX source {source}: {error}") from error
        citations.update(found)
        for include in reversed(includes):
            include_path = Path(include)
            if not include_path.suffix:
                include_path = include_path.with_suffix(".tex")
            if not include_path.is_absolute():
                include_path = source.parent / include_path
            pending.append(include_path.resolve())

    return citations, len(visited)


def _raw_block(block: Block) -> str:
    if block.raw is not None:
        return block.raw
    return f"@{block.entry_type}{{{block.body}}}"


def _parse_library(
    library_text: str,
) -> tuple[
    list[tuple[str, Block]],
    dict[str, tuple[ParsedEntry, Block]],
    list[Block],
]:
    _, _, validation_problems = validate_text(library_text)
    if validation_problems:
        details = "\n".join(f"  - {problem}" for problem in validation_problems)
        raise ExportError(f"the source library is invalid:\n{details}")

    blocks, scan_problems = scan_blocks(library_text)
    if scan_problems:
        raise ExportError(
            "cannot parse the source library: " + "; ".join(scan_problems)
        )

    macros: list[tuple[str, Block]] = []
    entries: dict[str, tuple[ParsedEntry, Block]] = {}
    preambles: list[Block] = []
    for block in blocks:
        block_type = block.entry_type.lower()
        if block_type == "string":
            assignment = split_assignment(block.body)
            if assignment is None or not IDENTIFIER_RE.fullmatch(assignment[0].strip()):
                raise ExportError(f"invalid @STRING block on line {block.line}")
            macros.append((assignment[0].strip().lower(), block))
        elif block_type == "preamble":
            preambles.append(block)
        elif block_type != "comment":
            entry, problems = parse_entry(block)
            if entry is None or problems:
                raise ExportError(
                    "cannot parse the source library: " + "; ".join(problems)
                )
            if entry.key in entries:
                raise ExportError(
                    f"duplicate citation key in source library: {entry.key}"
                )
            entries[entry.key] = (entry, block)
    return macros, entries, preambles


def _dependency_keys(entry: ParsedEntry) -> set[str]:
    dependencies: set[str] = set()
    for name, value in entry.fields:
        if name in {"crossref", "xref"}:
            key = unwrap_value(value)
            if key:
                dependencies.add(key)
        elif name == "xdata":
            dependencies.update(
                key.strip() for key in unwrap_value(value).split(",") if key.strip()
            )
    return dependencies


def select_bibliography(
    library_text: str, cited_keys: set[str]
) -> tuple[str, int, int]:
    """Select cited entries, their dependencies, and their string macros."""
    macros, entries, preambles = _parse_library(library_text)
    selected_keys = set(entries) if "*" in cited_keys else set(cited_keys)
    selected_keys.discard("*")

    missing = selected_keys - entries.keys()
    if missing:
        formatted = ", ".join(sorted(missing))
        raise ExportError(
            f"citation keys are missing from the source library: {formatted}"
        )

    pending = list(selected_keys)
    while pending:
        key = pending.pop()
        entry, _ = entries[key]
        for dependency in _dependency_keys(entry):
            if dependency not in entries:
                raise ExportError(
                    f"entry {key} depends on missing bibliography entry {dependency}"
                )
            if dependency not in selected_keys:
                selected_keys.add(dependency)
                pending.append(dependency)

    macro_names = {name for name, _ in macros}
    selected_macros: set[str] = set()
    for key in selected_keys:
        entry, _ = entries[key]
        for _, value in entry.fields:
            bare_value = value.strip().lower()
            if bare_value in macro_names and bare_value not in MONTH_MACROS:
                selected_macros.add(bare_value)

    output_blocks = [
        _raw_block(block) for name, block in macros if name in selected_macros
    ]
    output_blocks.extend(_raw_block(block) for block in preambles)
    output_blocks.extend(
        _raw_block(block) for key, (_, block) in entries.items() if key in selected_keys
    )
    output = "\n\n".join(output_blocks) + "\n"
    return output, len(selected_keys), len(selected_macros)


def write_atomic(path: Path, text: str, force: bool) -> None:
    """Write a UTF-8 file without exposing a partial result."""
    existing_mode: int | None = None
    if path.exists() and not force:
        raise ExportError(
            f"output file already exists: {path}; use --force to replace it"
        )
    if path.exists():
        existing_mode = stat.S_IMODE(path.stat().st_mode)
    if not path.parent.is_dir():
        raise ExportError(f"output directory does not exist: {path.parent}")

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=".bib-export.tmp.",
            delete=False,
        ) as temporary:
            temporary.write(text)
            temporary_path = Path(temporary.name)
        if existing_mode is None:
            current_umask = os.umask(0)
            os.umask(current_umask)
            temporary_path.chmod(0o666 & ~current_umask)
        else:
            temporary_path.chmod(existing_mode)
        os.replace(temporary_path, path)
    except OSError as error:
        raise ExportError(f"cannot write output file {path}: {error}") from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def build_parser(script_dir: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create a standalone BibTeX file that contains only entries cited "
            "by a LaTeX paper."
        ),
        epilog=(
            "Example: ./export_bibliography.py ../paper/main.tex "
            "../paper/submission.bib"
        ),
    )
    parser.add_argument("paper", type=Path, help="main LaTeX source file")
    parser.add_argument("output", type=Path, help="new reduced BibTeX file")
    parser.add_argument(
        "--library",
        type=Path,
        default=script_dir / "all.bib",
        help="source BibTeX library (default: repository all.bib)",
    )
    parser.add_argument(
        "--force", action="store_true", help="replace an existing output file"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    script_dir = Path(__file__).resolve().parent
    arguments = build_parser(script_dir).parse_args(argv)
    paper = arguments.paper.resolve()
    library = arguments.library.resolve()
    output = arguments.output.resolve()

    if output == library:
        print("Cannot replace the source bibliography.", file=sys.stderr)
        return 1
    if output == paper:
        print("Cannot replace the main LaTeX source.", file=sys.stderr)
        return 1
    if output.suffix.lower() != ".bib":
        print("The output file must use the .bib extension.", file=sys.stderr)
        return 1

    try:
        citations, source_count = collect_citations(paper)
        if not citations:
            raise ExportError(
                "the LaTeX sources contain no supported citation commands"
            )
        library_text = library.read_text(encoding="utf-8")
        reduced, entry_count, macro_count = select_bibliography(
            library_text, citations
        )
        write_atomic(output, reduced, arguments.force)
    except FileNotFoundError:
        print(f"Source bibliography does not exist: {library}", file=sys.stderr)
        return 1
    except (OSError, UnicodeError) as error:
        print(f"Cannot read source bibliography {library}: {error}", file=sys.stderr)
        return 1
    except ExportError as error:
        print(f"Cannot export bibliography: {error}", file=sys.stderr)
        return 1

    print(f"Read {source_count} LaTeX source file(s).")
    print(f"Wrote {entry_count} entries and {macro_count} macros to {output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
