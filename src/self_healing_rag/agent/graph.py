"""The main agent — decides when to consult the documents and when to answer directly."""

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from self_healing_rag.config import OPENROUTER_BASE_URL
from self_healing_rag.settings_schema import UserSettings

from .tools import ask_documents


def build_main_agent(settings: UserSettings, api_key: str):
    llm = ChatOpenAI(
        model=settings.models.agent,
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        temperature=0,
    )
    return create_agent(
        model=llm,
        tools=[ask_documents],
        system_prompt=settings.prompts.agent_system,
    )
