# OWNER: @team_personalization
# INTENT: shared_component
# DEPENDS ON: None
# CREATED: 2025-09-11

"""Signature for extracting insights from conversation turns - Conversational Agent Version."""

import dspy


class InsightExtractionSignature(dspy.Signature):
    """Extract key insights and learnings from a conversation turn.

    Analyzes a conversation turn to extract key learnings and update a user's profile.
    The goal is to distill permanent user traits, data interests, and query patterns.
    """

    user_query: str = dspy.InputField(desc="The user's original query or input")
    agent_response: str = dspy.InputField(
        desc="The agent's complete response to the user"
    )
    session_context: str = dspy.InputField(
        desc="Additional context about the current session and data analysis"
    )
    existing_profile_summary: str = dspy.InputField(
        desc="The user's current profile summary. The new summary should be an evolution of this."
    )
    updated_profile_summary: str = dspy.OutputField(
        desc="A new, concise summary of the user's identity, preferences, and data interests. This should integrate new learnings with the existing_profile_summary. Example: 'User is a marketing analyst who frequently asks about campaign performance and prefers monthly trending data.'"
    )
    key_learnings: str = dspy.OutputField(
        desc="Important insights about user behavior, data interests, or query patterns discovered in this interaction"
    )
    preference_updates: str = dspy.OutputField(
        desc="JSON string of specific preference updates to apply to the user profile (e.g., data dimensions, metrics of interest, analysis patterns)"
    )