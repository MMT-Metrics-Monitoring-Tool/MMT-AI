from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
# from optimum.onnxruntime import ORTModelForSequenceClassification
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import torch
import os

load_dotenv()
# .env needs to have the parameter HF_ACCESS_TOKEN as the HuggingFace access token which is permitted to use the model specified below.
HF_ACCESS_TOKEN = os.getenv("HF_ACCESS_TOKEN")

model_id = "meta-llama/Meta-Llama-3.1-8B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(model_id, token=HF_ACCESS_TOKEN)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype="auto",
    # export=True,
    # provider="ROCMExecutionProvider", # Utilise AMD GPU.
    token=HF_ACCESS_TOKEN)

urls = (
    "https://coursepages2.tuni.fi/comp-se-610/",
)

generator = pipeline(
    "text-generation",
    tokenizer=tokenizer,
    model=model_id,
    model_kwargs={"torch_dtype": torch.bfloat16},
    device_map="auto",
)

snippets = [
    "Sample",
]

sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
encoded_snippets = sentence_model.encode(snippets)


def retrieve_snippet(query):
    encoded_query = model.encode([query])
    similarity = model.similarity(encoded_snippets, encoded_query) # Evaluate similarity
    retrieved_text = snippets[similarity.argmax().item()] # Get the text with highest similarity
    return retrieved_text


def perform_query(query):
    # retrieved_text = retrieve_snippet(query)

    messages = (
        {"role": "system", "content": "You are a pirate software project manager who always responds in pirate speak!"},
        {"role": "user", "content": query},
    )

    response = generator(messages, max_new_tokens=256)[-1]["generated_text"][-1]["content"]
    return response


def main():
    response = perform_query("Who are you?")
    print(response)


if __name__ == "__main__":
    main()
