"""
Service de statistiques et metriques du chatbot RAG.
Enregistre les conversations, messages, feedbacks et temps de reponse.
Stocke dans PostgreSQL via SQLAlchemy ou dans Redis.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from collections import defaultdict

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, DateTime, Text, select, func
import sqlalchemy as sa

from app.core.config import settings

logger = logging.getLogger(__name__)


# ─── Modeles SQLAlchemy ────────────────────────────────────────────────────

class Base(DeclarativeBase):
      pass


class ConversationRecord(Base):
      __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    user_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_activity: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    feedback: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)


class MessageRecord(Base):
      __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(36), index=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    response_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sources_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    feedback: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)


# ─── Service Stats ─────────────────────────────────────────────────────────

class StatsService:
      """
          Service centralise pour les statistiques du chatbot.
              - Enregistre chaque echange dans PostgreSQL
                  - Maintient des compteurs en temps reel dans Redis
                      - Fournit des agregations pour le dashboard admin
                          """

    def __init__(self):
              self._engine = None
              self._redis: aioredis.Redis | None = None

    async def _get_engine(self):
              """Initialise le moteur SQLAlchemy de maniere paresseuse."""
              if self._engine is None:
                            self._engine = create_async_engine(
                                              settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
                                              pool_size=10,
                                              max_overflow=20,
                                              echo=False,
                            )
                            async with self._engine.begin() as conn:
                                              await conn.run_sync(Base.metadata.create_all)
                                      return self._engine

          async def _get_redis(self) -> aioredis.Redis:
                    """Initialise le client Redis de maniere paresseuse."""
                    if self._redis is None:
                                  self._redis = aioredis.from_url(
                                                    settings.REDIS_URL,
                                                    encoding="utf-8",
                                                    decode_responses=True,
                                  )
                              return self._redis

    async def record_conversation(
              self,
              conversation_id: str,
              user_id: str,
              user_name: str = "",
    ) -> None:
              """Enregistre une nouvelle conversation."""
        try:
                      engine = await self._get_engine()
                      async with AsyncSession(engine) as session:
                                        existing = await session.get(ConversationRecord, conversation_id)
                                        if not existing:
                                                              record = ConversationRecord(
                                                                                        id=conversation_id,
                                                                                        user_id=user_id,
                                                                                        user_name=user_name,
                                                              )
                                                              session.add(record)
                                                              await session.commit()

                                    # Incrementer le compteur Redis
                                    redis = await self._get_redis()
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            await redis.incr(f"stats:conversations:total")
            await redis.incr(f"stats:conversations:day:{today}")
            await redis.sadd(f"stats:active_users:{today}", user_id)

except Exception as e:
            logger.error(f"Erreur enregistrement conversation: {e}")

    async def record_message(
              self,
              message_id: str,
              conversation_id: str,
              user_id: str,
              role: str,
              content: str,
              response_time_ms: Optional[float] = None,
              sources_count: int = 0,
    ) -> None:
              """Enregistre un message et met a jour les statistiques."""
        try:
                      engine = await self._get_engine()
            async with AsyncSession(engine) as session:
                              # Enregistrer le message
                              record = MessageRecord(
                                                    id=message_id,
                                                    conversation_id=conversation_id,
                                                    user_id=user_id,
                                                    role=role,
                                                    content=content[:2000],  # Tronquer pour la base
                                                    response_time_ms=response_time_ms,
                                                    sources_count=sources_count,
                              )
                              session.add(record)

                # Mettre a jour le compteur de la conversation
                              conv = await session.get(ConversationRecord, conversation_id)
                if conv:
                                      conv.message_count += 1
                                      conv.last_activity = datetime.now(timezone.utc)

                await session.commit()

            # Metriques Redis temps reel
            redis = await self._get_redis()
            hour_key = datetime.now(timezone.utc).strftime("%Y-%m-%d:%H")

            await redis.incr(f"stats:messages:total")
            await redis.incr(f"stats:messages:hour:{hour_key}")

            if response_time_ms and role == "assistant":
                              # Temps de reponse moyen par heure (liste glissante)
                              await redis.lpush(f"stats:response_times:{hour_key}", response_time_ms)
                              await redis.ltrim(f"stats:response_times:{hour_key}", 0, 999)

            # Top requetes (pour les messages utilisateur)
            if role == "user" and content:
                              query_key = content[:100].strip()
                              await redis.zincrby("stats:top_queries", 1, query_key)

except Exception as e:
            logger.error(f"Erreur enregistrement message: {e}")

    async def record_feedback(
              self,
              conversation_id: str,
              message_id: Optional[str],
              feedback: str,
    ) -> None:
              """Enregistre le feedback utilisateur (positive/negative)."""
        try:
                      engine = await self._get_engine()
            async with AsyncSession(engine) as session:
                              if message_id:
                                                    msg = await session.get(MessageRecord, message_id)
                                                    if msg:
                                                                              msg.feedback = feedback

                                                conv = await session.get(ConversationRecord, conversation_id)
                if conv:
                                      conv.feedback = feedback

                await session.commit()

            # Compteurs Redis
            redis = await self._get_redis()
            await redis.incr(f"stats:feedback:{feedback}")

except Exception as e:
            logger.error(f"Erreur enregistrement feedback: {e}")

    async def get_dashboard_stats(self) -> dict[str, Any]:
              """
                      Retourne les statistiques completes pour le dashboard admin.
                              Combine PostgreSQL (historique) et Redis (temps reel).
                                      """
        try:
                      redis = await self._get_redis()
            engine = await self._get_engine()

            # Stats globales Redis
            total_conversations = int(await redis.get("stats:conversations:total") or 0)
            total_messages = int(await redis.get("stats:messages:total") or 0)
            feedback_positive = int(await redis.get("stats:feedback:positive") or 0)
            feedback_negative = int(await redis.get("stats:feedback:negative") or 0)

            # Utilisateurs actifs aujourd'hui
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            active_users_today = await redis.scard(f"stats:active_users:{today}")

            # Temps de reponse moyen (derniere heure)
            current_hour = datetime.now(timezone.utc).strftime("%Y-%m-%d:%H")
            response_times_raw = await redis.lrange(f"stats:response_times:{current_hour}", 0, -1)
            avg_response_time = 0.0
            if response_times_raw:
                              times = [float(t) for t in response_times_raw]
                avg_response_time = sum(times) / len(times)

            # Conversations par jour (30 derniers jours depuis PostgreSQL)
            conversations_by_day = []
            async with AsyncSession(engine) as session:
                              thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
                result = await session.execute(
                                      select(
                                                                func.date(ConversationRecord.created_at).label("date"),
                                                                func.count(ConversationRecord.id).label("count"),
                                      )
                                      .where(ConversationRecord.created_at >= thirty_days_ago)
                                      .group_by(func.date(ConversationRecord.created_at))
                                      .order_by(func.date(ConversationRecord.created_at))
                )
                for row in result:
                                      conversations_by_day.append({
                                                                "date": str(row.date),
                                                                "count": row.count,
                                      })

                # Total documents depuis Qdrant (approximation via Redis)
                total_docs = int(await redis.get("stats:documents:total") or 0)

            # Temps de reponse par heure (24 dernieres heures)
            response_times_chart = []
            for i in range(24):
                              hour = (datetime.now(timezone.utc) - timedelta(hours=23 - i))
                hour_key = hour.strftime("%Y-%m-%d:%H")
                times_raw = await redis.lrange(f"stats:response_times:{hour_key}", 0, -1)
                avg = 0.0
                if times_raw:
                                      times = [float(t) for t in times_raw]
                                      avg = sum(times) / len(times)
                                  response_times_chart.append({
                                                        "hour": hour.strftime("%H:00"),
                                                        "avg_ms": round(avg, 1),
                                  })

            # Top requetes (depuis Redis sorted set)
            top_queries_raw = await redis.zrevrangebyscore(
                              "stats:top_queries",
                              "+inf", "-inf",
                              start=0, num=10,
                              withscores=True,
            )
            top_queries = [
                              {"query": q, "count": int(score)}
                              for q, score in top_queries_raw
            ]

            # Activite utilisateurs par heure
            user_activity = []
            for i in range(24):
                              hour = (datetime.now(timezone.utc) - timedelta(hours=23 - i))
                msg_key = hour.strftime("stats:messages:hour:%Y-%m-%d:%H")
                count = int(await redis.get(msg_key) or 0)
                user_activity.append({
                                      "hour": hour.strftime("%H:00"),
                                      "users": count,
                })

            return {
                              "total_conversations": total_conversations,
                              "total_messages": total_messages,
                              "active_users_today": active_users_today,
                              "avg_response_time_ms": round(avg_response_time, 1),
                              "total_documents": total_docs,
                              "feedback_positive": feedback_positive,
                              "feedback_negative": feedback_negative,
                              "conversations_by_day": conversations_by_day,
                              "top_queries": top_queries,
                              "response_times": response_times_chart,
                              "user_activity": user_activity,
            }

except Exception as e:
            logger.error(f"Erreur get_dashboard_stats: {e}")
            return {
                              "total_conversations": 0,
                              "total_messages": 0,
                              "active_users_today": 0,
                              "avg_response_time_ms": 0.0,
                              "total_documents": 0,
                              "feedback_positive": 0,
                              "feedback_negative": 0,
                              "conversations_by_day": [],
                              "top_queries": [],
                              "response_times": [],
                              "user_activity": [],
            }

    async def increment_document_count(self, delta: int = 1) -> None:
              """Met a jour le compteur de documents indexes."""
        redis = await self._get_redis()
        await redis.incrby("stats:documents:total", delta)


# Singleton
_stats_service: StatsService | None = None


def get_stats_service() -> StatsService:
      """Dependency injection pour FastAPI."""
    global _stats_service
    if _stats_service is None:
              _stats_service = StatsService()
    return _stats_service
