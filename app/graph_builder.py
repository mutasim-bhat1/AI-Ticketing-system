from langgraph.graph import StateGraph, END
from app.state import TicketState
from app.nodes import WorkflowNodes


def build_ticket_graph(llm, tools, config: dict):
    """
    Assembles the agentic StateGraph workflow.

    OLD GRAPH (7 nodes, hardcoded tool order):
        extract_intents → intent_router → search_kb → decision_node → action_node/escalation_node → intent_router → aggregate

    NEW GRAPH (4 nodes, LLM chooses tools):
        extract_intents → intent_router → agent → intent_router → ... → aggregate

    The 'agent' node is where ALL the intelligence lives — the LLM
    autonomously decides which tools to call inside a ReAct loop.
    """
    nodes = WorkflowNodes(llm, tools, config)

    workflow = StateGraph(TicketState)

    # ─── Define Nodes (only 4 now!) ───────────────────────────
    workflow.add_node("extract_intents", nodes.extract_intents_node)
    workflow.add_node("intent_router", nodes.intent_router_node)
    workflow.add_node("agent", nodes.agent_node)            # ← THE agentic node
    workflow.add_node("aggregate", nodes.aggregate_node)

    # ─── Define Flow ──────────────────────────────────────────
    workflow.set_entry_point("extract_intents")
    workflow.add_edge("extract_intents", "intent_router")

    # Router: process next intent or aggregate results
    def should_continue_loop(state: TicketState):
        if state.get("current_intent") is not None:
            return "process"
        return "aggregate"

    workflow.add_conditional_edges(
        "intent_router",
        should_continue_loop,
        {
            "process": "agent",
            "aggregate": "aggregate"
        }
    )

    # After agent processes an intent, go back to router for the next one
    workflow.add_edge("agent", "intent_router")

    # Aggregation is the final step
    workflow.add_edge("aggregate", END)

    return workflow.compile()
