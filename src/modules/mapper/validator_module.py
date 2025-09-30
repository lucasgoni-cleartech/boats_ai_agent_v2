"""
DSPy module for Looker Query validation.

Implements the ValidatorSignature to validate Looker query JSON
against the Explore schema before execution.
"""

import json
import logging
import dspy
from ..signatures.validator import ValidatorSignature
from src.utils.date_normalizer import to_absolute_range

logger = logging.getLogger(__name__)


class ValidatorModule(dspy.Module):
    """
    DSPy module that validates Looker query JSON against schema.

    Uses ChainOfThought reasoning to:
    1. Parse the Looker query JSON structure
    2. Check all fields exist in the schema
    3. Verify measures are measures, dimensions are dimensions
    4. Validate filter field references
    5. Return either the same JSON if valid, or clarification_request if invalid

    Validation rules:
    - All fields in "fields", "filters", "sorts", "pivots" must exist in schema
    - Field types must match (measures vs dimensions)
    - Returns clarification_request for any validation failures
    """

    def __init__(self):
        super().__init__()
        self.validator = dspy.ChainOfThought(ValidatorSignature)

    def forward(self, looker_query: str, schema_json: str, today_iso: str = None) -> str:
        """
        Validate Looker query against schema and normalize time_intent.

        Args:
            looker_query: Looker query JSON string to validate
            schema_json: Looker explore schema as JSON string
            today_iso: Current date in YYYY-MM-DD format (for time_intent normalization)

        Returns:
            Either the same JSON if valid, or clarification_request JSON if invalid
        """
        # First, run the DSPy validation
        result = self.validator(
            looker_query=looker_query,
            schema_json=schema_json
        )

        validated_query_str = result.validated_query

        # Post-process: normalize time_intent and ensure view field is present
        try:
            query_json = json.loads(validated_query_str)

            # If this is a valid query (not a clarification_request)
            if "clarification_request" not in query_json and "explore" in query_json:
                # Ensure view field exists
                if "view" not in query_json:
                    query_json["view"] = query_json["explore"]
                    logger.info("ValidatorModule: auto-added 'view' field = %s", query_json["view"])

                # Normalize time_intent to absolute date range
                if "time_intent" in query_json and today_iso:
                    time_intent = query_json["time_intent"]
                    range_str = to_absolute_range(time_intent, today_iso)

                    if range_str:
                        # Ensure filters dict exists
                        if "filters" not in query_json:
                            query_json["filters"] = {}

                        # Set the absolute date filter
                        query_json["filters"]["consumer_sessions.visit_day_date"] = range_str
                        logger.info("ValidatorModule: absolute date filter -> %s", range_str)

                        # Remove time_intent from the final query (it's been converted)
                        del query_json["time_intent"]
                    else:
                        # Failed to normalize time_intent - return clarification request
                        logger.warning("ValidatorModule: Failed to normalize time_intent: %s", time_intent)
                        return json.dumps({
                            "clarification_request": "Please specify a valid timeframe (e.g., 'last 7 days', 'this month', or 'YYYY-MM-DD to YYYY-MM-DD')."
                        })

                # Return the updated JSON
                validated_query_str = json.dumps(query_json)

        except json.JSONDecodeError:
            # If we can't parse the JSON, just return as-is (validation already handled)
            logger.warning("ValidatorModule: Could not parse validated query JSON for processing")
            pass

        return validated_query_str