from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
import chromadb
import requests
import os


load_dotenv()
model_name = os.environ["MODEL_NAME"]

chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="documents")

embedding_model = OllamaEmbeddings(model=model_name)

urls = (
    "https://coursepages2.tuni.fi/comp-se-610/",
    "https://coursepages2.tuni.fi/comp-se-610/schedule/",
    "https://coursepages2.tuni.fi/comp-se-610/guidelines/",
)


def fetch_text_from_url(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    return " ".join([p.get_text() for p in soup.find_all("p")])

def add_documents_from_urls():
    for url in urls:
        text = fetch_text_from_url(url)
        doc_id = str(hash(url))
        embedding = embedding_model.embed_query(text)

        collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            metadatas=[{"url": url}],
            documents=[text]
        )

def retrieve_relevant_documents(query, top_k=3):
    query_embedding = embedding_model.embed_query(query)
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)
    return results["documents"][0] if "documents" in results else []

