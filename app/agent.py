import json
import os
from pathlib import Path
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain.agents import create_agent
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

# Get general support email from env
GENERAL_SUPPORT_EMAIL = os.getenv("GENERAL_SUPPORT_EMAIL", "mutasimbhat1@gmail.com")

# System prompt for the agent
SYSTEM_PROMPT = f"""You are an AI customer support ticketing agent. Your job is to intelligently route user queries to the appropriate department.

**WORKFLOW:**

1. **ALWAYS start by calling search_kb()** with the user's query to find a matching service.

2. **If a service is found:**
   - Check if `auto_reply_allowed` is true:
     * If TRUE: Call generate_reply() and provide a helpful response
     * If FALSE: Call send_email() with:
       - email: the service's email address
       - subject: A clear subject line (e.g., "New Ticket: [Service Name]")
       - body: Include the user's original query and any relevant context
   
3. **If NO service is found (error returned):**
   - The query is still valid! Don't just escalate.
   - Create a ticket for the "General Support" category
   - Call send_email() with:
     - email: "{GENERAL_SUPPORT_EMAIL}" (general support email)
     - subject: "General Support Request"
     - body: The user's query with context
   
4. **ONLY call escalate()** if:
   - The query is abusive, spam, or completely nonsensical
   - You genuinely cannot understand what the user wants
   - There's a technical error preventing you from processing

**IMPORTANT RULES:**
- ALWAYS send an email for queries that need human attention (auto_reply_allowed = false)
- Be proactive: Even if no KB match, still create a ticket via email
- Be helpful: Acknowledge the user's request in your response
- Never leave a user without action taken

Always respond professionally and confirm what action you've taken."""

# Initialize Gemini model
# llm = ChatGoogleGenerativeAI(
#     model="gemini-2.5-flash",
#     google_api_key=os.getenv("GEMINI_API_KEY"),
#     temperature=0
# )
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    groq_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0
)

# Create tools with dependencies injected (no globals!)
tools = create_tools(knowledge_base=KB, smtp_config=SMTP_CONFIG)

# Note: create_agent() doesn't work well with Groq
# Using manual tool-calling approach instead
def handle_query(query: str) -> dict:
    """Handle incoming user query through manual tool orchestration."""
    try:
        # Step 1: Search knowledge base
        search_tool = tools[0]  # search_kb
        generate_reply_tool = tools[1]  # generate_reply
        send_email_tool = tools[2]  # send_email
        escalate_tool = tools[3]  # escalate
        
        # Search KB
        kb_result = search_tool.invoke({"query": query})
        
        # Step 2: Decide action based on KB result
        if isinstance(kb_result, dict) and "error" in kb_result:
            # No match found - send to general support
            print(f"\n📧 No KB match - Sending to general support...")
            email_result = send_email_tool.invoke({
                "email": GENERAL_SUPPORT_EMAIL,
                "subject": "General Support Request",
                "body": f"User Query: {query}\n\nNo matching service found in knowledge base. Requires human review."
            })
            response = f"Thank you for contacting us. Your query has been forwarded to our general support team for review. You will receive a response shortly.\n\n{email_result}"
        
        else:
            # Match found - ALWAYS send email for ticket tracking
            service_name = kb_result.get('service')
            department = kb_result.get('department')
            authority = kb_result.get('authority')
            email_address = kb_result.get('email')
            
            print(f"\n📧 KB Match: {service_name} - Sending email to {department}...")
            
            # Send email to create ticket
            email_result = send_email_tool.invoke({
                "email": email_address,
                "subject": f"New Ticket: {service_name}",
                "body": f"User Query: {query}\n\nService: {service_name}\nDepartment: {department}\nAuthority: {authority}\n\nThis ticket has been automatically created and routed to your department."
            })
            
            # Check if auto-reply is allowed
            if kb_result.get("auto_reply_allowed"):
                # Generate friendly auto-reply for user
                auto_reply = generate_reply_tool.invoke({"query": query})
                response = f"{auto_reply}\n\nYour ticket has been created and forwarded to {department} ({authority}). Ticket reference: {service_name}.\n\n{email_result}"
            else:
                # No auto-reply, just confirmation
                response = f"Your request has been received and a ticket has been created. It has been forwarded to {department} ({authority}) for review. You will receive a detailed response from our team shortly.\n\n{email_result}"
        
        return {
            "status": "success",
            "response": response,
            "query": query
        }
    
    except Exception as e:
        # Detailed error for debugging
        import traceback
        error_details = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(f"\n❌ ERROR in handle_query:\n{error_details}\n")
        
        return {
            "status": "error",
            "error": str(e),
            "query": query
        }
