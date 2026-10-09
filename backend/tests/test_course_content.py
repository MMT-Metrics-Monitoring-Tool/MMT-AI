from chatbot import course_content
from chatbot.course_content import CourseContent, html_to_markdown


PAGE = """<html><body><nav>Menu</nav><main><h1 class="entry-title">Schedule</h1>
<div class="entry-content">
<h2>Course schedule</h2>
<ul><li>Moodle submissions deadlines:</li>
<li><ul><li>Test plan <del>23.10.2026</del> 30.10.2026</li></ul></li></ul>
<table><tr><td>Meeting</td><td>Deadline</td></tr><tr><td>Sprint 1 review</td><td><strong>09.10.2026</strong></td></tr></table>
</div></main><footer>Footer</footer></body></html>"""


def test_html_to_markdown_keeps_structure_and_drops_navigation():
    markdown = html_to_markdown(PAGE)
    assert markdown.startswith("# Schedule")
    assert "## Course schedule" in markdown
    assert "- Moodle submissions deadlines:" in markdown
    assert "  - Test plan ~~23.10.2026~~ 30.10.2026" in markdown
    assert "| Sprint 1 review | **09.10.2026** |" in markdown
    assert "Menu" not in markdown and "Footer" not in markdown


def test_failed_refresh_keeps_last_good_page():
    responses = iter(["# First version", RuntimeError("network down")])

    def fetch(url):
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    content = CourseContent(urls=("https://example.invalid/",), ttl_seconds=0, fetch_fn=fetch)
    assert "# First version" in content.get()
    assert "# First version" in content.get()


def test_failed_fetch_is_retried_before_the_ttl(monkeypatch):
    calls = []

    def fetch(url):
        calls.append(url)
        if len(calls) == 1:
            raise RuntimeError("network down")
        return "# Page"

    now = [1_800_000_000.0]
    monkeypatch.setattr(course_content.time, "time", lambda: now[0])
    content = CourseContent(urls=("https://example.invalid/",), ttl_seconds=3600, fetch_fn=fetch)
    assert content.get() == "(Course material could not be loaded.)"
    now[0] += course_content.RETRY_SECONDS + 1
    assert "# Page" in content.get()
    now[0] += 60
    content.get()
    assert len(calls) == 2
