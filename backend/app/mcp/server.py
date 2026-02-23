"""
MCP Server - Model Context Protocol
Expose le RAG comme source de connaissance pour Claude Desktop, Cursor, etc.

Usage dans Claude Desktop (~/.config/claude/claude_desktop_config.json) :
{
  "mcpServers": {
      "rag-expert-metier": {
            "command": "python",
                  "args": ["-m", "app.mcp.server"],
                        "cwd": "/chemin/vers/rag-expert-chatbot/backend"
    }
      }
      }
      """
import asyncio
import json
import sqlite3
from pathlib import Path

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from app.core.config import settings

app = Server("rag-expert-metier")


def get_rag_service():
      """Lazy import pour eviter les imports circulaires."""
      from app.services.rag_service import RAGService
      return RAGService()


@app.list_tools()
async def list_tools() -> list[types.Tool]:
      """Liste tous les outils MCP disponibles."""
      return [
          types.Tool(
              name="rechercher_documentation",
              description=(
                  "Recherche dans la documentation interne de l'entreprise. "
                  "Utilise la recherche semantique vectorielle pour trouver les passages pertinents. "
                  "Retourne les extraits les plus pertinents avec leurs sources."
              ),
              inputSchema={
                  "type": "object",
                  "properties": {
                      "query": {
                          "type": "string",
                          "description": "La question ou le terme de recherche"
                      },
                      "departement": {
                          "type": "string",
                          "description": "Filtrer par departement (rh, finance, juridique, technique, commercial)",
                          "enum": ["rh", "finance", "juridique", "technique", "commercial", "general"]
                      },
                      "nb_resultats": {
                          "type": "integer",
                          "description": "Nombre de resultats a retourner (defaut: 5)",
                          "default": 5,
                          "minimum": 1,
                          "maximum": 20
                      }
                  },
                  "required": ["query"]
              }
          ),
          types.Tool(
              name="poser_question_expert",
              description=(
                  "Pose une question a l'expert metier RAG. "
                  "Retourne une reponse complete basee sur la documentation interne, "
                  "avec les sources citees."
              ),
              inputSchema={
                  "type": "object",
                  "properties": {
                      "question": {
                          "type": "string",
                          "description": "La question a poser a l'expert"
                      },
                      "departement": {
                          "type": "string",
                          "description": "Contexte de departement pour la recherche"
                      }
                  },
                  "required": ["question"]
              }
          ),
          types.Tool(
              name="lister_documents",
              description="Liste tous les documents indexes dans la base de connaissance avec leurs metadonnees.",
              inputSchema={
                  "type": "object",
                  "properties": {
                      "categorie": {
                          "type": "string",
                          "description": "Filtrer par categorie de document"
                      },
                      "recent_jours": {
                          "type": "integer",
                          "description": "Nombre de jours pour les documents recents (defaut: tous)",
                          "default": 0
                      }
                  }
              }
          ),
          types.Tool(
              name="statistiques_base",
              description="Retourne les statistiques de la base de connaissance (nombre de documents, chunks, etc.).",
              inputSchema={
                  "type": "object",
                  "properties": {}
              }
          )
      ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
      """Execute un outil MCP."""

    if name == "rechercher_documentation":
              rag = get_rag_service()
              query = arguments["query"]
              departement = arguments.get("departement")
              nb_resultats = arguments.get("nb_resultats", 5)

        docs = await rag._retrieve_documents(query, departement)
        docs = docs[:nb_resultats]

        results = []
        for doc in docs:
                      results.append({
                                        "contenu": doc.page_content,
                                        "source": doc.metadata.get("source_file", ""),
                                        "chemin": doc.metadata.get("source_path", ""),
                                        "categorie": doc.metadata.get("category", ""),
                                        "departement": doc.metadata.get("department", ""),
                      })

        return [types.TextContent(
                      type="text",
                      text=json.dumps(results, ensure_ascii=False, indent=2)
        )]

elif name == "poser_question_expert":
        rag = get_rag_service()
        question = arguments["question"]
        departement = arguments.get("departement")

        result = await rag.chat(
                      message=question,
                      user_id="mcp-client",
                      department_filter=departement
        )

        response_text = f"**Reponse :**\n{result['answer']}\n\n"
        if result.get("sources"):
                      response_text += "**Sources :**\n"
                      for source in result["sources"]:
                                        response_text += f"- {source['file']}\n"
                                response_text += f"\n*Confiance : {result.get('confidence', 'inconnue')}*"

        return [types.TextContent(type="text", text=response_text)]

elif name == "lister_documents":
        db_path = Path("ingestion_tracker.db")
        if not db_path.exists():
                      return [types.TextContent(type="text", text="Base de donnees d'indexation non trouvee.")]

        conn = sqlite3.connect(str(db_path))
        query = "SELECT filepath, indexed_at, chunk_count, status FROM indexed_files WHERE status = 'success'"
        rows = conn.execute(query).fetchall()
        conn.close()

        documents = [
                      {
                                        "fichier": Path(r[0]).name,
                                        "indexe_le": r[1],
                                        "chunks": r[2],
                                        "statut": r[3]
                      }
                      for r in rows
        ]

        return [types.TextContent(
                      type="text",
                      text=json.dumps(documents, ensure_ascii=False, indent=2)
        )]

elif name == "statistiques_base":
        db_path = Path("ingestion_tracker.db")
        if not db_path.exists():
                      return [types.TextContent(type="text", text="Base de donnees non trouvee.")]

        conn = sqlite3.connect(str(db_path))
        stats_rows = conn.execute(
                      "SELECT status, COUNT(*), SUM(chunk_count) FROM indexed_files GROUP BY status"
        ).fetchall()
        conn.close()

        stats = {
                      "par_statut": {r[0]: {"fichiers": r[1], "chunks": r[2] or 0} for r in stats_rows},
                      "total_fichiers": sum(r[1] for r in stats_rows),
                      "total_chunks": sum((r[2] or 0) for r in stats_rows),
        }

        return [types.TextContent(
                      type="text",
                      text=json.dumps(stats, ensure_ascii=False, indent=2)
        )]

else:
        return [types.TextContent(type="text", text=f"Outil inconnu : {name}")]


@app.list_resources()
async def list_resources() -> list[types.Resource]:
      """Liste les ressources MCP disponibles."""
    return [
              types.Resource(
                            uri="documents://index",
                            name="Index documentaire",
                            description="Liste complete des documents indexes dans la base de connaissance",
                            mimeType="application/json",
              )
    ]


@app.read_resource()
async def read_resource(uri: str) -> str:
      """Lit une ressource MCP."""
    if uri == "documents://index":
              db_path = Path("ingestion_tracker.db")
        if not db_path.exists():
                      return "[]"
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
                      "SELECT filepath, indexed_at, chunk_count FROM indexed_files WHERE status = 'success'"
        ).fetchall()
        conn.close()
        documents = [{"fichier": Path(r[0]).name, "date": r[1], "chunks": r[2]} for r in rows]
        return json.dumps(documents, ensure_ascii=False, indent=2)
    raise ValueError(f"Ressource inconnue : {uri}")


async def main():
      """Point d'entree du serveur MCP."""
    async with stdio_server() as streams:
              await app.run(
                            streams[0],
                            streams[1],
                            app.create_initialization_options()
              )


if __name__ == "__main__":
      asyncio.run(main())
