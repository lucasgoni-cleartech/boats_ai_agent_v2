"""
Basic tests for the conversational agent.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from pathlib import Path

from src.modules.agent.conversational_agent import ConversationalAgent


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        "agent": {
            "name": "Test Agent",
            "version": "1.0.0-test"
        },
        "looker": {
            "base_url": "https://test.looker.com",
            "client_id": "test_client",
            "client_secret": "test_secret",
            "explore": {
                "model": "test_model",
                "explore": "test_explore"
            }
        },
        "dspy": {
            "model": "openai/gpt-4",
            "temperature": 0.1,
            "max_tokens": 1000
        },
        "memory": {
            "type": "in_memory",
            "max_history_turns": 10
        }
    }


@pytest.fixture
def mock_recipes():
    """Mock recipes for testing."""
    return {
        "recipes": [
            {
                "name": "test_recipe",
                "description": "Test recipe",
                "triggers": ["test query"],
                "query_template": {
                    "dimensions": ["country"],
                    "measures": ["revenue"],
                    "limit": 10
                }
            }
        ],
        "parameter_mappings": {
            "dimensions": {"country": "country"},
            "measures": {"revenue": "revenue"}
        }
    }


class TestConversationalAgent:
    """Test cases for ConversationalAgent."""
    
    @patch('src.modules.agent.conversational_agent.yaml.safe_load')
    @patch('src.modules.agent.conversational_agent.json.load')
    @patch('builtins.open')
    def test_initialization(self, mock_open, mock_json_load, mock_yaml_load, mock_config, mock_recipes):
        """Test agent initialization."""
        mock_yaml_load.return_value = mock_config
        mock_json_load.return_value = mock_recipes
        
        agent = ConversationalAgent("test_config.yaml")
        
        assert agent.config == mock_config
        assert agent.memory is not None
        assert agent.looker_client is not None
        assert agent.recipes == mock_recipes
    
    @patch('src.modules.agent.conversational_agent.yaml.safe_load')
    @patch('src.modules.agent.conversational_agent.json.load')
    @patch('builtins.open')
    @pytest.mark.asyncio
    async def test_intent_detection(self, mock_open, mock_json_load, mock_yaml_load, mock_config, mock_recipes):
        """Test intent detection functionality."""
        mock_yaml_load.return_value = mock_config
        mock_json_load.return_value = mock_recipes
        
        agent = ConversationalAgent("test_config.yaml")
        
        # Mock the triage module
        agent.triage_module = Mock()
        mock_result = Mock()
        mock_result.intent = "GATHER_DATA_FROM_LOOKER"
        agent.triage_module.return_value = mock_result
        
        result = await agent._detect_intent("show me revenue")
        
        assert result.intent == "GATHER_DATA_FROM_LOOKER"
        agent.triage_module.assert_called_once()
    
    def test_capabilities_query(self, mock_config, mock_recipes):
        """Test capabilities query handling."""
        with patch('src.modules.agent.conversational_agent.yaml.safe_load') as mock_yaml, \
             patch('src.modules.agent.conversational_agent.json.load') as mock_json, \
             patch('builtins.open'):
            
            mock_yaml.return_value = mock_config
            mock_json.return_value = mock_recipes
            
            agent = ConversationalAgent("test_config.yaml")
            response = agent._handle_capabilities_query()
            
            assert response["status"] == "success"
            assert response["intent"] == "capabilities"
            assert "Query Looker data" in response["message"]
    
    def test_friendly_conversation(self, mock_config, mock_recipes):
        """Test friendly conversation handling."""
        with patch('src.modules.agent.conversational_agent.yaml.safe_load') as mock_yaml, \
             patch('src.modules.agent.conversational_agent.json.load') as mock_json, \
             patch('builtins.open'):
            
            mock_yaml.return_value = mock_config
            mock_json.return_value = mock_recipes
            
            agent = ConversationalAgent("test_config.yaml")
            response = agent._handle_friendly_conversation("hello")
            
            assert response["status"] == "success"
            assert response["intent"] == "friendly"
            assert "Hello" in response["message"]
    
    def test_query_from_recipe(self, mock_config, mock_recipes):
        """Test building query from recipe."""
        with patch('src.modules.agent.conversational_agent.yaml.safe_load') as mock_yaml, \
             patch('src.modules.agent.conversational_agent.json.load') as mock_json, \
             patch('builtins.open'):
            
            mock_yaml.return_value = mock_config
            mock_json.return_value = mock_recipes
            
            agent = ConversationalAgent("test_config.yaml")
            query = agent._build_query_from_recipe("test_recipe", {"limit": 5})
            
            assert query["dimensions"] == ["country"]
            assert query["measures"] == ["revenue"]
            assert query["limit"] == 5
    
    def test_session_info(self, mock_config, mock_recipes):
        """Test session info retrieval."""
        with patch('src.modules.agent.conversational_agent.yaml.safe_load') as mock_yaml, \
             patch('src.modules.agent.conversational_agent.json.load') as mock_json, \
             patch('builtins.open'):
            
            mock_yaml.return_value = mock_config
            mock_json.return_value = mock_recipes
            
            agent = ConversationalAgent("test_config.yaml")
            info = agent.get_session_info()
            
            assert "agent_status" in info
            assert "looker_connected" in info
            assert "memory_stats" in info
            assert "available_recipes" in info