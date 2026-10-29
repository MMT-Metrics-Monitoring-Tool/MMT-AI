from dataclasses import dataclass
from pathlib import Path

from database import db

import uuid


MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def apply_migrations() -> None:
    """Creates the chatbot tables if they do not exist yet."""
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        sql = path.read_text(encoding="utf-8")
        db.run_script(sql)


@dataclass
class AnswerStats:
    model: str | None = None
    prompt_version: str | None = None
    first_token_ms: int | None = None
    total_ms: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    error: str | None = None


class ConversationStore:
    """Stores conversations, messages and feedback in the chatbot_ tables of the MMT database."""

    def get_or_create_conversation(self, conversation_id: str | None, user_id: str, project_id: int) -> str:
        """Returns the conversation ID to use.
        An existing conversation is only reused if it belongs to the same user and project, otherwise a new one is created.
        """
        if conversation_id:
            rows = db.fetch_all(
                "SELECT id FROM chatbot_conversations WHERE id = %s AND user_id = %s AND project_id = %s",
                (conversation_id, user_id, project_id),
            )
            if rows:
                return conversation_id
        new_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO chatbot_conversations (id, user_id, project_id) VALUES (%s, %s, %s)",
            (new_id, user_id, project_id),
        )
        return new_id

    def get_history(self, conversation_id: str, max_messages: int) -> list[dict[str, str]]:
        """Returns the latest messages of a conversation, oldest first, as {"role", "content"} dictionaries.
        Failed answers are left out.
        """
        rows = db.fetch_all(
            "SELECT role, content FROM chatbot_messages "
            "WHERE conversation_id = %s AND error IS NULL "
            "ORDER BY seq DESC LIMIT %s",
            (conversation_id, max_messages),
        )
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

    def add_message(self, conversation_id: str, role: str, content: str, stats: AnswerStats | None = None) -> str:
        stats = stats or AnswerStats()
        message_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO chatbot_messages (id, conversation_id, role, content, model, prompt_version, "
            "first_token_ms, total_ms, prompt_tokens, completion_tokens, error) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (message_id, conversation_id, role, content, stats.model, stats.prompt_version,
             stats.first_token_ms, stats.total_ms, stats.prompt_tokens, stats.completion_tokens, stats.error),
        )
        return message_id

    def save_feedback(self, message_id: str, user_id: str, rating: int, comment: str | None) -> bool:
        """Saves feedback for an assistant message. Returns False if the message does not belong to the user."""
        rows = db.fetch_all(
            "SELECT m.id FROM chatbot_messages m "
            "INNER JOIN chatbot_conversations c ON c.id = m.conversation_id "
            "WHERE m.id = %s AND m.role = 'assistant' AND c.user_id = %s",
            (message_id, user_id),
        )
        if not rows:
            return False
        db.execute(
            "INSERT INTO chatbot_feedback (message_id, user_id, rating, comment) VALUES (%s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE rating = VALUES(rating), comment = VALUES(comment)",
            (message_id, user_id, rating, comment),
        )
        return True

    def get_latest_conversation_id(self, user_id: str, project_id: int) -> str | None:
        """Returns the latest conversation ID for a user and project, or None if there is none."""
        rows = db.fetch_all(
            "SELECT id FROM chatbot_conversations WHERE user_id = %s AND project_id = %s "
            "ORDER BY created_at DESC LIMIT 1",
            (user_id, project_id),
        )
        return rows[0]["id"] if rows else None

    def get_message_for_display(self, conversation_id: str, user_id: str, project_id: int, limit: int = 100) -> list[dict]:
        """Messages for the widget, oldest first. Ownership is verified in the query."""
        rows = db.fetch_all(
            "SELECT m.id, m.role, m.content, m.created_at, f.rating "
            "FROM chatbot_messages m "
            "INNER JOIN chatbot_conversations c ON c.id = m.conversation_id "
            "LEFT JOIN chatbot_feedback f ON f.message_id = m.id AND f.user_id = c.user_id "
            "WHERE m.conversation_id = %s AND c.user_id = %s AND c.project_id = %s "
            "AND m.error IS NULL "
            "ORDER BY m.seq DESC LIMIT %s",
            (conversation_id, user_id, project_id, limit),
        )
        return [
            {"id": r["id"], "role": r["role"], "content": r["content"],
            "createdAt": r["created_at"].isoformat(), "rating": r["rating"]}
            for r in reversed(rows)
        ]

