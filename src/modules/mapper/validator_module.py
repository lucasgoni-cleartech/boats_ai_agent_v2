"""
DSPy module for Looker Query validation.

Implements the ValidatorSignature to validate Looker query JSON
against the Explore schema before execution.
"""

import json
import logging
import dspy
from ..signatures.validator import ValidatorSignature

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

    def forward(self, looker_query: str, schema_json: str) -> str:
        """
        Validate Looker query against schema.

        Args:
            looker_query: Looker query JSON string to validate
            schema_json: Looker explore schema as JSON string

        Returns:
            Either the same JSON if valid, or clarification_request JSON if invalid
        """
        # First, run the DSPy validation
        result = self.validator(
            looker_query=looker_query,
            schema_json=schema_json
        )

        validated_query_str = result.validated_query

        # Post-process to ensure "view" field is present
        try:
            query_json = json.loads(validated_query_str)

            # If this is a valid query (not a clarification_request), ensure view field exists
            if "clarification_request" not in query_json and "explore" in query_json:
                if "view" not in query_json:
                    query_json["view"] = query_json["explore"]
                    logger.info("ValidatorModule: auto-added 'view' field = %s", query_json["view"])

                    # Return the updated JSON
                    validated_query_str = json.dumps(query_json)

        except json.JSONDecodeError:
            # If we can't parse the JSON, just return as-is (validation already handled)
            logger.warning("ValidatorModule: Could not parse validated query JSON for view field processing")
            pass

        return validated_query_str