"""
Tests for conversation memory functionality.
"""

import pytest
from datetime import datetime

from src.memory.conversation_memory import ConversationMemory


class TestConversationMemory:
    """Test cases for ConversationMemory."""
    
    def test_initialization(self):
        """Test memory initialization."""
        memory = ConversationMemory()
        
        assert memory.conversation_history == []
        assert "preferences" in memory.user_profile
        assert "data_interests" in memory.user_profile
        assert "created_at" in memory.user_profile
    
    def test_add_turn(self):
        """Test adding conversation turns."""
        memory = ConversationMemory()
        
        memory.add_turn("test query", "test response", {"intent": "test"})
        
        assert len(memory.conversation_history) == 1
        turn = memory.conversation_history[0]
        assert turn["user_query"] == "test query"
        assert turn["agent_response"] == "test response"
        assert turn["metadata"]["intent"] == "test"
        assert "timestamp" in turn
    
    def test_get_recent_history(self):
        """Test retrieving recent history."""
        memory = ConversationMemory()
        
        # Add multiple turns
        for i in range(7):
            memory.add_turn(f"query {i}", f"response {i}")
        
        recent = memory.get_recent_history(3)
        assert len(recent) == 3
        assert recent[0]["user_query"] == "query 4"  # Last 3 should be 4, 5, 6
        assert recent[-1]["user_query"] == "query 6"
        
        # Test with more turns than available
        recent_all = memory.get_recent_history(10)
        assert len(recent_all) == 7
    
    def test_history_summary(self):
        """Test history summary generation."""
        memory = ConversationMemory()
        
        # Empty history
        summary = memory.get_history_summary()
        assert summary == "No previous conversation history."
        
        # With history
        memory.add_turn("show me revenue", "Here's the revenue data")
        memory.add_turn("what about by country?", "Here's revenue by country")
        
        summary = memory.get_history_summary()
        assert "show me revenue" in summary
        assert "what about by country?" in summary
        assert "User:" in summary
    
    def test_user_profile_updates(self):
        """Test user profile updates."""
        memory = ConversationMemory()
        
        # Test profile updates
        memory.update_user_profile({"role": "analyst", "company": "test_corp"})
        
        assert memory.user_profile["role"] == "analyst"
        assert memory.user_profile["company"] == "test_corp"
        assert "updated_at" in memory.user_profile
    
    def test_data_interests(self):
        """Test data interest tracking."""
        memory = ConversationMemory()
        
        memory.add_data_interest("revenue_analysis")
        memory.add_data_interest("customer_analytics")
        memory.add_data_interest("revenue_analysis")  # Duplicate
        
        interests = memory.user_profile["data_interests"]
        assert len(interests) == 2  # No duplicates
        assert "revenue_analysis" in interests
        assert "customer_analytics" in interests
    
    def test_query_patterns(self):
        """Test query pattern tracking."""
        memory = ConversationMemory()
        
        memory.add_query_pattern("trend_queries")
        memory.add_query_pattern("comparison_queries")
        memory.add_query_pattern("trend_queries")  # Duplicate
        
        patterns = memory.user_profile["query_patterns"]
        assert len(patterns) == 2  # No duplicates
        assert "trend_queries" in patterns
        assert "comparison_queries" in patterns
    
    def test_user_profile_summary(self):
        """Test user profile summary generation."""
        memory = ConversationMemory()
        
        # Empty profile
        summary = memory.get_user_profile_summary()
        assert "New user" in summary
        
        # With profile data
        memory.update_user_profile({"preferences": {"chart_type": "bar"}})
        memory.add_data_interest("revenue_analysis")
        memory.add_query_pattern("trend_analysis")
        
        summary = memory.get_user_profile_summary()
        assert "chart_type: bar" in summary
        assert "revenue_analysis" in summary
        assert "trend_analysis" in summary
    
    def test_clear_history(self):
        """Test clearing conversation history."""
        memory = ConversationMemory()
        
        memory.add_turn("test", "test")
        memory.update_user_profile({"role": "analyst"})
        
        memory.clear_history()
        
        assert len(memory.conversation_history) == 0
        assert memory.user_profile["role"] == "analyst"  # Profile preserved
    
    def test_reset_session(self):
        """Test full session reset."""
        memory = ConversationMemory()
        
        memory.add_turn("test", "test")
        memory.update_user_profile({"role": "analyst"})
        
        memory.reset_session()
        
        assert len(memory.conversation_history) == 0
        assert memory.user_profile.get("role") is None  # Profile reset
        assert "preferences" in memory.user_profile  # Structure preserved
    
    def test_session_stats(self):
        """Test session statistics."""
        memory = ConversationMemory()
        
        memory.add_turn("test1", "response1")
        memory.add_turn("test2", "response2")
        memory.add_data_interest("revenue")
        memory.add_query_pattern("trends")
        
        stats = memory.get_session_stats()
        
        assert stats["total_turns"] == 2
        assert stats["data_interests_count"] == 1
        assert stats["query_patterns_count"] == 1
        assert "profile_created" in stats
        assert "profile_updated" in stats