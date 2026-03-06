import json
import os
from pathlib import Path
from langchain_groq import ChatGroq
from dotenv import load_dotenv

from app.tools import create_tools
from app.graph_builder import build_ticket_graph

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


def handle_query(query: str) -> dict:
    """
    Enterprise-grade handler for multi-intent support queries.
    Uses a deterministic StateGraph to process each intent independently.
    """
    try:
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
        print(f"\n🚀 [START] Processing Query: {query}")
        final_state = ticket_workflow.invoke(initial_state)
        print(f"🏁 [END] Workflow complete.\n")

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

        return {
            "status": "error",
            "error": str(e),
            "query": query
        }
