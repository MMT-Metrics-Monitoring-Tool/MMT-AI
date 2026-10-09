from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from auth import build_authenticator
from chatbot.context import ContextBuilder
from chatbot.course_content import CourseContent
from chatbot.llm import build_llm_client
from chatbot.prompt_loader import PromptLoader
from chatbot.service import ChatService
from database.conversations import ConversationStore, apply_migrations
from database.sql_executor import get_project_snapshot
from rate_limit import RateLimiter

import os
import threading

load_dotenv()


def _env_flag(name: str, default: str) -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes", "on")


def _startup_tasks(course_content: CourseContent) -> None:
    if _env_flag("DB_AUTO_MIGRATE", "true"):
        try:
            apply_migrations()
        except Exception as exc:
            print(f"Database: migrations failed, chatbot tables may be missing: {exc}")
    # Fetched in the background, so the first question does not wait for the course pages.
    threading.Thread(target=course_content.pages, daemon=True).start()


def create_app(*, run_startup_tasks: bool = True) -> FastAPI:
    prompt_loader = PromptLoader(
            prompt_dir=os.getenv("PROMPT_DIR", "./prompts"),
            cache_ttl_seconds=int(os.getenv("PROMPT_TTL", "30")),
    )
    course_content = CourseContent()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if run_startup_tasks:
            _startup_tasks(course_content)
        yield

    app = FastAPI(lifespan=lifespan)

    # Authentication uses the Authorization header, not cookies, so credentials are not needed for CORS.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",")],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["Retry-After"],
    )

    app.state.authenticator = build_authenticator()
    app.state.llm = build_llm_client()
    app.state.chat_service = ChatService(
        context=ContextBuilder(
            prompt_loader=prompt_loader,
            course_content=course_content,
            get_project_snapshot=get_project_snapshot,
        ),
        llm=app.state.llm,
        store=ConversationStore(),
        history_messages=int(os.getenv("HISTORY_MESSAGES", 10)),
    )
    app.state.rate_limiter = RateLimiter(
        max_requests=int(os.getenv("RATE_LIMIT_REQUESTS", 20)),
        window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", 600)),
    )
    app.state.max_prompt_chars = int(os.getenv("MAX_PROMPT_CHARS", 2000))
    app.include_router(api_router)

    return app
