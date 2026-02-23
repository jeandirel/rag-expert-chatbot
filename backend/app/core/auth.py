"""
Authentification SSO via Keycloak (JWT / OIDC)
Gestion des roles : ChatbotUser, ChatbotAdmin, ChatbotPower
"""
from dataclasses import dataclass, field
from typing import List, Optional

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
import structlog

from app.core.config import settings

logger = structlog.get_logger()
security = HTTPBearer(auto_error=False)

_jwks_client: Optional[PyJWKClient] = None


def get_jwks_client() -> PyJWKClient:
      """Retourne le client JWKS (cached)."""
      global _jwks_client
      if _jwks_client is None:
                _jwks_client = PyJWKClient(settings.get_jwks_uri())
            return _jwks_client


@dataclass
class User:
      """Modele utilisateur extrait du token JWT."""
    id: str
    email: str
    name: str
    roles: List[str] = field(default_factory=list)
    department: str = ""
    preferred_username: str = ""

    def is_admin(self) -> bool:
              return "ChatbotAdmin" in self.roles

    def is_power_user(self) -> bool:
              return "ChatbotPower" in self.roles or self.is_admin()


async def get_current_user(
      credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
      """
          Valide le token JWT Keycloak et retourne l'utilisateur connecte.
              En mode developpement (LLM_PROVIDER=mock), retourne un utilisateur de test.
                  """
    if settings.LLM_PROVIDER == "mock":
              return User(
                            id="test-user-id",
                            email="test@example.com",
                            name="Test User",
                            roles=["ChatbotUser", "ChatbotAdmin"],
                            department="technique"
              )

    if not credentials:
              raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token d'authentification manquant",
                            headers={"WWW-Authenticate": "Bearer"},
              )

    token = credentials.credentials

    try:
              jwks_client = get_jwks_client()
              signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
                      token,
                      signing_key.key,
                      algorithms=["RS256"],
                      audience=settings.KEYCLOAK_CLIENT_ID,
                      options={"verify_exp": True},
        )

        resource_access = payload.get("resource_access", {})
        client_roles = resource_access.get(settings.KEYCLOAK_CLIENT_ID, {}).get("roles", [])
        realm_roles = payload.get("realm_access", {}).get("roles", [])
        all_roles = list(set(client_roles + realm_roles))

        return User(
                      id=payload.get("sub", ""),
                      email=payload.get("email", ""),
                      name=payload.get("name", payload.get("preferred_username", "")),
                      preferred_username=payload.get("preferred_username", ""),
                      roles=all_roles,
                      department=payload.get("department", ""),
        )

except jwt.ExpiredSignatureError:
        raise HTTPException(
                      status_code=status.HTTP_401_UNAUTHORIZED,
                      detail="Token expire",
                      headers={"WWW-Authenticate": "Bearer"},
        )
except jwt.InvalidTokenError as e:
        logger.warning("Token JWT invalide", error=str(e))
        raise HTTPException(
                      status_code=status.HTTP_401_UNAUTHORIZED,
                      detail="Token invalide",
                      headers={"WWW-Authenticate": "Bearer"},
        )
except Exception as e:
        logger.error("Erreur d'authentification", error=str(e))
        raise HTTPException(
                      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                      detail="Erreur d'authentification",
        )


async def require_admin(user: User = Depends(get_current_user)) -> User:
      """Dependance FastAPI - exige le role ChatbotAdmin."""
    if not user.is_admin():
              raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Acces administrateur requis",
              )
          return user


async def require_power_user(user: User = Depends(get_current_user)) -> User:
      """Dependance FastAPI - exige le role ChatbotPower ou ChatbotAdmin."""
    if not user.is_power_user():
              raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Acces utilisateur avance requis",
              )
          return user
