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
    # We combine 'service' and 'keywords' for a richer semantic representation
    kb_embeddings = []
    for item in knowledge_base:
        text_to_embed = f"{item['service']} {' '.join(item['keywords'])}"
        embedding = embeddings_model.embed_query(text_to_embed)
        kb_embeddings.append(embedding)

    @tool
    def search_kb(query: str) -> dict:
        """
        Search the knowledge base for a matching service using semantic similarity.
        
        Args:
            query: The user's query text
        
        Returns:
            A service dict with: service, department, email, authority, auto_reply_allowed, keywords, and confidence
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
    Factory function to create an intelligent generate_reply tool using the LLM.
    
    Returns:
        A LangChain tool function that generates context-aware replies
    """
    @tool
    def generate_reply(query: str, resolution: str) -> str:
        """
        Dynamically synthesize a helpful response using the LLM and KB facts.
        """
        log_tool_call("generate_reply", {"query": query})
        
        # We craft a prompt to ensure the AI uses the provided data to answer naturally
        prompt = (
            "You are a helpful customer support agent. A user has asked a question, "
            "and we have found the relevant information in our knowledge base.\n\n"
            f"USER QUERY: {query}\n"
            f"KNOWLEDGE BASE FACTS: {resolution}\n\n"
            "INSTRUCTIONS:\n"
            "1. Rewrite the information in a professional, empathetic, and helpful way.\n"
            "2. Address the user's query directly.\n"
            "3. Do not make up any facts; only use the knowledge base facts provided.\n"
            "4. Keep it concise but thorough.\n"
            "5. Do NOT mention that you are an AI or using a 'Knowledge Base'. Just answer as the support team.\n\n"
            "YOUR RESPONSE:"
        )
        
        try:
            # Call the LLM to generate the personalized response
            ai_response = llm.invoke(prompt)
            # Extract content (ChatGroq returns an AIMessage object)
            response_text = ai_response.content if hasattr(ai_response, 'content') else str(ai_response)
            
            return response_text
            
        except Exception as e:
            print(f"[LOG] LLM Generation failed: {e}. Falling back to template.")
            # Fallback if the LLM call fails
            return f"Thank you for reaching out. Based on our records: {resolution}"
    
    return generate_reply


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
        create_send_email_tool(smtp_config),
        create_escalate_tool()
    ]
