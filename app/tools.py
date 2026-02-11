"""
Tool factory functions for the AI ticketing agent.
Uses closures to avoid global state and improve testability.
"""
from langchain.tools import tool
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def create_search_kb_tool(knowledge_base: list):
    """
    Factory function to create a search_kb tool with KB injected via closure.
    
    Args:
        knowledge_base: List of service dictionaries from kb.json
    
    Returns:
        A LangChain tool function that searches the knowledge base
    """
    @tool
    def search_kb(query: str) -> dict:
        """
        Search the knowledge base for a matching service based on keywords.
        
        Args:
            query: The user's query text
        
        Returns:
            A service dict with: service, department, email, authority, auto_reply_allowed, keywords
            OR {"error": "No matching service found"} if no match
        
        Use this FIRST for every query to find the appropriate department.
        """
        query_lower = query.lower()
        
        for item in knowledge_base:
            for kw in item["keywords"]:
                if kw in query_lower:
                    return item
        
        return {"error": "No matching service found"}
    
    return search_kb


def create_generate_reply_tool():
    """
    Factory function to create a generate_reply tool.
    
    Returns:
        A LangChain tool function that generates auto-replies
    """
    @tool
    def generate_reply(query: str) -> str:
        """
        Generate a generic auto-reply response for simple queries.
        
        Args:
            query: The user's query text
        
        Returns:
            A generic acknowledgment message
        
        ONLY use this when:
        - search_kb() found a service with auto_reply_allowed = true
        - The query can be handled with a simple acknowledgment
        """
        return (
            "Thank you for contacting us. "
            "Your request has been received and noted. "
            "Our team will review your query and take appropriate action. "
            "You will receive a response shortly."
        )
    
    return generate_reply


def create_send_email_tool(smtp_config: dict):
    """
    Factory function to create a send_email tool with SMTP config injected via closure.
    
    Args:
        smtp_config: Dictionary with keys: sender_email, sender_password, smtp_host, smtp_port
    
    Returns:
        A LangChain tool function that sends emails via SMTP
    """
    @tool
    def send_email(email: str, subject: str, body: str) -> str:
        """
        Send an email ticket to the appropriate department for human handling.
        
        Args:
            email: The department's email address (from KB or general support email)
            subject: Clear subject line (e.g., "New Ticket: Password Reset")
            body: The user's query with any relevant context
        
        Returns:
            Confirmation message
        
        Use this when:
        - search_kb() found a service with auto_reply_allowed = false
        - No KB match but query is valid (send to general support)
        - The query requires human attention
        
        Example:
            send_email(
                email="academics@example.com",
                subject="New Ticket: Academic Support - Grade Query",
                body="User Query: I want to see my 8th class results\\n\\nRequires academic office review."
            )
        """
        sender_email = smtp_config["sender_email"]
        sender_password = smtp_config["sender_password"]
        smtp_host = smtp_config["smtp_host"]
        smtp_port = smtp_config["smtp_port"]
        
        # Print to terminal for logging
        print("\n" + "="*60)
        print(" SENDING EMAIL")
        print("="*60)
        print(f"From: {sender_email}")
        print(f"To: {email}")
        print(f"Subject: {subject}")
        print(f"Body:\n{body}")
        print("="*60)
        
        try:
            # Create email message
            message = MIMEMultipart()
            message["From"] = sender_email
            message["To"] = email
            message["Subject"] = subject
            
            # Add body to email
            message.attach(MIMEText(body, "plain"))
            
            # Connect to SMTP server
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()  # Secure the connection
                server.login(sender_email, sender_password)
                server.send_message(message)
            
            print(" EMAIL SENT SUCCESSFULLY!")
            print("="*60 + "\n")
            return f" Email ticket sent successfully to {email}"
            
        except Exception as e:
            error_msg = f" Failed to send email: {str(e)}"
            print(error_msg)
            print("="*60 + "\n")
            return error_msg
    
    return send_email


def create_escalate_tool():
    """
    Factory function to create an escalate tool.
    
    Returns:
        A LangChain tool function that escalates queries to human review
    """
    @tool
    def escalate(reason: str) -> str:
        """
        Escalate to human review for problematic queries.
        
        Args:
            reason: Clear explanation of why escalation is needed
        
        Returns:
            Escalation confirmation message
        
        ONLY use this as a LAST RESORT when:
        - Query is abusive, spam, or nonsensical
        - Technical error prevents processing
        - You genuinely cannot understand the request
        
        DO NOT use for:
        - Queries that don't match KB (send email instead)
        - Valid queries that need human help (send email instead)
        """
        return f"Escalated for human review. Reason: {reason}"
    
    return escalate


def create_tools(knowledge_base: list, smtp_config: dict) -> list:
    """
    Create all tools with their dependencies injected.
    
    Args:
        knowledge_base: List of service dictionaries from kb.json
        smtp_config: Dictionary with SMTP configuration
    
    Returns:
        List of LangChain tool functions
    """
    return [
        create_search_kb_tool(knowledge_base),
        create_generate_reply_tool(),
        create_send_email_tool(smtp_config),
        create_escalate_tool()
    ]
