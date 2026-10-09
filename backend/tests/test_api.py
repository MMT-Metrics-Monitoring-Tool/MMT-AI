import datetime
import json
import uuid

import jwt
import pytest
from fastapi.testclient import TestClient

from app import create_app
from chatbot.context import ContextBuilder
from chatbot.course_content import CourseContent
from chatbot.prompt_loader import PromptLoader
from chatbot.service import ChatService
from rate_limit import RateLimiter


class FakeLLM:
    model = "fake-model"

    def __init__(self, chunks=("Hello", " there"), error=None):
        self.chunks = chunks
        self.error = error
        self.calls = []

    def stream(self, messages, result):
        self.calls.append(messages)
        for chunk in self.chunks:
            result.text += chunk
            yield chunk
        if self.error:
            raise self.error
        result.first_token_ms, result.total_ms = 10, 20

    def ping(self):
        pass


class MemoryStore:
    """In-memory stand-in for ConversationStore."""
    def __init__(self):
        self.conversations = {}
        self.messages = []
        self.feedback = {}

    def get_or_create_conversation(self, conversation_id, user_id, project_id):
        if self.conversations.get(conversation_id) == (user_id, project_id):
            return conversation_id
        new_id = str(uuid.uuid4())
        self.conversations[new_id] = (user_id, project_id)
        return new_id

    def get_history(self, conversation_id, max_messages):
        rows = [m for m in self.messages if m["conversation_id"] == conversation_id and not m["stats"].error]
        return [{"role": m["role"], "content": m["content"]} for m in rows][-max_messages:]

    def add_message(self, conversation_id, role, content, stats=None):
        from database.conversations import AnswerStats
        message_id = str(uuid.uuid4())
        self.messages.append({"id": message_id, "conversation_id": conversation_id, "role": role,
                              "content": content, "stats": stats or AnswerStats()})
        return message_id

    def save_feedback(self, message_id, user_id, rating, comment):
        for m in self.messages:
            if m["id"] == message_id and m["role"] == "assistant" and self.conversations[m["conversation_id"]][0] == user_id:
                self.feedback[message_id] = rating
                return True
        return False


def token(user_id="22", project_ids=(1,), minutes=5):
    payload = {"sub": user_id, "project_ids": list(project_ids),
               "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=minutes)}
    return jwt.encode(payload, "test-secret-key-that-is-at-least-32-bytes", algorithm="HS256")


def parse_events(body):
    events = []
    for block in body.strip().split("\n\n"):
        lines = block.split("\n")
        events.append((lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))))
    return events


@pytest.fixture
def setup():
    app = create_app(run_startup_tasks=False)
    llm = FakeLLM()
    store = MemoryStore()
    context = ContextBuilder(
        prompt_loader=PromptLoader(),
        course_content=CourseContent(urls=("https://example.invalid/",), fetch_fn=lambda url: "# Schedule\n\n- Test plan 30.10.2099."),
        get_project_snapshot=lambda project_id: f"Snapshot of project {project_id}",
    )
    app.state.llm = llm
    app.state.chat_service = ChatService(context=context, llm=llm, store=store)
    return TestClient(app), app, llm, store


def test_chat_streams_events_and_stores_both_messages(setup):
    client, _, llm, store = setup
    response = client.post("/chat", json={"prompt": "When is the test plan due?", "project_id": 1},
                           headers={"Authorization": token()})
    assert response.status_code == 200
    events = parse_events(response.text)
    assert [name for name, _ in events] == ["start", "status", "token", "token", "done"]
    assert "".join(data["text"] for name, data in events if name == "token") == "Hello there"
    assert [m["role"] for m in store.messages] == ["user", "assistant"]
    assert store.messages[1]["content"] == "Hello there"
    assert store.messages[1]["stats"].model == "fake-model"
    assert events[-1][1]["message_id"] == store.messages[1]["id"]

    system_prompt = llm.calls[0][0]["content"]
    assert "Snapshot of project 1" in system_prompt
    assert "Test plan" in system_prompt and "{course_material}" not in system_prompt


