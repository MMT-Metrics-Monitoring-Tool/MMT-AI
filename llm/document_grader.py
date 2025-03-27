from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import JsonOutputParser
from typing import List
import os


load_dotenv()
model_name = os.environ["MODEL_NAME"]

llm = ChatOllama(model=model_name, format="json", temperature=0)

system_prompt = """You are a grader assessing relevance of a retrieved document to a user question.
Here is the retrieved document:\n\n{document}\n
Here is the user question:\n\n{question}\n
If the document contains keywords relevant to the user question, grade it as relevant.
The test does not have to be stringent. The goal is to filter out erroneous retrievals.
Give a binary score 'yes' or 'no' based on whether the document is relevant to the question.
Provide the binary score as JSON with a single key 'score' and no preamble or explanation."""

prompt_template = PromptTemplate(
    template=system_prompt,
    input_variables=["question", "document"],
)

chain = prompt_template | llm | JsonOutputParser()


def grade_document(question: str, document: str) -> str:
    result = chain.invoke({"question": question, "document": document})
    print(result.get("score"))
    return result.get("score")

def filter_irrelevant_documents(question: str, documents: List[str]) -> List[str]:
    relevant_documents = []
    for doc in documents:
        if grade_document(question, doc) == "yes":
            relevant_documents.append(doc)
    return relevant_documents
