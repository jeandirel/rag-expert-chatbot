.PHONY: help install setup start stop restart build test lint clean logs index

DOCKER_COMPOSE = docker compose -f infra/docker-compose.yml --env-file .env
BACKEND_DIR = backend
FRONTEND_DIR = frontend

help:
	@echo ""
	@echo "RAG Expert Chatbot - Commandes disponibles"
	@echo "==========================================="
	@echo ""
	@echo "  make setup          Configuration initiale complete"
	@echo "  make start          Demarrer toute la stack"
	@echo "  make stop           Arreter la stack"
	@echo "  make restart        Redemarrer la stack"
	@echo "  make build          Reconstruire les images Docker"
	@echo "  make logs           Afficher les logs en temps reel"
	@echo "  make index          Indexer les documents"
	@echo "  make index-watch    Indexer + surveiller les nouveaux docs"
	@echo "  make test           Lancer tous les tests"
	@echo "  make test-rag       Tests de qualite RAG (RAGAS)"
	@echo "  make lint           Linting backend + frontend"
	@echo "  make models         Telecharger les modeles Ollama"
	@echo "  make clean          Nettoyer les volumes Docker"
	@echo "  make status         Etat des services"
	@echo ""

setup: .env models
	@echo "Configuration initiale..."
	$(DOCKER_COMPOSE) up -d postgres redis
	@sleep 5
	cd $(BACKEND_DIR) && pip install -r requirements.txt
	cd $(BACKEND_DIR) && alembic upgrade head
	@echo "Setup termine ! Lancez: make start"

.env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo ".env cree depuis .env.example - Editez-le avec vos parametres"; \
	fi

models:
	@echo "Telechargement des modeles Ollama..."
	ollama pull mistral
	ollama pull nomic-embed-text
	@echo "Modeles telecharges"

start:
	@echo "Demarrage de RAG Expert Chatbot..."
	$(DOCKER_COMPOSE) up -d
	@echo ""
	@echo "Services disponibles :"
	@echo "  Chatbot  : http://localhost:3000"
	@echo "  API Docs : http://localhost:8000/api/docs"
	@echo "  Admin    : http://localhost:3000/admin"
	@echo "  Keycloak : http://localhost:8080"
	@echo "  Grafana  : http://localhost:3001"
	@echo ""

stop:
	$(DOCKER_COMPOSE) down

restart:
	$(DOCKER_COMPOSE) restart

build:
	$(DOCKER_COMPOSE) build --no-cache

build-prod:
	$(DOCKER_COMPOSE) build --no-cache --build-arg NODE_ENV=production

logs:
	$(DOCKER_COMPOSE) logs -f

logs-backend:
	$(DOCKER_COMPOSE) logs -f backend

logs-frontend:
	$(DOCKER_COMPOSE) logs -f frontend

status:
	$(DOCKER_COMPOSE) ps

index:
	@echo "Indexation des documents..."
	cd $(BACKEND_DIR) && python -m ingestion.pipeline --folder ../documents
	@echo "Indexation terminee"

index-watch:
	@echo "Demarrage du mode surveillance..."
	cd $(BACKEND_DIR) && python -m ingestion.pipeline --watch --folder ../documents

sharepoint-sync:
	@echo "Synchronisation SharePoint..."
	cd $(BACKEND_DIR) && python -m ingestion.sync_sharepoint

test:
	@echo "Lancement des tests..."
	cd $(BACKEND_DIR) && pytest tests/ -v --tb=short
	cd $(FRONTEND_DIR) && npm test -- --watchAll=false

test-unit:
	cd $(BACKEND_DIR) && pytest tests/unit/ -v

test-integration:
	cd $(BACKEND_DIR) && pytest tests/integration/ -v

test-rag:
	@echo "Tests de qualite RAG (RAGAS)..."
	cd $(BACKEND_DIR) && pytest tests/rag_quality/ -v --benchmark

lint:
	@echo "Linting backend..."
	cd $(BACKEND_DIR) && ruff check app/ ingestion/
	@echo "Linting frontend..."
	cd $(FRONTEND_DIR) && npm run lint

format:
	cd $(BACKEND_DIR) && ruff format app/ ingestion/

migrate:
	cd $(BACKEND_DIR) && alembic upgrade head

migrate-create:
	cd $(BACKEND_DIR) && alembic revision --autogenerate -m "$(name)"

clean:
	@echo "ATTENTION: Suppression de tous les volumes Docker (donnees perdues)"
	@read -p "Confirmer ? [y/N] " confirm && [ "$$confirm" = "y" ]
	$(DOCKER_COMPOSE) down -v
	@echo "Volumes supprimes"

reset-index:
	@echo "Reinitialisation de l'index vectoriel..."
	$(DOCKER_COMPOSE) exec qdrant curl -X DELETE http://localhost:6333/collections/rag_expert
	rm -f $(BACKEND_DIR)/ingestion_tracker.db
	@echo "Index reinitialise"

shell-backend:
	$(DOCKER_COMPOSE) exec backend bash

shell-postgres:
	$(DOCKER_COMPOSE) exec postgres psql -U admin -d chatbot_db

teams-build:
	@echo "Construction du manifest Teams..."
	cd teams-bot && zip -r ../rag-expert-teams.zip teams/ -x "*.DS_Store"
	@echo "Manifest cree : rag-expert-teams.zip"

install-dev:
	cd $(BACKEND_DIR) && pip install -r requirements.txt
	cd $(FRONTEND_DIR) && npm install

dev-backend:
	cd $(BACKEND_DIR) && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd $(FRONTEND_DIR) && npm run dev
