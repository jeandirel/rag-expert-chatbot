"""
Synchronisation SharePoint -> Qdrant
Tele-charge les fichiers depuis SharePoint (21 Go de docs metier)
et les indexe dans Qdrant via le pipeline d'ingestion.

Utilise : Office365-REST-Python-Client ou Microsoft Graph API
"""

import asyncio
import logging
import os
import tempfile
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from office365.runtime.auth.client_credential import ClientCredential
from office365.sharepoint.client_context import ClientContext

from app.core.config import settings
from backend.ingestion.pipeline import IngestionPipeline

logger = logging.getLogger(__name__)


class SharePointSyncer:
      """
          Synchronise les documents SharePoint vers Qdrant.
              Gere la deduplication par hash MD5 pour ne re-indexer
                  que les fichiers modifies.
                      """

    # Extensions supportees par Unstructured
      SUPPORTED_EXTENSIONS = {
          ".pdf", ".docx", ".doc", ".xlsx", ".xls",
          ".pptx", ".ppt", ".txt", ".md", ".html",
          ".eml", ".msg", ".csv", ".json",
      }

    def __init__(self):
              self.pipeline = IngestionPipeline()
              self._client: ClientContext | None = None
              self._processed_hashes: set[str] = set()

    def _get_client(self) -> ClientContext:
              """Initialise le client SharePoint avec credentials."""
              if self._client is None:
                            credentials = ClientCredential(
                                              settings.SHAREPOINT_CLIENT_ID,
                                              settings.SHAREPOINT_CLIENT_SECRET,
                            )
                            self._client = ClientContext(settings.SHAREPOINT_SITE_URL).with_credentials(
                                credentials
                            )
                            logger.info(f"Connecte a SharePoint: {settings.SHAREPOINT_SITE_URL}")
                        return self._client

    async def _download_file(
              self, ctx: ClientContext, server_relative_url: str, dest_path: Path
    ) -> bool:
              """Telecharge un fichier SharePoint vers le disque local."""
        try:
                      with open(dest_path, "wb") as f:
                                        ctx.web.get_file_by_server_relative_url(
                                                              server_relative_url
                                        ).download(f).execute_query()
                                    return True
except Exception as e:
            logger.error(f"Erreur download {server_relative_url}: {e}")
            return False

    def _compute_file_hash(self, file_path: Path) -> str:
              """Calcule le hash MD5 d'un fichier pour la deduplication."""
        md5 = hashlib.md5()
        with open(file_path, "rb") as f:
                      for chunk in iter(lambda: f.read(8192), b""):
                                        md5.update(chunk)
                                return md5.hexdigest()

    def _list_files_recursive(
              self, ctx: ClientContext, folder_url: str
    ) -> list[dict[str, Any]]:
              """
                      Liste recursivement tous les fichiers d'un dossier SharePoint.
                              Retourne une liste de dicts avec: name, server_relative_url, size, modified.
                                      """
        files = []

        try:
                      folder = ctx.web.get_folder_by_server_relative_url(folder_url)
            ctx.load(folder)
            ctx.execute_query()

            # Fichiers dans ce dossier
            folder.files.get().execute_query()
            for file in folder.files:
                              ext = Path(file.name).suffix.lower()
                              if ext in self.SUPPORTED_EXTENSIONS:
                                                    files.append({
                                                                              "name": file.name,
                                                                              "server_relative_url": file.serverRelativeUrl,
                                                                              "size": file.length,
                                                                              "modified": file.time_last_modified,
                                                                              "folder": folder_url,
                                                    })

                          # Sous-dossiers (recursif)
                          folder.folders.get().execute_query()
            for subfolder in folder.folders:
                              # Ignorer les dossiers systeme SharePoint
                              if subfolder.name.startswith("_"):
                                                    continue
                                                sub_files = self._list_files_recursive(
                                                                      ctx, subfolder.serverRelativeUrl
                                                )
                files.extend(sub_files)

