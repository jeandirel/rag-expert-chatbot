"""
Pipeline d'ingestion des documents
Gere le chargement, le parsing, l'embedding et l'indexation
"""
import hashlib
import sqlite3
import time
from pathlib import Path
from typing import Optional

import structlog
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from tqdm import tqdm
from unstructured.chunking.title import chunk_by_title
from unstructured.partition.auto import partition
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from app.services.llm_service import LLMService
from app.core.config import settings

logger = structlog.get_logger()

SUPPORTED_FORMATS = [
      ".pdf", ".docx", ".doc", ".xlsx", ".xls",
      ".pptx", ".ppt", ".txt", ".md", ".html",
      ".msg", ".eml", ".png", ".jpg", ".jpeg"
]

CATEGORY_KEYWORDS = {
      "procedure": ["procedure", "process", "etape", "workflow", "instruction"],
      "contrat": ["contrat", "contract", "accord", "convention", "avenant"],
      "rh": ["ressources humaines", "rh", "conge", "paie", "recrutement", "formation"],
      "technique": ["technique", "specification", "architecture", "api", "systeme"],
      "finance": ["budget", "facture", "comptabilite", "finance", "devis", "tresorerie"],
      "juridique": ["juridique", "legal", "reglementation", "conformite", "gdpr", "rgpd"],
      "commercial": ["commercial", "client", "vente", "offre", "proposition"],
}


class IngestionPipeline:
      """Pipeline complet d'ingestion des documents."""

    def __init__(self):
              self.llm_service = LLMService()
              self.db = self._init_tracking_db()
              self._vectorstore: Optional[Qdrant] = None

    def _init_tracking_db(self) -> sqlite3.Connection:
              """Initialise la base SQLite de suivi des fichiers indexes."""
              conn = sqlite3.connect("ingestion_tracker.db")
              conn.execute("""
                  CREATE TABLE IF NOT EXISTS indexed_files (
                      filepath TEXT PRIMARY KEY,
                      file_hash TEXT NOT NULL,
                      indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      chunk_count INTEGER DEFAULT 0,
                      status TEXT DEFAULT 'pending',
                      error_message TEXT
                  )
              """)
              conn.commit()
              return conn

    @property
    def vectorstore(self) -> Qdrant:
              if self._vectorstore is None:
                            client = QdrantClient(
                                              host=settings.QDRANT_HOST,
                                              port=settings.QDRANT_PORT
                            )
                            self._vectorstore = Qdrant(
                                client=client,
                                collection_name=settings.COLLECTION_NAME,
                                embeddings=self.llm_service.embeddings,
                            )
                        return self._vectorstore

    def get_file_hash(self, filepath: str) -> str:
              """Calcule le hash MD5 d'un fichier pour detecter les changements."""
        with open(filepath, "rb") as f:
                      return hashlib.md5(f.read()).hexdigest()

    def is_already_indexed(self, filepath: str, file_hash: str) -> bool:
              """Verifie si le fichier est deja indexe et inchange."""
        cursor = self.db.execute(
                      "SELECT file_hash, status FROM indexed_files WHERE filepath = ?",
                      (filepath,)
        )
        row = cursor.fetchone()
        return row is not None and row[0] == file_hash and row[1] == "success"

    def detect_category(self, filename: str, content: str) -> str:
              """Detection automatique de la categorie par mots-cles."""
        text = (filename + " " + content[:500]).lower()
        for cat, keywords in CATEGORY_KEYWORDS.items():
                      if any(kw in text for kw in keywords):
                                        return cat
                                return "general"

    def detect_department(self, filepath: str) -> str:
              """Detection du departement depuis le chemin du fichier."""
        path_parts = Path(filepath).parts
        departments = ["rh", "finance", "juridique", "technique", "commercial", "direction"]
        for part in path_parts:
                      for dept in departments:
                                        if dept in part.lower():
                                                              return dept
                                                  return "general"

    def process_file(self, filepath: str) -> int:
              """Traite un fichier et retourne le nombre de chunks indexes."""
        path = Path(filepath)
        if path.suffix.lower() not in SUPPORTED_FORMATS:
                      return 0

        try:
                      file_hash = self.get_file_hash(filepath)
