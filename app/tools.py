"""
Tool factory functions for the AI ticketing agent.
Uses closures to avoid global state and improve testability.
"""
from langchain.tools import tool
import smtplib
import os
import datetime
import numpy as np
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from langchain_huggingface import HuggingFaceEmbeddings
from app.analytics import track_email_sent, track_query_escalated

# Initialize local embedding model (free, fast)
embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def log_tool_call(tool_name: str, args: dict):
    """Utility to log tool calls to terminal with timestamp."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[LOG {timestamp}] TOOL CALL: {tool_name}")
    print(f"[LOG {timestamp}] ARGUMENTS: {args}")

def cosine_similarity(v1, v2):
    """Calculate cosine similarity between two vectors."""
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    return dot_product / (norm_v1 * norm_v2)

def create_search_kb_tool(knowledge_base: list, threshold: float = 0.4):
    """
    Factory function to create a search_kb tool with KB and embeddings injected via closure.
    
    Args:
        knowledge_base: List of service dictionaries from kb.json
        threshold: Minimum similarity score (0-1) to consider a match valid
    
    Returns:
        A LangChain tool function that searches the knowledge base using embeddings
    """
    # Pre-calculate embeddings for the Knowledge Base for efficiency
    # We embed 'service + description' — NO hardcoded keywords. The AI figures out
    # the semantic connection between the user's query and the service description.
    kb_embeddings = []
    for item in knowledge_base:
        text_to_embed = f"{item['service']}: {item.get('description', '')}"
        embedding = embeddings_model.embed_query(text_to_embed)
        kb_embeddings.append(embedding)

    @tool
    def search_kb(query: str) -> dict:
        """
        Search the knowledge base for a matching service using semantic similarity.
        
        Args:
            query: The user's query text
        
        Returns:
            A service dict with: service, department, email, authority, auto_reply_allowed, description, and confidence
            OR {"error": "No matching service found"} if no match above threshold
        """
        log_tool_call("search_kb", {"query": query})
        
        # 1. Embed the query
        query_embedding = embeddings_model.embed_query(query)
        
        # 2. Find the best match using cosine similarity
        print(f"[DEBUG] Calculating similarity scores for {len(kb_embeddings)} services...")
        best_score = -1
        best_match = None
        
        for i, kb_embedding in enumerate(kb_embeddings):
            score = cosine_similarity(query_embedding, kb_embedding)
            service_name = knowledge_base[i]['service']
            print(f"  - {service_name}: {round(float(score), 4)}")
            
            if score > best_score:
                best_score = float(score)
                best_match = knowledge_base[i]
        
        # 3. Apply confidence threshold
        if best_match and best_score >= threshold:
            # Return match with confidence score
            result = best_match.copy()
            result["confidence"] = round(best_score, 4)
            print(f"[LOG] WINNER: {result['service']} (Score: {result['confidence']} >= {threshold})")
            return result
        
        print(f"[LOG] REJECTED: Top match was {best_match['service'] if best_match else 'None'} with score {round(best_score, 4)} (Needs {threshold})")
        return {"error": "No matching service found above confidence threshold", "best_score": round(best_score, 4)}
    
    return search_kb


def create_generate_reply_tool(llm):
    """
    Factory function to create a TRULY agentic generate_reply tool.
    
    The LLM generates its OWN answer using its knowledge + the service context.
    No pre-written resolution is provided — the AI reasons and creates the response.
    
    Returns:
        A LangChain tool function that generates intelligent, original replies
    """
    @tool
    def generate_reply(query: str, service: str, department: str) -> str:
        """
        Generate an intelligent, context-aware response for the user's query.
        The AI uses its own knowledge and reasoning to craft helpful guidance.
        
        Args:
            query: The user's original question or request
            service: The matched service category (e.g. 'Password Reset')
            department: The responsible department (e.g. 'IT Support')
        """
        log_tool_call("generate_reply", {"query": query, "service": service, "department": department})
        
        prompt = (
            "You are a knowledgeable customer support agent for an organization.\n"
            "A user has submitted a support request, and it has been routed to the correct department.\n\n"
            f"USER QUERY: {query}\n"
            f"SERVICE CATEGORY: {service}\n"
            f"RESPONSIBLE DEPARTMENT: {department}\n\n"
            "INSTRUCTIONS:\n"
            "1. Provide a professional, empathetic, and helpful response.\n"
            "2. Use your knowledge to suggest common steps, processes, or resolutions for this type of issue.\n"
            "3. Be specific and actionable — give the user concrete steps they can take.\n"
            "4. If it's a process (like password reset, refund, etc.), outline the typical steps clearly.\n"
            "5. Mention that a support ticket has been created and the relevant team will follow up.\n"
            "6. Keep it concise but thorough.\n"
            "7. Do NOT mention that you are an AI. Respond as the support team.\n\n"
            "YOUR RESPONSE:"
        )
        
        try:
            ai_response = llm.invoke(prompt)
            response_text = ai_response.content if hasattr(ai_response, 'content') else str(ai_response)
            return response_text
            
        except Exception as e:
            print(f"[LOG] LLM Generation failed: {e}. Falling back to template.")
            return (
                f"Thank you for reaching out regarding {service}. "
                f"Your request has been forwarded to the {department} team. "
                f"A team member will get back to you shortly."
            )
    
    return generate_reply


def create_chat_tool(llm):
    """
    Factory function to create a chat tool for general conversational queries.
    This tool answers general questions WITHOUT creating tickets or sending emails.
    Used when the user asks something that is not a support request.
    """
    @tool
    def chat(query: str) -> str:
        """
        Answer a general user question directly using AI knowledge.
        Use this for non-support queries like greetings, general knowledge, or casual conversation.
        No ticket is created and no email is sent.
        
        Args:
            query: The user's general question or message
        """
        log_tool_call("chat", {"query": query})
        
        prompt = (
            "You are the 'AI Ticketing Management System'.\n"
            "STRICT RULES:\n"
            "1. IDENTITY: You are a professional support assistant. NEVER identify as 'Llama', 'Meta', or a generic AI model.\n"
            "2. MISSION: Help the user with their ticketing needs or answer general questions helpfully.\n"
            "3. STYLE: Professional, concise, and corporate.\n\n"
            f"USER QUERY: {query}"
        )
        
        try:
            response = llm.invoke(prompt)
            return response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            print(f"[LOG] Chat tool failed: {e}")
            return "I'm sorry, I couldn't process your request at the moment."
    return chat


def create_send_email_tool(smtp_config: dict):
    """
    Factory function to create a send_email tool with SMTP config injected via closure.
    """
    @tool
    def send_email(email: str, subject: str, body: str) -> str:
        """
        Send an email ticket to the appropriate department for human handling.
        """
        log_tool_call("send_email", {"email": email, "subject": subject})
        
        sender_email = smtp_config["sender_email"]
        sender_password = smtp_config["sender_password"]
        smtp_host = smtp_config["smtp_host"]
        smtp_port = smtp_config["smtp_port"]
        
        try:
            # Create email message
            message = MIMEMultipart()
            message["From"] = sender_email
            message["To"] = email
            message["Subject"] = subject
            message.attach(MIMEText(body, "plain"))
            
            # Connect to SMTP server
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()  # Secure the connection
                server.login(sender_email, sender_password)
                server.send_message(message)
            
            log_result = f"Email sent to {email}"
            print(f"[LOG] {log_result}")
            track_email_sent(
                to_email=email,
                subject=subject,
            )
            return f"Email ticket sent successfully to {email}"
            
        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            print(f"[LOG] ERROR: {error_msg}")
            return error_msg
    
    return send_email


def create_escalate_tool():
    """
    Factory function to create an escalate tool.
    """
    @tool
    def escalate(reason: str) -> str:
        """
        Escalate to human review for problematic queries.
        """
        log_tool_call("escalate", {"reason": reason})
        track_query_escalated(query="", reason=reason)
        return f"Escalated for human review. Reason: {reason}"
    
    return escalate


def create_tools(knowledge_base: list, smtp_config: dict, llm, threshold: float = 0.45) -> list:
    """
    Create all tools with their dependencies injected.
    
    Args:
        knowledge_base: List of service dictionaries from kb.json
        smtp_config: Dictionary with SMTP configuration
        llm: The ChatGroq LLM model
        threshold: Confidence threshold for KB search
    """
    return [
        create_search_kb_tool(knowledge_base, threshold),
        create_generate_reply_tool(llm),
        create_chat_tool(llm),
        create_send_email_tool(smtp_config),
        create_escalate_tool()
    ]
