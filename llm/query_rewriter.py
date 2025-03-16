from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain_ollama import ChatOllama
import os


load_dotenv()
model_name = os.environ["MODEL_NAME"]

llm = ChatOllama(model=model_name, temperature=0)

system_prompt = """You are a question re-writer that converts an input question to a better version that is optimized for vectorstore retrieval.\n
    Formulate an improved question based on the initial question below.\n
    Here is the initial question:\n\n{question}.\n\n
    Improved question with no preamble:\n\n"""

prompt_template = PromptTemplate(
    template=system_prompt,
    input_variables=["question", "generation"],
)

chain = prompt_template | llm


def grade_document(question: str) -> str:
    new_question = chain.invoke({"question": question})
    print(new_question)
    return new_question

