"""
Simplified memory utilities for conversational agent.

Provides basic conversation context management without the full MCP infrastructure.
For MVP, we'll use simple in-memory storage that can be extended to persistent storage later.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ConversationMemory:
    """
    Simple conversation memory for MVP conversational agent.
    
    Manages conversation history and user profile for a single session.
    Can be extended to use persistent storage (MCP, database, etc.) later.
    """

    def __init__(self):
        """Initialize in-memory conversation storage."""
        self.conversation_history: List[Dict[str, Any]] = []
        self.user_profile: Dict[str, Any] = {
            "preferences": {},
            "data_interests": [],
            "query_patterns": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        logger.info("ConversationMemory initialized with in-memory storage")

    def add_turn(self, user_query: str, agent_response: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a conversation turn to history."""
        turn = {
            "timestamp": datetime.now().isoformat(),
            "user_query": user_query,
            "agent_response": agent_response,
            "metadata": metadata or {}
        }
        self.conversation_history.append(turn)
        logger.debug(f"Added conversation turn: {len(self.conversation_history)} total turns")

    def get_recent_history(self, num_turns: int = 5) -> List[Dict[str, Any]]:
        """Get recent conversation turns."""
        return self.conversation_history[-num_turns:] if self.conversation_history else []

    def get_history_summary(self) -> str:
        """Get a summary of recent conversation history."""
        recent_turns = self.get_recent_history()
        if not recent_turns:
            return "No previous conversation history."
        
        summary_parts = []
        for turn in recent_turns:
            user_query = turn["user_query"][:100] + "..." if len(turn["user_query"]) > 100 else turn["user_query"]
            summary_parts.append(f"User: {user_query}")
        
        return "\n".join(summary_parts)

    def update_user_profile(self, profile_updates: Dict[str, Any]) -> None:
        """Update user profile with new information."""
        self.user_profile.update(profile_updates)
        self.user_profile["updated_at"] = datetime.now().isoformat()
        logger.debug(f"Updated user profile: {profile_updates}")

    def get_user_profile_summary(self) -> str:
        """Get a summary of the user profile."""
        profile = self.user_profile
        summary_parts = []
        
        if profile.get("preferences"):
            prefs = ", ".join([f"{k}: {v}" for k, v in profile["preferences"].items()])
            summary_parts.append(f"Preferences: {prefs}")
        
        if profile.get("data_interests"):
            interests = ", ".join(profile["data_interests"])
            summary_parts.append(f"Data interests: {interests}")
        
        if profile.get("query_patterns"):
            patterns = ", ".join(profile["query_patterns"])
            summary_parts.append(f"Query patterns: {patterns}")
        
        return "; ".join(summary_parts) if summary_parts else "New user with no established profile."

    def add_data_interest(self, interest: str) -> None:
        """Add a data interest to user profile."""
        if "data_interests" not in self.user_profile:
            self.user_profile["data_interests"] = []
        
        if interest not in self.user_profile["data_interests"]:
            self.user_profile["data_interests"].append(interest)
            self.user_profile["updated_at"] = datetime.now().isoformat()

    def add_query_pattern(self, pattern: str) -> None:
        """Add a query pattern to user profile."""
        if "query_patterns" not in self.user_profile:
            self.user_profile["query_patterns"] = []
        
        if pattern not in self.user_profile["query_patterns"]:
            self.user_profile["query_patterns"].append(pattern)
            self.user_profile["updated_at"] = datetime.now().isoformat()

    def clear_history(self) -> None:
        """Clear conversation history while preserving user profile."""
        self.conversation_history.clear()
        logger.info("Conversation history cleared")

    def reset_session(self) -> None:
        """Reset both conversation history and user profile."""
        self.conversation_history.clear()
        self.user_profile = {
            "preferences": {},
            "data_interests": [],
            "query_patterns": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        logger.info("Session reset - history and profile cleared")

    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        return {
            "total_turns": len(self.conversation_history),
            "profile_created": self.user_profile.get("created_at"),
            "profile_updated": self.user_profile.get("updated_at"),
            "data_interests_count": len(self.user_profile.get("data_interests", [])),
            "query_patterns_count": len(self.user_profile.get("query_patterns", []))
        }