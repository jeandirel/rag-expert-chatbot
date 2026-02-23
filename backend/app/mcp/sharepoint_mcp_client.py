"""
Client MCP SharePoint pour le backend RAG.

Se connecte au serveur MCP SharePoint pret a l'emploi :
  - Sofias-ai/mcp-sharepoint (pip install mcp-sharepoint-server)
      https://github.com/Sofias-ai/mcp-sharepoint

      Ce client expose les 10 outils SharePoint comme fonctions Python
      utilisables directement dans le pipeline RAG et le serveur MCP FastAPI.

      Outils disponibles :
        - list_sharepoint_folders     : lister les dossiers
          - list_sharepoint_documents   : lister les documents d'un dossier
            - get_document_content        : lire le contenu d'un document (PDF/DOCX/XLSX)
              - upload_document             : uploader un document
                - update_document             : mettre a jour un document
                  - delete_document             : supprimer un document
                    - create_folder               : creer un dossier
                      - delete_folder               : supprimer un dossier
                        - get_sharepoint_tree         : arborescence complete
                          - upload_document_from_path   : uploader depuis un chemin local
                          """

import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.core.config import settings

logger = logging.getLogger(__name__)


class SharePointMCPClient:
      """
          Client pour le serveur MCP SharePoint (Sofias-ai/mcp-sharepoint).

              Mode de connexion : stdio (subprocess) — le serveur MCP tourne
                  comme processus enfant et communique via stdin/stdout en JSON-RPC.

                      En production Docker, le serveur tourne dans son propre conteneur
                          et on se connecte via SSE/HTTP.
                              """

    def __init__(self):
              self._session: ClientSession | None = None
              self._available_tools: list[str] = []
              self._mode = os.getenv("MCP_CONNECTION_MODE", "subprocess")

    def _get_server_params(self) -> StdioServerParameters:
              """Parametres de connexion au serveur MCP SharePoint."""
              return StdioServerParameters(
                  command=sys.executable,
                  args=["-m", "mcp_sharepoint"],
                  env={
                      "SHP_ID_APP": settings.SHAREPOINT_CLIENT_ID,
                      "SHP_ID_APP_SECRET": settings.SHAREPOINT_CLIENT_SECRET,
                      "SHP_TENANT_ID": settings.SHAREPOINT_TENANT_ID,
                      "SHP_SITE_URL": settings.SHAREPOINT_SITE_URL,
                      "SHP_DOC_LIBRARY": getattr(settings, "SHAREPOINT_DOC_LIBRARY", "Shared Documents"),
                      "SHP_MAX_DEPTH": str(getattr(settings, "SHP_MAX_DEPTH", 15)),
                      "SHP_MAX_FOLDERS_PER_LEVEL": str(getattr(settings, "SHP_MAX_FOLDERS_PER_LEVEL", 100)),
                      "SHP_LEVEL_DELAY": str(getattr(settings, "SHP_LEVEL_DELAY", 0.5)),
                      **os.environ,
                  },
              )

    async def _call_tool(self, tool_name: str, arguments: dict) -> Any:
              """Appelle un outil MCP et retourne le resultat."""
              try:
                            server_params = self._get_server_params()
                            async with stdio_client(server_params) as (read, write):
                                async with ClientSession(read, write) as session:
                                                      await session.initialize()
                                                      result = await session.call_tool(tool_name, arguments)
                                                      if result.content:
                                                                                content = result.content[0]
                                                                                if hasattr(content, "text"):
                                                                                                              try:
                                                                                                                                                return json.loads(content.text)
                                                                                  except json.JSONDecodeError:
                                                                                        return content.text
                                                                            return None
