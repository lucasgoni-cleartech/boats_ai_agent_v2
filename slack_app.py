"""
Slack application entry point for the Conversational Looker Agent.

Simple Slack integration that runs the conversational agent through DMs.
"""

import asyncio
import logging
import sys
import signal
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from src.slack.slack_service1 import SlackService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SlackApp:
    """Main Slack application manager."""
    
    def __init__(self):
        """Initialize Slack application."""
        self.slack_service = SlackService()
        self.shutdown_event = asyncio.Event()
        self.setup_signal_handlers()
        
    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum: int, frame) -> None:
            logger.info(f"Received signal {signum}, initiating shutdown")
            if not self.shutdown_event.is_set():
                self.shutdown_event.set()
            else:
                logger.info("Force shutdown - exiting immediately")
                import sys
                sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start(self):
        """Start the Slack application."""
        logger.info("🐧 Starting Conversational Looker Agent - Slack Integration")
        
        try:
            # Verify environment setup
            await self._verify_setup()
            
            # Start Slack service
            await self.slack_service.start()
            
            logger.info("✅ Slack agent is now running! Send a DM to your Slack bot to interact.")
            logger.info("💬 Available interactions:")
            logger.info("   • Ask questions about data: 'Show me revenue by country'")
            logger.info("   • Get capabilities: 'What can you do?'")
            logger.info("   • Friendly conversation: 'Hello'")
            logger.info("   • Get help: 'help'")
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"Failed to start Slack application: {e}")
            raise
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the Slack application."""
        logger.info("🛑 Stopping Slack application...")

        try:
            if self.slack_service.is_running():
                await asyncio.wait_for(self.slack_service.stop(), timeout=3.0)
            logger.info("✅ Slack application stopped successfully")
        except asyncio.TimeoutError:
            logger.warning("Slack service stop timed out - forcing shutdown")
        except Exception as e:
            logger.error(f"Error stopping Slack application: {e}")
    
    async def _verify_setup(self):
        """Verify that environment is properly configured."""
        import os
        
        required_vars = [
            "OPENAI_API_KEY",
            "SLACK_BOT_TOKEN", 
            "SLACK_APP_TOKEN",
            "SLACK_SIGNING_SECRET"
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            logger.error("Make sure your .env file contains all required Slack and OpenAI credentials")
            raise ValueError(f"Missing environment variables: {missing_vars}")
        
        # Show masked credentials for verification
        openai_key = os.getenv("OPENAI_API_KEY")
        slack_bot = os.getenv("SLACK_BOT_TOKEN")
        
        logger.info(f"✅ OpenAI API key loaded: {openai_key[:10]}...{openai_key[-4:]}")
        logger.info(f"✅ Slack Bot token loaded: {slack_bot[:10]}...{slack_bot[-4:]}")
        
        allowed_user = os.getenv("ALLOWED_USER_ID")
        if allowed_user:
            logger.info(f"✅ Restricted to user: {allowed_user}")
        else:
            logger.info("⚠️  No user restriction (ALLOWED_USER_ID not set)")


async def main():
    """Main application entry point."""
    app = SlackApp()
    
    try:
        await app.start()
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Goodbye!")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)