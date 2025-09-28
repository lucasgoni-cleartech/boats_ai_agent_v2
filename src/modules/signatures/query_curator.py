# OWNER: @team_genie
# INTENT: shared_component
# DEPENDS ON: None
# CREATED: 2025-09-11

"""Signature for query curation using predefined Looker recipes."""

import dspy


class QueryCuratorSignature(dspy.Signature):
    """
    Given a user query, determine if it semantically matches one of the predefined Looker Explore recipes.
    If it matches, identify the recipe and extract its required parameters. If no recipe is a good match, classify as 'none'.

    This will be configured with specific Looker Explore schema and common query patterns.
    """

    recipe_descriptions: str = dspy.InputField(
        desc="A description of all available Looker Explore recipes and their required parameters."
    )
    user_query: str = dspy.InputField()

    recipe_name: str = dspy.OutputField(
        desc="The name of the best matching recipe from the available list, or 'none' if no confident match is found."
    )
    extracted_parameters_json: str = dspy.OutputField(
        desc='A JSON string containing the extracted parameters for the matched recipe, e.g., \'{"dimension": "country", "measure": "revenue", "limit": 10}\'. Return \'{}\' if no recipe is matched.'
    )