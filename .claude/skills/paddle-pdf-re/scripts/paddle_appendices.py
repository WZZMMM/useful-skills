"""Classify OCR pages by the appendix section active at their start."""

import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


PAGE_START = re.compile(
    r"^<!-- Original PDF (?P<appendix>Appendix )?p\.(?P<folio>[^<>\r\n]+) Begins -->(?=\r?$)",
    re.MULTILINE,
)
APPENDIX_FORMAT_VERSION = 2
_SUPPLEMENT = (
    r"(?:online|web|internet|electronic|supplementary|supplemental)\s+appendix"
    r"|(?:online|web|electronic|supplementary|supplemental)\s+(?:supplement|materials?|information)"
    r"|supporting\s+(?:materials?|information)|在线附录|网络附录|补充附录|补充材料|补充资料"
)
_APPENDIX = r"appendix|appendices|附\s*录"
_APPENDIX_FILE = re.compile(
    rf"^(?:the\s+)?(?:{_SUPPLEMENT}|{_APPENDIX})(?:\s*(?:[-–—:：]|\sfor\s)\s*.+)?$"
    rf"|(?:\s*[-–—_]+\s*|[（(])(?:the\s+)?(?:{_SUPPLEMENT}|{_APPENDIX})(?:[）)])?$",
    re.IGNORECASE,
)
_APPENDIX_TITLE = re.compile(
    rf"^(?P<label>{_APPENDIX})(?:\s*(?P<section>[A-Z]|\d{{1,2}}|[一二三四五六七八九十]))?"
    r"(?:(?:[ \t]*[.．:：、–—-][ \t]*|[ \t]+)(?P<title>.*?))?$",
    re.IGNORECASE,
)
_SUPPLEMENT_TITLE = re.compile(rf"^(?:{_SUPPLEMENT})(?=$|[\s:：.,，–—-])", re.IGNORECASE)
_SUPPLEMENT_SUFFIX = re.compile(rf"(?:^|\s)(?:{_SUPPLEMENT})[.:：]?$", re.IGNORECASE)
_LETTERED_PROOFS = re.compile(
    r"^A(?:[.．:：–—-]\s*|\s+)(?:(?:mathematical|technical)\s+)?proofs?(?:\s+of\b.*|[.:：])?$",
    re.IGNORECASE,
)
_APPENDIX_CAPTION = re.compile(
    r"""(?im)^[ \t]*(?:#{1,6}[ \t]+|<div\b[^>\r\n]*>[ \t]*|\*{1,2})?"""
    r"appendix[ \t]+(?:table|figure|fig\.?)[ \t]+[A-Z][. -]?\d+[a-z]?[.:：]",
)
_PDF_APPENDIX_LABEL = re.compile(r"^app(?:endix)?[\s.-]*[0-9]+$", re.IGNORECASE)
_REFERENCES = r"references|bibliography|literature cited|works cited|参考文献|引用文献"
_REFERENCE_TITLE = re.compile(rf"^(?:{_REFERENCES})[.:：]?$", re.IGNORECASE)
_APPENDIX_REFERENCES = re.compile(
    rf"^(?:appendix\s+(?:{_REFERENCES})|(?:{_REFERENCES})\s+(?:for|of|to|in)\s+"
    rf"(?:the\s+)?(?:{_SUPPLEMENT}|{_APPENDIX}|supplement)|附录(?:参考文献|引用文献))\b",
    re.IGNORECASE,
)
_MAIN_TITLE = re.compile(r"^(?:main (?:article|paper|text)|正文)[.:：]?$", re.IGNORECASE)
_MAIN_SECTION = re.compile(
    r"^(?:introduction|conclusions?|main results|empirical strategy|引言|结论)[.:：]?$",
    re.IGNORECASE,
)
_CONTENTS_TITLE = re.compile(
    r"^(?:(?:table of\s+)?contents|目\s*录|目录页|list of (?:tables|figures))[.:：]?$",
    re.IGNORECASE,
)
_PUBLISHER_NOTICE = re.compile(
    r"^open access\s+this article is licensed\b|^publisher['’]s note\b",
    re.IGNORECASE,
)
_TOC_ITEM = re.compile(r"(?:\.{2,}|·{2,}|…+|[ \t]{3,})\s*(?:[A-Z]-?\d+|\d+|[ivxlcdm]+)$", re.IGNORECASE)
_CAPTION = re.compile(r"^(?:table|figure|fig\.?|chart|exhibit|图|表)(?=$|[\s0-9A-Z（(.:：])", re.IGNORECASE)
_PROSE = re.compile(
    r"^(?:also\s+)?(?:shows?|presents?|reports?|lists?|discuss(?:es)?|provides?|includes?|contains?|"
    r"analy[sz]es?|describes?|illustrates?|explains?|demonstrates?|applies|see|"
    r"is|are|can|will|of\s+\S+|for\s+details|"
    r"中|显示|报告|给出|列出|详见|见|为|是)(?:\b|(?<=[\u4e00-\u9fff]))",
    re.IGNORECASE,
)
_POINTER = re.compile(
    r"(?:can be found|(?:is|are)\s+(?:freely\s+)?available|is located)\s+"
    r"(?:in the online version|online|at\b|on the (?:journal|publisher)|via\b)"
    r"|(?:can|may)\s+be accessed online|(?:详见|参见|请见|可在)[^。]{0,30}(?:网站|在线|网络)",
    re.IGNORECASE,
)
_ABSTRACT = re.compile(r"(?im)^[ \t]*(?:#{1,6}\s+|\*{1,2})?(?:abstract|摘\s*要)\b")
_SECTION_NUMBER = re.compile(r"^(?:(?:\d{1,2}|[IVXLCDM]{1,8})[.)、]?\s+|[一二三四五六七八九十]+[、．.]\s*)")
_FOLIO = re.compile(r"^([A-Z]{0,3})[-–—]?([0-9]{1,6})$")
_APPENDIX_FOLIOS = {"A", "APP", "OA", "S", "SA", "WA"}
_DIV = re.compile(r"^<div\b[^>]*>\s*(.*?)\s*</div\s*>$", re.IGNORECASE)
_BLOCK = re.compile(
    r"(?im)^[ \t]*(?P<fence>[\x60~]{3,})[^\n]*\n[\s\S]*?(?:^[ \t]*(?P=fence)[ \t]*\r?$|\Z)"
    r"|(?is:<(?P<tag>table|pre|code|script|style)\b[^>]*>.*?</(?P=tag)\s*>)"
    r"|(?s:<!--.*?-->|(?<!\\)\$\$.*?(?<!\\)\$\$|\\\[.*?\\\])",
)