except Exception as e:
            logger.error(f"Erreur appel MCP {tool_name}: {e}")
            raise

    async def list_tools(self) -> list[dict]:
              """Liste tous les outils disponibles sur le serveur MCP."""
              try:
                            server_params = self._get_server_params()
                            async with stdio_client(server_params) as (read, write):
                                async with ClientSession(read, write) as session:
                                                      await session.initialize()
                                                      tools = await session.list_tools()
                                                      return [
                                                          {
                                                              "name": t.name,
                                                              "description": t.description,
                                                              "input_schema": t.inputSchema,
                                                          }
                                                          for t in tools.tools
                                                      ]
              except Exception as e:
                            logger.error(f"Erreur list_tools MCP: {e}")
                            return []

          # ─── 10 outils SharePoint ─────────────────────────────────

    async def list_sharepoint_folders(
              self,
              folder_path: str = "",
    ) -> list[dict]:
              """
                      Liste tous les dossiers dans un chemin SharePoint.

                              Args:
                                          folder_path: Chemin relatif (ex: "Procedures/2024"). Vide = racine.

                                                  Returns:
                                                              Liste de dossiers avec name, path, item_count.
                                                                      """
              result = await self._call_tool(
                  "List_SharePoint_Folders",
                  {"folder_path": folder_path},
              )
              return result or []

    async def list_sharepoint_documents(
              self,
              folder_path: str = "",
    ) -> list[dict]:
              """
                      Liste tous les documents dans un dossier SharePoint.

                              Args:
                                          folder_path: Chemin du dossier (ex: "Documents/Normes").

                                                  Returns:
                                                              Liste de documents avec name, size, modified, url.
                                                                      """
              result = await self._call_tool(
                  "List_SharePoint_Documents",
                  {"folder_path": folder_path},
              )
              return result or []

    async def get_document_content(
              self,
              file_path: str,
    ) -> str:
              """
                      Recupere et extrait le contenu texte d'un document.
                              Supporte : PDF (PyMuPDF), Word (python-docx), Excel (openpyxl),
                                                 TXT, JSON, XML, HTML, Markdown.

                                                         Args:
                                                                     file_path: Chemin complet dans SharePoint (ex: "Documents/rapport.pdf").

                                                                             Returns:
                                                                                         Contenu textuel extrait du document.
                                                                                                 """
              result = await self._call_tool(
                  "Get_Document_Content",
                  {"file_path": file_path},
              )
              if isinstance(result, dict):
                            return result.get("content", str(result))
                        return str(result) if result else ""

    async def get_sharepoint_tree(
              self,
              root_path: str = "",
              max_depth: int = 5,
    ) -> dict:
              """
                      Retourne l'arborescence complete de SharePoint.

                              Args:
                                          root_path: Point de depart (vide = tout le site).
                                                      max_depth: Profondeur maximale (defaut: 5).

                                                              Returns:
                                                                          Arborescence JSON avec dossiers et fichiers.
                                                                                  """
        result = await self._call_tool(
                      "Get_SharePoint_Tree",
                      {"root_path": root_path, "max_depth": max_depth},
        )
        return result or {}

    async def upload_document(
              self,
              folder_path: str,
              file_name: str,
              content: str,
              is_binary: bool = False,
    ) -> dict:
              """
                      Upload un document dans SharePoint.

                              Args:
                                          folder_path: Dossier cible (ex: "Documents/Rapports").
                                                      file_name: Nom du fichier (ex: "rapport_2024.docx").
                                                                  content: Contenu (texte ou base64 si binaire).
                                                                              is_binary: True si le contenu est en base64.

                                                                                      Returns:
                                                                                                  Infos du fichier cree.
                                                                                                          """
        return await self._call_tool(
                      "Upload_Document",
                      {
                                        "folder_path": folder_path,
                                        "file_name": file_name,
                                        "content": content,
                                        "is_binary": is_binary,
                      },
        ) or {}

    async def upload_document_from_path(
              self,
              local_path: str,
              folder_path: str,
              file_name: Optional[str] = None,
    ) -> dict:
              """
                      Upload un fichier local vers SharePoint.

                              Args:
                                          local_path: Chemin local du fichier.
                                                      folder_path: Dossier cible dans SharePoint.
                                                                  file_name: Nom de destination (si different du nom local).

                                                                          Returns:
                                                                                      Infos du fichier cree.
                                                                                              """
        return await self._call_tool(
                      "Upload_Document_From_Path",
                      {
                                        "local_path": local_path,
                                        "folder_path": folder_path,
                                        "file_name": file_name or Path(local_path).name,
                      },
        ) or {}

    async def update_document(
              self,
              file_path: str,
              content: str,
              is_binary: bool = False,
    ) -> dict:
              """
                      Met a jour le contenu d'un document existant dans SharePoint.

                              Args:
                                          file_path: Chemin complet dans SharePoint.
                                                      content: Nouveau contenu.
                                                                  is_binary: True si base64.
                                                                          """
        return await self._call_tool(
                      "Update_Document",
                      {"file_path": file_path, "content": content, "is_binary": is_binary},
        ) or {}

    async def delete_document(self, file_path: str) -> dict:
              """
                      Supprime un document de SharePoint.

                              Args:
                                          file_path: Chemin complet dans SharePoint.
                                                  """
        return await self._call_tool(
                      "Delete_Document",
                      {"file_path": file_path},
        ) or {}

    async def create_folder(self, folder_path: str) -> dict:
              """
                      Cree un nouveau dossier dans SharePoint.

                              Args:
                                          folder_path: Chemin complet du dossier a creer.
                                                  """
        return await self._call_tool(
                      "Create_Folder",
                      {"folder_path": folder_path},
        ) or {}

    async def delete_folder(self, folder_path: str) -> dict:
              """
                      Supprime un dossier vide de SharePoint.

                              Args:
                                          folder_path: Chemin complet du dossier a supprimer.
                                                  """
        return await self._call_tool(
                      "Delete_Folder",
                      {"folder_path": folder_path},
        ) or {}

    # ─── Methodes utilitaires ──────────────────────────────────

    async def search_documents(
              self,
              query: str,
              folder_path: str = "",
    ) -> list[dict]:
              """
                      Recherche des documents par nom dans SharePoint.
                              (Filtre cote client sur la liste des documents)

                                      Args:
                                                  query: Terme de recherche (insensible a la casse).
                                                              folder_path: Dossier a explorer (vide = tout).

                                                                      Returns:
                                                                                  Liste des documents correspondants.
                                                                                          """
        all_docs = await self.list_sharepoint_documents(folder_path)
        query_lower = query.lower()
        return [
                      doc for doc in all_docs
                      if query_lower in str(doc.get("name", "")).lower()
        ]

    async def get_document_for_rag(self, file_path: str) -> dict:
              """
                      Recupere un document avec son contenu pour l'indexation RAG.

                              Returns:
                                          Dict avec: file_path, content, metadata.
                                                  """
        content = await self.get_document_content(file_path)
        filename = Path(file_path).name
        return {
                      "file_path": file_path,
                      "filename": filename,
                      "content": content,
                      "source": "sharepoint_mcp",
                      "file_type": Path(filename).suffix.lower(),
        }

    async def health_check(self) -> bool:
              """Verifie que le serveur MCP SharePoint est accessible."""
        try:
                      tools = await self.list_tools()
                      logger.info(f"MCP SharePoint: {len(tools)} outils disponibles")
                      return len(tools) > 0
