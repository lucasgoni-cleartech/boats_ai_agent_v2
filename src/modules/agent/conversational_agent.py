"""
Main conversational agent for Looker integration.

Orchestrates the conversation flow, intent detection, query building, and response synthesis.
"""

import json
import logging
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

import dspy

from ..signatures.triage import TriageSignature
from ..signatures.query_curator import QueryCuratorSignature  
from ..signatures.response_synthesizer import ResponseSynthesizerSignature
from ..signatures.insight_extractor import InsightExtractionSignature
from ...memory.conversation_memory import ConversationMemory
from ...looker.service import LookerService
from ...looker.schema_loader import explore_schema_loader
from ...looker.query_builder import LookerQueryBuilder
from ...looker.deterministic_query_builder import DeterministicQueryBuilder

logger = logging.getLogger(__name__)


class ConversationalAgent:
    """
    Main conversational agent for Looker data queries.
    
    Handles the complete conversation flow:
    1. Intent detection (triage)
    2. Query curation and building  
    3. Looker API calls
    4. Response synthesis
    5. Memory management
    """

    def __init__(self, config_path: str):
        """Initialize the conversational agent with configuration."""
        self.config = self._load_config(config_path)
        
        # Initialize components
        self.memory = ConversationMemory()
        self.looker_service = self._initialize_looker_service()
        self.schema_loader = explore_schema_loader
        self.query_builder: Optional[LookerQueryBuilder] = None
        self.deterministic_query_builder: Optional[DeterministicQueryBuilder] = None
        self.recipes = self._load_recipes()
        
        # Initialize DSPy modules
        self._initialize_dspy_modules()
        
        # Initialize Looker schema (async, so done separately)
        self.schema: Optional[Dict[str, Any]] = None
        
        logger.info("ConversationalAgent initialized")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)

    def _load_recipes(self) -> Dict[str, Any]:
        """Load Looker query recipes."""
        recipe_path = Path(__file__).parent.parent.parent.parent / "config" / "looker_recipes.json"
        with open(recipe_path, 'r') as file:
            return json.load(file)

    def _initialize_looker_service(self) -> LookerService:
        """Initialize real Looker service."""
        import os

        # Get config from environment variables (required for real API)
        base_url = os.getenv("LOOKER_BASE_URL")
        client_id = os.getenv("LOOKER_CLIENT_ID")
        client_secret = os.getenv("LOOKER_CLIENT_SECRET")
        default_limit = int(os.getenv("LOOKER_DEFAULT_LIMIT", "500"))

        if not all([base_url, client_id, client_secret]):
            raise ValueError("Missing required Looker environment variables. Check LOOKER_BASE_URL, LOOKER_CLIENT_ID, LOOKER_CLIENT_SECRET")

        return LookerService(
            base_url=base_url,
            client_id=client_id,
            client_secret=client_secret,
            default_limit=default_limit
        )

    def _initialize_dspy_modules(self) -> None:
        """Initialize DSPy modules for conversation processing."""
        # Configure DSPy
        dspy_config = self.config["dspy"]
        
        # Modern DSPy configuration
        import os
        os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
        
        # DSPy 3.0.3 correct initialization
        import dspy
        
        # Configure DSPy with LM for version 3.0+
        lm = dspy.LM(
            model=dspy_config["model"],
            max_tokens=dspy_config["max_tokens"],
            temperature=dspy_config["temperature"]
        )
        dspy.configure(lm=lm)
        
        # Initialize modules
        self.triage_module = dspy.ChainOfThought(TriageSignature)
        self.query_curator = dspy.ChainOfThought(QueryCuratorSignature)
        self.response_synthesizer = dspy.ChainOfThought(ResponseSynthesizerSignature)
        self.insight_extractor = dspy.ChainOfThought(InsightExtractionSignature)

    async def initialize_looker_schema(self) -> None:
        """Initialize Looker schema from JSON file."""
        try:
            # Load schema from JSON file
            self.schema = self.schema_loader.load_schema()

            if self.schema:
                self.query_builder = LookerQueryBuilder(self.schema)
                self.deterministic_query_builder = DeterministicQueryBuilder(self.schema)
                logger.info("Looker schema loaded successfully from JSON", extra={
                    "model": self.schema.get("model"),
                    "explore": self.schema.get("explore"),
                    "filters_count": len(self.schema.get("filters", [])),
                    "measures_count": len(self.schema.get("measures", []))
                })
            else:
                logger.error("Failed to load Looker schema from JSON")

        except Exception as e:
            logger.error(f"Failed to initialize Looker schema: {e}")

    async def process_query(self, user_query: str, session_id: str = "default") -> Dict[str, Any]:
        """Process a user query and return response."""
        try:
            logger.info(f"Processing query: {user_query}")
            # Step 1: Intent detection
            intent_result = self._detect_intent(user_query)
            intent = intent_result.intent
            
            logger.info(f"Detected intent: {intent}")
            
            # Step 2: Route based on intent
            if intent == "GATHER_DATA_FROM_LOOKER":
                response = await self._handle_data_query(user_query, intent_result)
            elif intent == "GET_EXECUTIVE_SUMMARY":
                response = await self._handle_executive_summary(user_query)
            elif intent == "DRILL_DOWN_ANALYSIS":
                response = await self._handle_drill_down(user_query)
            elif intent == "AGENT_CAPABILITIES":
                response = self._handle_capabilities_query()
            elif intent == "DATA_SOURCE_INFO":
                response = self._handle_data_source_info()
            elif intent == "FRIENDLY_CONVERSATION":
                response = self._handle_friendly_conversation(user_query)
            elif intent == "MANAGE_CONVERSATION":
                response = self._handle_conversation_management(user_query)
            else:
                response = self._handle_other_query(user_query)
            
            # Step 3: Add to memory and extract insights
            self.memory.add_turn(
                user_query=user_query,
                agent_response=response["message"],
                metadata={"intent": intent, "session_id": session_id}
            )
            
            # Step 4: Extract insights for future personalization
            await self._extract_insights(user_query, response["message"])
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "message": "I encountered an error processing your request. Please try again.",
                "status": "error",
                "error": str(e)
            }

    def _detect_intent(self, user_query: str) -> Any:
        """Detect user intent using triage module."""
        try:
            logger.info("Starting intent detection")
            conversation_history = self.memory.get_history_summary()
            logger.info(f"Got conversation history: {conversation_history}")

            result = self.triage_module(
                user_query=user_query,
                conversation_history=conversation_history
            )
            logger.info(f"Triage result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in _detect_intent: {e}")
            # Return a default intent
            class DefaultIntentResult:
                intent = "FRIENDLY_CONVERSATION"
            return DefaultIntentResult()

    async def _handle_data_query(self, user_query: str, intent_result: Any) -> Dict[str, Any]:
        """Handle data gathering queries from Looker."""
        try:
            # Step 1: Try to match with predefined recipes
            recipe_result = await self._curate_query(user_query)
            
            # Step 2: Build Looker query
            if recipe_result.recipe_name != "none":
                # Use recipe-based query
                query_config = self._build_query_from_recipe(
                    recipe_result.recipe_name,
                    json.loads(recipe_result.extracted_parameters_json)
                )
            else:
                # Build query from intent
                query_config = self.query_builder.build_query_from_intent(
                    user_query, {}
                ) if self.query_builder else self._get_default_query()

            # Check if clarification is needed
            if query_config.get("error") == "clarification_needed":
                return {
                    "message": query_config.get("message"),
                    "status": "clarification_needed",
                    "intent": "data_query"
                }

            # Step 3: Execute Looker query
            import os
            query_timezone = os.getenv("LOOKER_QUERY_TIMEZONE", "UTC")
            looker_data = await self.looker_service.run_inline_query(query_config, query_timezone)

            # Format result to match expected structure
            looker_result = {
                "status": "success",
                "data": looker_data,
                "query": query_config,
                "row_count": len(looker_data)
            }
            
            # Step 4: Synthesize response
            response_text = await self._synthesize_response(
                raw_output=json.dumps(looker_result),
                user_query=user_query
            )
            
            return {
                "message": response_text,
                "status": "success",
                "data": looker_result.get("data", []),
                "query": query_config,
                "intent": "data_query"
            }
            
        except Exception as e:
            logger.error(f"Error handling data query: {e}")
            return {
                "message": "I encountered an error retrieving the data. Please try rephrasing your question.",
                "status": "error",
                "error": str(e)
            }

    async def _curate_query(self, user_query: str) -> Any:
        """Curate query using recipe matching."""
        recipe_descriptions = "\n".join([
            f"- {recipe['name']}: {recipe['description']}"
            for recipe in self.recipes["recipes"]
        ])
        
        return self.query_curator(
            recipe_descriptions=recipe_descriptions,
            user_query=user_query
        )

    def _build_query_from_recipe(self, recipe_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Build Looker query from recipe and parameters."""
        # Find the recipe
        recipe = next(
            (r for r in self.recipes["recipes"] if r["name"] == recipe_name),
            None
        )
        
        if recipe:
            query = recipe["query_template"].copy()
            
            # Apply parameter mappings
            mappings = self.recipes.get("parameter_mappings", {})
            
            # Apply parameters to query
            for param, value in parameters.items():
                if param == "limit":
                    query["limit"] = value
                elif param in mappings.get("dimensions", {}):
                    mapped_dim = mappings["dimensions"][param]
                    if mapped_dim not in query["dimensions"]:
                        query["dimensions"].append(mapped_dim)
                # Add more parameter handling as needed
            
            return query
        else:
            return self._get_default_query()

    async def _handle_executive_summary(self, user_query: str) -> Dict[str, Any]:
        """Handle requests for executive summary of recent data."""
        recent_data = self._get_recent_conversation_data()
        
        if not recent_data:
            return {
                "message": "I don't have any recent data to summarize. Please ask me to retrieve some data first.",
                "status": "info"
            }
        
        summary_response = await self._synthesize_response(
            raw_output=f"Summary request for: {recent_data}",
            user_query=user_query
        )
        
        return {
            "message": summary_response,
            "status": "success",
            "intent": "executive_summary"
        }

    async def _handle_drill_down(self, user_query: str) -> Dict[str, Any]:
        """Handle drill-down analysis requests."""
        # For MVP, provide guidance on drill-down capabilities
        return {
            "message": "I can help you drill down into specific data. Please specify what dimension you'd like to drill down by (e.g., 'drill down by product category' or 'show me this data by region').",
            "status": "info",
            "intent": "drill_down"
        }

    def _handle_capabilities_query(self) -> Dict[str, Any]:
        """Handle questions about agent capabilities."""
        capabilities = [
            "Query Looker data using natural language",
            "Analyze trends and patterns in your data",
            "Provide executive summaries of key insights",
            "Support drill-down analysis",
            "Remember conversation context for better responses"
        ]
        
        message = "I'm a conversational AI agent that can help you with:\n\n" + \
                 "\n".join(f"• {cap}" for cap in capabilities) + \
                 "\n\nJust ask me questions about your data in natural language!"
        
        return {
            "message": message,
            "status": "success",
            "intent": "capabilities"
        }

    def _handle_data_source_info(self) -> Dict[str, Any]:
        """Handle questions about available data sources."""
        if self.schema:
            dimensions = self.query_builder.get_available_dimensions()
            measures = self.query_builder.get_available_measures()
            
            message = "I have access to the following data:\n\n"
            message += "**Dimensions (ways to group data):**\n"
            message += "\n".join(f"• {dim['label']}" for dim in dimensions[:5])
            message += "\n\n**Measures (what to calculate):**\n"
            message += "\n".join(f"• {measure['label']}" for measure in measures[:5])
            message += "\n\nTry asking questions like 'Show me revenue by country' or 'What are the trends over time?'"
        else:
            message = "I'm still connecting to the data source. Please try again in a moment."
        
        return {
            "message": message,
            "status": "success",
            "intent": "data_source_info"
        }

    def _handle_friendly_conversation(self, user_query: str) -> Dict[str, Any]:
        """Handle friendly/casual conversation."""
        friendly_responses = {
            "hello": "Hello! I'm here to help you explore your Looker data. What would you like to know?",
            "hi": "Hi there! Ready to dive into some data analysis?",
            "thank": "You're welcome! Happy to help with your data questions.",
            "how are you": "I'm doing great and ready to help you with data analysis! What can I show you today?"
        }
        
        query_lower = user_query.lower()
        response = None
        
        for key, message in friendly_responses.items():
            if key in query_lower:
                response = message
                break
        
        if not response:
            response = "Thanks for the kind words! Is there anything specific about your data you'd like to explore?"
        
        return {
            "message": response,
            "status": "success",
            "intent": "friendly"
        }

    def _handle_conversation_management(self, user_query: str) -> Dict[str, Any]:
        """Handle conversation management requests."""
        query_lower = user_query.lower()
        
        if any(phrase in query_lower for phrase in ["clear", "reset", "start over"]):
            self.memory.clear_history()
            return {
                "message": "I've cleared our conversation history. We can start fresh! What would you like to explore?",
                "status": "success",
                "intent": "conversation_management"
            }
        else:
            stats = self.memory.get_session_stats()
            return {
                "message": f"We've had {stats['total_turns']} conversation turns so far. I can help you clear the conversation or continue where we left off.",
                "status": "info",
                "intent": "conversation_management"
            }

    def _handle_other_query(self, user_query: str) -> Dict[str, Any]:
        """Handle queries that don't fit other categories."""
        return {
            "message": "I'm not sure how to help with that specific request. I'm designed to help you explore and analyze your Looker data. Try asking me about trends, comparisons, or specific metrics you'd like to see.",
            "status": "info",
            "intent": "other"
        }

    async def _synthesize_response(self, raw_output: str, user_query: str) -> str:
        """Synthesize natural language response from raw data."""
        user_profile = self.memory.get_user_profile_summary()
        history = self.memory.get_history_summary()
        
        result = self.response_synthesizer(
            raw_module_output=raw_output,
            user_profile_summary=user_profile,
            short_term_history=history
        )
        
        return result.synthesized_response

    async def _extract_insights(self, user_query: str, agent_response: str) -> None:
        """Extract insights from conversation turn for personalization."""
        try:
            profile_summary = self.memory.get_user_profile_summary()
            
            result = self.insight_extractor(
                user_query=user_query,
                agent_response=agent_response,
                session_context="Looker data conversation",
                existing_profile_summary=profile_summary
            )
            
            # Update user profile based on insights
            if result.preference_updates:
                try:
                    updates = json.loads(result.preference_updates)
                    self.memory.update_user_profile(updates)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse preference updates JSON")
            
            # Add data interests based on query
            self._extract_data_interests(user_query)
            
        except Exception as e:
            logger.error(f"Failed to extract insights: {e}")

    def _extract_data_interests(self, user_query: str) -> None:
        """Extract data interests from user query."""
        # Simple keyword extraction for data interests
        interests = []
        
        if any(word in user_query.lower() for word in ["revenue", "sales", "income"]):
            interests.append("revenue_analysis")
        if any(word in user_query.lower() for word in ["customer", "user", "client"]):
            interests.append("customer_analytics")
        if any(word in user_query.lower() for word in ["trend", "time", "over time"]):
            interests.append("trend_analysis")
        if any(word in user_query.lower() for word in ["country", "region", "location"]):
            interests.append("geographic_analysis")
        
        for interest in interests:
            self.memory.add_data_interest(interest)

    def _get_recent_conversation_data(self) -> str:
        """Get recent conversation data for summary."""
        recent_turns = self.memory.get_recent_history(3)
        if not recent_turns:
            return ""
        
        data_points = []
        for turn in recent_turns:
            if turn.get("metadata", {}).get("intent") == "data_query":
                data_points.append(f"Asked: {turn['user_query'][:100]}...")
        
        return "; ".join(data_points)

    def _get_default_query(self) -> Dict[str, Any]:
        """Get default query configuration."""
        return {
            "model": "default_model",
            "explore": "default_explore", 
            "dimensions": ["country"],
            "measures": ["revenue"],
            "sorts": ["revenue desc"],
            "limit": 10
        }

    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information."""
        return {
            "agent_status": "ready",
            "looker_connected": self.schema is not None,
            "memory_stats": self.memory.get_session_stats(),
            "available_recipes": len(self.recipes["recipes"])
        }