@dataclass(frozen=True)
class Boundary:
    position: int
    depth: int | None
    kind: str


def page_marker(folio: str, *, appendix: bool = False) -> str:
    section = "Appendix " if appendix else ""
    return f"<!-- Original PDF {section}p.{folio} Begins -->"


def _folio_number(value):
    match = _FOLIO.fullmatch(unicodedata.normalize("NFKC", value).strip().upper())
    return (match[1], int(match[2])) if match else None


def _restart(folios, index):
    previous = next((label for label in reversed(folios[max(index - 2, 0):index]) if label), None)
    sequence = [label for label in folios[index:index + 3] if label]
    if not previous or len(sequence) < 2:
        return False
    first, second = sequence[:2]
    return (
        first[1] == 1 and second == (first[0], 2)
        and (previous[1] >= first[1] or previous[0] != first[0])
    )


def _visible_prefix(text):
    without_comments = re.sub(r"(?s)<!--.*?-->", "", text)
    with_images = re.sub(r"(?i)<img\b[^>\r\n]+>", "[image]", without_comments)
    return " ".join(re.sub(r"<[^>\r\n]+>", "", with_images).split())


def _at_start(text, position):
    before = _visible_prefix(text[:position])
    return not before or bool(len(before) <= 70 and re.fullmatch(
        r"(?i)(?:copyright.{0,58}|©.{0,65}|supplement(?:ary)? materials?|online supplement)", before,
    ))


