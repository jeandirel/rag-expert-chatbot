# ============================================================
# Stage 1 : Build de l'application React/Vite
# ============================================================
FROM node:20-alpine AS builder

WORKDIR /app

# Copier les fichiers de dependances
COPY package.json package-lock.json* ./

# Installer les dependances
RUN npm ci --frozen-lockfile

# Copier le code source
COPY . .

# Variables d'environnement de build (overridables via --build-arg)
ARG VITE_API_URL=http://localhost:8000
ARG VITE_APP_TITLE="RAG Expert Chatbot"
ARG VITE_KEYCLOAK_URL=http://localhost:8080
ARG VITE_KEYCLOAK_REALM=rag-chatbot
ARG VITE_KEYCLOAK_CLIENT_ID=rag-frontend

ENV VITE_API_URL=$VITE_API_URL
ENV VITE_APP_TITLE=$VITE_APP_TITLE
ENV VITE_KEYCLOAK_URL=$VITE_KEYCLOAK_URL
ENV VITE_KEYCLOAK_REALM=$VITE_KEYCLOAK_REALM
ENV VITE_KEYCLOAK_CLIENT_ID=$VITE_KEYCLOAK_CLIENT_ID

# Build de production
RUN npm run build

# ============================================================
# Stage 2 : Serveur Nginx de production
# ============================================================
FROM nginx:1.25-alpine AS production

# Supprimer la config nginx par defaut
RUN rm /etc/nginx/conf.d/default.conf

# Copier la config nginx personnalisee
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copier les fichiers buildés depuis le stage builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Script d'entrypoint pour substituer les env vars au runtime
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Permissions
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html && \
        chown -R nginx:nginx /var/cache/nginx && \
            chown -R nginx:nginx /var/log/nginx && \
                chown -R nginx:nginx /etc/nginx/conf.d && \
                    touch /var/run/nginx.pid && \
                        chown -R nginx:nginx /var/run/nginx.pid

                        USER nginx

                        EXPOSE 80

                        HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
                            CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

                            ENTRYPOINT ["/docker-entrypoint.sh"]
                            CMD ["nginx", "-g", "daemon off;"]
