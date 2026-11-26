"""Recover page footnotes omitted by PaddleOCR's Markdown renderer."""

import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass

if __package__:
    from .paddle_folios import folio_free_footer
else:
    from paddle_folios import folio_free_footer


CIRCLED = r"[\u2460-\u2473\u24ea-\u24ff\u2776-\u2793\u3251-\u325f\u32b1-\u32bf]"
SUPERSCRIPT = r"[⁰¹²³⁴⁵⁶⁷⁸⁹]{1,3}"
DIGITS = r"[0-9０-９]{1,3}"
SYMBOL = r"[*＊∗]{1,3}|[†‡※]|\\(?:ddagger|dagger|ddag|dag|ast|star)"
TOKEN = rf"(?:{CIRCLED}|{SUPERSCRIPT}|{DIGITS}|{SYMBOL})"
SUP_EXPRESSION = rf"(?:\{{\s*\}}\s*)?(?:\^\s*(?:\{{\s*({TOKEN})\s*\}}|({TOKEN}))|\\textsuperscript\s*\{{\s*({TOKEN})\s*\}})"
MATH_MARKER = re.compile(rf"(?:\$\s*{SUP_EXPRESSION}\s*\$|\\\(\s*{SUP_EXPRESSION}\s*\\\))")
HTML_MARKER = re.compile(rf"<sup\b[^>]*>\s*({TOKEN})\s*</sup\s*>", re.IGNORECASE)
RAW_MARKER = re.compile(rf"\\?(?:{CIRCLED}|{SUPERSCRIPT}|[*＊∗]{{1,3}}|[†‡※])")
NOTE_NUMBER = re.compile(rf"(?:[（(]({DIGITS})[)）]|({DIGITS})(?:[.．](?=\s)|[、)）]))")
BARE_NOTE_NUMBER = re.compile(rf"^({DIGITS})[ \t\u3000]+(?=[^\W\d_]|[\"'“‘（(])")

BLOCK_ZONES = re.compile(
    r"(?m)^[ \t]*(?P<fence>[\x60~]{3,})[^\n]*\n"
    r"(?:(?!^[ \t]*(?P=fence)[ \t]*\r?$)[\s\S])*(?:^[ \t]*(?P=fence)[ \t]*\r?$|\Z)"
    r"|(?is:<(?P<tag>table|figure|pre|code|div|script|style|a)\b[^>]*>.*?</(?P=tag)\s*>)"
    r"|(?s:(?P<opaque><!--.*?(?:-->|\Z)|(?<!\\)\$\$.*?(?<!\\)\$\$|\\\[.*?\\\]))"
    r"|(?m:^[ \t]*\|[^\n]*\|[ \t]*\r?$)"
    r"|(?m:^[ \t]{0,3}\[[^\]\n]+\]:[^\n]*(?:\n(?:[ \t]*\n)?(?: {4}|\t)[^\n]*)*)"
)
INLINE_ZONES = re.compile(
    r"(?P<ticks>\x60+)[^\n]+?(?P=ticks)(?!\x60)"
    r"|!?\[[^\]\n]*\]\((?:[^()\n]|\([^\n]*?\))*\)"
    r"|!?\[[^\]\n]*\]\[[^\]\n]*\]|\[\^[^\]\n]*\]"
    r"|(?i:https?://[^\s<>\u3000]+|<[^>\n]+>)"
    r"|(?:(?<![\w*])|(?=\*{1,3}\w))(?<!\\)(?P<emphasis>\*{1,3})(?=[^*\s])[^\n]*?(?<=\S)(?P=emphasis)(?!\*)"
    r"|(?<!\w)(?P<underline>_{1,3})(?=\S)[^\n]*?(?<=\S)(?P=underline)(?!\w)"
)
INLINE_MATH = re.compile(r"(?<![\\$])\$(?!\$)[^$\n]*?(?<!\\)\$|\\\([^\n]*?\\\)")
PARAGRAPH = re.compile(r"\S.*?(?=\n[ \t]*\r?\n|\Z)", re.DOTALL)
DEFINITION = re.compile(r"^\[\^[^\]\n]+\]:[ \t]*")
ATTACHED = re.compile(r"""[\w.,!?。！？、，）)”’"'»\]】」』》]$""")
LIST_LINE = re.compile(rf"^[ \t]*(?:[-+*][ \t]+|{DIGITS}[.)、][ \t]*|{CIRCLED})")


@dataclass
class Note:
    content: str
    marker: str | None
    body: str
    kind: str


def _key(token):
    if re.fullmatch(CIRCLED, token):
        return f"circle-{int(unicodedata.numeric(token))}"
    aliases = {
        "∗": "*",
        r"\ast": "*",
        r"\star": "*",
        r"\dag": "†",
        r"\dagger": "†",
        r"\ddag": "‡",
        r"\ddagger": "‡",
    }
    return aliases.get(token, unicodedata.normalize("NFKC", token).replace("∗", "*"))


