from bs4 import BeautifulSoup
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from typing import List
import chromadb
import hashlib
from langchain_text_splitters import RecursiveCharacterTextSplitter
import requests
import os


load_dotenv()
model_name = os.environ["MODEL_NAME"]
embedding_model_name = "all-MiniLM-L6-v2"
chunk_size = int(os.getenv("EMBEDDING_CHUNK_SIZE", 256))
chunk_overlap = int(os.getenv("EMBEDDING_CHUNK_OVERLAP", 64))

chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="documents")

class _SentenceTransformerEmbeddings:
    def __init__(self, model_name: str):
        self._model = SentenceTransformer(model_name)

    def embed_query(self, text: str) -> List[float]:
        return self._model.encode(text).tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._model.encode(texts).tolist()

embedding_model = _SentenceTransformerEmbeddings(model_name=embedding_model_name)

# These are fetched, parsed, and saved into the vectorstore at startup.
urls = (
    "https://coursepages2.tuni.fi/comp-se-610/",
    "https://coursepages2.tuni.fi/comp-se-610/schedule/",
    "https://coursepages2.tuni.fi/comp-se-610/guidelines/",
)


def fetch_text_from_url(url: str) -> str:
    """Fetches HTML documents and extracts text.

    Args:
        url (str): The URL which to retrieve.

    Returns:
        str: The contents of the URL as text without HTML elements.
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    for row in soup.find_all("tr"):
        cells = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
        row.replace_with(soup.new_string("\n" + " | ".join(cells) + "\n"))
    return soup.get_text(separator="\n", strip=True)

def split_to_chunks(text: str, size: int, overlap: int) -> List[str]:
    """Splits long text into chunks of specified size and overlap.

    Args:
        text (str): The text to split into chunks.
        size (int): The size of the resulting chunks in bytes.
        overlap (int): The overlap of the resulting chunks in bytes.

    Returns:
        List[str]: A list of the resulting text chunks.
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=size, chunk_overlap=overlap)
    return splitter.split_text(text)

def doc_exists(doc_id: str) -> bool:
    """Checks whether a document with the given document ID exists in the vectorstore.

    Args:
        doc_id (str): The ID of the document to check.

    Returns:
        bool: True if the document is already saved, False otherwise.
    """
    # TODO limit output to "metadatas."
    existing_data = collection.get(ids=[doc_id])
    return bool(existing_data["ids"])

def add_document(doc_id: str, embedding: List[float], url: str, chunk: str) -> bool:
    """Saves a document into the vectorstore.

    Args:
        doc_id (str): The ID to use for the document in the vectorstore.
        embedding (List[float]): The calculated embedding of the document.
        url (str): The URL from which the document was retrieved.
        chunk (str): The text chunk i.e. the document.

    Returns:
        bool: True if saving was successful, False otherwise.
    """
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
    """Generates an ID for a document.

    Args:
        url (str): The URL from which the document is retrieved.
        chunk_index (int): The index of the chunk resulting from splitting the document.

    Returns:
        str: The document ID.
    """
    url_hash = hashlib.md5(url.encode()).hexdigest() # hashlib.md5 is consistent, unlike Python's hash() which has randomisation.
    return f"{url_hash}_{chunk_index}"

def process_chunks(chunks: List[str], url: str) -> None:
    """Processes text chunks. Saves them to the vectorstore, skipping existing ones.

    Args:
        chunks (List[str]): The list of chunks to save.
        url (str): The URL from which the document was retrieved.
    """
    for i, chunk in enumerate(chunks):
        doc_id = generate_doc_id(chunk, i)
        embedding = embedding_model.embed_query(chunk)
        result = add_document(doc_id, embedding, url, chunk)
        if not result: # Move on to next document if a chunk has already been saved. TODO What about updated documents? Purge all periodically?
            print(f"Vectorstore: Skipped existing document -> {url}")
            return
    print(f"Vectorstore: Document added -> {url}")

def add_documents_from_urls() -> None:
    """Adds documents from programmatically predefined URLs.
    """
    for url in urls:
        text = fetch_text_from_url(url)
        chunks = split_to_chunks(text, chunk_size, chunk_overlap)
        process_chunks(chunks, url)

def retrieve_documents(query: str, top_k: int=10):
    """Retrieves relevant text snippets based on a similarity search performed with a query string.

    Args:
        query (str): The user query to search the vectorstore with.
        top_k (int, optional): The amount of most relevant text snippets to return. Defaults to 10.

    Returns:
        _type_: _description_
    """
    query_embedding = embedding_model.embed_query(query)
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)

    docs = results.get("documents", [])
    return docs[0] if docs else []