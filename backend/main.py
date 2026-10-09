from app import create_app
import os
import uvicorn

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
            "main:app",
            host=os.getenv("APP_HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            reload=os.getenv("RELOAD", "false").lower() in ("1", "true", "yes", "on"),
    )
