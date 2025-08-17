from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain_ollama import ChatOllama

from rag.llm import prompt_loader

import os


load_dotenv()
model_name = os.environ["MODEL_NAME"]

llm = ChatOllama(model=model_name, temperature=0)

system_prompt = prompt_loader.get_prompt("rewriter_prompt")

prompt_template = PromptTemplate(
    template=system_prompt,
    input_variables=["question", "generation"],
)

chain = prompt_template | llm


def rewrite_question(question: str) -> str:
    """Prompts the LLM to rewrite the user question, optimised for vectorstore retrieval.

    Args:
        question (str): The user question to rewrite.

    Returns:
        str: The retrieval optimised question.
    """
    response = chain.invoke({"question": question})
    return response.content

