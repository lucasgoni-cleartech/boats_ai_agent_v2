"""
DSPy Signature for Natural Language to Looker Query mapping.

Converts natural language business questions into structured Looker query JSON
for the bg.consumer_sessions explore.
"""

import dspy


class NL2LookerSignature(dspy.Signature):
    """
    Map natural language query to structured Looker query JSON.

    Takes a business question in English and converts it to a valid Looker query
    that can be executed against the consumer_sessions explore. Uses the provided
    schema and NL dictionary to ensure field validity and synonym mapping.

    The output JSON must comply with the Looker query schema including model,
    explore, fields, filters, sorts, pivots, and limit parameters.
    """

    query: str = dspy.InputField(
        desc="Natural language business question to be mapped to Looker query"
    )
    today_iso: str = dspy.InputField(
        desc="Current date in YYYY-MM-DD format for relative date calculations"
    )
    schema_json: str = dspy.InputField(
        desc="Complete Looker explore schema as JSON string containing available dimensions and measures"
    )
    dictionary_yaml: str = dspy.InputField(
        desc="NL dictionary YAML text with preferred synonyms for metrics and dimensions"
    )

    looker_query: str = dspy.OutputField(
        desc="Valid JSON string representing the Looker query with model, explore, fields, filters, sorts, pivots, and limit"
    )