except Exception as e:
            logger.warning(f"Impossible de lister {folder_url}: {e}")

        return files

    async def sync_library(
              self,
              library_name: str = "Documents",
              folder_path: str = "",
              force_reindex: bool = False,
    ) -> dict[str, int]:
              """
                      Synchronise une bibliotheque SharePoint.

                              Args:
                                          library_name: Nom de la bibliotheque (ex: "Documents")
                                                      folder_path: Sous-dossier optionnel (ex: "/Procedures")
                                                                  force_reindex: Re-indexer meme si le fichier n'a pas change

                                                                          Returns:
                                                                                      Dict avec: total, indexed, skipped, errors
                                                                                              """
        ctx = self._get_client()

        # Construire le chemin base
        site_name = settings.SHAREPOINT_SITE_URL.rstrip("/").split("/")[-1]
        base_url = f"/sites/{site_name}/{library_name}{folder_path}"

        logger.info(f"Debut synchronisation SharePoint: {base_url}")
        logger.info(f"Force reindex: {force_reindex}")

        stats = {"total": 0, "indexed": 0, "skipped": 0, "errors": 0}

        # Lister tous les fichiers
        all_files = self._list_files_recursive(ctx, base_url)
        stats["total"] = len(all_files)

        logger.info(f"Fichiers trouves: {stats['total']}")

        # Traiter chaque fichier
        for file_info in all_files:
                      file_name = file_info["name"]
            server_url = file_info["server_relative_url"]

            try:
                              with tempfile.TemporaryDirectory() as tmp_dir:
                    tmp_path = Path(tmp_dir) / file_name

                    # Telecharger le fichier
                    success = await self._download_file(ctx, server_url, tmp_path)
                    if not success:
                                              stats["errors"] += 1
                                              continue

                    # Calculer le hash pour deduplication
                    file_hash = self._compute_file_hash(tmp_path)
                    if not force_reindex and file_hash in self._processed_hashes:
                                              logger.debug(f"Skip (deja indexe): {file_name}")
                                              stats["skipped"] += 1
                                              continue

                    # Metadata enrichies pour le document
                    metadata = {
                                              "source": "sharepoint",
                                              "sharepoint_url": server_url,
                                              "sharepoint_site": settings.SHAREPOINT_SITE_URL,
                                              "library": library_name,
                                              "folder": file_info["folder"],
                                              "file_hash": file_hash,
                                              "file_size_bytes": file_info["size"],
                                              "last_modified": str(file_info.get("modified", "")),
                                              "indexed_at": datetime.now(timezone.utc).isoformat(),
                    }

                    # Indexer via le pipeline
                    await self.pipeline.ingest_file(
                                              file_path=tmp_path,
                                              metadata=metadata,
                                              collection_name=settings.QDRANT_COLLECTION_NAME,
                    )

                    self._processed_hashes.add(file_hash)
                    stats["indexed"] += 1
                    logger.info(
                                              f"Indexe [{stats['indexed']}/{stats['total']}]: {file_name} "
                                              f"({file_info['size'] // 1024} KB)"
                    )

except Exception as e:
                logger.error(f"Erreur indexation {file_name}: {e}")
                stats["errors"] += 1

        logger.info(
                      f"Synchronisation terminee: "
                      f"{stats['indexed']} indexes, "
                      f"{stats['skipped']} ignores, "
                      f"{stats['errors']} erreurs"
        )
        return stats

    async def sync_all(self, force_reindex: bool = False) -> dict[str, Any]:
              """Synchronise toutes les bibliotheques configurees."""
        results = {}

        libraries = getattr(settings, "SHAREPOINT_LIBRARIES", ["Documents"])
        if isinstance(libraries, str):
                      libraries = [lib.strip() for lib in libraries.split(",")]

        for library in libraries:
                      logger.info(f"Synchronisation bibliotheque: {library}")
            stats = await self.sync_library(
                              library_name=library,
                              force_reindex=force_reindex,
            )
            results[library] = stats

        return results


async def run_sync(force: bool = False) -> None:
      """Point d'entree principal pour la synchronisation."""
    logging.basicConfig(
              level=logging.INFO,
              format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    syncer = SharePointSyncer()

    logger.info("=== Debut de la synchronisation SharePoint -> Qdrant ===")
    logger.info(f"Site SharePoint: {settings.SHAREPOINT_SITE_URL}")
    logger.info(f"Collection Qdrant: {settings.QDRANT_COLLECTION_NAME}")

    results = await syncer.sync_all(force_reindex=force)

    # Rapport final
    total_indexed = sum(r["indexed"] for r in results.values())
    total_errors = sum(r["errors"] for r in results.values())
    total_skipped = sum(r["skipped"] for r in results.values())

    logger.info("=== Rapport de synchronisation ===")
    for library, stats in results.items():
              logger.info(
                            f"  {library}: "
                            f"{stats['indexed']} indexes, "
                            f"{stats['skipped']} ignores, "
                            f"{stats['errors']} erreurs / "
                            f"{stats['total']} total"
              )
    logger.info(
              f"Total: {total_indexed} indexes, "
              f"{total_skipped} ignores, "
              f"{total_errors} erreurs"
    )


if __name__ == "__main__":
      import argparse

    parser = argparse.ArgumentParser(description="Synchronisation SharePoint -> Qdrant")
    parser.add_argument(
              "--force",
              action="store_true",
              help="Re-indexer tous les fichiers meme s'ils n'ont pas change",
    )
    parser.add_argument(
              "--library",
              type=str,
              default=None,
              help="Nom de la bibliotheque SharePoint a synchroniser",
    )
    args = parser.parse_args()

    if args.library:
              syncer = SharePointSyncer()
        asyncio.run(syncer.sync_library(library_name=args.library, force_reindex=args.force))
else:
        asyncio.run(run_sync(force=args.force))