except Exception as e:
            logger.error("Erreur lecture fichier", filepath=filepath, error=str(e))
            return 0

        if self.is_already_indexed(filepath, file_hash):
                      logger.debug("Fichier deja indexe", filepath=path.name)
            return 0

        logger.info("Traitement du fichier", filename=path.name)

        try:
                      elements = partition(
                                        filename=filepath,
                                        strategy="hi_res",
                                        infer_table_structure=True,
                                        extract_images_in_pdf=False,
                                        languages=["fra", "eng"]
                      )

            chunks = chunk_by_title(
                              elements,
                              max_characters=settings.CHUNK_SIZE,
                              new_after_n_chars=800,
                              overlap=settings.CHUNK_OVERLAP,
            )

            texts = []
            metadatas = []
            for i, chunk in enumerate(chunks):
                              text = str(chunk).strip()
                if len(text) < 20:
                                      continue

                category = self.detect_category(path.name, text)
                department = self.detect_department(filepath)

                texts.append(text)
                metadatas.append({
                                      "source_file": path.name,
                                      "source_path": str(filepath),
                                      "file_type": path.suffix,
                                      "chunk_index": i,
                                      "category": category,
                                      "department": department,
                                      "file_hash": file_hash,
                                      "doc_id": file_hash,
                })

            if not texts:
                              logger.warning("Aucun contenu extrait", filepath=path.name)
                return 0

            self.vectorstore.add_texts(texts=texts, metadatas=metadatas)

            self.db.execute("""
                            INSERT OR REPLACE INTO indexed_files
                                            (filepath, file_hash, indexed_at, chunk_count, status)
                                                            VALUES (?, ?, CURRENT_TIMESTAMP, ?, 'success')
                                                                        """, (str(filepath), file_hash, len(texts)))
            self.db.commit()

            logger.info("Fichier indexe", filename=path.name, chunks=len(texts))
            return len(texts)

except Exception as e:
            logger.error("Erreur traitement", filepath=path.name, error=str(e))
            self.db.execute("""
                            INSERT OR REPLACE INTO indexed_files
                                            (filepath, file_hash, indexed_at, chunk_count, status, error_message)
                                                            VALUES (?, ?, CURRENT_TIMESTAMP, 0, 'error', ?)
                                                                        """, (str(filepath), file_hash, str(e)))
            self.db.commit()
            return 0

    def process_all(self, folder: str = None) -> dict:
              """Lance l'ingestion complete d'un dossier."""
        folder = folder or settings.DOCUMENTS_FOLDER
        folder_path = Path(folder)

        if not folder_path.exists():
                      folder_path.mkdir(parents=True)
            logger.warning("Dossier cree", folder=str(folder_path))
            return {"total": 0, "indexed": 0, "skipped": 0, "errors": 0}

        all_files = []
        for fmt in SUPPORTED_FORMATS:
                      all_files.extend(folder_path.rglob(f"*{fmt}"))

        total = len(all_files)
        logger.info("Debut ingestion", total_files=total, folder=str(folder_path))

        indexed = 0
        skipped = 0
        errors = 0

        for filepath in tqdm(all_files, desc="Indexation"):
                      try:
                                        result = self.process_file(str(filepath))
                if result > 0:
                                      indexed += 1
else:
                    skipped += 1
except Exception as e:
                errors += 1
                logger.error("Erreur inattendue", filepath=str(filepath), error=str(e))

        stats = {
                      "total": total,
                      "indexed": indexed,
                      "skipped": skipped,
                      "errors": errors,
        }
        logger.info("Ingestion terminee", **stats)
        return stats

    def watch(self, folder: str = None):
              """Mode surveillance - indexe automatiquement les nouveaux fichiers."""
        folder = folder or settings.DOCUMENTS_FOLDER
        logger.info("Mode surveillance actif", folder=folder)

        self.process_all(folder)

        event_handler = DocumentHandler(self)
        observer = Observer()
        observer.schedule(event_handler, folder, recursive=True)
        observer.start()

        try:
                      while True:
                                        time.sleep(60)
except KeyboardInterrupt:
            observer.stop()
        observer.join()

    def get_stats(self) -> dict:
              """Retourne les statistiques d'indexation."""
        cursor = self.db.execute("""
                    SELECT status, COUNT(*), SUM(chunk_count)
                                FROM indexed_files GROUP BY status
                                        """)
        stats = {}
        for row in cursor:
                      stats[row[0]] = {"files": row[1], "chunks": row[2] or 0}
        return stats


class DocumentHandler(FileSystemEventHandler):
      """Handler pour la surveillance du dossier de documents."""

    def __init__(self, pipeline: IngestionPipeline):
              self.pipeline = pipeline

    def on_created(self, event):
              if not event.is_directory:
                            logger.info("Nouveau document detecte", path=event.src_path)
            self.pipeline.process_file(event.src_path)

    def on_modified(self, event):
              if not event.is_directory:
                            logger.info("Document modifie detecte", path=event.src_path)
            self.pipeline.process_file(event.src_path)


if __name__ == "__main__":
      import argparse
    parser = argparse.ArgumentParser(description="Pipeline d'ingestion RAG")
    parser.add_argument("--folder", default=None, help="Dossier a indexer")
    parser.add_argument("--watch", action="store_true", help="Mode surveillance")
    args = parser.parse_args()

    pipeline = IngestionPipeline()
    if args.watch:
              pipeline.watch(args.folder)
else:
        stats = pipeline.process_all(args.folder)
        print(f"Indexation terminee: {stats}")
