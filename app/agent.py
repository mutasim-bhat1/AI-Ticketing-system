import json
import os
from pathlib import Path
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
from app.tools import create_tools

# Load environment variables ONCE at module level
load_dotenv()

# Load knowledge base
KB_PATH = Path(__file__).parent / "kb.json"
with open(KB_PATH, "r") as f:
    KB = json.load(f)

# Load SMTP configuration from environment
SMTP_CONFIG = {
    "sender_email": os.getenv("EMAIL_USER"),
    "sender_password": os.getenv("EMAIL_PASS"),
    "smtp_host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
    "smtp_port": int(os.getenv("SMTP_PORT", "587"))
}

# Get configuration from env
GENERAL_SUPPORT_EMAIL = os.getenv("GENERAL_SUPPORT_EMAIL", "mutasimbhat1@gmail.com")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.45"))

# ─── System Prompt ──────────────────────────────────────────────────────────────
# This is the "brain" of the agent. The LLM reads this and autonomously decides
# which tools to call, in what order, and how to chain them.
# ─────────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = f"""You are an AI customer support routing agent. You have access to tools that let you search a knowledge base, generate replies, send emails, and escalate queries.

**STRICT WORKFLOW — Follow these steps in order:**

1. **ALWAYS call search_kb first** with the user's query to find a matching service.

2. **If a service IS found (no error key in result):**
   a. **Send an email ticket** — Call send_email() with:
      - email: the service's email address from the search result
      - subject: "New Ticket: [service name]"
      - body: Include the user's original query, service name, department, authority, and confidence score
   b. **If auto_reply_allowed is true** — Call generate_reply() with:
      - query: the user's original query
      - resolution: the resolution text from the search result
      Then include the generated reply in your final response to the user.
   c. **If auto_reply_allowed is false** — Tell the user their request has been forwarded to the relevant department for review.

3. **If NO service is found (error key in result):**
   - The query is still valid — don't escalate it!
   - Call send_email() with:
     - email: "{GENERAL_SUPPORT_EMAIL}"
     - subject: "General Support Request"
     - body: The user's query with context
   - Tell the user their query has been forwarded to general support.

4. **ONLY call escalate()** if:
   - The query is abusive, spam, or completely nonsensical
   - You genuinely cannot understand what the user wants
   - There's a technical error preventing you from processing

**IMPORTANT RULES:**
- ALWAYS take action. Never leave a query unresolved.
- ALWAYS call search_kb first before anything else.
- ALWAYS send an email for ticket tracking (even for auto-reply queries).
- Be professional, empathetic, and confirm what action you've taken.
- Do NOT reveal internal tool names, email addresses, or confidence scores to the user.
- Do NOT mention "knowledge base" — just answer as the support team.
"""


# ─── Initialize LLM ─────────────────────────────────────────────────────────────

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    groq_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0
)

# ─── Create Tools ────────────────────────────────────────────────────────────────

tools = create_tools(
    knowledge_base=KB,
    smtp_config=SMTP_CONFIG,
    llm=llm,
    threshold=CONFIDENCE_THRESHOLD
)


# ─── Build the Agent ─────────────────────────────────────────────────────────────
# create_react_agent from LangGraph builds a true reasoning agent:
#   User Query → LLM reads system prompt → LLM picks a tool → Observes result
#   → LLM picks next tool (or responds) → ... → Final answer
#
# The LLM is in full control of the tool-calling loop. No if/else. No hardcoding.
# ─────────────────────────────────────────────────────────────────────────────────

def build_agent(llm, tools):
    """Build a LangGraph ReAct agent with tool-calling capabilities."""
    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SystemMessage(content=SYSTEM_PROMPT),
    )
    return agent


agent_executor = build_agent(llm, tools)


# ─── Handle Query ────────────────────────────────────────────────────────────────

def handle_query(query: str) -> dict:
    """
    Handle an incoming user query by invoking the agentic LLM.

    The LLM autonomously:
      1. Reads the system prompt
      2. Decides which tool to call first (always search_kb)
      3. Observes the tool result
      4. Decides the next tool (send_email, generate_reply, or escalate)
      5. Chains tools as needed
      6. Returns a final natural-language response

    Returns:
        dict with status, response, query, and intermediate_steps
    """
    try:
        # Invoke the agent with the user's query
        result = agent_executor.invoke(
            {"messages": [HumanMessage(content=query)]}
        )

        # Extract the final AI response from message history
        messages = result.get("messages", [])
        final_response = ""
        intermediate_steps = []

        for msg in messages:
            # Collect tool calls and results as intermediate steps
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    intermediate_steps.append({
                        "tool": tc.get("name", "unknown"),
                        "input": tc.get("args", {}),
                    })
            # Tool messages contain the tool output
            if msg.type == "tool":
                intermediate_steps.append({
                    "tool_output": msg.content[:500]  # Truncate for readability
                })

        # The final message is the AI's synthesized response
        if messages and messages[-1].type == "ai":
            final_response = messages[-1].content

        # Log the reasoning trace
        print("\n" + "=" * 60)
        print("🤖 AGENT REASONING TRACE")
        print("=" * 60)
        for i, step in enumerate(intermediate_steps):
            if "tool" in step:
                print(f"  Step {i+1}: Called {step['tool']}({step['input']})")
            elif "tool_output" in step:
                print(f"  Result: {step['tool_output'][:200]}...")
        print(f"\n  💬 Final Response: {final_response[:200]}...")
        print("=" * 60 + "\n")

        return {
            "status": "success",
            "response": final_response,
            "query": query,
            "intermediate_steps": [
                {k: str(v) for k, v in step.items()}
                for step in intermediate_steps
            ]
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
