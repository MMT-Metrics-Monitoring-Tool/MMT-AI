from dataclasses import dataclass
from typing import Any, cast
from collections.abc import Iterator
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_ollama import ChatOllama
from langchain_core.messages import trim_messages
from langchain_core.runnables import RunnableConfig, RunnablePassthrough
from operator import itemgetter

from database.sql_executor import get_project_data
from rag.document_grader import GraderAgent
from rag.document_manager import retrieve_documents
from rag.query_rewriter import RewriterAgent
from rag.query_router import RouterAgent
from session_manager import SessionManager

import os


load_dotenv()


@dataclass(frozen=True)
class LLMServices:
    session_manager: SessionManager
    rag_prompt_template: Any


def build_services(*,
        get_project_data_fn=get_project_data,
        secret_key,
        algorithm,
        prompt_loader
) -> LLMServices:
    """
    Factory: builds the session manager. Requires the chain of the main question-answering agent, which is why this is done here.
    """
    MODEL_NAME = os.environ["MODEL_NAME"]
    llm = ChatOllama(
        model=MODEL_NAME,
    )

    # Trimming the message history, so that context length is not exceeded.
    trimmer = trim_messages(
        strategy="last",
        token_counter=llm,
        include_system=True,
        allow_partial=False,
        start_on="human",
        max_tokens=10240, # TODO 1024*10 tokens for now. Should implement a vector database for long-term memory.
    )

    system_prompt = prompt_loader.get_prompt("system")
    database_prompt = prompt_loader.get_prompt("database")
    rag_prompt = prompt_loader.get_prompt("rag")

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        ("human", "{question}"),
    ])

    chain = (
        RunnablePassthrough.assign(messages=itemgetter("messages") | trimmer)
        | prompt_template
        | llm
    )

    session_manager = SessionManager(
        chain=chain,
        system_prompt=system_prompt,
        database_prompt=database_prompt,
        get_project_data=get_project_data_fn,
        secret_key=secret_key,
        algorithm=algorithm,
    )

    rag_prompt_template = PromptTemplate(
        template=rag_prompt,
        input_variables=["documents", "question"],
    )

    return LLMServices(
        session_manager=session_manager,
        rag_prompt_template=rag_prompt_template,
    )


def generate_response(
        question: str,
        session_id: str,
        project_id: int,
        *,
        services: LLMServices,
        router_agent: RouterAgent,
        grader_agent: GraderAgent,
        rewriter_agent: RewriterAgent,
) -> Iterator[str]:
    """Generates a chatbot response as a stream.

    Yields:
        Iterator[str]: The generated response as a stream.
    """
    sm: SessionManager = services.session_manager
    llm_runnable = sm.get_runnable(session_id=session_id, project_id=project_id)
    route = router_agent.route_question(question)
    if route == "vector_database":
        retrieved_documents = retrieve_documents(question)
        # Here we determine whether the fetched documents are relevant. Irrelevant documents are removed from the list.
        relevant_documents = grader_agent.filter_irrelevant_documents(question, retrieved_documents)
        # If the list of relevant documents is empty, iterate on the vectorstore search.
        # The search is attempted only twice, after which the system resorts to a general knowledge answer.
        if not relevant_documents:
            question = rewriter_agent.rewrite_question(question)
            relevant_documents = retrieve_documents(question)
        documents_as_string = "\n".join(relevant_documents)
        prompt = services.rag_prompt_template.invoke({"documents": documents_as_string, "question": question}).to_string()
    else: # General knowledge and project data have the same path for now.
        prompt = question

    config = cast(RunnableConfig, {
        "configurable": {
            "session_id": session_id,
            "project_id": project_id,
        }
    })
    messages = sm.get_history(session_id)
    for chunk in llm_runnable.stream(
        {
            "messages": messages,
            "question": prompt,
        },
        config=config,
    ):
        yield chunk.content

