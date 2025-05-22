from api import app

from rag.document_manager import add_documents_from_urls


if __name__ == "__main__":
    add_documents_from_urls() # Fetch initial data into ChromaDB on startup.
    app.run(host="0.0.0.0", port=5000, debug=True)

