from __future__ import annotations

from html import unescape
from html.parser import HTMLParser
from typing import List, Optional, Tuple

from upgrade_copilot.index.models import CleanedDocument, SourceDocument, TextBlock


def normalize_whitespace(text: str) -> str:
    return " ".join(unescape(text).split())


class _HTMLBlockParser(HTMLParser):
    _HEADING_TAGS = {f"h{level}" for level in range(1, 7)}
    _TEXT_TAGS = _HEADING_TAGS | {"title", "p", "li", "pre", "code"}
    _IGNORE_TAGS = {"script", "style", "noscript"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.blocks: list[TextBlock] = []
        self._active_tag: Optional[str] = None
        self._buffer: List[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag in self._IGNORE_TAGS:
            self._ignored_depth += 1
            return

        if self._ignored_depth:
            return

        if tag in self._TEXT_TAGS:
            self._flush()
            self._active_tag = tag

    def handle_endtag(self, tag: str) -> None:
        if tag in self._IGNORE_TAGS and self._ignored_depth:
            self._ignored_depth -= 1
            return

        if self._ignored_depth:
            return

        if tag == self._active_tag:
            self._flush()
            self._active_tag = None

    def handle_data(self, data: str) -> None:
        if self._ignored_depth or not self._active_tag:
            return
        self._buffer.append(data)

    def close(self) -> None:
        super().close()
        self._flush()

    def _flush(self) -> None:
        if not self._active_tag or not self._buffer:
            self._buffer = []
            return

        text = normalize_whitespace("".join(self._buffer))
        self._buffer = []
        if not text:
            return

        if self._active_tag in self._HEADING_TAGS:
            level = int(self._active_tag[1])
            self.blocks.append(TextBlock(kind="heading", text=text, level=level))
            return

        kind = "title" if self._active_tag == "title" else "text"
        self.blocks.append(TextBlock(kind=kind, text=text))


def clean_document(document: SourceDocument) -> CleanedDocument:
    parser = _HTMLBlockParser()
    parser.feed(document.content)
    parser.close()

    title = document.title
    for block in parser.blocks:
        if block.kind == "title":
            title = block.text
            break

    blocks = [block for block in parser.blocks if block.kind != "title"]
    return CleanedDocument(source=document, title=title, blocks=blocks)
