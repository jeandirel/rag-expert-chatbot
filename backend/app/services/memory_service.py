"""
Service Memory - Gestion de l'historique des conversations via Redis
"""
import json
import time
from typing import Optional

import redis.asyncio as aioredis
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class MemoryService:
      """Gestion de l'historique conversationnel via Redis."""

    def __init__(self):
              self._redis = None

    @property
    def redis(self):
              if self._redis is None:
                            self._redis = aioredis.from_url(
                                              settings.REDIS_URL,
                                              encoding="utf-8",
                                              decode_responses=True
                            )
                        return self._redis

    async def get_history(self, conversation_id: str) -> list:
              """Recupere l'historique d'une conversation."""
        data = await self.redis.get(f"conv:{conversation_id}")
        if not data:
                      return []
                  try:
                                return json.loads(data)
except json.JSONDecodeError:
            return []

    async def save_exchange(
              self,
              conversation_id: str,
              question: str,
              answer: str,
              sources: list,
              user_id: str = "unknown"
    ):
              """Sauvegarde un echange question/reponse dans l'historique."""
        history = await self.get_history(conversation_id)

        exchange = {
                      "question": question,
                      "answer": answer,
                      "sources": sources,
                      "timestamp": time.time(),
        }
        history.append(exchange)

        history = history[-settings.CONVERSATION_HISTORY_LENGTH * 2:]

        await self.redis.setex(
                      f"conv:{conversation_id}",
                      settings.REDIS_SESSION_TTL,
                      json.dumps(history)
        )

        meta = {
                      "user_id": user_id,
                      "last_activity": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        existing_meta = await self.redis.get(f"conv_meta:{conversation_id}")
        if existing_meta:
                      existing = json.loads(existing_meta)
                      meta["started_at"] = existing.get("started_at", meta["last_activity"])
else:
            meta["started_at"] = meta["last_activity"]

        await self.redis.setex(
                      f"conv_meta:{conversation_id}",
                      settings.REDIS_SESSION_TTL,
                      json.dumps(meta)
        )

        await self.redis.sadd(f"user_convs:{user_id}", conversation_id)
        await self.redis.expire(f"user_convs:{user_id}", settings.REDIS_SESSION_TTL * 7)

    async def list_conversations(self, user_id: str) -> list:
              """Liste toutes les conversations d'un utilisateur."""
        conv_ids = await self.redis.smembers(f"user_convs:{user_id}")
        conversations = []
        for conv_id in conv_ids:
                      meta_data = await self.redis.get(f"conv_meta:{conv_id}")
                      history_data = await self.redis.get(f"conv:{conv_id}")
                      if meta_data and history_data:
                                        try:
                                                              meta = json.loads(meta_data)
                                                              history = json.loads(history_data)
                                                              conversations.append({
                                                                  "conversation_id": conv_id,
                                                                  "message_count": len(history),
                                                                  "last_message": history[-1].get("question", "")[:80] if history else "",
                                                                  "started_at": meta.get("started_at", ""),
                                                                  "last_activity": meta.get("last_activity", ""),
                                                              })
except Exception:
                    continue

        conversations.sort(key=lambda x: x.get("last_activity", ""), reverse=True)
        return conversations

    async def delete_conversation(self, conversation_id: str, user_id: str):
              """Supprime une conversation."""
        await self.redis.delete(f"conv:{conversation_id}")
        await self.redis.delete(f"conv_meta:{conversation_id}")
        await self.redis.srem(f"user_convs:{user_id}", conversation_id)

    async def clear_all_user_conversations(self, user_id: str):
              """Supprime toutes les conversations d'un utilisateur."""
        conv_ids = await self.redis.smembers(f"user_convs:{user_id}")
        for conv_id in conv_ids:
                      await self.delete_conversation(conv_id, user_id)
