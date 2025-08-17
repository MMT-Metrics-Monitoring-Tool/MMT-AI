from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import JsonOutputParser

from rag.llm import prompt_loader

import os


load_dotenv()
model_name = os.environ["MODEL_NAME"]

llm = ChatOllama(model=model_name, format="json", temperature=0)

system_prompt = prompt_loader.get_prompt("router_prompt")

prompt_template = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{question}"),
])

chain = prompt_template | llm | JsonOutputParser()


def route_question(question: str) -> str:
    """Routes the question to a datasource which is required to answer the question.

    Args:
        question (str): The user question.

    Returns:
        str: A JSON string containing a key 'datasource' with the value of 'vector_database', 'project_database', or 'general_knowledge'.
    """
    result = chain.invoke({"question": question})
    return result.get("datasource")
