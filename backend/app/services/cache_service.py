"""
Service de cache Redis pour le chatbot RAG.
Cache les reponses semantiquement similaires pour accelerer les requetes
repetitives et reduire la charge sur le LLM et Qdrant.
"""

import hashlib
import json
import logging
from typing import Any, Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

# TTL par defaut: 1 heure
DEFAULT_TTL = 3600

# TTL cache des embeddings: 24 heures
EMBEDDING_TTL = 86400

# TTL cache des resultats de recherche: 30 minutes
SEARCH_TTL = 1800


class CacheService:
      """
          Service de cache Redis multi-niveaux:
              1. Cache exact: reponses pour requetes identiques
                  2. Cache embeddings: eviter de recalculer les embeddings
                      3. Cache recherche: resultats Qdrant pour requetes similaires
                          4. Rate limiting: protection contre l'abus
                              """

    def __init__(self):
              self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
              """Initialise le client Redis de maniere paresseuse."""
              if self._redis is None:
                            self._redis = aioredis.from_url(
                                              settings.REDIS_URL,
                                              encoding="utf-8",
                                              decode_responses=True,
                                              max_connections=50,
                            )
                            # Test de connexion
                            await self._redis.ping()
                            logger.info("Cache Redis connecte")
                        return self._redis

    def _make_key(self, prefix: str, content: str) -> str:
              """Cree une cle Redis a partir d'un hash SHA256."""
        hash_val = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"cache:{prefix}:{hash_val}"

    # ─── Cache de reponses ─────────────────────────────────────────────

    async def get_response(
              self,
              query: str,
              user_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
              """
                      Recupere une reponse en cache pour une requete donnee.
                              La cle est basee sur le hash de la requete normalisee.
                                      """
        try:
                      redis = await self._get_redis()
                      # Normaliser la requete (lowercase, strip)
                      normalized = query.lower().strip()
                      key = self._make_key("response", normalized)

            cached = await redis.get(key)
            if cached:
                              data = json.loads(cached)
                              logger.debug(f"Cache HIT pour: {query[:50]}...")
                              return data

            logger.debug(f"Cache MISS pour: {query[:50]}...")
            return None

except Exception as e:
            logger.warning(f"Erreur lecture cache: {e}")
            return None

    async def set_response(
              self,
              query: str,
              response: dict[str, Any],
              ttl: int = DEFAULT_TTL,
    ) -> None:
              """Met en cache une reponse pour une requete."""
        try:
                      redis = await self._get_redis()
                      normalized = query.lower().strip()
                      key = self._make_key("response", normalized)

            await redis.setex(
                              key,
                              ttl,
                              json.dumps(response, ensure_ascii=False),
            )
            logger.debug(f"Cache SET pour: {query[:50]}... (TTL: {ttl}s)")

except Exception as e:
            logger.warning(f"Erreur ecriture cache: {e}")

    async def invalidate_response(self, query: str) -> bool:
              """Invalide le cache pour une requete specifique."""
        try:
                      redis = await self._get_redis()
                      key = self._make_key("response", query.lower().strip())
                      deleted = await redis.delete(key)
                      return bool(deleted)
except Exception as e:
            logger.warning(f"Erreur invalidation cache: {e}")
            return False

    # ─── Cache des embeddings ─────────────────────────────────────────

    async def get_embedding(self, text: str) -> Optional[list[float]]:
              """Recupere un embedding en cache."""
        try:
                      redis = await self._get_redis()
                      key = self._make_key("embedding", text)
                      cached = await redis.get(key)
                      if cached:
                                        return json.loads(cached)
                                    return None
except Exception as e:
            logger.warning(f"Erreur lecture embedding cache: {e}")
            return None

    async def set_embedding(
              self,
              text: str,
              embedding: list[float],
              ttl: int = EMBEDDING_TTL,
    ) -> None:
              """Met en cache un embedding de texte."""
        try:
                      redis = await self._get_redis()
            key = self._make_key("embedding", text)
            await redis.setex(key, ttl, json.dumps(embedding))
except Exception as e:
            logger.warning(f"Erreur ecriture embedding cache: {e}")

    # ─── Cache des resultats de recherche ──────────────────────────────

    async def get_search_results(
              self,
              query: str,
              top_k: int = 5,
    ) -> Optional[list[dict]]:
              """Recupere les resultats de recherche Qdrant en cache."""
        try:
                      redis = await self._get_redis()
            key = self._make_key("search", f"{query}:k={top_k}")
            cached = await redis.get(key)
            if cached:
                              logger.debug(f"Search cache HIT: {query[:30]}...")
                              return json.loads(cached)
                          return None
except Exception as e:
            logger.warning(f"Erreur lecture search cache: {e}")
            return None

    async def set_search_results(
              self,
              query: str,
              results: list[dict],
              top_k: int = 5,
              ttl: int = SEARCH_TTL,
    ) -> None:
              """Met en cache les resultats de recherche Qdrant."""
        try:
                      redis = await self._get_redis()
            key = self._make_key("search", f"{query}:k={top_k}")
            await redis.setex(key, ttl, json.dumps(results, ensure_ascii=False))
except Exception as e:
            logger.warning(f"Erreur ecriture search cache: {e}")

    # ─── Rate limiting ─────────────────────────────────────────────────

    async def check_rate_limit(
              self,
              user_id: str,
              limit: int = 60,
              window_seconds: int = 60,
    ) -> tuple[bool, int]:
              """
                      Verifie le rate limit pour un utilisateur.

                              Returns:
                                          (is_allowed, requests_remaining)
                                                  """
        try:
                      redis = await self._get_redis()
            key = f"ratelimit:{user_id}:{window_seconds}"

            pipe = redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_seconds)
            results = await pipe.execute()

            current_count = results[0]
            remaining = max(0, limit - current_count)
            is_allowed = current_count <= limit

            if not is_allowed:
                              logger.warning(f"Rate limit depasse pour {user_id}: {current_count}/{limit}")

            return is_allowed, remaining

