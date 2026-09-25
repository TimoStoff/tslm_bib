#!/usr/bin/env python3
"""Convert one fetched DOI record and append it to the library."""

from __future__ import annotations

from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from bibtex_tools import (
    ParsedEntry,
    first_author_surname,
    parse_entry,
    scan_blocks,
    unwrap_value,
)


REMOVED_FIELDS = {"url", "publisher", "issn", "address"}
ACCEPT_HEADER = "application/x-bibtex; charset=utf-8"
TYPE_NAMES = {
    "article": "Article",
    "inproceedings": "InProceedings",
    "book": "Book",
    "incollection": "InCollection",
    "misc": "Misc",
    "techreport": "TechReport",
    "phdthesis": "PhDThesis",
    "mastersthesis": "MastersThesis",
    "proceedings": "Proceedings",
    "manual": "Manual",
    "unpublished": "Unpublished",
}


def load_map(path: Path) -> list[tuple[str, str]]:
    mappings: list[tuple[str, str]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}:{line_number}: expected macro=Crossref venue")
        macro, venue = (part.strip() for part in line.split("=", 1))
        if not macro or not venue:
            raise ValueError(f"{path}:{line_number}: empty macro or venue")
        mappings.append((macro, venue))
    return mappings


def normalize_venue(value: str) -> str:
    value = unwrap_value(value)
    value = value.replace("\\&", "and").replace("&", "and")
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def find_venue(entry: ParsedEntry, mappings: list[tuple[str, str]]) -> tuple[str, str] | None:
    fields = entry.field_map()
    candidates: list[tuple[int, str, str]] = []
    for field_name in ("journal", "booktitle"):
        if field_name not in fields:
            continue
        actual = normalize_venue(fields[field_name])
        for macro, full_name in mappings:
            expected = normalize_venue(full_name)
            words = expected.split()
            is_variable_conference_name = len(words) >= 3 and expected in actual
            is_named_series = macro in {"interspeech", "oceans"} and expected in actual
            if expected == actual or is_variable_conference_name or is_named_series:
                candidates.append((len(expected), macro, field_name))
    if not candidates:
        return None
    _, macro, field_name = max(candidates)
    return macro, field_name


def braced(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return "{" + value[1:-1] + "}"
    return value


def convert_entry(entry: ParsedEntry, mappings: list[tuple[str, str]]) -> tuple[str, str | None]:
    fields = [(name, braced(value)) for name, value in entry.fields if name not in REMOVED_FIELDS]
    temporary = ParsedEntry(entry.entry_type, entry.key, tuple(fields), entry.line)
    venue_match = find_venue(temporary, mappings)
    fields_dict = dict(fields)

    if "author" not in fields_dict or "year" not in fields_dict:
        raise ValueError("Crossref record must contain author and year fields")
    surname = first_author_surname(fields_dict["author"])
    year_match = re.search(r"[0-9]{4}", unwrap_value(fields_dict["year"]))
    if not surname or year_match is None:
        raise ValueError("Crossref record has an unusable author or year field")

    comment: str | None = None
    if venue_match is None:
        suffix = "VENUE"
        returned_venue = next(
            (unwrap_value(fields_dict[name]) for name in ("journal", "booktitle") if name in fields_dict),
            "missing journal or booktitle",
        )
        comment = f"% TODO(VENUE): Add or map the Crossref venue: {returned_venue}"
    else:
        suffix, venue_field = venue_match
        fields = [
            (name, suffix if name == venue_field else value) for name, value in fields
        ]

    normalized_fields: list[tuple[str, str]] = []
    for name, value in fields:
        month = unwrap_value(value).lower()
        if name == "month" and month in {
            "jan", "feb", "mar", "apr", "may", "jun",
            "jul", "aug", "sep", "oct", "nov", "dec",
        }:
            value = month
        normalized_fields.append((name, value))

    key = f"{surname}{year_match.group(0)[-2:]}{suffix}"
    entry_type = TYPE_NAMES.get(entry.entry_type, entry.entry_type[:1].upper() + entry.entry_type[1:])
    lines = [f"@{entry_type}{{{key},"]
    for index, (name, value) in enumerate(normalized_fields):
        comma = "," if index < len(normalized_fields) - 1 else ""
        lines.append(f"  {name:<14}= {value}{comma}")
    lines.append("}")
    return "\n".join(lines), comment


def existing_keys(text: str) -> set[str]:
    keys: set[str] = set()
    blocks, _ = scan_blocks(text)
    for block in blocks:
        if block.entry_type.lower() in {"string", "comment", "preamble"}:
            continue
        entry, _ = parse_entry(block)
        if entry is not None:
            keys.add(entry.key)
    return keys


def fetch_bibtex(doi: str) -> tuple[str, int]:
    encoded_doi = quote(doi, safe="/:;()[]%")
    request = Request(
        f"https://doi.org/{encoded_doi}",
        headers={"Accept": ACCEPT_HEADER, "User-Agent": "tslm-bib DOI importer"},
    )
    with urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8")
        return body, response.status


def print_response_error(message: str, response: str) -> None:
    print(message, file=sys.stderr)
    print("Response:", file=sys.stderr)
    print(response, file=sys.stderr)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        program = Path(argv[0]).name
        print(f"Usage: ./{program} DOI", file=sys.stderr)
        print(
            f"Example: ./{program} 10.1038/s41597-024-03960-3",
            file=sys.stderr,
        )
        return 2

    script_dir = Path(__file__).resolve().parent
    doi = argv[1]
    try:
        response, status = fetch_bibtex(doi)
    except HTTPError as error:
        response = error.read().decode("utf-8", errors="replace")
        print_response_error(
            f"The DOI service returned HTTP status {error.code}.", response
        )
        return 1
    except URLError as error:
        print(f"The DOI request failed: {error.reason}", file=sys.stderr)
        return 1
    except (OSError, UnicodeError) as error:
        print(f"The DOI request failed: {error}", file=sys.stderr)
        return 1

    try:
        blocks, scan_problems = scan_blocks(response)
        normal_blocks = [
            block for block in blocks if block.entry_type.lower() not in {"string", "comment", "preamble"}
        ]
        if scan_problems or len(normal_blocks) != 1:
            print_response_error(
                f"The DOI service did not return one BibTeX entry. HTTP status: {status}",
                response,
            )
            return 1
        entry, parse_problems = parse_entry(normal_blocks[0])
        if entry is None or parse_problems:
            print_response_error(
                "The DOI service returned invalid BibTeX: "
                + ("; ".join(parse_problems) or "cannot parse the entry"),
                response,
            )
            return 1
        mappings = load_map(script_dir / "crossref_abbreviation_map.txt")
        converted, comment = convert_entry(entry, mappings)

        library_path = script_dir / "all.bib"
        library = library_path.read_text(encoding="utf-8")
        new_key = converted.split("{", 1)[1].split(",", 1)[0]
        if new_key in existing_keys(library):
            raise ValueError(f"citation key {new_key!r} already exists")

        if library.endswith("\n\n"):
            addition = ""
        elif library.endswith("\n"):
            addition = "\n"
        else:
            addition = "\n\n"
        if comment is not None:
            addition += comment + "\n"
        addition += converted + "\n"
        with library_path.open("a", encoding="utf-8") as library_file:
            library_file.write(addition)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"Cannot import DOI {doi}: {error}", file=sys.stderr)
        return 1

    print("The entry was appended to all.bib. Check every field before you commit.")
    print("Crossref usually omits conference page numbers. Add them when applicable.")
    print("Then run ./format_library.sh.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
