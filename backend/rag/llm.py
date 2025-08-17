from cachetools import TTLCache
from collections.abc import Iterator
from dotenv import load_dotenv
from functools import partial
from langchain.prompts import ChatPromptTemplate, PromptTemplate, MessagesPlaceholder
from langchain_ollama import ChatOllama
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, trim_messages
from langchain_core.runnables import RunnablePassthrough
from langchain_core.runnables.history import RunnableWithMessageHistory
from operator import itemgetter

from database.sql_executor import get_project_data
from rag.document_grader import filter_irrelevant_documents
from rag.document_manager import retrieve_documents
from rag.prompt_loader import PromptLoader
from rag.query_rewriter import rewrite_question
from rag.query_router import route_question

import os


load_dotenv()
MODEL_NAME = os.environ["MODEL_NAME"]
MAX_SESSIONS = os.environ["MAX_SESSIONS"]
SESSION_TTL_SECONDS = os.environ["SESSION_TTL_SECONDS"]
SESSION_MAX_MESSAGES = os.environ["SESSION_MAX_MESSAGES"]

llm = ChatOllama(
    model=MODEL_NAME,
    streaming=True,
)

prompt_loader = PromptLoader("./prompts")

system_prompt = prompt_loader.get_prompt("system")
database_prompt = prompt_loader.get_prompt("database")
rag_prompt = prompt_loader.get_prompt("rag")

# Trimming the message history, so that context length is not exceeded.
trimmer = trim_messages(
    strategy="last",
    token_counter=llm,
    include_system=True,
    allow_partial=False,
    start_on="human",
    max_tokens=10240, # TODO 1024*10 tokens for now. Should implement a vector database for long-term memory.
)

messages = [SystemMessage(system_prompt)]
store = TTLCache(maxsize=MAX_SESSIONS, ttl=SESSION_TTL_SECONDS)

prompt_template = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="messages"),
    ("human", "{question}"),
])

rag_prompt_template = PromptTemplate(
    template=rag_prompt,
    input_variables=["documents", "question"],
)

chain = RunnablePassthrough.assign(messages=itemgetter("messages") | trimmer) | prompt_template | llm

# This TTLCacle is used to save the RunnableWithMessageHistory-objects for each session.
# These contain the whole LLM invokation pipeline, which can be called directly.
# Such an approach is required because the second argument, get_session_history requires two arguments, which is not supported by the Runnable.
llm_runnables = TTLCache(maxsize=MAX_SESSIONS, ttl=SESSION_TTL_SECONDS)


def get_system_prompt_with_data(data: str) -> str:
    """Appends the system and database prompts.

    Args:
        data (str): The data to inject into the database prompt.

    Returns:
        str: The combined prompt including data.
    """
    return system_prompt + "\n\n" + database_prompt.format(data=data)


def create_session_history(session_id: str, project_id: int=None) -> BaseChatMessageHistory:
    """Creates session history for the given session ID.

    Stores the created history in the 'store' TTLCache. Key as session_id and value as the message history.
    The project ID is used for creating the system prompt using project data.

    Args:
        session_id (str): ID of the session to create history for.
        project_id (str): ID of the project to fetch database data for.
    """
    store[session_id] = InMemoryChatMessageHistory()
    if not project_id: # Create system prompt without project data.
        print(f"DEBUG: Creating message history for {session_id} without project data.")
        store[session_id].add_message(SystemMessage(system_prompt))
        return store[session_id]
    print(f"DEBUG: Creating message history for {session_id}.")
    data = get_project_data(project_id)
    combined_system_message = get_system_prompt_with_data(data)
    store[session_id].add_message(SystemMessage(combined_system_message))


def get_session_history(session_id: str, project_id: int=None) -> BaseChatMessageHistory:
    """Get session history for the given session ID.

    Fetches the sessions message history. Delegates history creation to create_session_history() it if it does not exist yet.
    Project ID is specifically needed for the creation of new session history.

    Args:
        session_id (str): ID of the session to get history for.
        project_id (int): ID of the project to fetch data for if creating a new history.

    Returns:
        BaseChatMessageHistory: The retrieved message history of the session.
    """
    if session_id not in store:
        create_session_history(session_id, project_id)
    history = store[session_id]
    if len(history.messages) > SESSION_MAX_MESSAGES:
        history.messages = history.messages[-MAX_MESSAGES:]
    return history


def get_llm_runnable(session_id: str, project_id: int) -> RunnableWithMessageHistory:
    """Gets the LLM runnable object for the current session.

    Args:
        session_id (str): The session ID of the user session whose Runnable to return.
        project_id (int): The project ID associated with the current session. Needed when creating a new Runnable.

    Returns:
        RunnableWithMessageHistory: The Runnable for the current user session.
    """
    if session_id not in llm_runnables:
        # See the RunnableWithMessageHistory documentation. It has nice examples on how this works.
        chain_with_session_history = RunnableWithMessageHistory(
            chain,
            partial(get_session_history, project_id=project_id),
            input_messages_key="question",
            history_messages_key="messages",
        )
        llm_runnables[session_id] = chain_with_session_history
    return llm_runnables[session_id]


def generate_response(question: str, session_id: str, project_id: int) -> Iterator[str]:
    """Generates a chatbot response as a stream.

    Args:
        question (str): The user query.
        session_id (str): The ID of the user's session.
        project_id (int): The ID associated with the user's project.

    Yields:
        Iterator[str]: The generated response as a stream.
    """
    llm_runnable = get_llm_runnable(session_id, project_id)
    route = route_question(question)
    if route == "vector_database":
        retrieved_documents = retrieve_documents(question)
        # Here we determine whether the fetched documents are relevant. Irrelevant documents are removed from the list.
        relevant_documents = filter_irrelevant_documents(question, retrieved_documents)
        # If the list of relevant documents is empty, iterate on the vectorstore search.
        # The search is attempted only twice, after which the system resorts to a general knowledge answer.
        if not relevant_documents:
            question = rewrite_question(question)
            relevant_documents = retrieve_documents(question)
        documents_as_string = "\n".join(relevant_documents)
        prompt = rag_prompt_template.invoke({"documents": documents_as_string, "question": question}).to_string()
    else: # Using general knowledge or project data.
        prompt = question

    config = {"configurable": {
        "session_id": session_id,
        "project_id": project_id,
    }}
    for chunk in llm_runnable.stream(
        {
            "messages": messages,
            "question": prompt,
        },
        config=config,
    ):
        yield chunk.content