except Exception as e:
            logger.warning(f"Erreur rate limit check: {e}")
            return True, limit  # En cas d'erreur Redis, autoriser

    async def get_rate_limit_info(
              self,
              user_id: str,
              window_seconds: int = 60,
    ) -> dict[str, int]:
              """Retourne les infos de rate limit pour un utilisateur."""
        try:
                      redis = await self._get_redis()
            key = f"ratelimit:{user_id}:{window_seconds}"
            current = int(await redis.get(key) or 0)
            ttl = await redis.ttl(key)
            return {"current": current, "reset_in": ttl}
except Exception:
            return {"current": 0, "reset_in": window_seconds}

    # ─── Cache generique ────────────────────────────────────────────────

    async def get(self, key: str) -> Optional[Any]:
              """Recupere une valeur generique depuis le cache."""
        try:
                      redis = await self._get_redis()
            value = await redis.get(f"cache:generic:{key}")
            if value:
                              return json.loads(value)
                          return None
except Exception as e:
            logger.warning(f"Erreur get cache {key}: {e}")
            return None

    async def set(
              self,
              key: str,
              value: Any,
              ttl: int = DEFAULT_TTL,
    ) -> None:
              """Stocke une valeur generique dans le cache."""
        try:
                      redis = await self._get_redis()
            await redis.setex(
                              f"cache:generic:{key}",
                              ttl,
                              json.dumps(value, ensure_ascii=False, default=str),
            )
except Exception as e:
            logger.warning(f"Erreur set cache {key}: {e}")

    async def delete(self, key: str) -> bool:
              """Supprime une cle du cache."""
        try:
                      redis = await self._get_redis()
            deleted = await redis.delete(f"cache:generic:{key}")
            return bool(deleted)
except Exception as e:
            logger.warning(f"Erreur delete cache {key}: {e}")
            return False

    async def flush_pattern(self, pattern: str) -> int:
              """Supprime toutes les cles correspondant a un pattern."""
        try:
                      redis = await self._get_redis()
            keys = await redis.keys(f"cache:{pattern}:*")
            if keys:
                              deleted = await redis.delete(*keys)
                              logger.info(f"Cache flush: {deleted} cles supprimees (pattern: {pattern})")
                              return deleted
                          return 0
except Exception as e:
            logger.warning(f"Erreur flush cache pattern {pattern}: {e}")
            return 0

    async def get_cache_stats(self) -> dict[str, Any]:
              """Retourne les statistiques du cache Redis."""
        try:
                      redis = await self._get_redis()
            info = await redis.info("stats")
            memory = await redis.info("memory")
            keyspace = await redis.info("keyspace")

            return {
                              "hits": info.get("keyspace_hits", 0),
                              "misses": info.get("keyspace_misses", 0),
                              "hit_rate": round(
                                                    info.get("keyspace_hits", 0) /
                                                    max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1) * 100,
                                                    1
                              ),
                              "memory_used_mb": round(memory.get("used_memory", 0) / 1024 / 1024, 2),
                              "total_keys": sum(
                                                    int(v.get("keys", 0))
                                                    for v in (keyspace or {}).values()
                                                    if isinstance(v, dict)
                              ),
            }
except Exception as e:
            logger.warning(f"Erreur stats cache: {e}")
            return {}

    async def health_check(self) -> bool:
              """Verifie que Redis est accessible."""
        try:
                      redis = await self._get_redis()
            pong = await redis.ping()
            return pong
except Exception:
            return False


# Singleton
_cache_service: CacheService | None = None


def get_cache_service() -> CacheService:
      """Dependency injection pour FastAPI."""
    global _cache_service
    if _cache_service is None:
              _cache_service = CacheService()
    return _cache_service
