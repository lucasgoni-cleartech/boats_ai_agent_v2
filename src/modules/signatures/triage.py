# OWNER: @team_core_routing
# INTENT: triage
# DEPENDS ON: None
# CREATED: 2025-09-11

"""Signature for the triage intent detection module - Conversational Agent Version."""

from typing import Literal

import dspy


class TriageSignature(dspy.Signature):
    """Determine user intent from query and available options for conversational Looker agent.

    GATHER_DATA_FROM_LOOKER: User asks a question about data that requires querying Looker Explore (e.g., 'show me revenue by country', 'what are our top 5 campaigns?', 'give me a trend of user signups'). This is the default for most analytical questions.
    GET_EXECUTIVE_SUMMARY: User asks for a summary, insights, interpretation, or a qualitative question about previously retrieved data (e.g., 'summarize these findings', 'what does this mean?', 'how are the campaigns performing?', 'give me an executive summary', 'what are the key insights?'). This is for analytical questions about current conversation data.
    DRILL_DOWN_ANALYSIS: User asks a follow-up question that explicitly seeks to **filter, segment, or 'drill down' into the currently presented data**. This is triggered by phrases like 'drill down', 'open by', 'deep dive', 'show me this for [new segment]', or requests to filter current results.
    AGENT_CAPABILITIES: User asks about the agent's capabilities, features, or what it can do (e.g., 'What can you do for me?', 'What are your capabilities?', 'How can you help me?', 'What features do you have?')
    DATA_SOURCE_INFO: User asks about available data sources, what information is available in Looker, or requests sample queries (e.g., 'What data sources are available?', 'What information do you have?', 'Give me sample queries', 'What data can I access from Looker?')
    FRIENDLY_CONVERSATION: User is greeting, having casual conversation, or expressing thanks (e.g., 'Hello', 'Hi', 'Thank you', 'How are you')
    MANAGE_CONVERSATION: User wants to manage their conversation history, clear context, or start fresh (e.g., 'clear history', 'start over', 'new conversation')
    OTHER: Everything else that doesn't fit above categories

    CRITICAL CONTEXT RULES:
    - **INTENT HIERARCHY**: The default for any new request for data, metrics, or analysis is `GATHER_DATA_FROM_LOOKER`. Only use `DRILL_DOWN_ANALYSIS` if the user uses explicit drill-down commands on existing data.

    - **`GATHER_DATA_FROM_LOOKER` Triggers**:
      - Use for general data inquiries: 'show me revenue by country', 'what are our top 5 campaigns?', 'give me a trend of user signups'.
      - Use if the query mentions Looker, specific metrics, dimensions, or data exploration.
      - This is the standard path for asking for a new slice or view of data from Looker.

    - **`DRILL_DOWN_ANALYSIS` Triggers**:
      - Use **only** when the user uses explicit command-like language to filter the *current* conversation data, such as: 'open by...', 'let's drill down on...', 'deep dive into...', 'filter this by...', 'show me just the...'.
      - This intent is for modifying or segmenting existing conversation results, not for fetching new data from Looker.

    - **`MANAGE_CONVERSATION` Triggers**:
      - Use for queries like 'clear the conversation', 'start fresh', 'reset context', 'new session'.
      - This covers conversation management and context clearing.

    - If the user query asks for analytical insights, interpretation, or qualitative questions about data already in the conversation, the intent is GET_EXECUTIVE_SUMMARY.
    """

    user_query: str = dspy.InputField(desc="The full, unaltered text from the user.")

    conversation_history: str = dspy.InputField(
        desc="A summary of the recent conversation turns and the user's profile."
    )

    intent: Literal[
        "GATHER_DATA_FROM_LOOKER",
        "GET_EXECUTIVE_SUMMARY", 
        "DRILL_DOWN_ANALYSIS",
        "AGENT_CAPABILITIES",
        "DATA_SOURCE_INFO",
        "FRIENDLY_CONVERSATION",
        "MANAGE_CONVERSATION",
        "OTHER",
    ] = dspy.OutputField(desc="The single, most likely classified intent of the user.")