from app import create_app
import os
import uvicorn

from rag.document_manager import add_documents_from_urls

app = create_app()

if __name__ == "__main__":
    if os.getenv("LOAD_STARTUP_DOCUMENTS", "true").lower() in ("1", "true", "yes", "on"):
        add_documents_from_urls() # Fetch initial data into ChromaDB on startup.
    uvicorn.run(
            "main:app",
            host=os.getenv("APP_HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            reload=os.getenv("RELOAD", "false").lower() in ("1", "true", "yes", "on"),
    )

