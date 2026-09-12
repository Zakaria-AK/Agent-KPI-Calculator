"""LLM factory for the planner/coder/finalizer nodes.

Talks to a GPT model deployed on Azure AI Foundry, via its OpenAI-compatible
"v1" endpoint (AZURE_API_BASE ending in /openai/v1). That surface is plain
OpenAI-shaped -- base_url + api_key + model -- unlike the older Azure OpenAI
resource endpoint, which needs AzureChatOpenAI's deployment-path routing and
an api-version query param. Credentials come from .env (see .env.example):
AZURE_API_KEY, AZURE_API_BASE, MODEL_NAME (the deployment name).
"""

import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


@lru_cache
def get_llm(temperature: float = 0.0) -> ChatOpenAI:
    return ChatOpenAI(
        api_key=os.environ["AZURE_API_KEY"],
        base_url=os.environ["AZURE_API_BASE"],
        model=os.environ["MODEL_NAME"],
        temperature=temperature,
    )
