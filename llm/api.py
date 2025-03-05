from flask import Flask, request, jsonify
from flask_cors import CORS
from llm import generate_response


app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])


@app.route('/chat', methods = ['POST'])
def chatbot_endpoint():
    data = request.json
    prompt = data.get("prompt", "")
    response = generate_response(prompt)
    return jsonify({"response": response})

