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
    4. Extract time intent WITHOUT computing absolute dates
    5. Generate valid Looker query JSON with structured time_intent

    Follows the JSON schema requirements:
    - model: "bg", explore: "consumer_sessions", view: "consumer_sessions"
    - fields: array of valid schema fields
    - filters: ONLY categorical filters (NO date strings)
    - time_intent: structured timeframe description (NO absolute dates)
    - sorts: field sorting with desc/asc
    - limit: row limit (default 100)
    - top_n: for Top/Bottom-N queries
    - clarification_request: if query is ambiguous
    """

    def __init__(self):
        super().__init__()
        # Create a custom ChainOfThought with time_intent prompt
        self.mapper = self._create_time_intent_mapper()

    def _create_time_intent_mapper(self):
        """Create a ChainOfThought mapper with time_intent contract."""
        mapper = dspy.ChainOfThought(NL2LookerSignature)

        # Override the signature with time_intent instructions
        mapper.signature = NL2LookerSignature.with_instructions(
            """You are a precise NL-to-Looker JSON mapper. Convert natural language queries to valid Looker JSON.

CRITICAL REQUIREMENTS:
1. ALWAYS return valid JSON only - no prose, explanations, or markdown
2. ALWAYS set: "model": "bg", "explore": "consumer_sessions", "view": "consumer_sessions"
3. DO NOT compute or emit date strings in filters
4. DO NOT include date filters in the "filters" object
5. Use "time_intent" to describe timeframes structurally (NO absolute dates)

FILTERS:
- Include ONLY categorical filters (country, region, device, portal, browser, etc.)
- Example: {"consumer_sessions.portal": "web", "consumer_sessions.country": "US"}
- NEVER include date/time fields in filters

TIME_INTENT STRUCTURE:
Provide a separate "time_intent" object with one of these presets:

1. Last N days: {"preset": "last_n_days", "n": 7, "field": "consumer_sessions.visit_day_date"}
2. Yesterday: {"preset": "yesterday", "field": "consumer_sessions.visit_day_date"}
3. Today: {"preset": "today", "field": "consumer_sessions.visit_day_date"}
4. MTD/QTD/YTD: {"preset": "mtd", "field": "consumer_sessions.visit_day_date"}
   (also: "qtd", "ytd", "prev_month", "prev_quarter", "prev_year")
5. Absolute range: {"preset": "absolute", "start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "field": "consumer_sessions.visit_day_date"}

DEFAULT: If no timeframe mentioned → {"preset": "last_n_days", "n": 30, "field": "consumer_sessions.visit_day_date"}

AMBIGUOUS DATES:
- If user provides ambiguous date like "03/04" that cannot be disambiguated, return ONLY:
  {"clarification_request": "Do you mean 2025-04-03 or 2025-03-04? Please specify the date in YYYY-MM-DD."}

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
  "pivots": ["consumer_sessions.field1"],
  "filters": {"consumer_sessions.portal": "web"},
  "sorts": ["consumer_sessions.field1 desc"],
  "limit": 100,
  "top_n": 10,
  "time_intent": {"preset": "last_n_days", "n": 7, "field": "consumer_sessions.visit_day_date"}
}

PIVOTS:
- Optional: maximum 1 field in "pivots" array
- If used, the pivot field MUST also be in "fields" array

For clarification: {"clarification_request": "Clear question about what needs clarification"}
"""
        )

        return mapper

    def forward(self, query: str, today_iso: str, schema_json: str, dictionary_yaml: str) -> str:
        """
        Convert natural language query to Looker JSON with time_intent.

        Args:
            query: Natural language business question
            today_iso: Current date in YYYY-MM-DD format (for LLM context only)
            schema_json: Looker explore schema as JSON string
            dictionary_yaml: NL dictionary YAML text

        Returns:
            Valid Looker query JSON string with time_intent (NO date strings in filters)
        """
        # Pass today_iso and timezone as context (LLM will NOT compute dates)
        enhanced_schema = schema_json + f"\n\n// CONTEXT: today_iso={today_iso}, timezone=America/New_York"
        enhanced_dictionary = dictionary_yaml + f"\n\n# CONTEXT: today_iso={today_iso}, timezone=America/New_York"

        result = self.mapper(
            query=query,
            today_iso=today_iso,
            schema_json=enhanced_schema,
            dictionary_yaml=enhanced_dictionary
        )

        looker_query_str = result.looker_query

        # Post-process to ensure "view" field is present
        try:
            query_json = json.loads(looker_query_str)

            # If this is a valid query (not a clarification_request)
            if "clarification_request" not in query_json and "explore" in query_json:
                # Ensure view field exists
                if "view" not in query_json:
                    query_json["view"] = "consumer_sessions"
                    logger.info("NL2LookerModule: auto-added 'view' field = %s", query_json["view"])

                # Return the updated JSON
                looker_query_str = json.dumps(query_json)

        except json.JSONDecodeError:
            # If we can't parse the JSON, just return as-is (let validation handle it)
            logger.warning("NL2LookerModule: Could not parse generated query JSON for processing")
            pass

        return looker_query_str