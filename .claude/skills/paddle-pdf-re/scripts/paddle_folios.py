"""Read printed page labels and suppress visible PaddleOCR margin furniture."""

import html
import re
import unicodedata
from collections import Counter
from urllib.parse import unquote


_NUMERALS = (
    r"\u3007\u96f6\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d"
    r"\u5341\u767e\u5343\u4e07\u842c\u5eff\u5345\u534c"
)
_FOLIO = rf"(?:(?:[A-Z]{{1,2}}-?)?[0-9]{{1,6}}|[ivxlcdm]{{1,12}}|[{_NUMERALS}]{{1,10}})"
_ROMAN = re.compile(r"M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})")
_WRAPPERS = (("(", ")"), ("[", "]"), ("\u3010", "\u3011"), ("\u3014", "\u3015"))
_DASHES = r"\-\u2010-\u2015\u2212\u00b7\u2022"
_NUMBER_BLOCKS = {"number", "page_number"}
_MARGIN_BLOCKS = {"header", "footer", "header_image", "footer_image", *_NUMBER_BLOCKS}
_PAGE_WORD = (rf"(?:\u7b2c\s*)?({_FOLIO})\s*[\u9875\u9801]"
              rf"|(?:page\b\s*:?|p\.)\s*({_FOLIO})(?:\s+of\s+\d+)?")
_RANGE = re.compile(r"\d+\s*[-\u2010-\u2015\u2212]\s*(?:[A-Z]{1,2}-?)?\d+", re.IGNORECASE)
_DATE_OR_ISSUE = re.compile(
    r"(?:\b(?:vol(?:ume)?|no|number|issue|year|series|part|chapter|section|appendix|table|fig(?:ure)?|eq(?:uation)?)\.?"
    r"|\b(?:january|february|march|april|may|june|july|august|september|october|november|december)"
    r"|[\u7b2c\u5e74\u5377\u671f])\s*[:.,]?\s*$", re.IGNORECASE,
)
_IDENTIFIER = re.compile(r"\b(?:doi|issn|isbn|arxiv|pmid)\b|https?://", re.IGNORECASE)
_SEPARATOR = r"(?:\s*[|\u00b7\u2022]\s*|\s+[-\u2010-\u2015]\s+)"
_NOTE_START = re.compile(
    r"^(?:\$\s*\^|[\u2460-\u2473*\u2020\u2021]|\[?\d+[.)\]]\s*|(?:note|source|author)s?\s*:|see\s)"
    r"|^(?:\u4f5c\u8005\u7b80\u4ecb|\u57fa\u91d1\u9879\u76ee|\u6ce8)[\uff1a:]", re.IGNORECASE,
)
_PUBLICATION_LINE = re.compile(
    r"^[^\n:]{2,90},\s*Vol\.\s*\d+,\s*No\.\s*\d+\s*\([^\n)]*\b\d{4}\)\s*,\s*"
    r"\d+\s*[-\u2010-\u2015\u2212]\s*\d+\s*$", re.IGNORECASE,
)
_PUBLISHER_FOOTER = re.compile(
    r"^(?:This content downloaded from\b|All use subject to https?://"
    r"|\u4e2d\u56fd\u77e5\u7f51\s+https?://[^\s]+\s*$"
    r"|(?:\(C\)|\u00a9)\s*\d{4}[^\n]*\b(?:Published by|All rights reserved)\b)",
    re.IGNORECASE,
)
_IMAGE = re.compile(
    r"!\[[^\]\r\n]*\]\(\s*(?:<(?P<angle>[^>\r\n]+)>|(?P<url>[^\s)]+))"
    r"(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)|<img\b[^>\r\n]*>", re.IGNORECASE,
)
_IMAGE_SRC = re.compile(r"\bsrc\s*=\s*(['\"])(.*?)\1", re.IGNORECASE)
_EMPTY_IMAGE_DIV = re.compile(r"^[ \t]*<div\b[^>\r\n]*>\s*</div>[ \t]*$", re.IGNORECASE)


