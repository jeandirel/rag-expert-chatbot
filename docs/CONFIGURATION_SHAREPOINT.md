# 📂 Configuration SharePoint — Connexion et Synchronisation

Ce guide explique comment connecter votre SharePoint (21 Go de documentation métier)
au chatbot RAG pour l'indexation et la synchronisation automatique.

> ⚠️ **Sécurité** : Tous les secrets doivent rester dans votre fichier `.env` local,
> > jamais dans le code source ou dans Git.
> >
> > ---
> >
> > ## Prérequis
> >
> > - Accès administrateur à votre tenant Azure AD
> > - - Accès administrateur au site SharePoint cible
> >   - - PowerShell ou Azure CLI (optionnel, pour certaines étapes)
> >    
> >     - ---
> >
> > ## Etape 1 — Créer l'App Registration Azure AD pour SharePoint
> >
> > > Si vous avez déjà une App Registration pour le SSO, vous pouvez utiliser
> > > > la même app en ajoutant les permissions SharePoint, ou créer une app dédiée.
> > > >
> > > > ### 1.1 Créer une nouvelle App Registration
> > > >
> > > > 1. [portail Azure](https://portal.azure.com) → **Azure Active Directory** → **App registrations** → **New registration**
> > > > 2. 2. Remplissez :
> > > >    3.    - **Name** : `RAG Chatbot SharePoint Sync`
> > > >          -    - **Supported account types** : `Accounts in this organizational directory only`
> > > >               -    - **Redirect URI** : laissez vide (application non interactive)
> > > >                    - 3. Cliquez **Register**
> > > >                     
> > > >                      4. ### 1.2 Récupérer les identifiants
> > > >                     
> > > >                      5. Sur la page **Overview**, notez :
> > > >                      6. ```
> > > >                         Application (client) ID  → SHAREPOINT_CLIENT_ID
> > > > Directory (tenant) ID    → SHAREPOINT_TENANT_ID
> > > > ```
> > > >
> > > > ### 1.3 Créer le Client Secret
> > > >
> > > > 1. Menu gauche → **Certificates & secrets** → **New client secret**
> > > > 2. Description : `sharepoint-sync`
> > > > 3. Expiration : selon votre politique (max 24 mois)
> > > > 4. Cliquez **Add** → **copiez immédiatement** la valeur → `SHAREPOINT_CLIENT_SECRET`
> > > >
> > > > ---
> > > >
> > > > ## Etape 2 — Configurer les permissions SharePoint
> > > >
> > > > ### 2.1 Ajouter les permissions API
> > > >
> > > > 1. Menu gauche → **API permissions** → **Add a permission**
> > > > 2. Sélectionnez **SharePoint**
> > > > 3. **Application permissions** (pas Delegated) → ajoutez :
> > > >    - `Sites.Read.All` — Lire tous les sites SharePoint
> > > >    - `Files.Read.All` — Lire tous les fichiers
> > > > 4. Cliquez **Add permissions**
> > > >
> > > > 5. Optionnel — Pour accéder aussi via Microsoft Graph :
> > > >    - **Microsoft Graph** → **Application permissions** → ajoutez :
> > > >    - `Sites.Read.All`
> > > >    - `Files.Read.All`
> > > >
> > > > 6. Cliquez **Grant admin consent for [votre organisation]**
> > > >    (nécessite d'être administrateur du tenant)
> > > >
> > > > ### 2.2 Vérifier les permissions accordées
> > > >
> > > > Les permissions doivent toutes avoir le statut **Granted** (coche verte).
> > > >
> > > > ---
> > > >
> > > > ## Etape 3 — Trouver l'URL de votre site SharePoint
> > > >
> > > > ### Option A — Via le navigateur
> > > >
> > > > Naviguez vers votre site SharePoint et copiez l'URL jusqu'au nom du site :
> > > > ```
> > > > https://VOTRE_ORG.sharepoint.com/sites/NOM_DU_SITE
> > > > ```
> > > >
> > > > ### Option B — Via PowerShell
> > > >
> > > > ```powershell
> > > > Connect-PnPOnline -Url "https://VOTRE_ORG.sharepoint.com" -Interactive
> > > > Get-PnPTenantSite | Select Title, Url
> > > > ```
> > > >
> > > > ### Option C — Via Microsoft Graph API
> > > >
> > > > ```bash
> > > > curl -H "Authorization: Bearer TOKEN" \
> > > >   "https://graph.microsoft.com/v1.0/sites?search=*"
> > > > ```
> > > >
> > > > ---
> > > >
> > > > ## Etape 4 — Variables d'environnement
> > > >
> > > > Ajoutez ces variables dans votre fichier `.env` **local** :
> > > >
> > > > ```env
> > > > # ── SharePoint ──────────────────────────────────────────────
> > > > SHAREPOINT_SITE_URL=https://VOTRE_ORG.sharepoint.com/sites/NOM_DU_SITE
> > > > SHAREPOINT_CLIENT_ID=VOTRE_APPLICATION_CLIENT_ID
> > > > SHAREPOINT_CLIENT_SECRET=VOTRE_CLIENT_SECRET
> > > > SHAREPOINT_TENANT_ID=VOTRE_TENANT_ID
> > > >
> > > > # Bibliothèques à synchroniser (séparées par virgule)
> > > > SHAREPOINT_LIBRARIES=Documents,Procedures,Normes
> > > >
> > > > # Interval de synchro automatique (en secondes, 0 = désactivé)
> > > > SHAREPOINT_SYNC_INTERVAL=3600
> > > > ```
> > > >
> > > > ---
> > > >
> > > > ## Etape 5 — Lancer la synchronisation
> > > >
> > > > ### 5.1 Première synchronisation (indexation complète)
> > > >
> > > > ```bash
> > > > # Depuis la racine du projet
> > > > make sync-sharepoint
> > > >
> > > > # Ou directement avec Python
> > > > cd backend
> > > > python -m ingestion.sync_sharepoint --force
> > > > ```
> > > >
> > > > Cela va :
> > > > 1. Se connecter à SharePoint via l'API REST
> > > > 2. 2. Lister récursivement tous les fichiers des bibliothèques configurées
> > > >    3. 3. Télécharger chaque fichier dans un dossier temporaire
> > > >       4. 4. Extraire le texte via Unstructured.io
> > > >          5. 5. Découper en chunks et calculer les embeddings
> > > >             6. 6. Indexer dans Qdrant avec les métadonnées SharePoint
> > > >               
> > > >                7. ### 5.2 Synchronisation d'une seule bibliothèque
> > > >               
> > > >                8. ```bash
> > > >                   python -m ingestion.sync_sharepoint --library "Documents"
> > > >                   python -m ingestion.sync_sharepoint --library "Procedures" --force
> > > >                   ```
> > > >
> > > > ### 5.3 Synchronisation automatique (cron)
> > > >
> > > > Le service d'ingestion dans Docker Compose surveille automatiquement
> > > > les changements si `SHAREPOINT_SYNC_INTERVAL > 0`.
> > > >
> > > > Vous pouvez aussi configurer un cron :
> > > > ```bash
> > > > # Toutes les heures
> > > > 0 * * * * cd /app && python -m ingestion.sync_sharepoint >> /var/log/sync.log 2>&1
> > > >
> > > > # Toutes les nuits à 2h
> > > > 0 2 * * * cd /app && python -m ingestion.sync_sharepoint --force >> /var/log/sync.log 2>&1
> > > > ```
> > > >
> > > > ---
> > > >
> > > > ## Etape 6 — Extensions de fichiers supportées
> > > >
> > > > Le pipeline d'ingestion supporte ces formats :
> > > >
> > > > | Format | Extension | Notes |
> > > > |--------|-----------|-------|
> > > > | PDF | `.pdf` | Avec extraction des pages |
> > > > | Word | `.docx`, `.doc` | Incluant les tableaux |
> > > > | Excel | `.xlsx`, `.xls` | Toutes les feuilles |
> > > > | PowerPoint | `.pptx`, `.ppt` | Texte des slides |
> > > > | Texte | `.txt`, `.md` | Direct |
> > > > | HTML | `.html`, `.htm` | Extraction du contenu |
> > > > | Email | `.eml`, `.msg` | Corps et métadonnées |
> > > > | CSV | `.csv` | En tableau |
> > > >
> > > > ---
> > > >
> > > > ## Etape 7 — Vérification
> > > >
> > > > ### Vérifier les documents indexés
> > > >
> > > > Via l'interface admin du chatbot :
> > > > 1. Ouvrez `http://localhost:3000/admin`
> > > > 2. 2. Onglet **Documents** → vous voyez la liste des fichiers indexés
> > > >   
> > > >    3. Via l'API :
> > > >    4. ```bash
> > > >       curl -H "Authorization: Bearer TOKEN" \
> > > >         http://localhost:8000/api/v1/documents/?source=sharepoint
> > > >       ```
> > > >
> > > > ### Vérifier les stats Qdrant
> > > >
> > > > ```bash
> > > > # Nombre total de chunks indexés
> > > > curl http://localhost:6333/collections/rag-documents
> > > > ```
> > > >
> > > > ### Tester une recherche
> > > >
> > > > ```bash
> > > > curl -X POST \
> > > >   -H "Authorization: Bearer TOKEN" \
> > > >   -H "Content-Type: application/json" \
> > > >   -d '{"query": "procédure de validation", "top_k": 5}' \
> > > >   http://localhost:8000/api/v1/documents/search
> > > > ```
> > > >
> > > > ---
> > > >
> > > > ## Etape 8 — Pour 21 Go de documentation
> > > >
> > > > Votre volume de 21 Go nécessite quelques ajustements de configuration :
> > > >
> > > > ### Temps d'indexation estimé
> > > >
> > > > | Volume | Temps estimé | Chunks attendus |
> > > > |--------|-------------|-----------------|
> > > > | 1 Go | ~30 min | ~50 000 |
> > > > | 5 Go | ~2h30 | ~250 000 |
> > > > | 21 Go | ~10-12h | ~1 000 000+ |
> > > >
> > > > ### Optimisations recommandées
> > > >
> > > > ```env
> > > > # Augmenter le batch size pour l'indexation
> > > > QDRANT_BATCH_SIZE=200
> > > >
> > > > # Paralléliser l'extraction (workers)
> > > > INGESTION_WORKERS=4
> > > >
> > > > # Augmenter la mémoire Qdrant (dans docker-compose.yml)
> > > > # QDRANT__STORAGE__ON_DISK_PAYLOAD=true
> > > > ```
> > > >
> > > > ### Indexation en plusieurs passes
> > > >
> > > > ```bash
> > > > # Bibliothèque par bibliothèque pour mieux contrôler
> > > > python -m ingestion.sync_sharepoint --library "Procedures"
> > > > python -m ingestion.sync_sharepoint --library "Normes"
> > > > python -m ingestion.sync_sharepoint --library "Documents"
> > > > ```
> > > >
> > > > ---
> > > >
> > > > ## Dépannage
> > > >
> > > > ### Erreur "Access Denied" lors de la connexion
> > > >
> > > > → Vérifiez que les permissions `Sites.Read.All` ont bien été accordées
> > > >   avec **Grant admin consent**.
> > > >
> > > > ### Erreur "Site not found"
> > > >
> > > > → Vérifiez l'URL du site : elle doit se terminer par le nom du site, pas par une page.
> > > >   ✅ `https://org.sharepoint.com/sites/MonSite`
> > > >   ❌ `https://org.sharepoint.com/sites/MonSite/Documents/Forms/AllItems.aspx`
> > > >
> > > > ### Fichiers non téléchargés
> > > >
> > > > → Vérifiez que l'extension est dans `SUPPORTED_EXTENSIONS` dans `sync_sharepoint.py`.
> > > >
> > > > ### Indexation lente
> > > >
> > > > → Activez `INGESTION_WORKERS=4` et assurez-vous que Ollama tourne sur GPU si possible.
> > > >
> > > > ### Erreur de mémoire avec les gros fichiers PDF
> > > >
> > > > → Ajoutez dans `.env` :
> > > > ```env
> > > > UNSTRUCTURED_MAX_PAGES=500
> > > > CHUNK_SIZE=1000
> > > > CHUNK_OVERLAP=200
> > > > ```
> > > >
> > > > ---
> > > >
> > > > ## Ressources
> > > >
> > > > - [SharePoint REST API](https://learn.microsoft.com/en-us/sharepoint/dev/sp-add-ins/get-to-know-the-sharepoint-rest-service)
> > > > - - [Office365-REST-Python-Client](https://github.com/vgrem/Office365-REST-Python-Client)
> > > >   - - [Microsoft Graph Files API](https://learn.microsoft.com/en-us/graph/api/resources/onedrive)
> > > >     - 
