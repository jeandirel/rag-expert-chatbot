"""
Configuration centrale de l'application
Toutes les variables d'environnement sont lues ici
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Literal


class Settings(BaseSettings):
      """Configuration de l'application depuis les variables d'environnement."""

    # ── API ───────────────────────────────────────────────────
      APP_NAME: str = "RAG Expert Chatbot"
      APP_VERSION: str = "1.0.0"
      DEBUG: bool = False
      LOG_LEVEL: str = "INFO"

    # ── Securite ─────────────────────────────────────────────
      SECRET_KEY: str = "change-this-in-production"
      ALGORITHM: str = "HS256"
      ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
      CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # ── LLM Provider ─────────────────────────────────────────
      LLM_PROVIDER: Literal["ollama", "groq", "gemini", "openai", "mock"] = "ollama"

    # Ollama (local)
      OLLAMA_BASE_URL: str = "http://localhost:11434"
      LLM_MODEL: str = "mistral"
      EMBEDDING_MODEL: str = "nomic-embed-text"

    # Groq
      GROQ_API_KEY: str = ""

    # Google Gemini
      GOOGLE_API_KEY: str = ""

    # OpenAI
      OPENAI_API_KEY: str = ""

    # ── Parametres RAG ────────────────────────────────────────
      CHUNK_SIZE: int = 1000
      CHUNK_OVERLAP: int = 200
      TOP_K_RESULTS: int = 6
      LLM_TEMPERATURE: float = 0.1
      LLM_MAX_TOKENS: int = 2000
      CONVERSATION_HISTORY_LENGTH: int = 10

    # ── Qdrant ───────────────────────────────────────────────
      QDRANT_HOST: str = "localhost"
      QDRANT_PORT: int = 6333
      COLLECTION_NAME: str = "rag_expert"

    # ── PostgreSQL ───────────────────────────────────────────
      DATABASE_URL: str = "postgresql+asyncpg://admin:password@localhost:5432/chatbot_db"

    # ── Redis ────────────────────────────────────────────────
      REDIS_URL: str = "redis://localhost:6379/0"
      REDIS_SESSION_TTL: int = 7200
      REDIS_CACHE_TTL: int = 3600

    # ── Keycloak SSO ─────────────────────────────────────────
      KEYCLOAK_URL: str = "http://localhost:8080"
      KEYCLOAK_REALM: str = "chatbot-realm"
      KEYCLOAK_CLIENT_ID: str = "chatbot-app"
      KEYCLOAK_CLIENT_SECRET: str = "secret"

    # ── Documents ────────────────────────────────────────────
      DOCUMENTS_FOLDER: str = "./documents"

    # ── SharePoint ───────────────────────────────────────────
      SHAREPOINT_ENABLED: bool = False
      SHAREPOINT_URL: str = ""
      SHAREPOINT_SITE: str = ""
      SHAREPOINT_USER: str = ""
      SHAREPOINT_PASSWORD: str = ""
      SHAREPOINT_LIBRARY: str = "Documents"
      SYNC_INTERVAL_HOURS: int = 4

    # Graph API (webhooks temps reel)
      GRAPH_TENANT_ID: str = ""
      GRAPH_CLIENT_ID: str = ""
      GRAPH_CLIENT_SECRET: str = ""
      WEBHOOK_NOTIFICATION_URL: str = ""

    # ── Teams Bot ────────────────────────────────────────────
      TEAMS_BOT_ENABLED: bool = False
      TEAMS_APP_ID: str = ""
      TEAMS_APP_PASSWORD: str = ""

    # ── Monitoring ───────────────────────────────────────────
      PROMETHEUS_ENABLED: bool = True

    class Config:
              env_file = ".env"
              env_file_encoding = "utf-8"
              case_sensitive = False

    def get_jwks_uri(self) -> str:
              """Retourne l'URI JWKS pour la validation des tokens Keycloak."""
              return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}/protocol/openid-connect/certs"

    def get_openid_config_uri(self) -> str:
              """Retourne l'URI de configuration OpenID Connect."""
              return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}/.well-known/openid-configuration"

    def is_llm_configured(self) -> bool:
              """Verifie si le LLM est correctement configure."""
              if self.LLM_PROVIDER == "ollama":
                            return bool(self.OLLAMA_BASE_URL)
elif self.LLM_PROVIDER == "groq":
            return bool(self.GROQ_API_KEY)
elif self.LLM_PROVIDER == "gemini":
            return bool(self.GOOGLE_API_KEY)
elif self.LLM_PROVIDER == "openai":
            return bool(self.OPENAI_API_KEY)
elif self.LLM_PROVIDER == "mock":
            return True
        return False


@lru_cache()
def get_settings() -> Settings:
      """Retourne l'instance de configuration (cached)."""
      return Settings()


settings = get_settings()
