from dotenv import load_dotenv
from flask import Flask, Response, request, jsonify, abort
from flask_cors import CORS
from llm import generate_response, get_sessions
import datetime
import jwt
import os
import uuid


load_dotenv()
ALGORITHM = os.environ["JWT_ALGORITHM"]
SECRET_KEY = os.environ["JWT_SECRET_KEY"]
MMT_HOST = os.getenv("HOST", "localhost") # MMT_HOST = Host of the front-end module.

app = Flask(__name__)
CORS(app, origins=[f"http://{MMT_HOST}:5173", f"http://{MMT_HOST}"])

# TODO A way to remove inactive sessions.
sessions = {}


def generate_jwt_token(existing_session_id: str=None) -> str:
    session_id = existing_session_id if existing_session_id else str(uuid.uuid4())
    expiration = datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
    
    sessions[session_id] = datetime.datetime.utcnow()
    token = jwt.encode({"session_id": session_id, "exp": expiration}, SECRET_KEY, algorithm=ALGORITHM)
    return token

@app.route('/start_session', methods = ['GET'])
def start_session():
    existing_token = request.headers.get("Authorization")

    if existing_token:
        try:
            decoded = jwt.decode(existing_token, SECRET_KEY, algorithms=[ALGORITHM])
            session_id = decoded["session_id"]
            return jsonify({"token": generate_jwt_token(session_id)})
        except jwt.ExpiredSignatureError:
            pass

    token = generate_jwt_token()
    return jsonify({"token": generate_jwt_token()})

@app.route('/chat', methods = ['POST'])
def chatbot_endpoint():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Missing token"}), 401
    
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        session_id = decoded["session_id"]
        sessions[session_id] = datetime.datetime.utcnow() # Update last seen timestamp.
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Session expired"}), 401

    prompt = request.json.get("prompt", "")
    project_id = request.json.get("project_id", "")

    if not prompt and prompt.isspace():
        return jsonify({"error": "Prompt not found in request"}), 500
    if not project_id:
        return jsonify({"error": "Project ID not found in request"}), 500

    def stream_response():
        for chunk in generate_response(prompt, session_id, project_id):
            yield chunk

    return Response(stream_response(), content_type="text/event-stream")


# Debug stuff for localhost
def is_local_request():
    return request.remote_addr in ("127.0.0.1", "::1")

@app.route('/debug', methods = ['GET'])
def debug_info():
    if not is_local_request():
        abort(403)
    return jsonify({"session_info": get_sessions()})
