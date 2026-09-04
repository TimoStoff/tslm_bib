"""Small BibTeX parsing helpers for the repository scripts."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


IDENTIFIER_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.:+/-]*\Z")
INTEGER_RE = re.compile(r"[0-9]+\Z")


@dataclass(frozen=True)
class Block:
    entry_type: str
    body: str
    line: int
    raw: str | None = None


@dataclass(frozen=True)
class ParsedEntry:
    entry_type: str
    key: str
    fields: tuple[tuple[str, str], ...]
    line: int

    def field_map(self) -> dict[str, str]:
        return dict(self.fields)


def _is_escaped(text: str, position: int) -> bool:
    backslashes = 0
    position -= 1
    while position >= 0 and text[position] == "\\":
        backslashes += 1
        position -= 1
    return backslashes % 2 == 1


def scan_blocks(text: str) -> tuple[list[Block], list[str]]:
    """Find BibTeX blocks without treating braces in STRING quotes as syntax."""
    blocks: list[Block] = []
    problems: list[str] = []
    position = 0

    while position < len(text):
        marker = text.find("@", position)
        if marker < 0:
            break

        type_match = re.match(r"@([A-Za-z]+)\s*([({])", text[marker:])
        if type_match is None:
            position = marker + 1
            continue

        entry_type = type_match.group(1)
        opener = type_match.group(2)
        closer = "}" if opener == "{" else ")"
        body_start = marker + type_match.end()
        depth = 1
        in_quote = False
        cursor = body_start

        while cursor < len(text):
            character = text[cursor]
            if entry_type.lower() == "string" and character == '"':
                if not _is_escaped(text, cursor):
                    in_quote = not in_quote
            elif not in_quote:
                if character == opener:
                    depth += 1
                elif character == closer:
                    depth -= 1
                    if depth == 0:
                        break
            cursor += 1

        line = text.count("\n", 0, marker) + 1
        if depth != 0:
            problems.append(
                f"line {line}: unterminated @{entry_type} block; "
                "a value may have unbalanced braces"
            )
            break

        blocks.append(
            Block(entry_type, text[body_start:cursor], line, text[marker : cursor + 1])
        )
        position = cursor + 1

    return blocks, problems


def split_top_level(text: str, separator: str = ",") -> tuple[list[str], bool]:
    """Split on a separator that is outside braces and quoted strings."""
    parts: list[str] = []
    start = 0
    depth = 0
    in_quote = False

    for position, character in enumerate(text):
        if character == '"' and not _is_escaped(text, position):
            in_quote = not in_quote
            continue
        if in_quote:
            continue
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth < 0:
                return parts + [text[start:]], False
        elif character == separator and depth == 0:
            parts.append(text[start:position])
            start = position + 1

    parts.append(text[start:])
    return parts, depth == 0 and not in_quote


def split_assignment(text: str) -> tuple[str, str] | None:
    """Split one field assignment at its top-level equals sign."""
    depth = 0
    in_quote = False
    for position, character in enumerate(text):
        if character == '"' and not _is_escaped(text, position):
            in_quote = not in_quote
            continue
        if in_quote:
            continue
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
        elif character == "=" and depth == 0:
            return text[:position].strip(), text[position + 1 :].strip()
    return None


def parse_entry(block: Block) -> tuple[ParsedEntry | None, list[str]]:
    """Parse a normal entry block into its key and ordered fields."""
    problems: list[str] = []
    pieces, balanced = split_top_level(block.body)
    if not balanced:
        problems.append(f"line {block.line}: unbalanced entry body")
    if len(pieces) < 2:
        problems.append(f"line {block.line}: entry has no fields")
        return None, problems

    key = pieces[0].strip()
    if not key:
        problems.append(f"line {block.line}: entry has an empty citation key")
        return None, problems

    fields: list[tuple[str, str]] = []
    seen: set[str] = set()
    for piece in pieces[1:]:
        if not piece.strip():
            continue
        assignment = split_assignment(piece)
        if assignment is None:
            problems.append(
                f"line {block.line}: {key}: field has no top-level equals sign"
            )
            continue
        field_name, value = assignment
        normalized_name = field_name.lower()
        if not IDENTIFIER_RE.fullmatch(field_name):
            problems.append(
                f"line {block.line}: {key}: invalid field name {field_name!r}"
            )
            continue
        if normalized_name in seen:
            problems.append(
                f"line {block.line}: {key}: repeated field {normalized_name!r}"
            )
        seen.add(normalized_name)
        fields.append((normalized_name, value))

    return ParsedEntry(block.entry_type.lower(), key, tuple(fields), block.line), problems


def braces_are_balanced(value: str) -> bool:
    depth = 0
    for character in value:
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def is_single_braced_string(value: str) -> bool:
    value = value.strip()
    if len(value) < 2 or value[0] != "{" or value[-1] != "}":
        return False
    depth = 0
    for position, character in enumerate(value):
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0 and position != len(value) - 1:
                return False
            if depth < 0:
                return False
    return depth == 0


def unwrap_value(value: str) -> str:
    value = value.strip()
    if is_single_braced_string(value):
        return value[1:-1].strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1].strip()
    return value


def split_first_author(authors: str) -> str:
    depth = 0
    position = 0
    while position < len(authors):
        character = authors[position]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
        elif depth == 0 and authors[position : position + 5].lower() == " and ":
            return authors[:position].strip()
        position += 1
    return authors.strip()


def latex_to_ascii(text: str) -> str:
    """Reduce common LaTeX name accents to their ASCII base letters."""
    replacements = {
        "ss": "ss",
        "ae": "ae",
        "oe": "oe",
        "aa": "a",
        "o": "o",
        "l": "l",
    }
    text = re.sub(
        r"\{\\[`'\"^~=.uvHckbdrt]\s*([A-Za-z])\}", r"\1", text
    )
    text = re.sub(
        r"\\[`'\"^~=.uvHckbdrt]\s*\{?([A-Za-z])\}?", r"\1", text
    )

    def replace_command(match: re.Match[str]) -> str:
        command = match.group(1)
        return replacements.get(command.lower(), "")

    text = re.sub(r"\\([A-Za-z]+)", replace_command, text)
    text = text.replace("{", "").replace("}", "")
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def first_author_surname(author_value: str) -> str:
    authors = unwrap_value(author_value)
    first_author = split_first_author(authors)
    name_parts, _ = split_top_level(first_author)
    if len(name_parts) > 1:
        surname_source = name_parts[0]
    else:
        words = first_author.split()
        surname_source = words[-1] if words else ""
    surname = re.sub(r"[^A-Za-z0-9]", "", latex_to_ascii(surname_source))
    return surname[:1].upper() + surname[1:] if surname else ""


def first_title_word(title_value: str) -> str:
    title = latex_to_ascii(unwrap_value(title_value))
    match = re.search(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", title)
    if match is None:
        return "Title"
    word = re.sub(r"[^A-Za-z0-9]", "", match.group(0))
    return word[:1].upper() + word[1:]
