# 🤖 RAG Expert Chatbot

> Chatbot RAG Expert Métiers — 100% Open Source — Zéro coût d'infrastructure
>
> [![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
> [![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com)
> [![React](https://img.shields.io/badge/React-18+-61dafb.svg)](https://reactjs.org)
> [![LangChain](https://img.shields.io/badge/LangChain-0.2+-yellow.svg)](https://langchain.com)
> [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
> [![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](docker-compose.yml)
>
> ---
>
> ## 🎯 Vue d'ensemble
>
> Chatbot RAG (Retrieval-Augmented Generation) expert métiers, conçu pour indexer et interroger une documentation d'entreprise volumineuse (testé sur 21 Go SharePoint).
>
> **Stack technique :**
> - LLM : Ollama (Mistral 7B local) ou Groq/Gemini (API gratuite)
> - - Recherche vectorielle : Qdrant + embeddings nomic-embed-text
>   - - Parsing documents : Unstructured.io (PDF, Word, Excel, PowerPoint, images OCR)
>     - - Backend : FastAPI + LangChain + Python 3.11
>       - - Frontend : React 18 + TypeScript + TailwindCSS
>         - - Auth SSO : Keycloak (OpenID Connect)
>           - - Base de données : PostgreSQL + Redis
>             - - Monitoring : Grafana + Prometheus
>               - - Teams : Bot Framework SDK
>                 - - MCP : Model Context Protocol Server
>                  
>                   - ---
>
> ## Fonctionnalités
>
> ### Chat
> - Reponses en streaming temps reel (comme ChatGPT)
> - - Rendu Markdown complet (code, tableaux, listes)
>   - - Sources citees et cliquables avec PDF Viewer integre
>     - - Historique des conversations avec recherche
>       - - Memoire conversationnelle contextuelle (reformulation auto)
>         - - Feedback par message
>           - - Regeneration de reponse / Stop generation
>             - - Copie en un clic / Export conversation
>               - - Indicateur de confiance (haute/moyenne/faible)
>                
>                 - ### Documents
>                 - - Sync automatique SharePoint (webhooks + cron 4h)
>                   - - Support : PDF, Word, Excel, PowerPoint, images (OCR), emails
>                     - - PDF Viewer integre avec surbrillance des passages sources
>                       - - Detection automatique de categorie et departement
>                         - - Reindexation incrementale (seulement les fichiers modifies)
>                          
>                           - ### Admin Dashboard
>                           - - Stats temps reel : requetes, temps de reponse, satisfaction
>                             - - Vue toutes les conversations
>                               - - Top questions posees
>                                 - - Documents les plus consultes
>                                   - - Gestion documents (upload, reindexation)
>                                     - - Export CSV/Excel
>                                       - - Gestion utilisateurs et roles
>                                        
>                                         - ### Integrations
>                                         - - Microsoft Teams (bot + onglet integre)
>                                           - - MCP Server (Claude Desktop, Cursor, etc.)
>                                             - - API REST complete (Swagger UI)
>                                               - - Webhooks SharePoint temps reel
>                                                
>                                                 - ---
>
> ## Demarrage rapide (30 minutes)
>
> ```bash
> # 1. Cloner
> git clone https://github.com/jeandirel/rag-expert-chatbot.git
> cd rag-expert-chatbot
>
> # 2. Configurer
> cp .env.example .env
>
> # 3. Lancer la stack
> docker compose up -d
>
> # 4. Installer Ollama et les modeles
> curl -fsSL https://ollama.ai/install.sh | sh
> ollama pull mistral
> ollama pull nomic-embed-text
>
> # 5. Indexer vos documents
> cp /votre/dossier/*.pdf ./documents/
> cd backend && python -m ingestion.pipeline
>
> # 6. Ouvrir http://localhost:3000
> ```
>
> | Service | URL |
> |---------|-----|
> | Chatbot | http://localhost:3000 |
> | Admin | http://localhost:3000/admin |
> | API Docs | http://localhost:8000/api/docs |
> | Keycloak | http://localhost:8080 |
> | Grafana | http://localhost:3001 |
>
> ---
>
> ## Structure du projet
>
> ```
> rag-expert-chatbot/
> ├── backend/          # API FastAPI (Python 3.11)
> │   ├── app/
> │   │   ├── main.py
> │   │   ├── api/v1/   # chat, admin, documents, webhooks
> │   │   ├── core/     # config, auth, database
> │   │   ├── services/ # rag, llm, search, memory, cache
> │   │   ├── models/   # SQLAlchemy models
> │   │   └── mcp/      # MCP Server
> │   ├── ingestion/    # Pipeline indexation documents
> │   └── tests/        # Unit + Integration + RAGAS
> ├── frontend/         # React 18 + TypeScript + Tailwind
> │   └── src/
> │       ├── components/ # Chat, PDFViewer, Admin, Auth
> │       ├── hooks/      # useChat (streaming SSE), useAdmin
> │       └── store/      # Zustand
> ├── teams-bot/        # Bot Microsoft Teams
> ├── infra/            # Docker Compose + Keycloak + Grafana
> ├── .github/workflows/ # CI/CD GitHub Actions
> └── docs/             # Documentation complete
> ```
>
> ---
>
> ## Licence
>
> MIT — voir LICENSE
>
> *Stack 100% open source — Aucune donnee envoyee a des tiers si LLM local*
