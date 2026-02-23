# 🔌 MCP SharePoint — Intégration prête à l'emploi

Ce projet intègre le serveur MCP SharePoint communautaire **Sofias-ai/mcp-sharepoint**,
le plus complet et le plus maintenu disponible en 2025.

> Source : https://github.com/Sofias-ai/mcp-sharepoint
> > Licence : MIT | Langage : Python | Install : `pip install mcp-sharepoint-server`
> >
> > ---
> >
> > ## Qu'est-ce que MCP ?
> >
> > MCP (Model Context Protocol) est un protocole standard créé par Anthropic qui permet
> > à un LLM (Claude, GPT, Mistral...) d'appeler des outils externes de façon standardisée.
> >
> > ```
> > LLM (Claude/Mistral)
> >     │  "Liste les documents dans /Procedures"
> >     ▼
> > MCP Server SharePoint   ← pip install mcp-sharepoint-server
> >     │  Graph API call
> >     ▼
> > SharePoint Online
> >     │  Retourne la liste
> >     ▼
> > LLM reçoit les résultats et répond à l'utilisateur
> > ```
> >
> > ---
> >
> > ## Les 10 outils disponibles
> >
> > | Outil | Description |
> > |-------|-------------|
> > | `List_SharePoint_Folders` | Lister les dossiers d'un répertoire |
> > | `List_SharePoint_Documents` | Lister les documents avec métadonnées |
> > | `Get_Document_Content` | Extraire le texte (PDF/DOCX/XLSX/TXT/HTML) |
> > | `Upload_Document` | Uploader un document (texte ou binaire) |
> > | `Upload_Document_From_Path` | Uploader depuis un fichier local |
> > | `Update_Document` | Mettre à jour un document existant |
> > | `Delete_Document` | Supprimer un document |
> > | `Create_Folder` | Créer un dossier |
> > | `Delete_Folder` | Supprimer un dossier vide |
> > | `Get_SharePoint_Tree` | Arborescence complète récursive |
> >
> > ---
> >
> > ## Installation
> >
> > ### Option A — Avec Docker Compose (recommandé)
> >
> > ```bash
> > # Démarrer avec le MCP SharePoint activé
> > docker compose -f infra/docker-compose.yml -f infra/docker-compose.mcp.yml up -d
> >
> > # Vérifier que le service est bien démarré
> > docker ps | grep mcp-sharepoint
> > docker logs rag-mcp-sharepoint --tail 20
> > ```
> >
> > Variables requises dans votre `.env` :
> > ```env
> > SHAREPOINT_CLIENT_ID=votre-client-id
> > SHAREPOINT_CLIENT_SECRET=votre-client-secret
> > SHAREPOINT_TENANT_ID=votre-tenant-id
> > SHAREPOINT_SITE_URL=https://votreorg.sharepoint.com/sites/NomDuSite
> > SHAREPOINT_DOC_LIBRARY=Shared Documents
> > ```
> >
> > ### Option B — Installation directe (dev local)
> >
> > ```bash
> > # Installer le serveur MCP SharePoint
> > pip install mcp-sharepoint-server
> >
> > # Tester la connexion
> > python backend/app/mcp/sharepoint_mcp_client.py
> > ```
> >
> > ### Option C — Claude Desktop (usage personnel)
> >
> > Ajoutez dans `~/.config/claude/claude_desktop_config.json` :
> > ```json
> > {
> >   "mcpServers": {
> >     "sharepoint": {
> >       "command": "mcp-sharepoint",
> >       "env": {
> >         "SHP_ID_APP": "votre-client-id",
> >         "SHP_ID_APP_SECRET": "votre-client-secret",
> >         "SHP_SITE_URL": "https://votreorg.sharepoint.com/sites/NomDuSite",
> >         "SHP_DOC_LIBRARY": "Shared Documents",
> >         "SHP_TENANT_ID": "votre-tenant-id"
> >       }
> >     }
> >   }
> > }
> > ```
> >
> > ---
> >
> > ## Utilisation dans le chatbot RAG
> >
> > ### Via l'API REST
> >
> > ```bash
> > # Lister les documents SharePoint via le chatbot
> > curl -X POST http://localhost:8000/api/v1/mcp/call \
> >   -H "Authorization: Bearer TOKEN" \
> >   -H "Content-Type: application/json" \
> >   -d '{
> >     "tool": "List_SharePoint_Documents",
> >     "arguments": {"folder_path": "Procedures/2024"}
> >   }'
> >
> > # Lire le contenu d'un document
> > curl -X POST http://localhost:8000/api/v1/mcp/call \
> >   -H "Authorization: Bearer TOKEN" \
> >   -H "Content-Type: application/json" \
> >   -d '{
> >     "tool": "Get_Document_Content",
> >     "arguments": {"file_path": "Documents/rapport_annuel.pdf"}
> >   }'
> >
> > # Arborescence complète
> > curl -X POST http://localhost:8000/api/v1/mcp/call \
> >   -H "Authorization: Bearer TOKEN" \
> >   -H "Content-Type: application/json" \
> >   -d '{
> >     "tool": "Get_SharePoint_Tree",
> >     "arguments": {"root_path": "", "max_depth": 3}
> >   }'
> > ```
> >
> > ### Via le chat (questions naturelles)
> >
> > Le LLM peut appeler les outils MCP automatiquement quand vous posez des questions :
> >
> > > "Quels documents PDF sont disponibles dans le dossier Procédures ?"
> > > > → appelle `List_SharePoint_Documents` avec `folder_path="Procedures"`
> > > >
> > > > > "Montre-moi le contenu du fichier norme_qualite.docx"
> > > > > > → appelle `Get_Document_Content` avec `file_path="Documents/norme_qualite.docx"`
> > > > > >
> > > > > > > "Quelle est l'arborescence de notre SharePoint ?"
> > > > > > > > → appelle `Get_SharePoint_Tree`
> > > > > > > >
> > > > > > > > ---
> > > > > > > >
> > > > > > > > ## Architecture d'intégration
> > > > > > > >
> > > > > > > > ```
> > > > > > > > ┌──────────────────────────────────────────────────────────┐
> > > > > > > > │                   Chatbot RAG Expert                     │
> > > > > > > > │                                                          │
> > > > > > > > │  ┌─────────────────┐     ┌────────────────────────────┐  │
> > > > > > > > │  │  FastAPI Backend │ ←── │  sharepoint_mcp_client.py  │  │
> > > > > > > > │  │  /api/v1/mcp/   │     │  (client MCP Python)       │  │
> > > > > > > > │  └─────────────────┘     └────────────┬───────────────┘  │
> > > > > > > > │                                       │ stdio/subprocess  │
> > > > > > > > └───────────────────────────────────────┼──────────────────┘
> > > > > > > >                                         │
> > > > > > > >                           ┌─────────────▼─────────────┐
> > > > > > > >                           │  mcp-sharepoint-server     │
> > > > > > > >                           │  (Sofias-ai, pip install)  │
> > > > > > > >                           │  10 outils MCP             │
> > > > > > > >                           └─────────────┬─────────────┘
> > > > > > > >                                         │ HTTPS / Graph API
> > > > > > > >                           ┌─────────────▼─────────────┐
> > > > > > > >                           │  SharePoint Online         │
> > > > > > > >                           │  (21 Go de documentation)  │
> > > > > > > >                           └───────────────────────────┘
> > > > > > > > ```
> > > > > > > >
> > > > > > > > ---
> > > > > > > >
> > > > > > > > ## Différence avec la synchronisation classique
> > > > > > > >
> > > > > > > > | | Sync Qdrant (sync_sharepoint.py) | MCP SharePoint |
> > > > > > > > |-|----------------------------------|----------------|
> > > > > > > > | **Usage** | Indexation en batch | Accès temps réel |
> > > > > > > > | **Vitesse** | Lent (traitement offline) | Rapide (on-demand) |
> > > > > > > > | **Cas d'usage** | Recherche sémantique RAG | Navigation, lecture directe |
> > > > > > > > | **Données** | Chunks dans Qdrant | Documents originaux |
> > > > > > > > | **Quand utiliser** | Toujours (base RAG) | En complément |
> > > > > > > >
> > > > > > > > **Les deux sont complémentaires** :
> > > > > > > > - La synchro Qdrant permet la **recherche sémantique** dans 21 Go de docs
> > > > > > > > - - Le MCP permet d'**accéder directement** à un document spécifique en temps réel
> > > > > > > >  
> > > > > > > >   - ---
> > > > > > > >
> > > > > > > > ## Autres MCP SharePoint disponibles
> > > > > > > >
> > > > > > > > Si vous souhaitez évaluer d'autres options :
> > > > > > > >
> > > > > > > > | Repo | Stars | Langage | Points forts |
> > > > > > > > |------|-------|---------|-------------|
> > > > > > > > | [Sofias-ai/mcp-sharepoint](https://github.com/Sofias-ai/mcp-sharepoint) | 61 | Python | **10 outils, pip installable, support binaire** |
> > > > > > > > | [DEmodoriGatsuO/sharepoint-mcp](https://github.com/DEmodoriGatsuO/sharepoint-mcp) | 42 | Python | Graph API, diagnostic tools |
> > > > > > > > | [Zerg00s/server-sharepoint](https://github.com/Zerg00s/server-sharepoint) | 23 | TypeScript | Claude Desktop, REST API |
> > > > > > > > | [BrianCusack/mcpsharepoint](https://github.com/BrianCusack/mcpsharepoint) | 21 | TypeScript | SharePoint organisationnel |
> > > > > > > >
> > > > > > > > ---
> > > > > > > >
> > > > > > > > ## Dépannage
> > > > > > > >
> > > > > > > > ### "ModuleNotFoundError: No module named 'mcp_sharepoint'"
> > > > > > > >
> > > > > > > > ```bash
> > > > > > > > pip install mcp-sharepoint-server
> > > > > > > > # ou
> > > > > > > > pip install git+https://github.com/Sofias-ai/mcp-sharepoint.git
> > > > > > > > ```
> > > > > > > >
> > > > > > > > ### "Authentication failed"
> > > > > > > >
> > > > > > > > Vérifiez que votre App Registration Azure AD a les permissions :
> > > > > > > > - `Sites.Read.All` (Application)
> > > > > > > > - - `Files.Read.All` (Application)
> > > > > > > >   - - Admin consent accordé
> > > > > > > >    
> > > > > > > >     - ### "Site not found"
> > > > > > > >    
> > > > > > > >     - L'URL doit être exactement : `https://TENANT.sharepoint.com/sites/NOM_SITE`
> > > > > > > >     - (sans slash final, sans page supplémentaire)
> > > > > > > >    
> > > > > > > >     - ### Le serveur MCP plante au démarrage Docker
> > > > > > > >
> > > > > > > > ```bash
> > > > > > > > docker logs rag-mcp-sharepoint --tail 50
> > > > > > > > # Vérifier les variables d'environnement
> > > > > > > > docker exec rag-mcp-sharepoint env | grep SHP_
> > > > > > > > ```
> > > > > > > > 
