from dataclasses import dataclass
from langchain_core.prompts import PromptTemplate
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import JsonOutputParser
from typing import Any, List, Literal

import os


@dataclass(frozen=True)
class GraderAgent:
    chain: Any

    def grade_document(self, question: str, document: str) -> Literal["yes", "no"]:
        """Grades the relevancy of a document against a user question.

        Returns:
            str: The grade 'yes' or 'no', specifying whether the document is relevant to the question.
        """
        result = self.chain.invoke({"question": question, "document": document})
        score = result.get("score")
        return "yes" if score == "yes" else "no"

    def filter_irrelevant_documents(self, question: str, documents: list[str]) -> list[str]:
        """Removes any irrelevant documents from a list based on their relevancy to the question.

        Returns:
            List[str]: A list containing only the relevant documents from the argument documents.
        """
        return [doc for doc in documents if self.grade_document(question, doc) == "yes"]


def build_grader_agent(*, prompt_loader, model_name: str | None = None) -> GraderAgent:
    """
    Factory: builds the grader agent with injected deps.
    """
    model = model_name or os.environ["MODEL_NAME"]    
    llm = ChatOllama(model=model, format="json", temperature=0)

    system_prompt = prompt_loader.get_prompt("grader_prompt")

    prompt_template = PromptTemplate(
            template=system_prompt,
            input_variables=["question", "document"],
    )

    chain = prompt_template | llm | JsonOutputParser()
    return GraderAgent(chain=chain)

