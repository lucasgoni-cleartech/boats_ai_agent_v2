"""
Schema Context Builder for LLM-based NL to Looker Query mapping.

Extracts and refines schema information to provide optimal context for deterministic mapping.
"""

import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class SchemaContextBuilder:
    """Builds refined context from Looker schema for LLM consumption."""

    def __init__(self, schema_json: Dict[str, Any]):
        """Initialize with Looker explore schema."""
        self.schema = schema_json
        self.measures = schema_json.get("measures", [])
        self.dimensions = schema_json.get("filters", [])  # In your schema, dimensions are in "filters"

    def build_refined_context(self) -> str:
        """Build refined context optimized for deterministic LLM mapping."""

        # Extract measures with enhanced descriptions
        measures_context = self._build_measures_context()

        # Extract key dimensions with semantic keywords
        dimensions_context = self._build_dimensions_context()

        # Add business rules and patterns
        patterns_context = self._build_patterns_context()

        context = f"""
LOOKER SCHEMA CONTEXT:

=== AVAILABLE MEASURES ===
{measures_context}

=== AVAILABLE DIMENSIONS ===
{dimensions_context}

=== MAPPING PATTERNS ===
{patterns_context}

=== BUSINESS RULES ===
- Always include at least one measure
- Time queries require consumer_sessions.visit_day_date
- Geographic queries use consumer_sessions.user_location_country
- Default measure is consumer_sessions.sessions
- Be consistent: same query → same mapping
"""

        return context.strip()

    def _build_measures_context(self) -> str:
        """Build measures context with semantic information."""
        measures_info = []

        for measure in self.measures:
            field_name = measure.get("field_name", "")
            label = measure.get("label", field_name)

            # Add semantic keywords based on field name
            keywords = self._extract_measure_keywords(field_name, label)

            measures_info.append(f"- {field_name}: {label}")
            if keywords:
                measures_info.append(f"  Keywords: {', '.join(keywords)}")

        return "\n".join(measures_info)

    def _build_dimensions_context(self) -> str:
        """Build key dimensions context with semantic keywords."""
        # Focus on most commonly used dimensions
        priority_dimensions = [
            "consumer_sessions.user_location_country",
            "consumer_sessions.visit_day_date",
            "consumer_sessions.device_category",
            "consumer_sessions.device_browser",
            "consumer_sessions.last_touch_channel",
            "consumer_sessions.user_location_city",
            "consumer_sessions.user_location_region"
        ]

        dimensions_info = []

        for dim in self.dimensions:
            field_name = dim.get("field_name", "")
            if field_name in priority_dimensions:
                label = dim.get("label", field_name)
                keywords = self._extract_dimension_keywords(field_name, label)

                dimensions_info.append(f"- {field_name}: {label}")
                if keywords:
                    dimensions_info.append(f"  Keywords: {', '.join(keywords)}")

        return "\n".join(dimensions_info)

    def _build_patterns_context(self) -> str:
        """Build common mapping patterns for consistency."""
        patterns = [
            "sessions/visits/traffic → consumer_sessions.sessions",
            "country/countries/location → consumer_sessions.user_location_country",
            "time/date/month/year/trend → consumer_sessions.visit_day_date",
            "browser/browsers → consumer_sessions.device_browser",
            "device/devices → consumer_sessions.device_category",
            "channel/channels/source → consumer_sessions.last_touch_channel",
            "city/cities → consumer_sessions.user_location_city",
            "this month → filter on visit_day_date",
            "last week → filter on visit_day_date"
        ]
        return "\n".join(f"- {pattern}" for pattern in patterns)

    def _extract_measure_keywords(self, field_name: str, label: str) -> List[str]:
        """Extract semantic keywords for a measure."""
        keywords = []

        if "sessions" in field_name.lower():
            keywords.extend(["sessions", "visits", "traffic", "count"])

        # Add more measure-specific keywords as needed
        return keywords

    def _extract_dimension_keywords(self, field_name: str, label: str) -> List[str]:
        """Extract semantic keywords for a dimension."""
        keywords = []

        field_lower = field_name.lower()

        if "country" in field_lower:
            keywords.extend(["country", "countries", "location", "geography"])
        elif "date" in field_lower:
            keywords.extend(["date", "time", "day", "month", "year", "when", "trend", "over time"])
        elif "browser" in field_lower:
            keywords.extend(["browser", "browsers"])
        elif "device" in field_lower:
            keywords.extend(["device", "devices", "platform"])
        elif "channel" in field_lower:
            keywords.extend(["channel", "channels", "source", "medium"])
        elif "city" in field_lower:
            keywords.extend(["city", "cities"])
        elif "region" in field_lower:
            keywords.extend(["region", "state", "province"])

        return keywords

    def get_available_fields_summary(self) -> Dict[str, List[str]]:
        """Get a summary of available fields for quick reference."""
        return {
            "measures": [m.get("field_name", "") for m in self.measures],
            "key_dimensions": [
                "consumer_sessions.user_location_country",
                "consumer_sessions.visit_day_date",
                "consumer_sessions.device_category",
                "consumer_sessions.device_browser",
                "consumer_sessions.last_touch_channel"
            ]
        }