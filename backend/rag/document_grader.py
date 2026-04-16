from dataclasses import dataclass
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from typing import Any, List, Literal
from langchain_openai import ChatOpenAI

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
    llm = ChatOpenAI(
      model=model,
      base_url=os.environ["API_BASE_URL"],
      api_key=os.environ["API_KEY"],
      temperature=0,
      model_kwargs={"response_format": {"type": "json_object"}},
  )


    system_prompt = prompt_loader.get_prompt("grader_prompt")

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Document:\n{document}\n\nQuestion:\n{question}"),
    ])

    chain = prompt_template | llm | JsonOutputParser()
    return GraderAgent(chain=chain)

