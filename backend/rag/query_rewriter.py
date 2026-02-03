from dataclasses import dataclass
from typing import Any
from langchain.prompts import PromptTemplate
from langchain_ollama import ChatOllama

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
    llm = ChatOllama(model=model, temperature=0)

    system_prompt = prompt_loader.get_prompt("rewriter_prompt")

    prompt_template = PromptTemplate(
            template=system_prompt,
            input_variables=["question", "generation"],
    )

    chain = prompt_template | llm
    return RewriterAgent(chain=chain)

