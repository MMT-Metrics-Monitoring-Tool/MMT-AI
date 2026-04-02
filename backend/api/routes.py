from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import jwt

from database.database_connector import DatabaseConnector


router = APIRouter()

def get_services(request: Request):
    return request.app.state.services


class ChatRequest(BaseModel):
    prompt: str
    project_id: int


def _check_database_connection() -> tuple[bool, str | None]:
    """Checks whether the database connection is available.

    Returns:
        tuple[bool, str | None]: A tuple containing a success flag and an optional error message.
    """
    db = DatabaseConnector()
    try:
        db.connect()
        connection = db.connection
        if not connection or not connection.is_connected():
            return False, "Database connection not available"

        result = db.query("SELECT 1")
        if result is None:
            return False, "Database query failed"

        return True, None
    except Exception as exc:
        return False, str(exc)
    finally:
        db.close()


def _check_llm_connection(router_agent) -> tuple[bool, str | None]:
    """Checks whether the LLM pipeline is reachable.

    Returns:
        tuple[bool, str | None]: A tuple containing a success flag and an optional error message.
    """
    try:
        router_agent.route_question("Health check ping")
        return True, None
    except Exception as exc:
        return False, str(exc)


@router.get("/health")
def health_check(request: Request):
    """Reports service health for backend, database, and llm checks.

    Returns:
        dict: The health status payload for all checks.
    """
    db_ok, db_error = _check_database_connection()
    llm_ok, llm_error = _check_llm_connection(request.app.state.router_agent)

    backend_ok = True

    checks = {
        "backend": {
            "ok": backend_ok,
        },
        "database": {
            "ok": db_ok,
            "error": db_error,
        },
        "llm": {
            "ok": llm_ok,
            "error": llm_error,
        },
    }

    all_healthy = backend_ok and db_ok and llm_ok
    payload = {
        "status": "ok" if all_healthy else "degraded",
        "checks": checks,
    }

    if all_healthy:
        return payload
    return JSONResponse(status_code=503, content=payload)


@router.get("/start_session")
def start_session(request: Request):
    """Starts a new front-end session. Handles token generation or renewal.

    Returns:
        dict: A dictionary containing the new token associated with the session.
    """
    existing_token = request.headers.get("Authorization")
    sm = get_services(request).session_manager

    if existing_token:
        try:
            decoded = jwt.decode(existing_token, sm.secret_key, algorithms=[sm.algorithm])
            session_id = decoded["session_id"]
            return {"token": sm.generate_jwt_token(session_id)}
        except jwt.ExpiredSignatureError:
            pass

    token = sm.generate_jwt_token()
    return {"token": token}


@router.post("/chat")
def chatbot_endpoint(chat_request: ChatRequest, request: Request):
    """The endpoint used for generating chatbot responses to user questions.

    Returns:
        StreamingResponse: The FastAPI response containing the generated stream.

    Yields:
        str: A partial response to the submitted user question.
    """
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")

    services = get_services(request)
    sm = services.session_manager
    try:
        session_id = sm.validate_jwt_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")

    prompt = chat_request.prompt
    project_id = chat_request.project_id

    if not prompt or prompt.isspace():
        raise HTTPException(status_code=400, detail="Prompt not found or empty")
    if project_id is None:
        raise HTTPException(status_code=400, detail="Project ID not found")

    def stream_response():
        from rag.llm import generate_response
        for chunk in generate_response(
                prompt, session_id, project_id,
                services=services,
                router_agent=request.app.state.router_agent,
                grader_agent=request.app.state.grader_agent,
                rewriter_agent=request.app.state.rewriter_agent,
        ):
            yield chunk

    return StreamingResponse(stream_response(), media_type="text/event-stream")

