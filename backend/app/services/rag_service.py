"""
Service RAG principal - Logique de retrieval et generation
"""
import json
import time
import uuid
from typing import AsyncGenerator, Optional

import structlog
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.core.config import settings
from app.services.llm_service import LLMService
from app.services.memory_service import MemoryService
from app.services.cache_service import CacheService
from app.services.stats_service import StatsService

logger = structlog.get_logger()

SYSTEM_PROMPT = """Tu es un expert metier senior avec acces a la documentation complete de l'entreprise.

REGLES STRICTES :
- Reponds UNIQUEMENT en te basant sur les documents fournis dans le contexte
- Si l'information n'est pas dans les documents, dis clairement "Je ne trouve pas cette information dans la documentation disponible"
- Cite toujours le nom du document source entre crochets [NomDocument.pdf]
- Sois precis, structure et professionnel dans tes reponses
- Utilise des listes a puces quand c'est pertinent pour la clarte
- Si plusieurs documents donnent des informations differentes, mentionne-le
- Reponds en francais sauf si la question est en anglais
"""


class RAGService:
      """Service principal pour le chatbot RAG."""

    def __init__(self):
              self.llm_service = LLMService()
              self.memory_service = MemoryService()
              self.cache_service = CacheService()
              self.stats_service = StatsService()
              self._vectorstore = None

    @property
    def vectorstore(self) -> Qdrant:
              if self._vectorstore is None:
                            client = QdrantClient(
                                              host=settings.QDRANT_HOST,
                                              port=settings.QDRANT_PORT
                            )
                            self._vectorstore = Qdrant(
                                client=client,
                                collection_name=settings.COLLECTION_NAME,
                                embeddings=self.llm_service.embeddings,
                            )
                        return self._vectorstore

    async def chat(
              self,
              message: str,
              conversation_id: Optional[str] = None,
              user_id: str = "anonymous",
              department_filter: Optional[str] = None,
    ) -> dict:
              """Traitement d'un message utilisateur - retourne une reponse complete."""
        start_time = time.time()
        conv_id = conversation_id or str(uuid.uuid4())

        cache_key = f"chat:{hash(message)}:{department_filter}"
        if cached := await self.cache_service.get(cache_key):
                      logger.info("Cache hit", key=cache_key)
                      return {**json.loads(cached), "conversation_id": conv_id, "cached": True}

        history = await self.memory_service.get_history(conv_id)
        contextualized_q = await self._contextualize_query(message, history)

        docs = await self._retrieve_documents(contextualized_q, department_filter)

        context = self._build_context(docs)
        sources = self._extract_sources(docs)

        full_prompt = self._build_prompt(message, context, history)
        answer = await self.llm_service.generate(full_prompt)

        confidence = self._assess_confidence(answer, docs)

        await self.memory_service.save_exchange(conv_id, message, answer, sources)

        response_time = (time.time() - start_time) * 1000
        await self.stats_service.track(
                      user_id=user_id,
                      question=message,
                      answer=answer,
                      sources=sources,
                      confidence=confidence,
                      response_time_ms=response_time
        )

        result = {
                      "answer": answer,
                      "sources": sources,
                      "confidence": confidence,
                      "conversation_id": conv_id,
                      "response_time_ms": round(response_time, 2),
                      "cached": False,
        }

        await self.cache_service.set(cache_key, json.dumps(result), ttl=1800)
        return result

    async def chat_stream(
              self,
              message: str,
              conversation_id: Optional[str] = None,
              user_id: str = "anonymous",
              department_filter: Optional[str] = None,
    ) -> AsyncGenerator[dict, None]:
              """Chatbot avec streaming token par token."""
              conv_id = conversation_id or str(uuid.uuid4())

        yield {"type": "conv_id", "data": conv_id}

        history = await self.memory_service.get_history(conv_id)
        contextualized_q = await self._contextualize_query(message, history)
        docs = await self._retrieve_documents(contextualized_q, department_filter)
        context = self._build_context(docs)
        full_prompt = self._build_prompt(message, context, history)

        full_answer = ""
        async for token in self.llm_service.stream(full_prompt):
                      full_answer += token
                      yield {"type": "token", "data": token}

        sources = self._extract_sources(docs)
        confidence = self._assess_confidence(full_answer, docs)

        yield {"type": "sources", "data": sources}
        yield {"type": "confidence", "data": confidence}
        yield {"type": "done", "data": True}

        await self.memory_service.save_exchange(conv_id, message, full_answer, sources)

    async def _retrieve_documents(self, query: str, department: Optional[str] = None):
              """Recherche hybride dans Qdrant."""
              search_kwargs = {"k": settings.TOP_K_RESULTS}

        if department:
                      search_kwargs["filter"] = Filter(
                                        must=[FieldCondition(
                                                              key="department",
                                                              match=MatchValue(value=department)
                                        )]
                      )

        retriever = self.vectorstore.as_retriever(search_kwargs=search_kwargs)
        return retriever.get_relevant_documents(query)

    def _build_context(self, docs) -> str:
              """Construit le contexte documentaire."""
              parts = []
              for doc in docs:
                            source = doc.metadata.get("source_file", "Document inconnu")
                            parts.append(f"[Source: {source}]\n{doc.page_content}")
                        return "\n\n---\n\n".join(parts)

    def _extract_sources(self, docs) -> list:
              """Extrait les sources uniques des documents retrouves."""
        seen = set()
        sources = []
        for doc in docs:
                      filename = doc.metadata.get("source_file", "")
                      if filename and filename not in seen:
                                        seen.add(filename)
                                        sources.append({
                                            "file": filename,
                                            "path": doc.metadata.get("source_path", ""),
                                            "category": doc.metadata.get("category", ""),
                                            "department": doc.metadata.get("department", ""),
                                        })
                                return sources

    def _build_prompt(self, question: str, context: str, history: list) -> list:
              """Construit le prompt complet avec historique."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        for exchange in history[-settings.CONVERSATION_HISTORY_LENGTH:]:
                      messages.append({"role": "user", "content": exchange["question"]})
            messages.append({"role": "assistant", "content": exchange["answer"]})

        user_content = f"""CONTEXTE DOCUMENTAIRE :
        {context}

        QUESTION : {question}

        REPONSE EXPERTE :"""

        messages.append({"role": "user", "content": user_content})
        return messages

    async def _contextualize_query(self, question: str, history: list) -> str:
              """Reformule la question en tenant compte de l'historique."""
        if not history:
                      return question

        history_text = "\n".join([
                      f"User: {h['question']}\nAssistant: {h['answer'][:200]}..."
                      for h in history[-3:]
        ])

        prompt = f"""Historique de conversation :
        {history_text}

        Question actuelle : {question}

        Si la question fait reference a quelque chose de l'historique, reformule-la de facon autonome.
        Sinon, retourne la question telle quelle. Reformulation :"""

        return await self.llm_service.generate_simple(prompt)

    def _assess_confidence(self, answer: str, docs: list) -> str:
              """Evalue le niveau de confiance de la reponse."""
        low_confidence_phrases = [
                      "je ne trouve pas",
                      "pas dans la documentation",
                      "je n'ai pas d'information",
                      "aucun document"
        ]
        if any(phrase in answer.lower() for phrase in low_confidence_phrases):
                      return "low"
        if len(docs) >= 4:
                      return "high"
        return "medium"
