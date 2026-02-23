"""
Service LLM - Abstraction multi-providers
Supporte : Ollama (local), Groq, Google Gemini, OpenAI, Mock (tests)
"""
from typing import AsyncGenerator, List
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class LLMService:
      """Abstraction unifiee pour tous les providers LLM."""

    def __init__(self):
              self._llm = None
              self._embeddings = None
              self._provider = settings.LLM_PROVIDER
              logger.info("LLM Service initialise", provider=self._provider)

    @property
    def llm(self):
              if self._llm is None:
                            self._llm = self._create_llm()
                        return self._llm

    @property
    def embeddings(self):
              if self._embeddings is None:
                            self._embeddings = self._create_embeddings()
                        return self._embeddings

    def _create_llm(self):
              """Cree le client LLM selon le provider configure."""
        if self._provider == "ollama":
                      from langchain_ollama import ChatOllama
                      return ChatOllama(
                          base_url=settings.OLLAMA_BASE_URL,
                          model=settings.LLM_MODEL,
                          temperature=settings.LLM_TEMPERATURE,
                          num_predict=settings.LLM_MAX_TOKENS,
                      )

elif self._provider == "groq":
            from langchain_groq import ChatGroq
            return ChatGroq(
                              api_key=settings.GROQ_API_KEY,
                              model=settings.LLM_MODEL,
                              temperature=settings.LLM_TEMPERATURE,
                              max_tokens=settings.LLM_MAX_TOKENS,
            )

elif self._provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                              google_api_key=settings.GOOGLE_API_KEY,
                              model=settings.LLM_MODEL,
                              temperature=settings.LLM_TEMPERATURE,
                              max_output_tokens=settings.LLM_MAX_TOKENS,
            )

elif self._provider == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                              api_key=settings.OPENAI_API_KEY,
                              model=settings.LLM_MODEL,
                              temperature=settings.LLM_TEMPERATURE,
                              max_tokens=settings.LLM_MAX_TOKENS,
            )

elif self._provider == "mock":
            return MockLLM()

else:
            raise ValueError(f"Provider LLM non supporte : {self._provider}")

    def _create_embeddings(self):
              """Cree le client d'embeddings selon le provider configure."""
        if self._provider == "ollama":
                      from langchain_ollama import OllamaEmbeddings
                      return OllamaEmbeddings(
                          base_url=settings.OLLAMA_BASE_URL,
                          model=settings.EMBEDDING_MODEL,
                      )

elif self._provider in ("groq", "gemini"):
            from langchain_ollama import OllamaEmbeddings
            logger.warning("Groq/Gemini n'ont pas d'embeddings - utilisation d'Ollama local")
            return OllamaEmbeddings(
                              base_url=settings.OLLAMA_BASE_URL,
                              model=settings.EMBEDDING_MODEL,
            )

elif self._provider == "openai":
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(
                              api_key=settings.OPENAI_API_KEY,
                              model="text-embedding-3-large",
            )

elif self._provider == "mock":
            return MockEmbeddings()

else:
            from langchain_ollama import OllamaEmbeddings
            return OllamaEmbeddings(
                              base_url=settings.OLLAMA_BASE_URL,
                              model=settings.EMBEDDING_MODEL,
            )

    async def generate(self, messages: list) -> str:
              """Genere une reponse complete (non-streaming)."""
              from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

        lc_messages = []
        for msg in messages:
                      role = msg.get("role", "user")
                      content = msg.get("content", "")
                      if role == "system":
                                        lc_messages.append(SystemMessage(content=content))
elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
else:
                lc_messages.append(HumanMessage(content=content))

        response = await self.llm.ainvoke(lc_messages)
        return response.content

    async def generate_simple(self, prompt: str) -> str:
              """Genere une reponse simple a partir d'un prompt texte."""
              from langchain_core.messages import HumanMessage
              response = await self.llm.ainvoke([HumanMessage(content=prompt)])
              return response.content

    async def stream(self, messages: list) -> AsyncGenerator[str, None]:
              """Streame la reponse token par token."""
              from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

        lc_messages = []
        for msg in messages:
                      role = msg.get("role", "user")
                      content = msg.get("content", "")
                      if role == "system":
                                        lc_messages.append(SystemMessage(content=content))
elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
else:
                lc_messages.append(HumanMessage(content=content))

        async for chunk in self.llm.astream(lc_messages):
                      if chunk.content:
                                        yield chunk.content


class MockLLM:
      """LLM factice pour les tests - retourne des reponses predefinies."""

    async def ainvoke(self, messages):
              from langchain_core.messages import AIMessage
              return AIMessage(content="Reponse de test du chatbot RAG Expert Metier.")

    async def astream(self, messages):
              tokens = ["Reponse", " de", " test", " du", " chatbot", " RAG."]
              for token in tokens:
                            from langchain_core.messages import AIMessageChunk
                            yield AIMessageChunk(content=token)


class MockEmbeddings:
      """Embeddings factices pour les tests."""

    def embed_documents(self, texts):
              return [[0.1] * 768 for _ in texts]

    def embed_query(self, text):
              return [0.1] * 768