def _key(text: str) -> str:
    plain = unicodedata.normalize("NFKC", html.unescape(text)).strip()
    plain = re.sub(r"(?m)^[ \t]*#{1,6}[ \t]+|[ \t]+#{1,6}[ \t]*$", "", plain)
    for marker in ("**", "__", "*", "_"):
        if plain.startswith(marker) and plain.endswith(marker) and len(plain) > 2 * len(marker):
            plain = plain[len(marker):-len(marker)].strip()
    return " ".join(plain.casefold().split())


def _folio(text: str) -> str | None:
    value = unicodedata.normalize("NFKC", html.unescape(text)).strip()
    for left, right in _WRAPPERS:
        if value.startswith(left) and value.endswith(right):
            value = value[1:-1].strip()
            break
    wrapped = re.fullmatch(rf"[{_DASHES}]+\s*(.+?)\s*[{_DASHES}]+", value)
    if wrapped:
        value = wrapped[1]
    explicit = re.fullmatch(_PAGE_WORD, value, re.IGNORECASE)
    if explicit:
        value = explicit[1] or explicit[2]
    if not re.fullmatch(_FOLIO, value, re.IGNORECASE):
        return None
    if value.isascii() and value.isalpha() and not _ROMAN.fullmatch(value.upper()):
        return None
    return value


def _is_bare_year(label: str) -> bool:
    return label.isascii() and label.isdecimal() and 1900 <= int(label) <= 2100


def _margin_folio(text: str) -> str | None:
    label = _folio(text)
    if label and (unicodedata.normalize("NFKC", text.strip()) != label or not _is_bare_year(label)):
        return label
    return None


def _explicit_edge_folios(text: str) -> set[str]:
    labels = set()
    left = re.match(rf"(?:{_PAGE_WORD})(?=[\s|\u00b7\u2022,:;])", text, re.IGNORECASE)
    right = re.search(rf"(?:{_PAGE_WORD})\s*$", text, re.IGNORECASE)
    for match in (left, right):
        if match and (match[1] or match.start() == 0 or not text[match.start() - 1].isalnum()):
            label = _folio(match[0])
            if label:
                labels.add(label)
    return labels


def _header_folios(text: str) -> set[str]:
    """Read printed labels at the edges of a combined running header."""
    line = unicodedata.normalize("NFKC", text.strip())
    label = _margin_folio(line)
    if label:
        return {label}
    if len(line) > 240:
        return set()
    explicit = _explicit_edge_folios(line)
    if explicit or _RANGE.search(line):
        return explicit
    labels = set()
    separator_pattern = rf"({_SEPARATOR}|\s+)"
    for pattern, follows_text in ((rf"(.+?){separator_pattern}(\S+)", True),
                                  (rf"(\S+){separator_pattern}(.+)", False)):
        match = re.fullmatch(pattern, line)
        if not match:
            continue
        context, separator, token = match.groups() if follows_text else match.group(3, 2, 1)
        label = _margin_folio(token)
        if not label or not any(char.isalpha() for char in context):
            continue
        if _IDENTIFIER.search(context) or (follows_text and _DATE_OR_ISSUE.search(context)):
            continue
        if token == label and label.isalpha() and not separator.strip() and len(separator) == 1:
            continue
        labels.add(label)
    return labels


def _mixed_footer_labels(content: str) -> dict[int, str]:
    lines = content.splitlines()
    positions = [index for index, line in enumerate(lines) if line.strip()]
    if len(positions) < 2:
        return {}
    labels = {}
    for index in (positions[0], positions[-1]):
        line = lines[index].strip()
        if _NOTE_START.match(line):
            continue
        label = _margin_folio(line)
        if label:
            labels[index] = label
    return labels