except Exception as e:
            logger.error(f"MCP SharePoint health check failed: {e}")
            return False


# ─── Singleton ─────────────────────────────────────────────────

_sharepoint_mcp_client: SharePointMCPClient | None = None


def get_sharepoint_mcp_client() -> SharePointMCPClient:
      """Dependency injection FastAPI."""
    global _sharepoint_mcp_client
    if _sharepoint_mcp_client is None:
              _sharepoint_mcp_client = SharePointMCPClient()
    return _sharepoint_mcp_client


# ─── Test rapide ───────────────────────────────────────────────

if __name__ == "__main__":
      async def test():
                client = SharePointMCPClient()

        print("=== Test MCP SharePoint (Sofias-ai/mcp-sharepoint) ===")

        print("\n1. Outils disponibles:")
        tools = await client.list_tools()
        for t in tools:
                      print(f"   - {t['name']}: {t['description'][:60]}...")

        print("\n2. Liste des dossiers racine:")
        folders = await client.list_sharepoint_folders()
        for f in folders[:5]:
                      print(f"   - {f}")

        print("\n3. Documents a la racine:")
        docs = await client.list_sharepoint_documents()
        for d in docs[:5]:
                      print(f"   - {d}")

        print("\n=== Test termine ===")

    asyncio.run(test())
