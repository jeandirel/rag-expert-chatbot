"""
RAG Expert Chatbot - Backend FastAPI
Point d'entree principal de l'application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import structlog

from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1.router import api_router
from app.api.webhooks import webhooks_router

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
      """Gestion du cycle de vie de l'application."""
      logger.info("Demarrage de RAG Expert Chatbot", version="1.0.0")
      async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Base de donnees initialisee")
    yield
    logger.info("Arret de l'application")


app = FastAPI(
      title="RAG Expert Chatbot API",
      description="API REST pour le chatbot RAG expert metiers",
      version="1.0.0",
      docs_url="/api/docs",
      redoc_url="/api/redoc",
      openapi_url="/api/openapi.json",
      lifespan=lifespan,
)

app.add_middleware(
      CORSMiddleware,
      allow_origins=settings.CORS_ORIGINS.split(","),
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(webhooks_router, prefix="/api/v1/webhooks")


@app.get("/health", tags=["health"])
async def health_check():
      return {"status": "ok", "version": "1.0.0"}


@app.get("/", tags=["root"])
async def root():
      return {
          "message": "RAG Expert Chatbot API",
          "docs": "/api/docs",
          "version": "1.0.0"
}
