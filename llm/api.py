from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from llm import generate_response
import datetime
import jwt
import os
import uuid


load_dotenv()
ALGORITHM = os.environ["JWT_ALGORITHM"]
SECRET_KEY = os.environ["JWT_SECRET_KEY"]

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])

# TODO A way to remove inactive sessions.
sessions = {}


def generate_jwt_token(existing_session_id=None):
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
    response = generate_response(prompt)
    return jsonify({"response": response})

