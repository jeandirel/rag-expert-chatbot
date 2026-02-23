"""
Routes API Admin - Dashboard, statistiques, gestion utilisateurs
Acces restreint au role ChatbotAdmin
"""
import json
import time
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
import io
import csv

from app.core.auth import get_current_user, require_admin, User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
async def get_stats(admin: User = Depends(require_admin)):
      """Retourne les statistiques globales pour le dashboard admin."""
      import redis as redis_lib
      from app.core.config import settings

    r = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)

    queries_raw = r.lrange("stats:queries", 0, 999)
    queries = [json.loads(q) for q in queries_raw]

    total_queries = int(r.get("stats:total_queries") or 0)
    now = time.time()
    today_queries = [q for q in queries if now - q.get("timestamp", 0) < 86400]
    week_queries = [q for q in queries if now - q.get("timestamp", 0) < 604800]

    from collections import Counter
    top_questions = Counter([q.get("question", "")[:100] for q in queries]).most_common(20)

    all_sources = []
    for q in queries:
              for s in q.get("sources", []):
                            if isinstance(s, dict):
                                              all_sources.append(s.get("file", ""))
                                  top_sources = Counter(filter(None, all_sources)).most_common(10)

          confidence_dist = Counter(q.get("confidence", "unknown") for q in queries)

    feedbacks_raw = r.lrange("stats:feedbacks", 0, 999)
    feedbacks = [json.loads(f) for f in feedbacks_raw]
    positive = sum(1 for f in feedbacks if f.get("feedback") == "positive")
    negative = sum(1 for f in feedbacks if f.get("feedback") == "negative")
    total_feedback = positive + negative
    satisfaction_rate = round((positive / total_feedback * 100) if total_feedback > 0 else 0, 1)

    response_times = [q.get("response_time_ms", 0) for q in queries if q.get("response_time_ms")]
    avg_response_time = round(sum(response_times) / len(response_times), 0) if response_times else 0

    daily_activity = _compute_daily_activity(queries)

    return {
              "total_queries": total_queries,
              "queries_today": len(today_queries),
              "queries_week": len(week_queries),
              "avg_response_time_ms": avg_response_time,
              "satisfaction_rate": satisfaction_rate,
              "positive_feedback": positive,
              "negative_feedback": negative,
              "top_questions": top_questions,
              "top_sources": top_sources,
              "confidence_distribution": dict(confidence_dist),
              "daily_activity": daily_activity,
    }


@router.get("/conversations")
async def list_all_conversations(
      page: int = Query(1, ge=1),
      per_page: int = Query(50, ge=1, le=200),
      user_filter: Optional[str] = None,
      admin: User = Depends(require_admin)
):
      """Liste toutes les conversations de tous les utilisateurs."""
      import redis as redis_lib
      from app.core.config import settings

    r = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
    pattern = f"conv:*"
    keys = r.keys(pattern)

    conversations = []
    for key in keys:
              data = r.get(key)
              if data:
                            try:
                                              history = json.loads(data)
                                              conv_id = key.replace("conv:", "")
                                              if history:
                                                                    conv_meta = r.get(f"conv_meta:{conv_id}")
                                                                    meta = json.loads(conv_meta) if conv_meta else {}
                                                                    user_id = meta.get("user_id", "unknown")

                                                  if user_filter and user_filter.lower() not in user_id.lower():
                                                                            continue

                                                  conversations.append({
                                                      "conversation_id": conv_id,
                                                      "user_id": user_id,
                                                      "message_count": len(history),
                                                      "last_message": history[-1].get("question", "")[:100] if history else "",
                                                      "started_at": meta.get("started_at", ""),
                                                      "last_activity": meta.get("last_activity", ""),
                                              })