def _leading_marker(content):
    match = MATH_MARKER.match(content) or HTML_MARKER.match(content)
    if match:
        return _key(next(group for group in match.groups() if group)), match.end()
    match = RAW_MARKER.match(content)
    if match:
        marker = _key(match.group().lstrip("\\"))
        if not (marker.startswith("*") and INLINE_ZONES.match(content)):
            return marker, match.end()
    match = NOTE_NUMBER.match(content)
    if match:
        return _key(next(group for group in match.groups() if group)), match.end()
    return None, 0


def _note(content, kind):
    marker, end = _leading_marker(content)
    body = content[end:].strip()
    if not body:
        return Note(content, None, content, kind)
    return Note(content, marker, body, kind)


def _normalized(content):
    return " ".join(content.split())


def _note_key(note):
    return note.marker, _normalized(note.body)


def _spans(text):
    """Include one-line notes within a Markdown paragraph and wrapped notes."""
    paragraphs = [(match.start(), match.end()) for match in PARAGRAPH.finditer(text)]
    lines = [(match.start(), match.end()) for match in re.finditer(r"(?m)^[^\n]*\S[^\n]*$", text)]
    opaque = [
        match.span() for match in BLOCK_ZONES.finditer(text)
        if match["fence"] or match["opaque"] or (match["tag"] or "").lower() in {"pre", "code", "script", "style"}
    ]
    candidates = {span for span in paragraphs + lines if not _overlap(*span, opaque)}
    return sorted(candidates, key=lambda span: (span[0], -span[1]))


def _matches(text, spans, note):
    matches = []
    for start, end in spans:
        chunk = text[start:end].strip()
        definition = DEFINITION.match(chunk)
        if definition and _normalized(chunk[definition.end():]) == _normalized(note.body):
            matches.append((start, end))
        elif _normalized(chunk) == _normalized(note.content):
            matches.append((start, end))
        elif note.marker and _note_key(_note(chunk, note.kind)) == _note_key(note):
            matches.append((start, end))
    return matches


def _overlap(start, end, spans):
    return any(start < stop and end > begin for begin, stop in spans)


def _attached(text, start, end, marker, raw):
    line_start = text.rfind("\n", 0, start) + 1
    before = text[line_start:start].rstrip()
    if not ATTACHED.search(before):
        return False
    if raw and LIST_LINE.match(text[line_start:start]):
        return False
    if raw and marker.startswith("circle-") and before.endswith("第"):
        return False
    if marker.isdecimal() and re.search(r"(?<!\w)[A-Za-z]$|[=×÷+][ ]*[A-Za-z]+$", before):
        # A superscript on a lone Latin variable can belong to the formula.
        return False
    if raw and marker.isdecimal() and before[-1].isdigit():
        return False
    if raw and marker.startswith("*"):
        # Bare asterisks are often Markdown emphasis, list markers or multiplication.
        line_end = text.find("\n", end)
        after = text[end:line_end if line_end != -1 else len(text)].strip()
        return not text[start - 1].isspace() and (not after or after[0] in ",.!?;:，。！？；：)]）")
    return True


def _references(text, excluded):
    """Collect explicit references outside formulas, code, links and table notes."""
    found = defaultdict(list)
    block_spans = excluded + [match.span() for match in BLOCK_ZONES.finditer(text)]
    inline_math = list(INLINE_MATH.finditer(text))
    html = list(HTML_MARKER.finditer(text))
    explicit = [match for match in inline_math if MATH_MARKER.fullmatch(match.group())] + html
    opaque = [
        match.span() for match in INLINE_ZONES.finditer(text)
        if not any(note.start() <= match.start() and match.end() <= note.end() for note in html)
    ]
    raw_excluded = block_spans + opaque + [match.span() for match in inline_math + html]
    for match in explicit + list(RAW_MARKER.finditer(text)):
        start, end = match.span()
        raw = match.re is RAW_MARKER
        if _overlap(start, end, raw_excluded if raw else block_spans + opaque):
            continue
        marker, _ = _leading_marker(match.group())
        if marker and _attached(text, start, end, marker, raw):
            found[marker].append((start, end))
    return found


