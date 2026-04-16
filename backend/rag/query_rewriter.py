from dataclasses import dataclass
from typing import Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

import os


@dataclass(frozen=True)
class RewriterAgent:
    chain: Any

    def rewrite_question(self, question: str) -> str:
        """
        Rewrites the user question optimized for retrieval.

        Returns:
            str: The rewritten question.
        """
        response = self.chain.invoke({"question": question})
        content = getattr(response, "content", response)

        # Runtime hardening.
        if not isinstance(content, str):
            raise TypeError("Expected string content")
        return content


def build_rewriter_agent(*, prompt_loader, model_name: str | None = None) -> RewriterAgent:
    """
    Factory: builds the rewriter agent with injected deps.
    """
    model = model_name or os.environ["MODEL_NAME"]
    llm = ChatOpenAI(
      model=model,
      base_url=os.environ["API_BASE_URL"],
      api_key=os.environ["API_KEY"],)

    system_prompt = prompt_loader.get_prompt("rewriter_prompt")

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{question}"),
    ])

    chain = prompt_template | llm
    return RewriterAgent(chain=chain)

