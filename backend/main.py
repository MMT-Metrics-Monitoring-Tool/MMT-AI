from app import create_app

from rag.document_manager import add_documents_from_urls

app = create_app()

if __name__ == "__main__":
    # TODO Vector store disabled for now.
    # add_documents_from_urls() # Fetch initial data into ChromaDB on startup.
    app.run(
            host="0.0.0.0",
            port=8000,
            debug=True,
            threaded=True,
    )

