from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rag.document_grader import build_grader_agent
from rag.llm import build_services
from rag.prompt_loader import PromptLoader
from api.routes import router as api_router

import os

from rag.query_rewriter import build_rewriter_agent
from rag.query_router import build_router_agent

load_dotenv()

def create_app() -> FastAPI:
    app = FastAPI()

    # MMT_HOST = Host of the front-end module:
    MMT_HOST = os.getenv("HOST", "localhost")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prompt_loader = PromptLoader(
            prompt_dir=os.getenv("PROMPT_DIR", "./prompts"),
            cache_ttl_seconds=int(os.getenv("PROMPT_TTL", "30")),
    )

    app.state.prompt_loader = prompt_loader
    llm_services = build_services(
            prompt_loader=prompt_loader,
            secret_key=os.environ["JWT_SECRET_KEY"],
            algorithm=os.environ["JWT_ALGORITHM"],
    )
    app.state.services = llm_services
    app.state.router_agent = build_router_agent(
        prompt_loader=prompt_loader,
        model_name=os.environ.get("ROUTER_MODEL_NAME"),
    )
    app.state.grader_agent = build_grader_agent(
        prompt_loader=prompt_loader,
        model_name=os.environ.get("GRADER_MODEL_NAME"),
    )
    app.state.rewriter_agent = build_rewriter_agent(
        prompt_loader=prompt_loader,
        model_name=os.environ.get("REWRITER_MODEL_NAME"),
    )
    app.include_router(api_router)

    return app

