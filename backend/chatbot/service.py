from collections.abc import Iterator
from dataclasses import dataclass

from auth import Principal
from chatbot.context import ContextBuilder
from chatbot.llm import LLMClient, StreamResult
from database.conversations import AnswerStats, ConversationStore


# Events streamed to the frontend, in order: start, status, token..., then done or error.
Event = tuple[str, dict]

STATUS_TEXT = "Reading the course material and your project data…"
ERROR_TEXT = "Sorry, I couldn't answer right now. Please try again in a moment."


@dataclass(frozen=True)
class ChatService:
    context: ContextBuilder
    llm: LLMClient
    store: ConversationStore
    history_messages: int = 10

    def answer(self, principal: Principal, project_id: int, question: str, conversation_id: str | None) -> Iterator[Event]:
        """Answers a question as a stream of events. Both the question and the answer are stored with timing and token usage."""
        conversation_id = self.store.get_or_create_conversation(conversation_id, principal.user_id, project_id)
        history = self.store.get_history(conversation_id, self.history_messages)
        self.store.add_message(conversation_id, "user", question)
        yield "start", {"conversation_id": conversation_id}
        yield "status", {"text": STATUS_TEXT}

        result = StreamResult()
        error = None
        try:
            messages = self.context.build_messages(question, history, project_id)
            for text in self.llm.stream(messages, result):
                yield "token", {"text": text}
        except GeneratorExit:
            error = "Client disconnected"
            raise
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            print(f"Chat: answer failed for conversation {conversation_id}: {error}")
        finally:
            stats = AnswerStats(
                model=self.llm.model,
                prompt_version=self.context.prompt_version,
                first_token_ms=result.first_token_ms,
                total_ms=result.total_ms,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                error=error,
            )
            message_id = self.store.add_message(conversation_id, "assistant", result.text, stats)

        if error:
            yield "error", {"text": ERROR_TEXT, "message_id": message_id}
        else:
            yield "done", {"message_id": message_id}
