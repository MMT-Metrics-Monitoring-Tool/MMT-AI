from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from chatbot.course_content import CourseContent
from chatbot.deadlines import extract_dated_items, format_upcoming
from chatbot.prompt_loader import PromptLoader


SYSTEM_PROMPT_NAME = "system"


@dataclass(frozen=True)
class ContextBuilder:
    """Assembles everything the model needs for one answer.
    All lookups and date calculations are done here in code, so answering takes a single LLM call.
    """
    prompt_loader: PromptLoader
    course_content: CourseContent
    get_project_snapshot: Callable[[int], str]

    @property
    def prompt_version(self) -> str:
        return self.prompt_loader.get_version(SYSTEM_PROMPT_NAME)

    def system_prompt(self, project_id: int, today: date, project_snapshot: str | None = None) -> str:
        pages = self.course_content.pages()
        dated_items = [item for markdown in pages.values() for item in extract_dated_items(markdown)]
        snapshot = project_snapshot if project_snapshot is not None else self.get_project_snapshot(project_id)
        values = {
            "{course_material}": self.course_content.get(),
            "{today}": today.strftime("%A %d.%m.%Y"),
            "{upcoming_dates}": format_upcoming(dated_items, today),
            "{project_data}": snapshot,
        }
        # str.replace instead of str.format, because the inserted texts may contain braces.
        prompt = self.prompt_loader.get_prompt(SYSTEM_PROMPT_NAME)
        for placeholder, value in values.items():
            prompt = prompt.replace(placeholder, value)
        return prompt

    def build_messages(
            self,
            question: str,
            history: list[dict[str, str]],
            project_id: int,
            today: date | None = None,
            project_snapshot: str | None = None,
    ) -> list[dict[str, str]]:
        """Returns the chat messages for the LLM: system prompt, conversation history and the new question.

        Args:
            today: Overrides today's date. Used by the evaluations to get reproducible answers.
            project_snapshot: Overrides the project data from the database. Used by the evaluations.
        """
        return [
            {"role": "system", "content": self.system_prompt(project_id, today or date.today(), project_snapshot)},
            *history,
            {"role": "user", "content": question},
        ]