def _after_cover_title(text, position):
    if position > 300:
        return False
    lines = [line.strip() for line in text[:position].splitlines() if line.strip()]
    return (
        len(lines) in {1, 2} and bool(re.match(r"^#\s+\S", lines[0]))
        and (len(lines) == 1 or not re.search(r"[.!?。！？]|^\W", lines[1]))
    )


def _heading(line, next_line):
    text = line.strip()
    styled = _DIV.fullmatch(text)
    if styled:
        text = styled[1]
    match = re.match(r"^(#{1,6})[ \t]+(.+?)\s*#*$", text)
    if match:
        return match[2].strip(), len(match[1]), True
    if re.fullmatch(r"(?:={2,}|-{2,})", next_line.strip()):
        return text, 1 if "=" in next_line else 2, True
    if len(text) > 4 and text[:2] in {"**", "__"} and text.endswith(text[:2]):
        return text[2:-2].strip(), None, True
    return text, None, styled is not None


def _boundary_kind(title, depth, styled, early, following):
    title = unicodedata.normalize("NFKC", title)
    if _PUBLISHER_NOTICE.match(title):
        return "publisher"
    if not title or len(title) > 190 or _TOC_ITEM.search(title):
        return None
    plain = _SECTION_NUMBER.sub("", title, count=1)
    if _CONTENTS_TITLE.fullmatch(plain):
        return "contents"
    if _MAIN_TITLE.fullmatch(plain):
        return "main"
    if _APPENDIX_REFERENCES.match(plain):
        return "appendix_references"
    if _REFERENCE_TITLE.fullmatch(plain):
        return "references"
    if styled and _MAIN_SECTION.fullmatch(plain):
        return "main_section"
    if styled and _LETTERED_PROOFS.fullmatch(plain):
        return "lettered_proofs"
    suffix = _SUPPLEMENT_SUFFIX.search(plain)
    if early and depth in {1, 2} and suffix and suffix.start():
        prefix = plain[:suffix.start()].strip()
        if (depth == 1 or prefix.endswith((":", "-", "–", "—"))) and not re.search(
            r"\b(?:see|from|in|the|an|of|to|its|and|or)$", prefix, re.IGNORECASE,
        ):
            return "supplement"

    supplement = _SUPPLEMENT_TITLE.match(plain)
    heading = _APPENDIX_TITLE.fullmatch(plain)
    if not supplement and not heading:
        return "cover" if early and depth == 1 and _ABSTRACT.search(following[:1300]) and not _CAPTION.match(plain) else None
    if not (early or styled or title.isupper()):
        return None
    remainder = plain[supplement.end():].lstrip(" :：.．-–—,，") if supplement else (heading["title"] or "")
    if _CAPTION.match(remainder) or _PROSE.match(remainder) or re.search(r"https?://", plain, re.IGNORECASE):
        return None
    if (supplement or re.match(r"^supplementary (?:data|information|materials?)\b", remainder, re.IGNORECASE)):
        first_body = next((line.strip() for line in following.splitlines() if line.strip()), "")
        if _POINTER.search(first_body):
            return None
    return "supplement" if supplement else "appendix"


def _boundaries(text):
    result = []
    protected = iter(match.span() for match in _BLOCK.finditer(text))
    blocked = next(protected, None)
    lines = text.splitlines(keepends=True)
    position = 0
    for index, line in enumerate(lines):
        start = position
        position += len(line)
        while blocked and blocked[1] <= start:
            blocked = next(protected, None)
        if blocked and blocked[0] < position:
            continue
        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        title, depth, styled = _heading(line, next_line)
        early = _at_start(text, start) if len(title) <= 190 and start < 700 else False
        if not early and (_SUPPLEMENT_TITLE.match(title) or _APPENDIX_TITLE.fullmatch(title)):
            early = _after_cover_title(text, start)
        kind = _boundary_kind(title, depth, styled, early, text[position:position + 1500])
        if kind == "contents" and early:
            return []
        if kind:
            result.append(Boundary(start, depth, kind))
    return result


