"""
Bot Microsoft Teams - RAG Expert Metier
Integre le chatbot RAG dans Microsoft Teams via le Bot Framework SDK
"""
import os
import httpx
from aiohttp import web
from botbuilder.core import (
    ActivityHandler,
    TurnContext,
    CardFactory,
    MessageFactory,
)
from botbuilder.integration.aiohttp import CloudAdapter, ConfigurationBotFrameworkAuthentication
from botbuilder.schema import Activity, ActivityTypes
from botframework.connector.auth import AuthenticationConfiguration
import json

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


class RAGExpertBot(ActivityHandler):
      """Bot Teams qui interroge le backend RAG."""

    async def on_message_activity(self, turn_context: TurnContext):
              """Traite les messages entrants."""
              user_message = turn_context.activity.text
              user_id = turn_context.activity.from_property.id
              conversation_id = f"teams_{turn_context.activity.conversation.id}"

        if not user_message or not user_message.strip():
                      await turn_context.send_activity("Bonjour ! Posez-moi une question sur la documentation.")
                      return

        if user_message.strip().lower() in ["/aide", "/help"]:
                      await self._send_help_card(turn_context)
                      return

        if user_message.strip().lower() in ["/nouveau", "/new", "/reset"]:
                      conversation_id = f"teams_{user_id}_{int(os.times()[4])}"
                      await turn_context.send_activity("Nouvelle conversation commencee !")
                      return

        await turn_context.send_activity(Activity(type=ActivityTypes.typing))

        try:
                      async with httpx.AsyncClient(timeout=60.0) as client:
                                        response = await client.post(
                                                              f"{BACKEND_URL}/api/v1/chat",
                                                              json={
                                                                                        "message": user_message,
                                                                                        "conversation_id": conversation_id,
                                                              },
                                                              headers={"X-Teams-User-ID": user_id},
                                        )

                          if response.status_code != 200:
                                                await turn_context.send_activity(
                                                                          "Desolee, une erreur s'est produite. Veuillez reessayer."
                                                )
                                                return

                data = response.json()
                answer = data.get("answer", "")
                sources = data.get("sources", [])
                confidence = data.get("confidence", "medium")

                card = self._build_answer_card(answer, sources, confidence)
                await turn_context.send_activity(
                                      MessageFactory.attachment(CardFactory.adaptive_card(card))
                )

except httpx.TimeoutException:
            await turn_context.send_activity(
                              "La recherche prend trop de temps. Veuillez simplifier votre question."
            )
