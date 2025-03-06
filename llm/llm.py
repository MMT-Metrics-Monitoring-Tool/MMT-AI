from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_ollama import ChatOllama
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, trim_messages
from langchain_core.runnables import RunnablePassthrough
from langchain_core.runnables.history import RunnableWithMessageHistory
from rag_manager import retrieve_relevant_documents
from operator import itemgetter
import os


load_dotenv()
model_name = os.environ["MODEL_NAME"]

llm = ChatOllama(model=model_name)

system_prompt = """You are a helpful chatbot in a software project monitoring tool.\n
    You answer project members' questions on the topics of project management and software development.\n
    Do not answer completely irrelevant questions such as those for cooking recipes.\n
    Answer concisely and offer to provide more insightful answers on subsequent questions on the topic.\n
    If the initial question is broad, answer using a summary or a list, shortly elaborating on each point."""

# Trimming the message history, so that context length is not exceeded.
trimmer = trim_messages(
    strategy="last",
    token_counter=llm,
    include_system=True,
    allow_partial=False,
    start_on="human",
    max_tokens=1024, # TODO 1024 tokens for now.
)

messages = [SystemMessage(system_prompt)]
store = {}

prompt_template = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="messages"),
    ("human", "{question}")
])

chain = RunnablePassthrough.assign(messages=itemgetter("messages") | trimmer) | prompt_template | llm

# Store message history. Currently supports only in-memory saving.
def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

# See the RunnableWithMessageHistory documentation. It has nice examples on how this works.
with_session_history = RunnableWithMessageHistory(chain, get_session_history, input_messages_key="question", history_messages_key="messages")

def generate_response(prompt: str, session_id: str) -> str:
    # relevant_documents = retrieve_relevant_documents(prompt)
    # print(relevant_documents)
    # full_prompt = "\n".join(relevant_documents) + "\n" + "If the text above is not relevant to the question below, disregard it and only answer the question below. Otherwise, answer the question below based on the text provided above. Do not acknowledge this line of text." + "\n" + prompt
    config = {"configurable": {"session_id": session_id}}
    response = with_session_history.invoke(
        {
            "messages": messages,
            "question": prompt,
        },
        config=config,
    )
    return response.content

