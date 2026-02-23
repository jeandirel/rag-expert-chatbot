# 🚀 Guide de démarrage rapide

Démarrez le chatbot RAG Expert en moins de 15 minutes.

---

## Prérequis

| Outil | Version minimale | Vérification |
|-------|-----------------|--------------|
| Docker | 24+ | `docker --version` |
| Docker Compose | 2.20+ | `docker compose version` |
| Git | 2.40+ | `git --version` |
| RAM disponible | 8 Go minimum, 16 Go recommandé | |
| Espace disque | 20 Go minimum | |

---

## Installation en 5 étapes

### Etape 1 — Cloner le projet

```bash
git clone https://github.com/jeandirel/rag-expert-chatbot.git
cd rag-expert-chatbot
```

### Etape 2 — Créer votre fichier de configuration

```bash
cp .env.example .env
```

Ouvrez `.env` avec votre éditeur et remplissez **au minimum** :

```env
# ── LLM (choisissez UN provider) ────────────────────────────

# Option A : Ollama local (100% gratuit, recommandé pour démarrer)
LLM_PROVIDER=ollama
OLLAMA_MODEL=mistral

# Option B : Groq (gratuit avec compte, très rapide)
# LLM_PROVIDER=groq
# GROQ_API_KEY=votre_cle_groq

# Option C : OpenAI
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...

# ── Sécurité (changez ces valeurs !) ────────────────────────
POSTGRES_PASSWORD=MotDePasseSecurise123!
KEYCLOAK_ADMIN_PASSWORD=AdminSecurise456!
SECRET_KEY=une-longue-chaine-aleatoire-de-32-caracteres-minimum

# ── SharePoint (optionnel pour démarrer) ────────────────────
# SHAREPOINT_SITE_URL=https://votreorg.sharepoint.com/sites/docs
# SHAREPOINT_CLIENT_ID=votre-client-id
# SHAREPOINT_CLIENT_SECRET=votre-secret
# SHAREPOINT_TENANT_ID=votre-tenant-id
```

### Etape 3 — Démarrer la stack

```bash
make start
```