def folio_free_footer(content: str) -> str:
    """Remove standalone folios from mixed footnote and footer OCR blocks."""
    labels = _mixed_footer_labels(content)
    if len({label.casefold() for label in labels.values()}) != 1:
        return content
    return "".join(line for index, line in enumerate(content.splitlines(keepends=True)) if index not in labels).strip()


def _box(block: dict) -> tuple | None:
    box = block.get("block_bbox")
    if (isinstance(box, (list, tuple)) and len(box) == 4
            and all(isinstance(value, (int, float)) for value in box)
            and 0 <= box[0] < box[2] and 0 <= box[1] < box[3]):
        return tuple(box)
    return None


def _margin(box: tuple | None, height: int | None) -> str | None:
    if not box or not height:
        return None
    if box[3] <= height * 0.2:
        return "top"
    if box[1] >= height * 0.82 and box[3] <= height * 1.01:
        return "bottom"
    return None


def _body_keys(content: str) -> set[str]:
    return {_key(value) for value in [content, *content.splitlines()] if value.strip()}


def _same_row_keys(items: list[tuple[str, tuple | None]]) -> set[str]:
    """Match margin blocks emitted together on a single Markdown line."""
    rows = [items] if not any(box for _, box in items) else []
    for content, box in sorted((item for item in items if item[1]), key=lambda item: item[1][0]):
        # Boxes in a row need to overlap vertically and be placed side by side.
        for row in rows:
            _, previous = row[-1]
            overlap = min(box[3], previous[3]) - max(box[1], previous[1])
            if overlap >= 0.5 * min(box[3] - box[1], previous[3] - previous[1]) and box[0] >= previous[2]:
                row.append((content, box))
                break
        else:
            rows.append([(content, box)])
    return {
        _key(" ".join(content for content, _ in row[start:end]))
        for row in rows for start in range(len(row)) for end in range(start + 2, len(row) + 1)
    }


def _remove_edge(text: str, keys: set[str], side: str, body: Counter) -> str:
    keys.discard("")
    if not keys:
        return text
    lines = text.splitlines(keepends=True)
    if side == "bottom":
        lines.reverse()
    first = 0
    while first < len(lines):
        start = first
        while start < len(lines) and not lines[start].strip():
            start += 1
        for end in range(min(start + 8, len(lines)), start, -1):
            if not lines[end - 1].strip():
                continue
            selected = lines[start:end]
            key = _key("".join(selected if side == "top" else reversed(selected)))
            if key not in keys:
                continue
            if body[key]:
                remaining = lines[end:]
                if side == "bottom":
                    remaining = remaining[::-1]
                remaining_keys = [_key(line) for line in remaining]
                if remaining_keys.count(key) < body[key]:
                    continue
            first = end
            keys.remove(key)
            break
        else:
            break
    if first:
        while first < len(lines) and not lines[first].strip():
            first += 1
    remaining = lines[first:]
    return "".join(remaining if side == "top" else reversed(remaining))


def _remove_mixed_footer(text: str, content: str, body: Counter) -> str:
    """Remove embedded folio lines when the complete footer appears at the end."""
    labels = _mixed_footer_labels(content)
    if len({label.casefold() for label in labels.values()}) != 1:
        return text
    raw_lines = content.splitlines()
    folio_keys = {_key(raw_lines[index]) for index in labels}
    lines = text.splitlines(keepends=True)
    end = len(lines)
    while end > 0 and not lines[end - 1].strip():
        end -= 1
    for start in range(end - 1, max(-1, end - max(12, len(raw_lines) * 2)), -1):
        if not lines[start].strip() or _key("".join(lines[start:end])) != _key(content):
            continue
        for index in sorted({start, end - 1}, reverse=True):
            key = _key(lines[index])
            if key in folio_keys and sum(_key(line) == key for line in lines) > body[key]:
                del lines[index]
        break
    return "".join(lines)


