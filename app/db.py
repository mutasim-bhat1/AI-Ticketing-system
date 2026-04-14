"""
Database module for the AI Ticketing System.
Handles persistent storage for tickets using SQLite.
"""

import sqlite3
import json
import time
from pathlib import Path
from typing import List, Dict, Any

DB_PATH = Path(__file__).parent / "ticketing.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database schema."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id TEXT PRIMARY KEY,
                user_email TEXT NOT NULL,
                subject TEXT NOT NULL,
                department TEXT NOT NULL,
                email TEXT,
                status TEXT DEFAULT 'open',
                priority TEXT DEFAULT 'medium',
                response TEXT,
                log TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    print("✅ [DB] Database initialized successfully.")

def create_ticket(ticket_data: Dict[str, Any], user_email: str) -> str:
    """Save a new ticket to the database."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO tickets (id, user_email, subject, department, email, status, priority, response, log)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticket_data["id"],
            user_email,
            ticket_data["subject"],
            ticket_data["department"],
            ticket_data.get("email"),
            ticket_data.get("status", "open"),
            ticket_data.get("priority", "medium"),
            ticket_data.get("response"),
            ticket_data.get("log")
        ))
        conn.commit()
    return ticket_data["id"]

def get_tickets(user_email: str = None, is_admin: bool = False) -> List[Dict[str, Any]]:
    """Retrieve tickets. Returns all for admin, or filtered for user."""
    with get_db() as conn:
        if is_admin:
            cursor = conn.execute("SELECT * FROM tickets ORDER BY created_at DESC")
        else:
            cursor = conn.execute("SELECT * FROM tickets WHERE user_email = ? ORDER BY created_at DESC", (user_email,))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def update_ticket_status(ticket_id: str, status: str):
    """Update the status of a specific ticket."""
    with get_db() as conn:
        conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
        conn.commit()

# Initialize on import
init_db()
