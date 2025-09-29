"""
DSPy module for Natural Language to Looker Query mapping.

Implements the NL2LookerSignature using DSPy ChainOfThought reasoning
to convert natural language business questions into structured Looker JSON.
"""

import json
import logging
import dspy
from ..signatures.nl_to_looker import NL2LookerSignature

logger = logging.getLogger(__name__)


class NL2LookerModule(dspy.Module):
    """
    DSPy module that maps natural language queries to Looker JSON.

    Uses ChainOfThought reasoning to:
    1. Parse the natural language query for business intent
    2. Map synonyms using the NL dictionary
    3. Identify relevant fields from the schema
    4. Handle date filters with absolute date ranges (YYYY-MM-DD to YYYY-MM-DD)
    5. Generate valid Looker query JSON

    Follows the JSON schema requirements:
    - model: "bg", explore: "consumer_sessions", view: "consumer_sessions"
    - fields: array of valid schema fields
    - filters: ABSOLUTE date filters in "YYYY-MM-DD to YYYY-MM-DD" format
    - sorts: field sorting with desc/asc
    - limit: row limit (default 100)
    - top_n: for Top/Bottom-N queries
    - clarification_request: if query is ambiguous
    """

    def __init__(self):
        super().__init__()
        # Create a custom ChainOfThought with enhanced prompt for absolute dates
        self.mapper = self._create_absolute_date_mapper()

    def _create_absolute_date_mapper(self):
        """Create a ChainOfThought mapper with custom prompt for absolute date handling."""
        mapper = dspy.ChainOfThought(NL2LookerSignature)

        # Override the signature with enhanced instructions
        mapper.signature = NL2LookerSignature.with_instructions(
            """You are a precise NL-to-Looker JSON mapper. Convert natural language queries to valid Looker JSON.

CRITICAL REQUIREMENTS:
1. ALWAYS return valid JSON only - no prose, explanations, or markdown
2. ALWAYS set: "model": "bg", "explore": "consumer_sessions", "view": "consumer_sessions"
3. ALWAYS include "consumer_sessions.visit_day_date" filter with ABSOLUTE date ranges in "YYYY-MM-DD to YYYY-MM-DD" format
4. Use today_iso and America/New_York timezone to compute all relative dates to absolute ranges

DATE CONVERSION RULES (today_iso as reference):
- "last 7 days" → 7-day window ending today_iso: "2025-09-22 to 2025-09-29"
- "yesterday" → single day: "2025-09-28 to 2025-09-28"
- "this quarter" / "QTD" → first day of current quarter to today_iso
- "previous month" → complete prior month: "2025-08-01 to 2025-08-31"
- "this month" / "MTD" → first day of current month to today_iso
- Single date "2025-09-15" → "2025-09-15 to 2025-09-15"
- If no timeframe mentioned → default: last 30 days absolute
- Ambiguous dates like "03/04" → return {"clarification_request": "Please specify the date format (MM/DD or DD/MM)"}

FIELD MAPPING:
- Use NL dictionary for synonym matching
- Validate all fields exist in schema
- Map "client" to "consumer_sessions.portal"

JSON STRUCTURE:
{
  "model": "bg",
  "explore": "consumer_sessions",
  "view": "consumer_sessions",
  "fields": ["consumer_sessions.field1", "consumer_sessions.field2"],
  "filters": {"consumer_sessions.visit_day_date": "YYYY-MM-DD to YYYY-MM-DD"},
  "sorts": ["consumer_sessions.field1 desc"],
  "limit": 100,
  "top_n": 10
}

For clarification: {"clarification_request": "Clear question about what needs clarification"}
"""
        )

        return mapper

    def forward(self, query: str, today_iso: str, schema_json: str, dictionary_yaml: str) -> str:
        """
        Convert natural language query to Looker JSON.

        Args:
            query: Natural language business question
            today_iso: Current date in YYYY-MM-DD format
            schema_json: Looker explore schema as JSON string
            dictionary_yaml: NL dictionary YAML text

        Returns:
            Valid Looker query JSON string with absolute date ranges
        """
        # Enhanced context for LLM with timezone and date handling instructions
        enhanced_schema = schema_json + f"\n\n// CONTEXT: today_iso={today_iso}, timezone=America/New_York"
        enhanced_dictionary = dictionary_yaml + f"\n\n# CONTEXT: today_iso={today_iso}, timezone=America/New_York"

        result = self.mapper(
            query=query,
            today_iso=today_iso,
            schema_json=enhanced_schema,
            dictionary_yaml=enhanced_dictionary
        )

        looker_query_str = result.looker_query

        # Post-process to ensure "view" field is present and log absolute dates
        try:
            query_json = json.loads(looker_query_str)

            # If this is a valid query (not a clarification_request)
            if "clarification_request" not in query_json and "explore" in query_json:
                # Ensure view field exists
                if "view" not in query_json:
                    query_json["view"] = "consumer_sessions"
                    logger.info("NL2LookerModule: auto-added 'view' field = %s", query_json["view"])

                # Log the absolute date filter if present
                if "filters" in query_json and "consumer_sessions.visit_day_date" in query_json["filters"]:
                    date_filter = query_json["filters"]["consumer_sessions.visit_day_date"]
                    logger.info("NL2LookerModule: absolute date filter -> %s", date_filter)
                else:
                    logger.warning("NL2LookerModule: Missing required absolute date filter")

                # Return the updated JSON
                looker_query_str = json.dumps(query_json)

        except json.JSONDecodeError:
            # If we can't parse the JSON, just return as-is (let validation handle it)
            logger.warning("NL2LookerModule: Could not parse generated query JSON for processing")
            pass

        return looker_query_str