except Exception as e:
            await turn_context.send_activity(
                              f"Une erreur s'est produite : {str(e)[:100]}"
            )

    async def on_members_added_activity(self, members_added, turn_context: TurnContext):
              """Message de bienvenue lors de l'ajout du bot."""
        for member in members_added:
                      if member.id != turn_context.activity.recipient.id:
                                        welcome_card = self._build_welcome_card()
                                        await turn_context.send_activity(
                                            MessageFactory.attachment(CardFactory.adaptive_card(welcome_card))
                                        )

    def _build_answer_card(self, answer: str, sources: list, confidence: str) -> dict:
              """Construit une Adaptive Card avec la reponse et les sources."""
        confidence_color = {
                      "high": "Good",
                      "medium": "Warning",
                      "low": "Attention"
        }.get(confidence, "Warning")

        confidence_text = {
                      "high": "Haute confiance",
                      "medium": "Confiance moyenne",
                      "low": "Faible confiance - verifiez les sources"
        }.get(confidence, "")

        body = [
                      {
                                        "type": "TextBlock",
                                        "text": answer,
                                        "wrap": True,
                                        "size": "Default"
                      }
        ]

        if confidence_text:
                      body.append({
                                        "type": "TextBlock",
                                        "text": confidence_text,
                                        "color": confidence_color,
                                        "size": "Small",
                                        "isSubtle": True
                      })

        if sources:
                      body.append({
                                        "type": "TextBlock",
                                        "text": "**Sources :**",
                                        "weight": "Bolder",
                                        "size": "Small",
                                        "spacing": "Medium"
                      })
                      for source in sources[:3]:
                                        body.append({
                                                              "type": "TextBlock",
                                                              "text": f"- {source.get('file', '')}",
                                                              "size": "Small",
                                                              "isSubtle": True,
                                                              "wrap": True
                                        })

                  return {
                                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                                "type": "AdaptiveCard",
                                "version": "1.5",
                                "body": body,
                                "actions": [
                                                  {
                                                                        "type": "Action.Submit",
                                                                        "title": "Pouce haut",
                                                                        "data": {"action": "feedback", "value": "positive"}
                                                  },
                                                  {
                                                                        "type": "Action.Submit",
                                                                        "title": "Pouce bas",
                                                                        "data": {"action": "feedback", "value": "negative"}
                                                  }
                                ]
                  }

    def _build_welcome_card(self) -> dict:
              """Carte de bienvenue."""
              return {
                  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                  "type": "AdaptiveCard",
                  "version": "1.5",
                  "body": [
                      {
                          "type": "TextBlock",
                          "text": "Expert Metier RAG",
                          "size": "Large",
                          "weight": "Bolder"
                      },
                      {
                          "type": "TextBlock",
                          "text": "Je suis votre assistant expert metier. Posez-moi vos questions sur la documentation interne.",
                          "wrap": True
                      },
                      {
                          "type": "TextBlock",
                          "text": "**Commandes disponibles :**\n- /aide - Afficher l'aide\n- /nouveau - Nouvelle conversation",
                          "wrap": True,
                          "size": "Small"
                      }
                  ]
              }

    async def _send_help_card(self, turn_context: TurnContext):
              """Envoie la carte d'aide."""
              help_card = {
                  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                  "type": "AdaptiveCard",
                  "version": "1.5",
                  "body": [
                      {
                          "type": "TextBlock",
                          "text": "Aide - Expert Metier RAG",
                          "size": "Large",
                          "weight": "Bolder"
                      },
                      {
                          "type": "TextBlock",
                          "text": "Posez vos questions en langage naturel sur la documentation interne.",
                          "wrap": True
                      },
                      {
                          "type": "TextBlock",
                          "text": "**Exemples :**",
                          "weight": "Bolder"
                      },
                      {
                          "type": "TextBlock",
                          "text": "- Quelle est la procedure de validation des contrats ?\n- Comment fonctionne le processus de recrutement ?\n- Quels sont les seuils budgetaires d'approbation ?",
                          "wrap": True
                      }
                  ]
              }
              await turn_context.send_activity(
                  MessageFactory.attachment(CardFactory.adaptive_card(help_card))
              )


def create_app():
      """Cree l'application aiohttp pour le bot Teams."""
      from botframework.connector.auth import SimpleCredentialProvider

    app_id = os.getenv("TEAMS_APP_ID", "")
    app_password = os.getenv("TEAMS_APP_PASSWORD", "")

    settings = type("Settings", (), {
              "APP_ID": app_id,
              "APP_PASSWORD": app_password,
    })()

    adapter = CloudAdapter(
              ConfigurationBotFrameworkAuthentication(settings)
    )

    bot = RAGExpertBot()

    async def messages(req: web.Request) -> web.Response:
              if req.method == "POST":
                            body = await req.json()
                            activity = Activity().deserialize(body)
                            auth_header = req.headers.get("Authorization", "")
                            response = await adapter.process(req, activity)
                            if response:
                                              return web.json_response(data=response.body)
                                          return web.Response(status=201)
                        return web.Response(status=405)

    web_app = web.Application()
    web_app.router.add_post("/api/messages", messages)
    return web_app


if __name__ == "__main__":
      port = int(os.getenv("PORT", 3978))
    app = create_app()
    print(f"Bot Teams demarre sur le port {port}")
    web.run_app(app, host="0.0.0.0", port=port)
