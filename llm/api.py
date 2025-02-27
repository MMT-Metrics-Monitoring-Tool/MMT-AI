from flask import Flask, request, jsonify
from flask_cors import CORS
from llm import generate_response
from rag_manager import retrieve_relevant_documents


app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])


@app.route('/chat', methods = ['POST'])
def get_chatbot_response():
    data = request.json
    prompt = data.get("prompt", "")
    relevant_documents = retrieve_relevant_documents(prompt)
    print(relevant_documents)
    full_prompt = "\n".join(relevant_documents) + "\n" + "If the text above is not relevant to the question below, disregard it and only answer the question below. Otherwise, answer the question below based on the text provided above. Do not acknowledge this line of text." + "\n" + prompt
    response = generate_response(full_prompt)
    return jsonify({"response": response})

