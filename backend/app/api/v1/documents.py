"""
Routes API pour la gestion des documents indexes dans Qdrant.
Permet de lister, rechercher, supprimer et re-indexer des documents.
"""

import logging
import mimetypes
import uuid
from pathlib import Path
from typing import Annotated, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.core.auth import get_current_user, require_admin
from app.core.config import settings
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])


# ─── Schemas ────────────────────────────────────────────────────────────────

class DocumentInfo(BaseModel):
      id: str
      filename: str
      source: str
      file_type: str
      chunk_count: int
      indexed_at: Optional[str] = None
      file_size_bytes: Optional[int] = None
      sharepoint_url: Optional[str] = None


class DocumentListResponse(BaseModel):
      documents: list[DocumentInfo]
      total: int
      page: int
      page_size: int


class DeleteResponse(BaseModel):
      deleted: int
      message: str


class SearchRequest(BaseModel):
      query: str
      top_k: int = 5
      score_threshold: float = 0.5
      filters: Optional[dict] = None


# ─── Routes ────────────────────────────────────────────────────────────────

@router.get("/", response_model=DocumentListResponse)
async def list_documents(
      page: int = Query(1, ge=1, description="Numero de page"),
      page_size: int = Query(20, ge=1, le=100, description="Taille de page"),
      source: Optional[str] = Query(None, description="Filtrer par source (sharepoint, upload, etc.)"),
      file_type: Optional[str] = Query(None, description="Filtrer par type (.pdf, .docx, etc.)"),
      search: Optional[str] = Query(None, description="Recherche par nom de fichier"),
      current_user: dict = Depends(get_current_user),
      rag_service: RAGService = Depends(RAGService),
):
      """
          Liste tous les documents indexes dans Qdrant.
              Supporte la pagination et le filtrage.
                  """
      try:
                client = rag_service.qdrant_client
                collection_name = settings.QDRANT_COLLECTION_NAME

          # Recuperer tous les points avec scroll
                offset = (page - 1) * page_size
                all_docs: dict[str, DocumentInfo] = {}

          # Scroll pour recuperer les documents uniques par filename
                scroll_result, next_offset = client.scroll(
                    collection_name=collection_name,
                    limit=1000,
                    with_payload=True,
                    with_vectors=False,
                )

          for point in scroll_result:
                        payload = point.payload or {}
                        filename = payload.get("filename", "Inconnu")
                        doc_id = payload.get("document_id", str(point.id))

            if doc_id not in all_docs:
                              all_docs[doc_id] = DocumentInfo(
                                                    id=doc_id,
                                                    filename=filename,
                                                    source=payload.get("source", "upload"),
                                                    file_type=Path(filename).suffix.lower(),
                                                    chunk_count=1,
                                                    indexed_at=payload.get("indexed_at"),
                                                    file_size_bytes=payload.get("file_size_bytes"),
                                                    sharepoint_url=payload.get("sharepoint_url"),
                              )
else:
                all_docs[doc_id].chunk_count += 1

        # Filtrage
          docs_list = list(all_docs.values())

        if source:
                      docs_list = [d for d in docs_list if d.source == source]
                  if file_type:
                                docs_list = [d for d in docs_list if d.file_type == file_type]
                            if search:
                                          search_lower = search.lower()
                                          docs_list = [d for d in docs_list if search_lower in d.filename.lower()]

        # Pagination
        total = len(docs_list)
        paginated = docs_list[offset: offset + page_size]

        return DocumentListResponse(
                      documents=paginated,
                      total=total,
                      page=page,
                      page_size=page_size,
        )

except Exception as e:
        logger.error(f"Erreur liste documents: {e}")
        raise HTTPException(
                      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                      detail=f"Erreur lors de la recuperation des documents: {str(e)}",
        )


@router.get("/{document_id}", response_model=DocumentInfo)
async def get_document(
      document_id: str,
      current_user: dict = Depends(get_current_user),
      rag_service: RAGService = Depends(RAGService),
):
      """Recupere les informations d'un document specifique."""
    try:
              client = rag_service.qdrant_client

        # Chercher les chunks de ce document
              results, _ = client.scroll(
                            collection_name=settings.QDRANT_COLLECTION_NAME,
                            scroll_filter=Filter(
                                              must=[
                                                                    FieldCondition(
                                                                                              key="document_id",
                                                                                              match=MatchValue(value=document_id),
                                                                    )
                                              ]
                            ),
                            limit=1000,
                            with_payload=True,
              )

        if not results:
                      raise HTTPException(
                                        status_code=status.HTTP_404_NOT_FOUND,
                                        detail=f"Document {document_id} non trouve",
                      )

        payload = results[0].payload or {}
        filename = payload.get("filename", "Inconnu")

        return DocumentInfo(
                      id=document_id,
                      filename=filename,
                      source=payload.get("source", "upload"),
                      file_type=Path(filename).suffix.lower(),
                      chunk_count=len(results),
                      indexed_at=payload.get("indexed_at"),
                      file_size_bytes=payload.get("file_size_bytes"),
                      sharepoint_url=payload.get("sharepoint_url"),
        )

