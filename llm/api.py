from flask import Flask, request, jsonify
from llm import generate_response
from rag_manager import retrieve_relevant_documents


app = Flask(__name__)


@app.route('/chat', methods = ['POST'])
def get_chatbot_response():
    data = request.json
    prompt = data.get("prompt", "")
    relevant_documents = retrieve_relevant_documents(prompt)
    print(relevant_documents)
    full_prompt = "\n".join(relevant_documents) + "\n" + prompt
    response = generate_response(full_prompt)
    return jsonify({"response": response})

