from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from rag.document_grader import build_grader_agent
from rag.llm import build_services
from rag.prompt_loader import PromptLoader
from api.routes import bp as api_bp

import os

from rag.query_rewriter import build_rewriter_agent
from rag.query_router import build_router_agent

load_dotenv()

def create_app() -> Flask:
    app = Flask(__name__)

    # MMT_HOST = Host of the front-end module:
    MMT_HOST = os.getenv("HOST", "localhost")
    CORS(app, origins=[f"http://{MMT_HOST}:5173", f"http://{MMT_HOST}"])

    prompt_loader = PromptLoader(
            prompt_dir=os.getenv("PROMPT_DIR", "./prompts"),
            cache_ttl_seconds=int(os.getenv("PROMPT_TTL", "30")),
    )

    app.extensions["prompt_loader"] = prompt_loader
    llm_services = build_services(
            prompt_loader=prompt_loader,
            secret_key=os.environ["JWT_SECRET_KEY"],
            algorithm=os.environ["JWT_ALGORITHM"],
    )
    app.extensions["services"] = llm_services
    app.extensions["router_agent"] = build_router_agent(prompt_loader=prompt_loader)
    app.extensions["grader_agent"] = build_grader_agent(prompt_loader=prompt_loader)
    app.extensions["rewriter_agent"] = build_rewriter_agent(prompt_loader=prompt_loader)
    app.register_blueprint(api_bp)

    return app

