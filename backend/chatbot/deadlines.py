from dataclasses import dataclass
from datetime import date

import re


# Full dates such as 09.10.2026. Dates without a year (e.g. sprint ranges "19.10.-30.10.") are not deadlines.
DATE_RE = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")
STRUCK_RE = re.compile(r"~~.*?~~")
MAX_LABEL_LENGTH = 140


@dataclass(frozen=True)
class DatedItem:
    date: date
    label: str


def _parse_dates(text: str) -> list[date]:
    dates = []
    for day, month, year in DATE_RE.findall(text):
        try:
            dates.append(date(int(year), int(month), int(day)))
        except ValueError:
            pass
    return dates


def _clean_label(text: str) -> str:
    text = DATE_RE.sub("", text).replace("**", "")
    # In "Deadlines (Sprint 0 review DL = ..." only the part inside the unclosed parenthesis describes the date.
    if text.count("(") > text.count(")"):
        text = text[text.rfind("(") + 1:]
    text = re.sub(r"\(\s*\)", "", text)
    text = " ".join(text.split()).replace(" .", ".")
    previous = None
    while previous != text:
        previous = text
        text = text.strip(" .,:;=-–")
        if text.endswith(")") and text.count(")") > text.count("("):
            text = text[:-1]
        text = re.sub(r"\s+(latest by|no later than|by)$", "", text)
    return text[:MAX_LABEL_LENGTH]


def _parent_label(text: str) -> str:
    """Shortens a parent list item to its first clause, e.g. "Peer feedback (link can be found...)" -> "Peer feedback"."""
    return _clean_label(re.split(r"[,:(]|\. ", DATE_RE.sub("", text))[0])


def _line_items(text: str, parent: str | None) -> list[DatedItem]:
    """Dated items from one line of text. Lines listing many dates are split at commas, one item per date."""
    if len(_parse_dates(text)) >= 3:
        segments = re.split(r"[,;]", text)
    else:
        segments = [text]
    items = []
    for segment in segments:
        label = _clean_label(segment)
        if parent:
            label = f"{parent}: {label}" if label else parent
        for d in _parse_dates(segment):
            items.append(DatedItem(d, label))
    return items


def extract_dated_items(markdown: str) -> list[DatedItem]:
    """Extracts every dated item from a course page in Markdown.

    Struck-through text is ignored. List items are labelled with their parent item (e.g. "Moodle submissions deadlines"),
    and table cells with the row's first cell and the column header (e.g. "Sprint 3 review - Review deadline").
    """
    items: list[DatedItem] = []
    parents: list[tuple[int, str]] = []
    table_header: list[str] | None = None

    for raw_line in markdown.splitlines():
        line = STRUCK_RE.sub("", raw_line).rstrip()
        stripped = line.strip()

        if not stripped.startswith("|"):
            table_header = None
        else:
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if all(set(cell) <= set("- ") for cell in cells):
                continue
            if table_header is None:
                table_header = cells
                continue
            for index, cell in enumerate(cells):
                row_label = _clean_label(cells[0])
                if index > 0 and index < len(table_header):
                    row_label = f"{row_label} - {table_header[index]}"
                for d in _parse_dates(cell):
                    items.append(DatedItem(d, row_label))
            continue

        if not stripped or stripped.startswith("#"):
            if stripped.startswith("#"):
                parents = []
            continue

        if stripped.startswith("- "):
            indent = len(line) - len(line.lstrip())
            text = stripped[2:]
            while parents and parents[-1][0] >= indent:
                parents.pop()
            parent = _parent_label(parents[-1][1]) if parents else None
            parents.append((indent, text))
        else:
            parents = []
            text, parent = stripped, None

        items += _line_items(text, parent or None)

    return items


def _relative(days: int) -> str:
    if days == 0:
        return "today"
    if days == 1:
        return "tomorrow"
    if days < 14:
        return f"in {days} days"
    return f"in {days // 7} weeks"


def format_upcoming(items: list[DatedItem], today: date, limit: int = 15) -> str:
    """Formats the next dated items from today onwards, sorted by date, with the time remaining."""
    upcoming = sorted({item for item in items if item.date >= today}, key=lambda item: (item.date, item.label))
    if not upcoming:
        return "No upcoming dates found in the course material."
    return "\n".join(
        f"- {item.date.strftime('%a %d.%m.%Y')} ({_relative((item.date - today).days)}): {item.label}"
        for item in upcoming[:limit]
    )
