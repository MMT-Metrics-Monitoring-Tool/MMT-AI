from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import jwt


router = APIRouter()

def get_services():
    from main import app
    return app.state.services


class ChatRequest(BaseModel):
    prompt: str
    project_id: int


@router.get("/start_session")
def start_session(request: Request):
    """Starts a new front-end session. Handles token generation or renewal.

    Returns:
        dict: A dictionary containing the new token associated with the session.
    """
    existing_token = request.headers.get("Authorization")
    sm = get_services().session_manager

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

    services = get_services()
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
        from main import app
        for chunk in generate_response(
                prompt, session_id, project_id,
                services=services,
                router_agent=app.state.router_agent,
                grader_agent=app.state.grader_agent,
                rewriter_agent=app.state.rewriter_agent,
        ):
            yield chunk

    return StreamingResponse(stream_response(), media_type="text/event-stream")