Cela démarre automatiquement :
- Backend FastAPI (port 8000)
- - Frontend React (port 3000)
  - - Qdrant vectorDB (port 6333)
    - - PostgreSQL (port 5432)
      - - Redis (port 6379)
        - - Keycloak SSO (port 8080)
          - - Prometheus + Grafana (ports 9090 / 3001)
           
            - > Premier démarrage : ~5-10 minutes (téléchargement des images Docker)
              >
              > ### Etape 4 — Télécharger le modèle LLM (si Ollama)
              >
              > ```bash
              > # Dans un autre terminal, pendant que Docker démarre
              > make pull-model
              >
              > # Ou manuellement :
              > docker exec -it rag-ollama ollama pull mistral
              > ```
              >
              > ### Etape 5 — Ouvrir le chatbot
              >
              > | Service | URL | Identifiants par défaut |
              > |---------|-----|------------------------|
              > | **Chatbot** | http://localhost:3000 | admin / admin |
              > | **API Docs** | http://localhost:8000/docs | — |
              > | **Admin Dashboard** | http://localhost:3000/admin | admin / admin |
              > | **Keycloak** | http://localhost:8080 | admin / AdminSecurise456! |
              > | **Grafana** | http://localhost:3001 | admin / admin |
              > | **Qdrant UI** | http://localhost:6333/dashboard | — |
              >
              > ---
              >
              > ## Indexer vos premiers documents
              >
              > ### Option A — Upload manuel (interface admin)
              >
              > 1. Allez sur http://localhost:3000/admin
              > 2. 2. Onglet **Documents** → **Uploader un document**
              >    3. 3. Glissez-déposez vos PDF, DOCX, etc.
              >      
              >       4. ### Option B — Dossier local
              >      
              >       5. ```bash
              >          # Copiez vos documents dans le dossier de données
              >          cp /chemin/vers/vos/docs/*.pdf ./data/documents/
              >
              >          # Lancez l'indexation
              >          make index
              >          ```
              >
              > ### Option C — SharePoint (après configuration)
              >
              > ```bash
              > # Configurer d'abord les variables SharePoint dans .env
              > # Voir docs/CONFIGURATION_SHAREPOINT.md
              >
              > make sync-sharepoint
              > ```
              >
              > ---
              >
              > ## Commandes utiles
              >
              > ```bash
              > make start          # Démarrer tous les services
              > make stop           # Arrêter tous les services
              > make restart        # Redémarrer
              > make logs           # Voir les logs en temps réel
              > make status         # Statut des conteneurs
              > make index          # Indexer les documents du dossier data/
              > make sync-sharepoint # Synchroniser depuis SharePoint
              > make test           # Lancer les tests
              > make clean          # Tout supprimer (données incluses !)
              > ```
              >
              > ---
              >
              > ## Configuration SSO Microsoft 365
              >
              > Pour connecter votre annuaire Azure AD :
              > → Suivez le guide **[docs/CONFIGURATION_SSO.md](./CONFIGURATION_SSO.md)**
              >
              > ---
              >
              > ## Configuration SharePoint
              >
              > Pour synchroniser vos 21 Go de documentation :
              > → Suivez le guide **[docs/CONFIGURATION_SHAREPOINT.md](./CONFIGURATION_SHAREPOINT.md)**
              >
              > ---
              >
              > ## Intégration Microsoft Teams
              >
              > Pour déployer le bot dans Teams :
              >
              > 1. Editez `teams-bot/teams/manifest.json` :
              > 2.    - Remplacez `YOUR_FRONTEND_URL` par votre URL réelle
              >       -    - Remplacez `YOUR_FRONTEND_DOMAIN` par votre domaine
              >            -    - Remplacez le `botId` par l'ID de votre Azure Bot Service
              >             
              >                 - 2. Créez le package :
              >                   3.    ```bash
              >                            cd teams-bot/teams
              >                            zip -r rag-expert-teams.zip manifest.json color.png outline.png
              >                            ```
              >
              > 3. Dans Teams Admin Center → **Manage apps** → **Upload an app** → uploadez le zip
              >
              > 4. ---
              >
              > 5. ## Dépannage rapide
              >
              > 6. ### Le frontend ne démarre pas
              >
              > 7. ```bash
              >    make logs | grep frontend
              >    # Vérifiez que le port 3000 est libre
              >    ```
              >
              > ### Ollama ne répond pas
              >
              > ```bash
              > docker exec -it rag-ollama ollama list
              > # Si vide, re-télécharger le modèle :
              > docker exec -it rag-ollama ollama pull mistral
              > ```
              >
              > ### Keycloak : impossible de se connecter
              >
              > ```bash
              > # Vérifier que Keycloak est démarré
              > docker ps | grep keycloak
              > # Voir les logs
              > docker logs rag-keycloak --tail 50
              > ```
              >
              > ### Qdrant : collection non trouvée
              >
              > ```bash
              > # Initialiser la collection
              > curl -X PUT http://localhost:6333/collections/rag-documents \
              >   -H "Content-Type: application/json" \
              >   -d '{"vectors": {"size": 768, "distance": "Cosine"}}'
              > ```
              >
              > ---
              >
              > ## Architecture des services
              >
              > ```
              > ┌─────────────────────────────────────────────────┐
              > │                  Utilisateur                     │
              > └─────────────────────┬───────────────────────────┘
              >                       │ HTTPS
              > ┌─────────────────────▼───────────────────────────┐
              > │           Frontend React (port 3000)             │
              > │    Chat UI | PDF Viewer | Admin Dashboard        │
              > └─────────────────────┬───────────────────────────┘
              >                       │ REST / SSE
              > ┌─────────────────────▼───────────────────────────┐
              > │           Backend FastAPI (port 8000)            │
              > │    RAG Service | LLM Service | MCP Server        │
              > └──────┬──────────────┬──────────────┬────────────┘
              >        │              │              │
              > ┌──────▼───┐   ┌──────▼───┐  ┌──────▼───┐
              > │  Qdrant  │   │  Redis   │  │ Postgres │
              > │ (vecteurs│   │  (cache  │  │ (stats   │
              > │  6333)   │   │   6379)  │  │  5432)   │
              > └──────────┘   └──────────┘  └──────────┘
              > ```
              >
              > ---
              >
              > ## Liens utiles
              >
              > - 📖 [README complet](../README.md)
              > - - 🔐 [Configuration SSO](./CONFIGURATION_SSO.md)
              >   - - 📂 [Configuration SharePoint](./CONFIGURATION_SHAREPOINT.md)
              >     - - 🐛 [Signaler un bug](https://github.com/jeandirel/rag-expert-chatbot/issues)
              >       - 