def _remove_margin_images(text: str, header_boxes: set, body_boxes: set) -> str:
    image_boxes = {"_".join(str(int(value)) for value in box) for box in header_boxes - body_boxes}

    def remove_image(match: re.Match) -> str:
        source = match["angle"] or match["url"]
        if not source:
            src_attr = _IMAGE_SRC.search(match[0])
            source = src_attr[2] if src_attr else ""
        filename = unquote(html.unescape(source)).split("?", 1)[0].split("/")[-1]
        if re.search(r"(?:^|[^A-Za-z])(?:header|footer)_image_box_", filename, re.IGNORECASE):
            return ""
        coordinates = re.search(r"_box_(\d+_\d+_\d+_\d+)\.[A-Za-z0-9]+$", filename)
        return "" if coordinates and coordinates[1] in image_boxes else match[0]

    def clean_line(line: str) -> str:
        cleaned = _IMAGE.sub(remove_image, line)
        if cleaned != line and (not cleaned.strip() or _EMPTY_IMAGE_DIV.fullmatch(cleaned.rstrip("\r\n"))):
            return ""
        return cleaned

    return "".join(clean_line(line) for line in text.splitlines(keepends=True))


def display_page(text: str, blocks: list, height: int | None, width: int | None) -> tuple[str, str]:
    """Return the page Markdown and an independently evidenced printed label, or ``unknown``."""
    dedicated = {}
    fallback = {}
    margins = {"top": [], "bottom": []}
    body = Counter()
    margin_images = set()
    body_images = set()
    mixed_footers = []
    title_tops = [box[1] for block in blocks if block.get("block_label") == "doc_title" and (box := _box(block))]

    for block in blocks:
        tag, content = block.get("block_label"), (block.get("block_content") or "").strip()
        box = _box(block)
        side = _margin(box, height)
        if tag in ("header_image", "footer_image"):
            if box:
                margin_images.add(box)
            continue
        if tag in ("image", "chart", "figure") and box:
            body_images.add(box)
        if tag not in _MARGIN_BLOCKS:
            if (tag == "text" and side == "top" and title_tops and box[3] <= min(title_tops)
                    and _PUBLICATION_LINE.fullmatch(content)):
                margins["top"].append((content, box))
            else:
                body.update(_body_keys(content))
            continue
        if height and box and side is None:
            body.update(_body_keys(content))
            continue

        if tag in _NUMBER_BLOCKS:
            label = _folio(content)
            if label and (not (box and width) or box[2] - box[0] <= width * 0.45):
                dedicated.setdefault(label.casefold(), label)
                for edge in (side,) if side else ("top", "bottom"):
                    margins[edge].append((content, box))
            continue

        edge = "top" if tag == "header" else "bottom"
        if side and side != edge:
            continue
        if tag == "header":
            labels = _header_folios(content)
            margins[edge].append((content, box))
        else:
            lines = content.splitlines()
            label = _margin_folio(content)
            labels = set()
            if label:
                labels.add(label)
                margins[edge].append((content, box))
            else:
                for line in lines:
                    line = line.strip()
                    if not line or _NOTE_START.match(line):
                        continue
                    explicit = _explicit_edge_folios(unicodedata.normalize("NFKC", line))
                    if re.search(_SEPARATOR, line):
                        explicit.update(_header_folios(line))
                    if _PUBLISHER_FOOTER.match(line) or explicit:
                        margins[edge].append((line, box))
                        labels.update(explicit)
                mixed = _mixed_footer_labels(content)
                if mixed:
                    labels.update(mixed.values())
                    mixed_footers.append(content)
                    margins[edge].extend((lines[index], None) for index in mixed)
        for label in sorted(labels):
            fallback.setdefault(label.casefold(), label)

    text = _remove_margin_images(text, margin_images, body_images)
    for edge, items in margins.items():
        keys = {_key(content) for content, _ in items}
        text = _remove_edge(text, keys | _same_row_keys(items), edge, body)
    for footer in mixed_footers:
        text = _remove_mixed_footer(text, footer, body)
    labels = dedicated or fallback
    return text, next(iter(labels.values())) if len(labels) == 1 else "unknown"