def test_conversation_history_is_sent_on_follow_up(setup):
    client, _, llm, _ = setup
    headers = {"Authorization": token()}
    first = parse_events(client.post("/chat", json={"prompt": "First question", "project_id": 1}, headers=headers).text)
    conversation_id = first[0][1]["conversation_id"]
    client.post("/chat", json={"prompt": "Second question", "project_id": 1, "conversation_id": conversation_id}, headers=headers)
    assert [m["content"] for m in llm.calls[1][1:]] == ["First question", "Hello there", "Second question"]


def test_conversation_of_another_user_is_not_reused(setup):
    client, _, llm, _ = setup
    first = parse_events(client.post("/chat", json={"prompt": "Secret", "project_id": 1}, headers={"Authorization": token("22")}).text)
    conversation_id = first[0][1]["conversation_id"]
    other = parse_events(client.post("/chat", json={"prompt": "Hi", "project_id": 1, "conversation_id": conversation_id},
                                     headers={"Authorization": token("31")}).text)
    assert other[0][1]["conversation_id"] != conversation_id
    assert len(llm.calls[1]) == 2


def test_llm_failure_sends_error_event_and_is_logged(setup):
    client, app, _, store = setup
    app.state.chat_service.llm.error = RuntimeError("model down")
    events = parse_events(client.post("/chat", json={"prompt": "Hi", "project_id": 1}, headers={"Authorization": token()}).text)
    assert events[-1][0] == "error"
    assert "RuntimeError: model down" in store.messages[-1]["stats"].error


def test_project_access_is_enforced(setup):
    client, *_ = setup
    response = client.post("/chat", json={"prompt": "Hi", "project_id": 2}, headers={"Authorization": token(project_ids=(1,))})
    assert response.status_code == 403


@pytest.mark.parametrize("headers, detail", [
    ({}, "Missing token"),
    ({"Authorization": "garbage"}, None),
    ({"Authorization": token(minutes=-1)}, "Session expired"),
])
def test_chat_requires_valid_token(setup, headers, detail):
    client, *_ = setup
    response = client.post("/chat", json={"prompt": "Hi", "project_id": 1}, headers=headers)
    assert response.status_code == 401
    if detail:
        assert response.json()["detail"] == detail


def test_prompt_validation(setup):
    client, *_ = setup
    headers = {"Authorization": token()}
    assert client.post("/chat", json={"prompt": "   ", "project_id": 1}, headers=headers).status_code == 400
    assert client.post("/chat", json={"prompt": "x" * 2001, "project_id": 1}, headers=headers).status_code == 413


def test_rate_limit(setup):
    client, app, *_ = setup
    app.state.rate_limiter = RateLimiter(max_requests=2, window_seconds=60)
    headers = {"Authorization": token()}
    codes = [client.post("/chat", json={"prompt": "Hi", "project_id": 1}, headers=headers).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_feedback_only_for_own_answers(setup):
    client, _, _, store = setup
    events = parse_events(client.post("/chat", json={"prompt": "Hi", "project_id": 1}, headers={"Authorization": token("22")}).text)
    message_id = events[-1][1]["message_id"]
    assert client.post("/feedback", json={"message_id": message_id, "rating": -1}, headers={"Authorization": token("31")}).status_code == 404
    assert client.post("/feedback", json={"message_id": message_id, "rating": 2}, headers={"Authorization": token("22")}).status_code == 422
    assert client.post("/feedback", json={"message_id": message_id, "rating": -1}, headers={"Authorization": token("22")}).status_code == 204
    assert store.feedback[message_id] == -1


def test_start_session_disabled_outside_dev_mode(setup):
    client, *_ = setup
    assert client.get("/start_session").status_code == 404


def test_health_reports_database_failure(setup, monkeypatch):
    client, *_ = setup
    from database import db

    def fail(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(db, "fetch_all", fail)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["checks"]["database"] == {"ok": False, "error": "db down"}
