from dataclasses import dataclass
import os
from typing import Any, Literal
from langchain.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import JsonOutputParser


Datasource = Literal["vector_database", "project_database", "general_knowledge"]


# TODO Include a dynamic description of vector store contents in the routing prompt.
# TODO Possibly simplify data source options: vector_store | other

@dataclass(frozen=True)
class RouterAgent:
    chain: Any

    def route_question(self, question: str) -> Datasource:
        """
        Routes the question to a data source.
        """
        result = self.chain.invoke({"question": question})
        ds = result.get("datasource")

        # Runtime hardening.
        if ds not in ("vector_database", "project_database", "general_knowledge"):
            return "general_knowledge"
        return ds


def build_router_agent(*, prompt_loader, model_name: str | None = None) -> RouterAgent:
    """
    Factory: builds the routes agent with injected deps.
    """
    model = model_name or os.environ["MODEL_NAME"]
    llm = ChatOllama(model=model, format="json", temperature=0)

    system_prompt = prompt_loader.get_prompt("router_prompt")

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{question}"),
    ])

    chain = prompt_template | llm | JsonOutputParser()
    return RouterAgent(chain=chain)

