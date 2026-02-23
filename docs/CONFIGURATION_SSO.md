# 🔐 Configuration SSO — Azure AD + Keycloak

Ce guide explique comment configurer l'authentification SSO (Single Sign-On)
avec votre compte Microsoft Azure AD / Microsoft 365 d'entreprise.

> ⚠️ **Important** : Ne commitez JAMAIS vos secrets dans Git.
> > Utilisez uniquement le fichier `.env` local (qui est dans `.gitignore`).
> >
> > ---
> >
> > ## Vue d'ensemble de l'architecture SSO
> >
> > ```
> > Utilisateur
> >     │
> >     ▼
> > React Frontend
> >     │  Redirige vers Keycloak
> >     ▼
> > Keycloak (Identity Broker)
> >     │  Federe vers Azure AD
> >     ▼
> > Azure Active Directory (Microsoft 365)
> >     │  Authentifie l'utilisateur
> >     ▼
> > Token JWT retourne au Frontend
> >     │
> >     ▼
> > FastAPI Backend (valide le token JWT)
> > ```
> >
> > ---
> >
> > ## Etape 1 — Enregistrer l'application dans Azure AD
> >
> > ### 1.1 Créer l'App Registration
> >
> > 1. Connectez-vous au [portail Azure](https://portal.azure.com)
> > 2. 2. Allez dans **Azure Active Directory** → **App registrations** → **New registration**
> >    3. 3. Remplissez :
> >       4.    - **Name** : `RAG Expert Chatbot`
> >             -    - **Supported account types** : `Accounts in this organizational directory only`
> >                  -    - **Redirect URI** : `Web` → `https://VOTRE_KEYCLOAK_URL/realms/rag-chatbot/broker/microsoft/endpoint`
> >                       - 4. Cliquez **Register**
> >                        
> >                         5. ### 1.2 Noter les identifiants
> >                        
> >                         6. Après création, notez ces valeurs (page Overview) :
> >                         7. ```
> >                            Application (client) ID  → votre AZURE_CLIENT_ID
> > Directory (tenant) ID    → votre AZURE_TENANT_ID
> > ```
> >
> > ### 1.3 Créer un Client Secret
> >
> > 1. Menu gauche → **Certificates & secrets** → **New client secret**
> > 2. Description : `keycloak-sso`
> > 3. Expiration : `24 months` (ou selon votre politique)
> > 4. Cliquez **Add**
> > 5. **Copiez immédiatement la valeur** (elle n'est visible qu'une fois) → `AZURE_CLIENT_SECRET`
> >
> > ### 1.4 Configurer les permissions API
> >
> > 1. Menu gauche → **API permissions** → **Add a permission**
> > 2. **Microsoft Graph** → **Delegated permissions** → ajoutez :
> >    - `email`
> >    - `openid`
> >    - `profile`
> >    - `User.Read`
> > 3. Cliquez **Grant admin consent** (nécessite droits admin)
> >
> > ### 1.5 Configurer les Redirect URIs supplémentaires
> >
> > 1. Menu gauche → **Authentication**
> > 2. Ajoutez dans **Redirect URIs** :
> >    ```
> >    https://VOTRE_KEYCLOAK_URL/realms/rag-chatbot/broker/microsoft/endpoint
> >    http://localhost:8080/realms/rag-chatbot/broker/microsoft/endpoint
> >    ```
> >    3. Cochez **ID tokens** et **Access tokens** dans Implicit grant
> >    4. Sauvegardez
> >
> >    ---
> >
> >    ## Etape 2 — Configurer Keycloak
> >
> >    ### 2.1 Accéder à Keycloak
> >
> >    Une fois Docker Compose démarré (`make start`), Keycloak est accessible sur :
> >    ```
> >    http://localhost:8080
> > ```
> >
> > Identifiants admin par défaut (voir `.env`) :
> > ```
> > KEYCLOAK_ADMIN=admin
> > KEYCLOAK_ADMIN_PASSWORD=VotreMotDePasseAdmin
> > ```
> >
> > ### 2.2 Créer le Realm
> >
> > 1. Cliquez sur le menu déroulant **master** (haut gauche) → **Create Realm**
> > 2. **Realm name** : `rag-chatbot`
> > 3. **Enabled** : ON
> > 4. Cliquez **Create**
> >
> > ### 2.3 Ajouter Azure AD comme Identity Provider
> >
> > 1. Dans le realm `rag-chatbot` → menu gauche → **Identity Providers**
> > 2. Cliquez **Add provider** → **Microsoft**
> > 3. Configurez :
> >
> > | Champ | Valeur |
> > |-------|--------|
> > | Alias | `microsoft` |
> > | Display Name | `Connexion Microsoft` |
> > | Client ID | `AZURE_CLIENT_ID` (depuis étape 1.2) |
> > | Client Secret | `AZURE_CLIENT_SECRET` (depuis étape 1.3) |
> > | Default Scopes | `openid email profile` |
> >
> > 4. **Tenant** : entrez votre `AZURE_TENANT_ID`
> > 5. Cliquez **Save**
> >
> > ### 2.4 Créer le Client pour le Frontend
> >
> > 1. Menu gauche → **Clients** → **Create client**
> > 2. Configurez :
> >
> > | Champ | Valeur |
> > |-------|--------|
> > | Client type | `OpenID Connect` |
> > | Client ID | `rag-frontend` |
> > | Name | `RAG Expert Frontend` |
> >
> > 3. Cliquez **Next**, puis :
> >
> > | Champ | Valeur |
> > |-------|--------|
> > | Client authentication | OFF (public client) |
> > | Authorization | OFF |
> > | Standard flow | ON |
> > | Direct access grants | OFF |
> >
> > 4. Cliquez **Next**, puis configurez les URLs :
> >
> > | Champ | Valeur |
> > |-------|--------|
> > | Root URL | `http://localhost:3000` |
> > | Home URL | `http://localhost:3000` |
> > | Valid redirect URIs | `http://localhost:3000/*` et `https://VOTRE_DOMAINE/*` |
> > | Valid post logout redirect URIs | `http://localhost:3000` |
> > | Web origins | `http://localhost:3000` et `https://VOTRE_DOMAINE` |
> >
> > 5. Cliquez **Save**
> >
> > ### 2.5 Créer le Client pour le Backend (optionnel)
> >
> > 1. Menu gauche → **Clients** → **Create client**
> > 2. **Client ID** : `rag-backend`
> > 3. **Client authentication** : ON (confidential)
> > 4. Après création → onglet **Credentials** → notez le `Client Secret`
> >
> > ### 2.6 Configurer les rôles
> >
> > 1. Menu gauche → **Realm roles** → **Create role**
> > 2. Créez ces deux rôles :
> >    - `user` — accès au chat
> >    - `admin` — accès au dashboard admin
> >
> > 3. Pour assigner un rôle admin à un utilisateur :
> >    - Menu gauche → **Users** → sélectionnez l'utilisateur
> >    - Onglet **Role mapping** → **Assign role** → sélectionnez `admin`
> >
> > ---
> >
> > ## Etape 3 — Variables d'environnement
> >
> > ### Fichier `.env` (backend)
> >
> > ```env
> > # ── Azure AD ────────────────────────────────────────────────
> > AZURE_TENANT_ID=VOTRE_TENANT_ID
> > AZURE_CLIENT_ID=VOTRE_CLIENT_ID
> > AZURE_CLIENT_SECRET=VOTRE_CLIENT_SECRET
> >
> > # ── Keycloak ────────────────────────────────────────────────
> > KEYCLOAK_URL=http://localhost:8080
> > KEYCLOAK_REALM=rag-chatbot
> > KEYCLOAK_CLIENT_ID=rag-backend
> > KEYCLOAK_CLIENT_SECRET=VOTRE_SECRET_BACKEND_CLIENT
> > KEYCLOAK_ADMIN=admin
> > KEYCLOAK_ADMIN_PASSWORD=VotreMotDePasseAdmin
> > ```
> >
> > ### Fichier `frontend/.env` (frontend)
> >
> > ```env
> > # ── Keycloak Frontend ───────────────────────────────────────
> > VITE_KEYCLOAK_URL=http://localhost:8080
> > VITE_KEYCLOAK_REALM=rag-chatbot
> > VITE_KEYCLOAK_CLIENT_ID=rag-frontend
> >
> > # ── API Backend ─────────────────────────────────────────────
> > VITE_API_URL=http://localhost:8000
> > ```
> >
> > ---
> >
> > ## Etape 4 — Vérification
> >
> > ### Tester l'authentification
> >
> > 1. Démarrez la stack : `make start`
> > 2. 2. Ouvrez `http://localhost:3000`
> >    3. 3. Cliquez **Se connecter**
> >       4. 4. Vous devriez voir le bouton **Connexion Microsoft**
> >          5. 5. Connectez-vous avec votre compte Microsoft 365
> >             6. 6. Vous êtes redirigé vers le chat
> >               
> >                7. ### Vérifier le token JWT
> >               
> >                8. Le token JWT contient ces claims :
> >                9. ```json
> >                   {
> >   "sub": "user-uuid",
> >   "email": "user@votreentreprise.com",
> >   "preferred_username": "prenom.nom",
> >   "realm_access": {
> >     "roles": ["user", "admin"]
> >   }
> > }
> > ```
> >
> > ### Vérifier via l'API
> >
> > ```bash
> > # Obtenir un token (via Keycloak)
> > TOKEN=$(curl -s -X POST \
> >   http://localhost:8080/realms/rag-chatbot/protocol/openid-connect/token \
> >   -d "client_id=rag-frontend&username=test@example.com&password=motdepasse&grant_type=password" \
> >   | jq -r .access_token)
> >
> > # Tester l'API avec le token
> > curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/chat/conversations
> > ```
> >
> > ---
> >
> > ## Etape 5 — Déploiement en production
> >
> > ### Variables à changer pour la production
> >
> > ```env
> > # Remplacer localhost par vos vrais domaines
> > KEYCLOAK_URL=https://auth.votreentreprise.com
> > VITE_KEYCLOAK_URL=https://auth.votreentreprise.com
> > VITE_API_URL=https://api.votreentreprise.com
> >
> > # Redirect URI Azure AD à mettre à jour aussi :
> > # https://auth.votreentreprise.com/realms/rag-chatbot/broker/microsoft/endpoint
> > ```
> >
> > ### Sécurisation Keycloak en production
> >
> > 1. Désactivez l'endpoint `/auth/admin` en accès public
> > 2. 2. Activez HTTPS obligatoire : **Realm Settings** → **Login** → **Require SSL** → `all requests`
> >    3. 3. Configurez un certificat TLS valide
> >       4. 4. Changez le mot de passe admin par défaut
> >         
> >          5. ---
> >         
> >          6. ## Dépannage
> >         
> >          7. ### Erreur "Invalid redirect URI"
> >
> > → Vérifiez que l'URL de redirection dans Azure AD correspond exactement à celle configurée dans Keycloak.
> >
> > ### Erreur "Client not found"
> >
> > → Vérifiez que `VITE_KEYCLOAK_CLIENT_ID=rag-frontend` correspond au Client ID créé dans Keycloak.
> >
> > ### Erreur "Token signature verification failed"
> >
> > → Vérifiez que `KEYCLOAK_URL` dans le backend pointe vers la même instance Keycloak que le frontend.
> >
> > ### L'utilisateur n'a pas le rôle admin
> >
> > → Dans Keycloak → Users → sélectionnez l'utilisateur → Role Mapping → assignez le rôle `admin`.
> >
> > ---
> >
> > ## Ressources utiles
> >
> > - [Documentation Keycloak](https://www.keycloak.org/documentation)
> > - - [Azure AD App Registration](https://learn.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)
> >   - - [Keycloak Microsoft Identity Provider](https://www.keycloak.org/docs/latest/server_admin/#microsoft)
> >     - 
