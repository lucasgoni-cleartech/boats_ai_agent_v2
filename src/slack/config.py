"""Simple configuration for Slack integration."""

import os
from typing import Optional

class SlackConfig:
    """Simple Slack configuration using environment variables."""
    
    def __init__(self):
        # Slack tokens (required)
        self.slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
        self.slack_app_token = os.getenv("SLACK_APP_TOKEN") 
        self.slack_signing_secret = os.getenv("SLACK_SIGNING_SECRET")
        
        # Security
        self.allowed_user_id = os.getenv("ALLOWED_USER_ID")
        self.allowed_channel_id = os.getenv("SLACK_ALLOWED_CHANNEL_ID")
        
        # OpenAI (already configured)
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Validate required fields
        if not all([self.slack_bot_token, self.slack_app_token, self.slack_signing_secret]):
            raise ValueError("Missing required Slack environment variables. Check SLACK_BOT_TOKEN, SLACK_APP_TOKEN, and SLACK_SIGNING_SECRET")
        
        if not self.openai_api_key:
            raise ValueError("Missing OPENAI_API_KEY environment variable")

# Global config instance
slack_config = SlackConfig()