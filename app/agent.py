import json
import os
import time
from pathlib import Path
from langchain_groq import ChatGroq
from dotenv import load_dotenv

from app.tools import create_tools
from app.graph_builder import build_ticket_graph
from app.analytics import (
    track_query_submitted,
    track_query_resolved,
    track_query_failed,
    track_ticket_created,
    shutdown as analytics_shutdown
)

# Load environment variables
load_dotenv()

# Load knowledge base
KB_PATH = Path(__file__).parent / "kb.json"
with open(KB_PATH, "r") as f:
    KB = json.load(f)

# Config injection
SMTP_CONFIG = {
    "sender_email": os.getenv("EMAIL_USER"),
    "sender_password": os.getenv("EMAIL_PASS"),
    "smtp_host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
    "smtp_port": int(os.getenv("SMTP_PORT", "587"))
}

APP_CONFIG = {
    "general_support_email": os.getenv("GENERAL_SUPPORT_EMAIL", "mutasimbhat1@gmail.com"),
    "confidence_threshold": float(os.getenv("CONFIDENCE_THRESHOLD", "0.45"))
}

# Initialize LLM
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    groq_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0
)

# Create tools (for use within workflow nodes)
tools = create_tools(
    knowledge_base=KB,
    smtp_config=SMTP_CONFIG,
    llm=llm,
    threshold=APP_CONFIG["confidence_threshold"]
)

# ─── Build the Compiled Graph ───────────────────────────────────────────────────
ticket_workflow = build_ticket_graph(llm, tools, APP_CONFIG)


def handle_query(query: str, user_id: str = None) -> dict:
    """
    Enterprise-grade handler for multi-intent support queries.
    Uses a deterministic StateGraph to process each intent independently.
    """
    try:
        # Track: user submitted a query
        track_query_submitted(query, user_id=user_id)
        start_time = time.time()

        # Initialize state
        initial_state = {
            "original_query": query,
            "intents": [],
            "current_intent": None,
            "current_intent_index": 0,
            "kb_result": None,
            "tickets_created": [],
            "responses": [],
            "final_response": ""
        }

        # Execute workflow
        print(f"\n\U0001f680 [START] Processing Query: {query}")
        final_state = ticket_workflow.invoke(initial_state)
        print(f"\U0001f3c1 [END] Workflow complete.\n")

        # Track: query resolved + ticket created (if any)
        duration = time.time() - start_time
        tickets = final_state.get("tickets_created", [])

        # Extract service/department from the first ticket (if created)
        service = tickets[0].get("service", "General") if tickets else "General"
        department = tickets[0].get("department", "General") if tickets else "General"

        track_query_resolved(
            query=query,
            service=service,
            department=department,
            tickets_count=len(tickets),
            duration_seconds=duration,
            user_id=user_id
        )

        # Track each ticket created
        for ticket in tickets:
            track_ticket_created(
                service=ticket.get("service", "Unknown"),
                department=ticket.get("department", "Unknown"),
                department_email=ticket.get("email", "Unknown"),
                query=query,
                user_id=user_id
            )

        return {
            "status": "success",
            "response": final_state["final_response"],
            "tickets_created": final_state["tickets_created"],
            "intents_processed": final_state["intents"]
        }

    except Exception as e:
        import traceback
        error_details = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(f"\n❌ ERROR in handle_query:\n{error_details}\n")

        # Track: query failed
        track_query_failed(query=query, error=str(e), user_id=user_id)

        return {
            "status": "error",
            "error": str(e),
            "query": query
        }

