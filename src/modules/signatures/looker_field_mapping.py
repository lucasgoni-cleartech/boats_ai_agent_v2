"""
DSPy Signature for deterministic Natural Language to Looker Field mapping.

Uses complete schema context for optimal mapping consistency.
"""

import dspy


class LookerFieldMappingSignature(dspy.Signature):
    """
    Map natural language query to specific Looker fields using complete schema context.

    Designed for maximum determinism: same query should always produce same mapping.
    Focus on identifying the core intent and mapping to the most appropriate fields.
    """

    schema_context: str = dspy.InputField(
        desc="Complete Looker schema context with available measures, dimensions, and mapping patterns"
    )
    user_query: str = dspy.InputField(
        desc="User's natural language query to be mapped to Looker fields"
    )

    # Core field mappings
    primary_measure: str = dspy.OutputField(
        desc="The main measure field name (e.g. 'consumer_sessions.sessions') or 'none' if no measure needed"
    )
    primary_dimension: str = dspy.OutputField(
        desc="The main dimension field name (e.g. 'consumer_sessions.user_location_country') or 'none' if no dimension needed"
    )

    # Time handling
    time_dimension: str = dspy.OutputField(
        desc="Time dimension field name if time-based query (e.g. 'consumer_sessions.visit_day_date') or 'none'"
    )
    time_filter: str = dspy.OutputField(
        desc="Time filter expression if mentioned (e.g. 'this month', 'last 7 days', 'last year') or 'none'"
    )

    # Query structure
    query_type: str = dspy.OutputField(
        desc="Type of query: 'total' (single metric), 'breakdown' (by dimension), 'timeseries' (over time), or 'complex'"
    )

    # Metadata
    confidence: str = dspy.OutputField(
        desc="Confidence in mapping: 'high' (clear match), 'medium' (good match), 'low' (uncertain)"
    )


class QueryStructureBuilderSignature(dspy.Signature):
    """
    Build final Looker query structure from mapped fields.

    Takes the field mappings and constructs a valid, executable Looker query.
    """

    mapped_fields: str = dspy.InputField(
        desc="JSON with mapped fields from LookerFieldMappingSignature"
    )
    user_query: str = dspy.InputField(
        desc="Original user query for context"
    )

    looker_query: str = dspy.OutputField(
        desc="Complete Looker query as JSON with model, view, fields, filters, sorts, limit"
    )
    query_description: str = dspy.OutputField(
        desc="Human-readable description of what this query will return"
    )
    confidence: str = dspy.OutputField(
        desc="Overall confidence in the final query: 'high', 'medium', 'low'"
    )