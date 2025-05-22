from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain_ollama import ChatOllama

import os


load_dotenv()
model_name = os.environ["MODEL_NAME"]

llm = ChatOllama(model=model_name, temperature=0)

system_prompt = """You are a question re-writer that converts an input question to a better version that is optimized for vectorstore retrieval.
Formulate an improved question based on the initial question below.
Here is the initial question:\n\n{question}.\n
Improved question with no preamble:\n\n"""

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
    print(response)
    return response.content

