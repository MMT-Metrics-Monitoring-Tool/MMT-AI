from flask import Blueprint, Response, jsonify, request, current_app
import jwt


bp = Blueprint("api", __name__)

def get_session_manager():
    return current_app.extensions["services"].session_manager

def get_generate_args():
    ext = current_app.extensions
    return (
            ext["services"],
            ext["router_agent"],
            ext["grader_agent"],
            ext["rewriter_agent"],
    )


@bp.route("/start_session", methods=["GET"])
def start_session():
    """Starts a new front-end session. Handles token generation or renewal.

    Returns:
        Response: A Flask response containing the new token associated with the session.
    """
    existing_token = request.headers.get("Authorization")
    sm = get_session_manager()

    if existing_token:
        try:
            decoded = jwt.decode(existing_token, sm.secret_key, algorithms=[sm.algorithm])
            session_id = decoded["session_id"]
            return jsonify({"token": sm.generate_jwt_token(session_id)})
        except jwt.ExpiredSignatureError:
            pass

    token = sm.generate_jwt_token()
    return jsonify({"token": token})


@bp.route("/chat", methods=["POST"])
def chatbot_endpoint():
    """The endpoint used for generating chatbot responses to user questions.

    Returns:
        Response: The Flask response containing the generated stream.

    Yields:
        str: A partial response to the submitted user question.
    """
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Missing token"}), 401

    sm = get_session_manager()
    try:
        session_id = sm.validate_jwt_token(token)
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Session expired"}), 401

    data = request.json
    if data is None:
        return jsonify({"error": "JSON data not found in request"}), 400

    prompt = data.get("prompt")
    project_id = data.get("project_id")

    if not prompt or prompt.isspace():
        return jsonify({"error": "Prompt not found or empty"}), 400
    if project_id is None:
        return jsonify({"error": "Project ID not found"}), 400

    def stream_response():
        args = get_generate_args()
        from rag.llm import generate_response
        for chunk in generate_response(
                prompt, session_id, project_id,
                services=args[0],
                router_agent=args[1],
                grader_agent=args[2],
                rewriter_agent=args[3],
        ):
            yield chunk

    return Response(stream_response(), content_type="text/event-stream")