def _split_notes(note, references):
    if note.marker is None or note.kind == "vision_footnote":
        return [note]

    # A separate line can start a new note. Inside a line require a strong
    # marker, a sentence boundary and explicit references for both notes.
    candidates = set(match.end() for match in re.finditer(r"\n[ \t]*(?=\S)", note.content))
    if note.marker in references:
        candidates.update(match.end() for match in re.finditer(r"[.!?。！？][ \t]*", note.content))
    protected = [match.span() for match in BLOCK_ZONES.finditer(note.content)]
    protected.extend(match.span() for match in INLINE_MATH.finditer(note.content))
    cuts = [0]
    previous = note.marker
    for start in sorted(candidates):
        marker, end = _leading_marker(note.content[start:])
        if not marker or marker == previous or any(begin < start < stop for begin, stop in protected):
            continue
        text_before = note.content[cuts[-1]:start]
        if not _note(text_before.strip(), note.kind).marker or not note.content[start + end:].strip():
            continue
        new_line = "\n" in text_before[len(text_before.rstrip()):]
        if not new_line:
            strong = MATH_MARKER.match(note.content[start:]) or HTML_MARKER.match(note.content[start:])
            if not (marker in references and previous in references and (strong or marker.startswith("circle-"))):
                continue
        elif NOTE_NUMBER.match(note.content[start:]):
            if not (previous.isdecimal() and int(marker) == int(previous) + 1):
                continue
        cuts.append(start)
        previous = marker
    if len(cuts) == 1:
        return [note]
    cuts.append(len(note.content))
    return [_note(note.content[start:end].strip(), note.kind) for start, end in zip(cuts, cuts[1:])]


def _footer_note(note, references):
    if not note.marker or not re.search(r"[^\W\d_]", note.body):
        return False
    return note.marker in references or bool(
        MATH_MARKER.match(note.content)
        or HTML_MARKER.match(note.content)
        or note.marker.startswith("circle-")
        or note.marker in {"†", "‡", "※"}
    )


def _bare_number(note, references):
    if note.marker is None and note.kind == "footnote":
        number = BARE_NOTE_NUMBER.match(note.content)
        if number:
            marker = _key(number[1])
            if len(references.get(marker, [])) == 1:
                return Note(note.content, marker, note.content[number.end():], note.kind)
    return note


def _apply_changes(text, changes):
    end = len(text)
    pieces = []
    for start, stop, replacement in sorted(changes, reverse=True):
        pieces.extend((text[stop:end], replacement))
        end = start
    return text[:end] + "".join(reversed(pieces))


def _visible_note(content):
    if re.match(r"^[0-9]{1,3}[.)][ \t]", content):
        return re.sub(r"^([0-9]+)([.)])", r"\1\\\2", content, count=1)
    if content.startswith("*") and _leading_marker(content)[0]:
        return re.sub(r"^\*+", lambda match: match.group().replace("*", r"\*"), content)
    return content


def render_footnotes(text: str, blocks: list, page_number: int) -> str:
    """Keep OCR note text and link unique same-page reference/definition pairs."""
    notes = []
    excluded = []
    spans = _spans(text)
    for block in blocks:
        kind = block.get("block_label")
        content = (block.get("block_content") or "").strip()
        if kind == "footer":
            content = folio_free_footer(content)
        if not content:
            continue
        if kind in {"footnote", "vision_footnote", "footer"}:
            note = _note(content, kind)
            notes.append(note)
            excluded.extend(_matches(text, spans, note))
        elif kind in {"figure_title", "table_title", "header", "number", "reference_content"}:
            excluded.extend(_matches(text, spans, Note(content, None, content, kind)))

    references = _references(text, excluded)
    recovered = []
    seen = set()
    for note in notes:
        if note.kind == "footer" and not _footer_note(note, references):
            continue
        note = _bare_number(note, references)
        parts = _split_notes(note, references)
        if len(parts) > 1 and _matches(text, spans, note):
            # The merged text is already visible. Leave it intact unless each
            # constituent can be located and handled independently.
            if not all(_matches(text, spans, part) for part in parts):
                parts = [Note(note.content, None, note.content, note.kind)]
        for part in parts:
            key = (part.kind == "vision_footnote", _note_key(part))
            if key not in seen:
                recovered.append(part)
                seen.add(key)

    marker_count = Counter(note.marker for note in recovered if note.kind != "vision_footnote")
    changes = []
    additions = []
    reserved = set(re.findall(r"\[\^([^\]\n]+)\]", text))
    for index, note in enumerate(recovered, 1):
        existing = _matches(text, spans, note)
        reference = references.get(note.marker, [])
        link = (
            note.kind != "vision_footnote" and marker_count[note.marker] == 1
            and len(reference) == 1
            and not any(DEFINITION.match(text[start:end].strip()) for start, end in existing)
        )
        if link:
            note_id = f"p{page_number}-{index}"
            while note_id in reserved:
                note_id += "-note"
            reserved.add(note_id)
            start, end = reference[0]
            if start and text[start - 1] in " \t":
                start -= 1
            changes.append((start, end, f"[^{note_id}]"))
            for start, end in existing:
                if not _overlap(start, end, [item[:2] for item in changes]):
                    changes.append((start, end, ""))
            body = note.body.replace("\n", "\n    ")
            additions.append(f"[^{note_id}]: {body}")
        elif not existing:
            additions.append(_visible_note(note.content))

    if not changes and not additions:
        return text
    return "\n\n".join(part for part in (_apply_changes(text, changes).rstrip(), *additions) if part) + "\n"
