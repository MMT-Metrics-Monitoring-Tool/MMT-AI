from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
import chromadb
import requests
import os


load_dotenv()
model_name = os.environ["MODEL_NAME"]

chroma_client = chromadb.PersistentClient(path="./chroma_db")
chroma_client.delete_collection("documents")
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
    # print(soup.get_text(separator="\n", strip=True))
    return soup.get_text(separator="\n", strip=True)

def split_to_chunks(text, chunk_size=512, overlap=64):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=64)
    return splitter.split_text(text)

def add_documents_from_urls():
    for url in urls:
        text = fetch_text_from_url(url)
        chunks = split_to_chunks(text)
        for i, chunk in enumerate(chunks):
            doc_id = f"{hash(url)}_{i}"
            embedding = embedding_model.embed_query(chunk)

            collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[{"url": url}],
                documents=[chunk]
            )

def retrieve_documents(query, top_k=10):
    query_embedding = embedding_model.embed_query(query)
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)
    return results["documents"][0] if "documents" in results else []