except HTTPException:
        raise
except Exception as e:
        logger.error(f"Erreur get document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}", response_model=DeleteResponse)
async def delete_document(
      document_id: str,
      current_user: dict = Depends(require_admin),
      rag_service: RAGService = Depends(RAGService),
):
      """
          Supprime tous les chunks d'un document de Qdrant.
              Necessite le role admin.
                  """
    try:
              client = rag_service.qdrant_client

        # Compter les chunks avant suppression
              results, _ = client.scroll(
                            collection_name=settings.QDRANT_COLLECTION_NAME,
                            scroll_filter=Filter(
                                              must=[
                                                                    FieldCondition(
                                                                                              key="document_id",
                                                                                              match=MatchValue(value=document_id),
                                                                    )
                                              ]
                            ),
                            limit=10000,
              )

        if not results:
                      raise HTTPException(
                                        status_code=status.HTTP_404_NOT_FOUND,
                                        detail=f"Document {document_id} non trouve",
                      )

        chunk_ids = [point.id for point in results]
        filename = (results[0].payload or {}).get("filename", document_id)

        # Supprimer les points
        client.delete(
                      collection_name=settings.QDRANT_COLLECTION_NAME,
                      points_selector=chunk_ids,
        )

        logger.info(f"Document supprime: {filename} ({len(chunk_ids)} chunks)")

        return DeleteResponse(
                      deleted=len(chunk_ids),
                      message=f"Document '{filename}' supprime ({len(chunk_ids)} chunks)",
        )

except HTTPException:
        raise
except Exception as e:
        logger.error(f"Erreur suppression document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
      file: UploadFile = File(...),
      current_user: dict = Depends(require_admin),
      rag_service: RAGService = Depends(RAGService),
):
      """
          Upload et indexe un document directement.
              Supporte: PDF, DOCX, TXT, MD, HTML, XLSX, PPTX.
                  Necessite le role admin.
                      """
    from app.services.ingestion import IngestionPipeline
    import tempfile

    ALLOWED_TYPES = {
              "application/pdf",
              "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
              "application/msword",
              "text/plain",
              "text/markdown",
              "text/html",
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
              "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }

    # Validation du type MIME
    content_type = file.content_type or mimetypes.guess_type(file.filename or "")[0]
    if content_type not in ALLOWED_TYPES:
              raise HTTPException(
                            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            detail=f"Type de fichier non supporte: {content_type}",
              )

    # Limite de taille: 50 Mo
    MAX_SIZE = 50 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_SIZE:
              raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"Fichier trop grand (max 50 Mo)",
              )

    try:
              with tempfile.TemporaryDirectory() as tmp_dir:
                            tmp_path = Path(tmp_dir) / (file.filename or "document")
                            tmp_path.write_bytes(content)

                  document_id = str(uuid.uuid4())
            metadata = {
                              "source": "upload",
                              "document_id": document_id,
                              "filename": file.filename,
                              "content_type": content_type,
                              "file_size_bytes": len(content),
                              "uploaded_by": current_user.get("preferred_username", "admin"),
            }

            pipeline = IngestionPipeline()
            await pipeline.ingest_file(
                              file_path=tmp_path,
                              metadata=metadata,
                              collection_name=settings.QDRANT_COLLECTION_NAME,
            )

        logger.info(f"Document uploade et indexe: {file.filename} ({len(content)} bytes)")

        return JSONResponse(
                      status_code=status.HTTP_201_CREATED,
                      content={
                                        "document_id": document_id,
                                        "filename": file.filename,
                                        "size_bytes": len(content),
                                        "message": "Document indexe avec succes",
                      },
        )

except Exception as e:
        logger.error(f"Erreur upload document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_documents(
      request: SearchRequest,
      current_user: dict = Depends(get_current_user),
      rag_service: RAGService = Depends(RAGService),
):
      """
          Recherche semantique dans les documents indexes.
              Retourne les chunks les plus pertinents.
                  """
    try:
              results = await rag_service.search(
                  query=request.query,
                  top_k=request.top_k,
                            score_threshold=request.score_threshold,
              )

        return {
                      "query": request.query,
                      "results": [
                                        {
                                                              "document_id": r.payload.get("document_id"),
                                                              "filename": r.payload.get("filename"),
                                                              "page_number": r.payload.get("page_number"),
                                                              "score": r.score,
                                                              "excerpt": r.payload.get("text", "")[:500],
                                                              "source": r.payload.get("source"),
                                        }
                                        for r in results
                      ],
                      "total": len(results),
        }

except Exception as e:
        logger.error(f"Erreur recherche: {e}")
        raise HTTPException(status_code=500, detail=str(e))