def _restarted_appendix(folios, bodies, events, start):
    """Confirm missing appendix openings from independent evidence in the new run."""
    first = folios[start]
    if not first or first[1] != 1:
        return False
    caption_pages = 0
    appendix_heading = False
    for index in range(start, len(folios)):
        expected = first[0], index - start + 1
        if folios[index] is not None and folios[index] != expected:
            break
        body = bodies[index]
        leading = [event.kind for event in events[index] if _at_start(body, event.position)]
        if any(kind in {"cover", "main"} for kind in leading) or (
            index <= start + 1 and "main_section" in leading
        ):
            break
        appendix_heading |= "appendix" in leading or "supplement" in leading
        caption_pages += bool(_APPENDIX_CAPTION.search(body))
        if appendix_heading and caption_pages >= 2:
            return True
    return False


def _page_sections(markers, text, stem):
    filename = re.sub(r"(?<=\w)_(?=\w)", " ", unicodedata.normalize("NFKC", stem)).strip()
    filename_match = _APPENDIX_FILE.search(filename) or _APPENDIX_FILE.search(stem)
    separate = bool(filename_match)
    scope = "supplement" if separate else "main"
    appendix_depth = None
    bibliography = False
    folios = [_folio_number(match["folio"]) for match in markers]
    ends = [match.start() for match in markers[1:]] + [len(text)]
    bodies = [text[match.end():end] for match, end in zip(markers, ends)]
    events_by_page = [_boundaries(body) for body in bodies]
    for index, (body, events) in enumerate(zip(bodies, events_by_page)):
        current = folios[index]
        restarted = _restart(folios, index)
        if (scope == "main" and bibliography and restarted and current
                and not any(event.kind == "cover" for event in events)
                and (current[0] in _APPENDIX_FOLIOS or
                     _restarted_appendix(folios, bodies, events_by_page, index))):
            scope = "supplement"
        at_start = scope
        for event in events:
            kind = event.kind
            leading = _at_start(body, event.position)
            if not leading and restarted and kind in {"appendix", "supplement"}:
                leading = _after_cover_title(body, event.position)
            if kind == "supplement":
                scope = "supplement"
                appendix_depth = event.depth
                bibliography = False
            elif kind == "appendix" or (kind == "lettered_proofs" and bibliography):
                if scope == "main":
                    scope = "supplement" if leading and restarted else "appendix"
                appendix_depth = event.depth
                bibliography = False
            elif kind == "appendix_references":
                if scope == "main":
                    scope = "appendix"
                bibliography = False
            elif kind == "references":
                subsection = appendix_depth and event.depth and event.depth > appendix_depth
                if scope != "supplement" and not subsection:
                    scope = "main"
                    bibliography = True
            elif kind == "publisher" and scope == "appendix":
                scope = "main"
            elif kind == "main" or (kind == "cover" and leading and restarted):
                scope = "main"
                bibliography = False
            elif (kind == "main_section" and scope == "appendix" and appendix_depth
                  and event.depth and event.depth < appendix_depth):
                scope = "main"
                bibliography = False
            if leading:
                at_start = scope
        yield at_start != "main"


def annotate_appendices(
    markdown: str, stem: str = "", *, page_overrides: Mapping[int, bool] | None = None,
    pdf_page_labels: Sequence[str] | None = None,
) -> str:
    """Rewrite page-start comments, using source label hints and physical overrides."""
    markers = list(PAGE_START.finditer(markdown))
    overrides = page_overrides or {}
    for index, selected in overrides.items():
        if type(index) is not int or not 1 <= index <= len(markers) or type(selected) is not bool:
            raise ValueError("Appendix overrides require an existing physical page and a boolean")
    sections = _page_sections(markers, markdown, stem)
    labels = pdf_page_labels if pdf_page_labels and len(pdf_page_labels) == len(markers) else None
    parts = []
    offset = 0
    for index, (match, detected) in enumerate(zip(markers, sections), 1):
        parts.append(markdown[offset:match.start()])
        source_appendix = labels is not None and bool(_PDF_APPENDIX_LABEL.fullmatch(labels[index - 1]))
        appendix = overrides.get(index, detected or source_appendix or bool(match["appendix"]))
        parts.append(page_marker(match["folio"], appendix=appendix))
        offset = match.end()
    parts.append(markdown[offset:])
    return "".join(parts)
