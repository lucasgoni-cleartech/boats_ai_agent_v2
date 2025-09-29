"""
DSPy Signature for Looker Query validation.

Validates a Looker query JSON against the Explore schema to ensure all fields
exist and are correctly typed before execution.
"""

import dspy


class ValidatorSignature(dspy.Signature):
    """
    Validate Looker query JSON against the Explore schema.

    Takes a Looker query JSON and verifies that all referenced fields exist
    in the schema and are properly typed (measures vs dimensions). Returns
    either the same query if valid, or a clarification request if invalid.

    Validation checks:
    - All fields in "fields", "filters", "sorts", "pivots" exist in schema
    - Measures are measures, dimensions are dimensions
    - Field references match schema structure
    """

    looker_query: str = dspy.InputField(
        desc="Looker query JSON string to be validated against the schema"
    )
    schema_json: str = dspy.InputField(
        desc="Complete Looker explore schema as JSON string containing field definitions and types"
    )

    validated_query: str = dspy.OutputField(
        desc="Either the same JSON unchanged if valid, or a clarification_request JSON object if fields are invalid or missing"
    )