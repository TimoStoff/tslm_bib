#!/usr/bin/env python3
"""Validate the structural and citation-key rules of the BibTeX library."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import re
import sys

from bibtex_tools import (
    IDENTIFIER_RE,
    INTEGER_RE,
    ParsedEntry,
    braces_are_balanced,
    first_author_surname,
    first_title_word,
    is_single_braced_string,
    parse_entry,
    scan_blocks,
    split_assignment,
    unwrap_value,
)


MONTHS = {"jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"}
SPECIAL_TYPES = {"string", "comment", "preamble"}
KEY_SHAPE_RE = re.compile(r"[A-Z][A-Za-z]*[0-9]{2}[A-Za-z][A-Za-z0-9]*\Z")


def _numeric_value(value: str) -> str | None:
    unwrapped = unwrap_value(value)
    return unwrapped if INTEGER_RE.fullmatch(unwrapped) else None


def _venue_macro(fields: dict[str, str]) -> str | None:
    for field_name in ("journal", "booktitle"):
        value = fields.get(field_name, "").strip()
        if IDENTIFIER_RE.fullmatch(value):
            return value.lower()
    return None


def validate_text(text: str) -> tuple[int, int, list[str]]:
    blocks, problems = scan_blocks(text)
    macros: dict[str, int] = {}
    entries: list[ParsedEntry] = []

    for block in blocks:
        entry_type = block.entry_type.lower()
        if entry_type == "string":
            assignment = split_assignment(block.body)
            if assignment is None or not IDENTIFIER_RE.fullmatch(assignment[0]):
                problems.append(f"line {block.line}: invalid @STRING definition")
                continue
            macros[assignment[0].lower()] = block.line
            continue
        if entry_type in SPECIAL_TYPES:
            continue
        entry, entry_problems = parse_entry(block)
        problems.extend(entry_problems)
        if entry is not None:
            entries.append(entry)

    key_counts = Counter(entry.key for entry in entries)
    for key, count in key_counts.items():
        if count > 1:
            problems.append(f"duplicate citation key {key!r} ({count} entries)")

    expected_groups: dict[str, list[ParsedEntry]] = defaultdict(list)

    for entry in entries:
        fields = entry.field_map()
        for field_name, value in entry.fields:
            if not braces_are_balanced(value):
                problems.append(
                    f"line {entry.line}: {entry.key}: {field_name} has unbalanced braces"
                )
                continue
            if not (
                is_single_braced_string(value)
                or INTEGER_RE.fullmatch(value.strip())
                or IDENTIFIER_RE.fullmatch(value.strip())
            ):
                problems.append(
                    f"line {entry.line}: {entry.key}: {field_name} has an invalid value {value!r}"
                )

        for field_name in ("journal", "booktitle", "publisher"):
            value = fields.get(field_name, "").strip()
            if IDENTIFIER_RE.fullmatch(value) and value.lower() not in macros:
                problems.append(
                    f"line {entry.line}: {entry.key}: undefined macro {value!r} in {field_name}"
                )

        if "month" in fields and fields["month"].strip().lower() not in MONTHS:
            problems.append(
                f"line {entry.line}: {entry.key}: month must be a bare BibTeX month macro"
            )

        required: tuple[str, ...] = ()
        if entry.entry_type == "article":
            required = ("author", "title", "journal", "year")
        elif entry.entry_type == "inproceedings":
            required = ("author", "title", "booktitle", "year")
        missing = [field_name for field_name in required if field_name not in fields]
        if missing:
            problems.append(
                f"line {entry.line}: {entry.key}: missing required field(s): {', '.join(missing)}"
            )

        if not KEY_SHAPE_RE.fullmatch(entry.key):
            problems.append(
                f"line {entry.line}: {entry.key}: citation key does not match LastnameYYvenue"
            )

        author = fields.get("author")
        year = _numeric_value(fields.get("year", ""))
        venue = _venue_macro(fields)
        if author is None or year is None or len(year) < 2 or venue is None:
            continue

        surname = first_author_surname(author)
        short_year = year[-2:]
        base_key = f"{surname}{short_year}{venue}"
        expected_groups[base_key].append(entry)

        year_match = re.search(r"[0-9]{2}", entry.key[len(surname) :])
        if year_match is None or year_match.group(0) != short_year:
            problems.append(
                f"line {entry.line}: {entry.key}: key year does not match year {year}"
            )
        if not entry.key.startswith(surname):
            problems.append(
                f"line {entry.line}: {entry.key}: key surname does not match first author {surname!r}"
            )
        prefix = f"{surname}{short_year}"
        if entry.key.startswith(prefix) and not entry.key[len(prefix) :].startswith(venue):
            problems.append(
                f"line {entry.line}: {entry.key}: key venue does not match macro {venue!r}"
            )

    for base_key, group in expected_groups.items():
        for entry in group:
            expected_key = base_key
            if len(group) > 1:
                expected_key += first_title_word(
                    entry.field_map().get("title", "")
                )
            if entry.key != expected_key:
                problems.append(
                    f"line {entry.line}: {entry.key}: expected citation key {expected_key!r}"
                )

    keys = [entry.key for entry in entries]
    if keys != sorted(keys):
        for previous, current in zip(keys, keys[1:]):
            if previous > current:
                problems.append(
                    f"entries are not sorted by key: {current!r} follows {previous!r}"
                )
                break

    return len(macros), len(entries), problems


def main(argv: list[str]) -> int:
    if len(argv) > 2:
        print(f"Usage: {Path(argv[0]).name} [BIB_FILE]", file=sys.stderr)
        return 2

    path = Path(argv[1]) if len(argv) == 2 else Path("all.bib")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        print(f"Cannot read {path}: {error}", file=sys.stderr)
        return 2

    macro_count, entry_count, problems = validate_text(text)
    print(f"Macros: {macro_count}")
    print(f"Entries: {entry_count}")
    if problems:
        print("Problems:")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print(f"OK: {path} is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
