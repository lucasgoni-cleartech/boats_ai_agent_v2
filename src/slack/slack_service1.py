"""Slack Bot service using Socket Mode with Conversational Agent integration."""

import asyncio
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

        # Register message handler for DMs
        @self.app.event("message")
        async def on_message(body, say, event, logger):
            """Handle direct messages using conversational agent."""
            try:
                # Filter only DMs and allowed users
                channel: str = event.get("channel", "")
                user_id: str = event.get("user", "")
                text: str = event.get("text", "")

                # Only process DMs
                if not channel.startswith("D"):
                    return
                
                # Check allowed user if configured
                if slack_config.allowed_user_id and user_id != slack_config.allowed_user_id:
                    logger.info("Ignoring message from unauthorized user", extra={
                        "user_id": user_id,
                        "allowed_user_id": slack_config.allowed_user_id
                    })
                    return

                logger.info("Processing DM message", extra={
                    "user_id": user_id,
                    "text": text[:100],  # Log first 100 chars for privacy
                    "channel": channel
                })

                # Use DSPy conversational agent
                response_data = await self.agent.process_query(text, user_id)
                formatted_response = self._format_response_for_slack(response_data)

                await say(formatted_response)
                logger.info("Sent response", extra={
                    "response_length": len(formatted_response),
                    "user_id": user_id,
                    "message_type": "simple_response"
                })

            except Exception as e:
                logger.error("Error handling DM message", extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "user_id": event.get("user", "unknown")
                })
                # Send error message to user
                try:
                    await say("😅 Something went wrong processing your message. Please try again or type 'help' for assistance.")
                except Exception:
                    pass  # If we can't even send error message, just log it

        # Register app_mention handler
        @self.app.event("app_mention")
        async def on_app_mention(body, say, event, logger):
            """Handle app mentions using conversational agent."""
            try:
                logger.info("App mention handler started")
                user_id: str = event.get("user", "")
                text: str = event.get("text", "")
                channel: str = event.get("channel", "")
                logger.info(f"Extracted: user={user_id}, text={text}, channel={channel}")

                # Check allowed user if configured
                logger.info(f"Checking auth: allowed_user={slack_config.allowed_user_id}, current_user={user_id}")
                if slack_config.allowed_user_id and user_id != slack_config.allowed_user_id:
                    logger.info("Ignoring mention from unauthorized user", extra={
                        "user_id": user_id,
                        "allowed_user_id": slack_config.allowed_user_id
                    })
                    return

                # Remove bot mention from text
                # Slack mentions come as <@BOTID> text, we want just the text part
                import re
                clean_text = re.sub(r'<@[UW][A-Z0-9]+>', '', text).strip()
                logger.info(f"Text cleaned: '{clean_text}'")

                logger.info("Processing app mention", extra={
                    "user_id": user_id,
                    "text": clean_text[:100],
                    "channel": channel
                })

                # Use DSPy conversational agent
                response_data = await self.agent.process_query(clean_text, user_id)
                formatted_response = self._format_response_for_slack(response_data)

                logger.info(f"About to send response: '{formatted_response}'")
                await say(formatted_response)
                logger.info("Response sent successfully")
                logger.info("Sent mention response", extra={
                    "response_length": len(formatted_response),
                    "user_id": user_id,
                    "message_type": "simple_response"
                })

            except Exception as e:
                import traceback
                logger.error("Error handling app mention", extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "user_id": event.get("user", "unknown"),
                    "traceback": traceback.format_exc(),
                    "clean_text": clean_text if 'clean_text' in locals() else "Not set"
                })
                try:
                    await say("😅 Something went wrong processing your mention. Please try again or type 'help' for assistance.")
                except Exception:
                    pass

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
        elif status == "clarification_needed":
            return f"🤔 {message}"
        elif intent == "data_query" and response_data.get("data"):
            # For data queries, show data info
            data_count = len(response_data.get("data", []))
            return f"📊 {message}\n\n*Retrieved {data_count} rows of data*"
        elif intent == "capabilities":
            return f"🤖 {message}"
        elif intent == "friendly":
            return f"👋 {message}"
        elif intent == "executive_summary":
            return f"📈 {message}"
        elif intent == "drill_down":
            return f"🔍 {message}"
        elif intent == "data_source_info":
            return f"📋 {message}"
        elif intent == "conversation_management":
            return f"🔄 {message}"
        else:
            return message

    async def stop(self) -> None:
        """Stop the Slack service cleanly."""
        if not self._running:
            logger.warning("SlackService is not running")
            return

        logger.info("Stopping SlackService...")

        try:
            # Close Socket Mode handler with timeout
            if self.socket_mode_handler is not None:
                try:
                    await asyncio.wait_for(self.socket_mode_handler.close(), timeout=2.0)
                except asyncio.TimeoutError:
                    logger.warning("Socket mode handler close timed out")
                self.socket_mode_handler = None

            # Close AsyncWebClient to avoid unclosed session warnings
            if self.app is not None and hasattr(self.app, "client") and hasattr(self.app.client, "close"):
                try:
                    await asyncio.wait_for(self.app.client.close(), timeout=1.0)
                except asyncio.TimeoutError:
                    logger.warning("App client close timed out")

            self.app = None
            self.agent = None
            self._running = False
            logger.info("SlackService stopped successfully")

        except Exception as e:
            logger.error("Error stopping SlackService", extra={"error": str(e)})
            self._running = False  # Force running to false even on error