"""Utility helpers for text processing and normalization."""

import re


def clean_page_content(text: str) -> str:
    """Clean and normalize PDF-extracted page content.

    - Normalize Windows/Mac line endings to \n
    - Collapse multiple blank lines to a single newline
    - Trim trailing spaces on each line
    - Collapse runs of spaces to single spaces (but keep newlines)
    - Strip leading/trailing whitespace
    """

    if not isinstance(text, str):
        return ""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t)  # collapse runs of spaces/tabs
    t = re.sub(r"\n{2,}", "\n", t)  # collapse blank lines
    return t.strip()
