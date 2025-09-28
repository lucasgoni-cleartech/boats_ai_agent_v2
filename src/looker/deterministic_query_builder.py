"""
Deterministic Query Builder using LLM with refined schema context.

Implements a step-by-step approach for maximum consistency and accuracy.
"""

import json
import logging
from typing import Dict, Any, Optional

import dspy

from .schema_context_builder import SchemaContextBuilder
from ..modules.signatures.looker_field_mapping import (
    LookerFieldMappingSignature,
    QueryStructureBuilderSignature
)

logger = logging.getLogger(__name__)


class DeterministicQueryBuilder:
    """
    Builds Looker queries using LLM with refined schema context.

    Designed for maximum determinism and consistency in NL → JSON mapping.
    """

    def __init__(self, schema_json: Dict[str, Any]):
        """Initialize with Looker schema."""
        self.schema = schema_json
        self.context_builder = SchemaContextBuilder(schema_json)
        self.refined_context = self.context_builder.build_refined_context()

        # Initialize DSPy modules
        self.field_mapper = dspy.ChainOfThought(LookerFieldMappingSignature)
        self.query_builder = dspy.ChainOfThought(QueryStructureBuilderSignature)

        logger.info("DeterministicQueryBuilder initialized with refined schema context")

    def build_query_from_nl(self, user_query: str) -> Dict[str, Any]:
        """
        Build Looker query from natural language using deterministic 3-step process.

        Args:
            user_query: User's natural language query

        Returns:
            Dictionary with Looker query or error information
        """
        try:
            logger.info(f"Building query for: {user_query}")

            # Step 1: Map natural language to fields
            field_mapping = self._map_fields(user_query)
            logger.info(f"Field mapping: {field_mapping}")

            # Step 2: Validate mapping confidence
            if field_mapping.confidence == "low":
                return self._create_clarification_response(user_query, field_mapping)

            # Step 3: Build final query structure
            query_result = self._build_query_structure(field_mapping, user_query)
            logger.info(f"Final query: {query_result.looker_query}")

            # Step 4: Parse and validate JSON
            final_query = self._parse_and_validate_query(query_result.looker_query)

            return {
                "query": final_query,
                "description": query_result.query_description,
                "confidence": query_result.confidence,
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Error building query: {e}")
            return {
                "error": "query_building_failed",
                "message": f"Failed to build query: {str(e)}",
                "status": "error"
            }

    def _map_fields(self, user_query: str) -> Any:
        """Step 1: Map natural language to Looker fields."""
        return self.field_mapper(
            schema_context=self.refined_context,
            user_query=user_query
        )

    def _build_query_structure(self, field_mapping: Any, user_query: str) -> Any:
        """Step 2: Build query structure from mapped fields."""
        mapped_fields_json = json.dumps({
            "primary_measure": field_mapping.primary_measure,
            "primary_dimension": field_mapping.primary_dimension,
            "time_dimension": field_mapping.time_dimension,
            "time_filter": field_mapping.time_filter,
            "query_type": field_mapping.query_type,
            "confidence": field_mapping.confidence
        })

        return self.query_builder(
            mapped_fields=mapped_fields_json,
            user_query=user_query
        )

    def _parse_and_validate_query(self, query_json: str) -> Dict[str, Any]:
        """Step 3: Parse and validate the generated query."""
        try:
            query = json.loads(query_json)

            # Ensure required fields
            if "model" not in query:
                query["model"] = self.schema.get("model", "bg")
            if "view" not in query:
                query["view"] = self.schema.get("explore", "consumer_sessions")
            if "explore" not in query:
                query["explore"] = self.schema.get("explore", "consumer_sessions")

            # Ensure at least one field
            if not query.get("fields") and not query.get("measures"):
                query["fields"] = ["consumer_sessions.sessions"]

            # Set reasonable defaults
            if "limit" not in query:
                query["limit"] = 10
            if "filters" not in query:
                query["filters"] = {}

            return query

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse query JSON: {e}")
            # Return safe default query
            return {
                "model": self.schema.get("model", "bg"),
                "view": self.schema.get("explore", "consumer_sessions"),
                "explore": self.schema.get("explore", "consumer_sessions"),
                "fields": ["consumer_sessions.sessions"],
                "filters": {},
                "limit": 10
            }

    def _create_clarification_response(self, user_query: str, field_mapping: Any) -> Dict[str, Any]:
        """Create clarification response for low-confidence mappings."""
        return {
            "error": "clarification_needed",
            "message": f"I need more specific information about '{user_query}'. Try asking:\\n• 'sessions this month'\\n• 'sessions by country'\\n• 'sessions today'\\n• 'sessions over time'",
            "status": "clarification_needed",
            "mapping_attempted": {
                "primary_measure": field_mapping.primary_measure,
                "primary_dimension": field_mapping.primary_dimension,
                "confidence": field_mapping.confidence
            }
        }

    def get_schema_summary(self) -> str:
        """Get summary of available schema fields."""
        return self.context_builder.get_available_fields_summary()