except Exception:
                continue

    conversations.sort(key=lambda x: x.get("last_activity", ""), reverse=True)
    total = len(conversations)
    start = (page - 1) * per_page
    end = start + per_page

    return {
              "total": total,
              "page": page,
              "per_page": per_page,
              "conversations": conversations[start:end]
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation_detail(
      conversation_id: str,
      admin: User = Depends(require_admin)
):
      """Recupere le detail complet d'une conversation (admin)."""
      import redis as redis_lib
      from app.core.config import settings

    r = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
    data = r.get(f"conv:{conversation_id}")
    if not data:
              from fastapi import HTTPException
              raise HTTPException(status_code=404, detail="Conversation non trouvee")

    history = json.loads(data)
    meta_data = r.get(f"conv_meta:{conversation_id}")
    meta = json.loads(meta_data) if meta_data else {}

    return {
              "conversation_id": conversation_id,
              "user_id": meta.get("user_id", "unknown"),
              "started_at": meta.get("started_at", ""),
              "last_activity": meta.get("last_activity", ""),
              "messages": history,
    }


@router.get("/users")
async def list_users(admin: User = Depends(require_admin)):
      """Liste les utilisateurs avec leurs statistiques."""
      import redis as redis_lib
      from app.core.config import settings

    r = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
    user_keys = r.keys("stats:user:*:query_count")

    users = []
    for key in user_keys:
              user_id = key.split(":")[2]
              query_count = int(r.get(key) or 0)
              users.append({
                  "user_id": user_id,
                  "query_count": query_count,
              })

    users.sort(key=lambda x: x["query_count"], reverse=True)
    return {"total": len(users), "users": users}


@router.get("/export/conversations")
async def export_conversations(
      format: str = Query("csv", regex="^(csv|json)$"),
      admin: User = Depends(require_admin)
):
      """Exporte toutes les conversations en CSV ou JSON."""
      import redis as redis_lib
      from app.core.config import settings

    r = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
    keys = r.keys("conv:*")

    all_data = []
    for key in keys:
              data = r.get(key)
              if data:
                            try:
                                              history = json.loads(data)
                                              conv_id = key.replace("conv:", "")
                                              meta_data = r.get(f"conv_meta:{conv_id}")
                                              meta = json.loads(meta_data) if meta_data else {}
                                              for msg in history:
                                                                    all_data.append({
                                                                                              "conversation_id": conv_id,
                                                                                              "user_id": meta.get("user_id", ""),
                                                                                              "question": msg.get("question", ""),
                                                                                              "answer": msg.get("answer", "")[:500],
                                                                                              "sources": ", ".join([s.get("file", "") for s in msg.get("sources", [])]),
                                                                                              "confidence": msg.get("confidence", ""),
                                                                    })
                            except Exception:
                                              continue

                    if format == "json":
                              return all_data

    output = io.StringIO()
    if all_data:
              writer = csv.DictWriter(output, fieldnames=all_data[0].keys())
        writer.writeheader()
        writer.writerows(all_data)

    return StreamingResponse(
              iter([output.getvalue()]),
              media_type="text/csv",
              headers={"Content-Disposition": "attachment; filename=conversations.csv"}
    )


@router.post("/reindex")
async def trigger_reindex(
      full: bool = False,
      admin: User = Depends(require_admin)
):
      """Declenche une reindexation des documents en arriere-plan."""
    from fastapi.background import BackgroundTasks
    from ingestion.pipeline import IngestionPipeline

    pipeline = IngestionPipeline()
    if full:
              import redis as redis_lib
        from app.core.config import settings
        r = redis_lib.from_url(settings.REDIS_URL)
        r.delete("ingestion:tracker")

    import asyncio
    asyncio.create_task(asyncio.to_thread(pipeline.process_all))
    return {"status": "reindex_started", "full": full}


def _compute_daily_activity(queries: list) -> list:
      """Calcule l'activite quotidienne sur les 30 derniers jours."""
    from datetime import datetime, timedelta
    from collections import defaultdict

    daily = defaultdict(int)
    for q in queries:
              ts = q.get("timestamp", 0)
        if ts:
                      date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                      daily[date_str] += 1

    result = []
    for i in range(29, -1, -1):
              date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        result.append({"date": date, "queries": daily.get(date, 0)})

    return result
