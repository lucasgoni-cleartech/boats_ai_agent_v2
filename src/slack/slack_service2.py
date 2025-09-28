"""Slack Bot service using Socket Mode with Conversational Agent integration."""

import logging
from typing import Optional

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler

from .config import slack_config
from ..modules.agent.conversational_agent import ConversationalAgent
from pathlib import Path

logger = logging.getLogger(__name__)


class SlackService:
    """Slack service using Socket Mode for conversational agent."""
    
    def __init__(self) -> None:
        """Initialize Slack service."""
        self.app: Optional[AsyncApp] = None
        self.socket_mode_handler: Optional[AsyncSocketModeHandler] = None
        self.agent: Optional[ConversationalAgent] = None
        self._running: bool = False
        
        # ⬇️ CHANGED: loggear el canal permitido (en vez de allowed_user_id)
        logger.info("SlackService initialized", extra={
            "allowed_channel_id": getattr(slack_config, "allowed_channel_id", None),  # CHANGED
            "has_bot_token": bool(slack_config.slack_bot_token),
            "has_app_token": bool(slack_config.slack_app_token),
        })

    def is_running(self) -> bool:
        """Check if the service is running."""
        return self._running

    async def start(self) -> None:
        """Start the Slack service and setup handlers."""
        if self._running:
            logger.warning("SlackService is already running")
            return

        logger.info("Starting SlackService...")

        # Initialize conversational agent
        config_path = Path(__file__).parent.parent.parent / "config" / "agent_config.yaml"
        self.agent = ConversationalAgent(str(config_path))
        await self.agent.initialize_looker_schema()
        logger.info("ConversationalAgent initialized")

        # Initialize Slack app
        self.app = AsyncApp(
            token=slack_config.slack_bot_token,
            signing_secret=slack_config.slack_signing_secret,
        )

        # ⬇️ ADDED: helper para verificar el único canal permitido
        def _is_allowed_channel(ev: dict) -> bool:
            ch = ev.get("channel", "")
            # Solo canal privado (G...) y que coincida EXACTO con ALLOWED_CHANNEL_ID
            if not ch or not ch.startswith("G"):
                return False
            if getattr(slack_config, "allowed_channel_id", None) and ch != slack_config.allowed_channel_id:
                return False
            return True

        # ⬇️ REMOVED: handler de DMs (message en canal D...), ya no lo usamos
        # @self.app.event("message")
        # async def on_message(...): ...

        # ⬇️ ADDED: handler para mensajes en el canal privado (message.groups)
        @self.app.event("message")
        async def on_private_channel_message(body, say, event, logger):
            """Handle messages ONLY in the single allowed private channel."""
            try:
                channel: str = event.get("channel", "")
                subtype: Optional[str] = event.get("subtype")
                user_id: str = event.get("user", "")
                text: str = event.get("text", "") or ""

                # Ignorar DMs y cualquier otro canal que no sea el permitido
                if not _is_allowed_channel(event):
                    return

                # Ignorar mensajes de bots / ediciones / borrados
                if subtype in {"bot_message", "message_changed", "message_deleted"}:
                    return

                logger.info("Processing channel message", extra={
                    "user_id": user_id,
                    "channel": channel,
                    "text_preview": text[:120],
                })

                # Procesar con tu agente
                response_data = await self.agent.process_query(text, session_id=user_id)

                # Responder en Slack
                formatted_response = self._format_response_for_slack(response_data)
                await say(formatted_response)

                logger.info("Sent response", extra={
                    "response_length": len(formatted_response),
                    "user_id": user_id,
                    "intent": response_data.get("intent", "unknown"),
                    "status": response_data.get("status", "unknown")
                })

            except Exception as e:
                logger.error("Error handling private channel message", extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "user_id": event.get("user", "unknown")
                })
                try:
                    await say("😅 Something went wrong processing your message. Please try again or type 'help' for assistance.")
                except Exception:
                    pass

        # ⬇️ ADDED: handler para menciones al bot en el canal privado (app_mention)
        @self.app.event("app_mention")
        async def on_app_mention(body, say, event, logger):
            """Handle @mentions ONLY in the single allowed private channel."""
            try:
                if not _is_allowed_channel(event):
                    return

                user_id: str = event.get("user", "")
                text: str = event.get("text", "") or ""

                logger.info("Processing app_mention", extra={
                    "user_id": user_id,
                    "channel": event.get("channel"),
                    "text_preview": text[:120],
                })

                response_data = await self.agent.process_query(text, session_id=user_id)
                await say(self._format_response_for_slack(response_data))

            except Exception as e:
                logger.error("Error handling app_mention", extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                })

        # Start Socket Mode connection
        self.socket_mode_handler = AsyncSocketModeHandler(self.app, slack_config.slack_app_token)
        await self.socket_mode_handler.start_async()

        self._running = True
        logger.info("SlackService started successfully")

    def _format_response_for_slack(self, response_data: dict) -> str:
        """Format conversational agent response for Slack."""
        message = response_data.get("message", "")
        status = response_data.get("status", "")
        intent = response_data.get("intent", "")
        
        # Add status emoji based on response type
        if status == "error":
            return f"❌ {message}"
        elif intent == "data_query" and response_data.get("data"):
            # For data queries, show data info
            data_count = len(response_data.get("data", []))
            return f"📊 {message}\n\n*Retrieved {data_count} rows of data*"
        elif intent == "capabilities":
            return f"🤖 {message}"
        elif intent == "friendly":
            return f"👋 {message}"
        else:
            return message

    async def stop(self) -> None:
        """Stop the Slack service cleanly."""
        if not self._running:
            logger.warning("SlackService is not running")
            return

        logger.info("Stopping SlackService...")

        try:
            # Close Socket Mode handler
            if self.socket_mode_handler is not None:
                await self.socket_mode_handler.close()
                self.socket_mode_handler = None

            # Close AsyncWebClient to avoid unclosed session warnings
            if self.app is not None and hasattr(self.app, "client") and hasattr(self.app.client, "close"):
                await self.app.client.close()

            self.app = None
            self.agent = None
            self._running = False
            logger.info("SlackService stopped successfully")

        except Exception as e:
            logger.error("Error stopping SlackService", extra={"error": str(e)})
            raise
