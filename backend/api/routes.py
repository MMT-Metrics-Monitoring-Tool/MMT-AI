from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Literal

from auth import AuthError, Principal
from database import db

import json


router = APIRouter()


class ChatRequest(BaseModel):
    prompt: str
    project_id: int
    conversation_id: str | None = None


class FeedbackRequest(BaseModel):
    message_id: str
    rating: Literal[1, -1]
    comment: str | None = Field(default=None, max_length=2000)


def authenticate(request: Request) -> Principal:
    """Verifies the MMT-issued token in the Authorization header.

    Raises:
        HTTPException: 401 if the token is missing, invalid or expired.
    """
    try:
        return request.app.state.authenticator.verify(request.headers.get("Authorization"))
    except AuthError as exc:
        raise HTTPException(status_code=401, detail="Session expired" if exc.expired else str(exc))


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _check(fn) -> dict:
    try:
        fn()
        return {"ok": True, "error": None}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/health")
def health_check(request: Request):
    """Reports service health for backend, database, and llm checks.

    Returns:
        dict: The health status payload for all checks.
    """
    checks = {
        "backend": {"ok": True},
        "database": _check(lambda: db.fetch_all("SELECT 1")),
        "llm": _check(request.app.state.llm.ping),
    }
    healthy = all(check["ok"] for check in checks.values())
    payload = {"status": "ok" if healthy else "degraded", "checks": checks}
    return payload if healthy else JSONResponse(status_code=503, content=payload)


@router.get("/start_session")
def start_session(request: Request):
    """Issues a development token, for running the chatbot without MMT. Disabled unless AUTH_DEV_MODE is enabled.

    Returns:
        dict: A dictionary containing the token.
    """
    authenticator = request.app.state.authenticator
    if not authenticator.dev_mode:
        raise HTTPException(status_code=404, detail="Not found")
    return {"token": authenticator.issue_dev_token()}


@router.post("/chat")
def chatbot_endpoint(chat_request: ChatRequest, request: Request):
    """The endpoint used for generating chatbot responses to user questions.

    Returns:
        StreamingResponse: Server-sent events: start, status, token (repeated), then done or error.
    """
    principal = authenticate(request)
    state = request.app.state

    if not principal.can_access(chat_request.project_id):
        raise HTTPException(status_code=403, detail="No access to this project")

    prompt = chat_request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt not found or empty")
    if len(prompt) > state.max_prompt_chars:
        raise HTTPException(status_code=413, detail=f"Prompt is longer than {state.max_prompt_chars} characters")

    if not state.rate_limiter.allow(principal.user_id):
        retry_after = state.rate_limiter.retry_after(principal.user_id)
        raise HTTPException(
            status_code=429, detail="Too many questions, please wait a moment", headers={"Retry-After": str(retry_after)},
        )

    events = state.chat_service.answer(principal, chat_request.project_id, prompt, chat_request.conversation_id)
    return StreamingResponse(
        (_sse(event, data) for event, data in events),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/feedback", status_code=204)
def feedback_endpoint(feedback: FeedbackRequest, request: Request):
    """Stores a thumbs up (1) or down (-1) for an answer. Users can only rate answers in their own conversations."""
    principal = authenticate(request)
    if not request.app.state.chat_service.store.save_feedback(
            feedback.message_id, principal.user_id, feedback.rating, feedback.comment,
    ):
        raise HTTPException(status_code=404, detail="Message not found")
    return Response(status_code=204)


@router.get("/history")
def history_endpoint(project_id: int, request: Request, conversation_id: str | None = None):
    """Returns the messages of a conversation so the widget can restore it after a page refresh.

    Without conversation_id the user's latest conversation in the project is used.

    Returns:
        dict: conversationId (None if there is nothing to restore) and the messages, oldest first.
    """
    principal = authenticate(request)
    if not principal.can_access(project_id):
        raise HTTPException(status_code=403, detail="No access to this project")

    store = request.app.state.chat_service.store
    conversation_id = conversation_id or store.get_latest_conversation_id(principal.user_id, project_id)
    if not conversation_id:
        return {"conversationId": None, "messages": []}

    messages = store.get_message_for_display(conversation_id, principal.user_id, project_id)
    if not messages:
        return {"conversationId": None, "messages": []}
    return {"conversationId": conversation_id, "messages": messages}