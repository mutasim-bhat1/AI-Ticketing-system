from typing import TypedDict, List, Dict, Optional


class TicketState(TypedDict):
    """
    Represents the state of the ticket routing workflow.

    The 'kb_result' and 'decision' fields are GONE — the agent
    manages its own reasoning internally. We only track the
    final outputs (tickets, responses) in the shared state.
    """
    original_query: str
    intents: List[str]
    current_intent: Optional[str]
    current_intent_index: int
    tickets_created: List[Dict]
    responses: List[str]
    final_response: str
