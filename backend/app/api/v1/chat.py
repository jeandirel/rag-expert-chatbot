"""
Routes API Chat - Endpoint principal du chatbot RAG
"""
import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.auth import get_current_user, User
from app.services.rag_service import RAGService

router = APIRouter(prefix="/chat", tags=["chat"])
rag_service = RAGService()


class ChatRequest(BaseModel):
      message: str
      conversation_id: Optional[str] = None
      department_filter: Optional[str] = None


class FeedbackRequest(BaseModel):
      conversation_id: str
      message_index: int
      feedback: str
      comment: Optional[str] = None


@router.post("")
async def chat(
      request: ChatRequest,
      user: User = Depends(get_current_user)
):
      """Envoie un message et retourne la reponse complete."""
      if not request.message.strip():
                raise HTTPException(status_code=400, detail="Le message ne peut pas etre vide")

      result = await rag_service.chat(
          message=request.message,
          conversation_id=request.conversation_id,
          user_id=user.id,
          department_filter=request.department_filter,
      )
      return result


@router.post("/stream")
async def chat_stream(
      request: ChatRequest,
      user: User = Depends(get_current_user)
):
      """Envoie un message et streame la reponse token par token (SSE)."""
      if not request.message.strip():
                raise HTTPException(status_code=400, detail="Le message ne peut pas etre vide")

      async def generate():
                try:
                              async for event in rag_service.chat_stream(
                                                message=request.message,
                                                conversation_id=request.conversation_id,
                                                user_id=user.id,
                                                department_filter=request.department_filter,
                              ):
                                                yield f"data: {json.dumps(event)}\n\n"
                except Exception as e:
                              yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
              generate(),
              media_type="text/event-stream",
              headers={
                            "Cache-Control": "no-cache",
                            "X-Accel-Buffering": "no",
              }
    )


@router.get("/conversations")
async def list_conversations(user: User = Depends(get_current_user)):
      """Liste toutes les conversations de l'utilisateur connecte."""
      from app.services.memory_service import MemoryService
      memory = MemoryService()
      return await memory.list_conversations(user.id)


@router.get("/conversations/{conversation_id}")
async def get_conversation(
      conversation_id: str,
      user: User = Depends(get_current_user)
):
      """Recupere l'historique complet d'une conversation."""
      from app.services.memory_service import MemoryService
      memory = MemoryService()
      history = await memory.get_history(conversation_id)
      if not history:
                raise HTTPException(status_code=404, detail="Conversation non trouvee")
            return {"conversation_id": conversation_id, "messages": history}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
      conversation_id: str,
      user: User = Depends(get_current_user)
):
      """Supprime une conversation."""
    from app.services.memory_service import MemoryService
    memory = MemoryService()
    await memory.delete_conversation(conversation_id, user.id)
    return {"status": "deleted", "conversation_id": conversation_id}


@router.post("/feedback")
async def submit_feedback(
      request: FeedbackRequest,
      user: User = Depends(get_current_user)
):
      """Enregistre le feedback utilisateur sur une reponse."""
    if request.feedback not in ["positive", "negative"]:
              raise HTTPException(status_code=400, detail="Feedback doit etre 'positive' ou 'negative'")

    from app.services.stats_service import StatsService
    stats = StatsService()
    await stats.save_feedback(
              user_id=user.id,
              conversation_id=request.conversation_id,
              message_index=request.message_index,
              feedback=request.feedback,
              comment=request.comment,
    )
    return {"status": "ok"}
