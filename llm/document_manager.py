from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from typing import List
import chromadb
import hashlib
import requests
import os


load_dotenv()
model_name = os.environ["MODEL_NAME"]
embedding_model_name = os.environ["EMBEDDING_MODEL_NAME"]
chunk_size = os.getenv("EMBEDDING_CHUNK_SIZE", 256)
chunk_overlap = os.getenv("EMBEDDING_CHUNK_OVERLAP", 64)

chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="documents")

embedding_model = OllamaEmbeddings(model=embedding_model_name)

urls = (
    "https://coursepages2.tuni.fi/comp-se-610/",
    "https://coursepages2.tuni.fi/comp-se-610/schedule/",
    "https://coursepages2.tuni.fi/comp-se-610/guidelines/",
)


def fetch_text_from_url(url: str) -> str:
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    # print(soup.get_text(separator="\n", strip=True))
    return soup.get_text(separator="\n", strip=True)

def split_to_chunks(text: str, chunk_size: int, overlap: int) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=64)
    return splitter.split_text(text)

def doc_exists(doc_id: str) -> bool:
    existing_data = collection.get(ids=[doc_id], include=["metadatas"]) # include-arg just to minimise unnecessary returned data.
    # print(f"Existing data: {existing_data}")
    return bool(existing_data["ids"])

def add_document(doc_id: str, embedding: List[float], url: str, chunk: str) -> bool:
    if doc_exists(doc_id):
        return False
    collection.add(
        ids=[doc_id],
        embeddings=[embedding],
        metadatas=[{"url": url}],
        documents=[chunk]
    )
    return True

def generate_doc_id(url: str, chunk_index: int) -> str:
    url_hash = hashlib.md5(url.encode()).hexdigest() # hashlib.md5 is consistent, unlike Python's hash() which has randomisation.
    return f"{url_hash}_{chunk_index}"

def process_chunks(chunks: List[str], url: str) -> None:
    for i, chunk in enumerate(chunks):
        doc_id = generate_doc_id(chunk, i)
        embedding = embedding_model.embed_query(chunk)
        result = add_document(doc_id, embedding, url, chunk)
        if not result: # Move on to next document if a chunk has already been saved. TODO What about updated documents? Purge all periodically?
            print(f"Vectorstore: Skipped existing document -> {url}")
            return
    print(f"Vectorstore: Document added -> {url}")

def add_documents_from_urls() -> None:
    for url in urls:
        text = fetch_text_from_url(url)
        chunks = split_to_chunks(text, chunk_size, chunk_overlap)
        process_chunks(chunks, url)

def retrieve_documents(query: str, top_k: int=10):
    query_embedding = embedding_model.embed_query(query)
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)
    return results["documents"][0] if "documents" in results else []

