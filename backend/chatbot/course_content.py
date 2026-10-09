from bs4 import BeautifulSoup, NavigableString, Tag

import os
import threading
import time
import requests


# The course pages. Small enough to be placed into the system prompt in full, which makes retrieval unnecessary.
COURSE_URLS = (
    "https://coursepages2.tuni.fi/comp-se-610/",
    "https://coursepages2.tuni.fi/comp-se-610/schedule/",
    "https://coursepages2.tuni.fi/comp-se-610/guidelines/",
)

RETRY_SECONDS = 60


def _inline_text(node) -> str:
    """Renders the inline content of an element as Markdown-ish text.
    Struck-through text is kept and marked, as the course pages use it for cancelled or moved dates.
    """
    if isinstance(node, NavigableString):
        return str(node)
    if not isinstance(node, Tag):
        return ""
    if node.name == "br":
        return "\n"
    inner = "".join(_inline_text(child) for child in node.children)
    if node.name in ("del", "s", "strike"):
        return f"~~{inner.strip()}~~" if inner.strip() else ""
    if node.name in ("strong", "b") and inner.strip():
        return f"**{inner.strip()}**"
    return inner


def _clean(text: str) -> str:
    return " ".join(text.split())


def _table_to_markdown(table: Tag) -> str:
    rows = []
    for tr in table.find_all("tr"):
        cells = [_clean(_inline_text(cell)).replace("|", "/") for cell in tr.find_all(["td", "th"])]
        if any(cells):
            rows.append(cells)
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    lines = ["| " + " | ".join(rows[0]) + " |", "|" + " --- |" * width]
    lines += ["| " + " | ".join(row) + " |" for row in rows[1:]]
    return "\n".join(lines)


def _block_to_markdown(node, depth: int = 0) -> list[str]:
    """Converts block-level HTML into Markdown lines, keeping headings, lists and tables."""
    if isinstance(node, NavigableString):
        text = _clean(str(node))
        return [text] if text else []
    if not isinstance(node, Tag):
        return []
    if node.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        return ["", "#" * int(node.name[1]) + " " + _clean(node.get_text(" ")), ""]
    if node.name == "table":
        return ["", _table_to_markdown(node), ""]
    if node.name in ("ul", "ol"):
        lines = []
        for li in node.find_all("li", recursive=False):
            nested = [child for child in li.children if isinstance(child, Tag) and child.name in ("ul", "ol")]
            own = "".join(_inline_text(child) for child in li.children if child not in nested)
            # A list item holding only a nested list is not given an empty bullet of its own.
            if _clean(own) or not nested:
                lines.append("  " * depth + "- " + _clean(own))
            for sub in nested:
                lines += _block_to_markdown(sub, depth + 1)
        return lines
    if node.name == "p":
        text = "\n".join(_clean(part) for part in _inline_text(node).split("\n"))
        return ["", text.strip(), ""] if text.strip() else []
    if node.name == "hr":
        return ["", "---", ""]
    lines = []
    for child in node.children:
        lines += _block_to_markdown(child, depth)
    return lines


def html_to_markdown(html: str) -> str:
    """Extracts the main page content as Markdown. Navigation, headers and footers are dropped."""
    soup = BeautifulSoup(html, "html.parser")
    root = soup.find(class_="entry-content") or soup.find("main") or soup.body or soup
    title = soup.find(class_="entry-title")
    lines = (["# " + _clean(title.get_text(" ")), ""] if title else []) + _block_to_markdown(root)

    # Collapse runs of blank lines.
    output: list[str] = []
    for line in lines:
        if line == "" and (not output or output[-1] == ""):
            continue
        output.append(line)
    return "\n".join(output).strip()


def fetch_page(url: str) -> str:
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return html_to_markdown(response.text)


class CourseContent:
    """Holds the course pages as Markdown. Pages are re-fetched once the TTL expires.
    If a refresh fails, the last successfully fetched version of the page is kept.
    """
    def __init__(self, urls=COURSE_URLS, ttl_seconds: int | None = None, fetch_fn=fetch_page):
        self.urls = urls
        self.ttl_seconds = ttl_seconds if ttl_seconds is not None else int(os.getenv("COURSE_CONTENT_TTL", 6 * 3600))
        self.fetch_fn = fetch_fn
        self._pages: dict[str, str] = {}
        self._last_loaded = 0.0
        self._lock = threading.Lock()

    def refresh(self) -> None:
        failed = False
        for url in self.urls:
            try:
                self._pages[url] = self.fetch_fn(url)
            except Exception as exc:
                failed = True
                print(f"Course content: failed to fetch {url}: {exc}")
        # After a failure, retry soon instead of waiting for the full TTL.
        retry_in = min(RETRY_SECONDS, self.ttl_seconds) if failed else self.ttl_seconds
        self._last_loaded = time.time() - self.ttl_seconds + retry_in

    def pages(self) -> dict[str, str]:
        """Returns the course pages as Markdown, keyed by URL. Refreshes them first if the TTL has expired."""
        with self._lock:
            if time.time() - self._last_loaded > self.ttl_seconds:
                self.refresh()
            return dict(self._pages)

    def get(self) -> str:
        """Returns all course pages as one Markdown document, each page tagged with its source URL."""
        pages = self.pages()
        if not pages:
            return "(Course material could not be loaded.)"
        return "\n\n".join(
            f'<page source="{url}">\n{pages[url]}\n</page>' for url in self.urls if url in pages
        )
