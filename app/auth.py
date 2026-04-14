"""
Simple Authentication Module for the AI Ticketing System.

Uses a JSON file store with bcrypt-hashed passwords.
Provides register, login, and token-based session management.
"""

import json
import os
import hashlib
import secrets
import time
from pathlib import Path

# ─── File-based User Store ──────────────────────────────────────────────────────
USERS_FILE = Path(__file__).parent / "users.json"
SESSIONS = {}  # token -> {user_id, email, name, role, expires}


def _load_users() -> dict:
    """Load users from JSON file."""
    if not USERS_FILE.exists():
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def _save_users(users: dict):
    """Save users to JSON file."""
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def _hash_password(password: str) -> str:
    """Hash a password using SHA-256 + salt."""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return f"{salt}:{hashed}"


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against its stored hash."""
    salt, expected_hash = stored_hash.split(":", 1)
    actual_hash = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return actual_hash == expected_hash


def _generate_token() -> str:
    """Generate a secure session token."""
    return secrets.token_urlsafe(48)


# ─── Public API ─────────────────────────────────────────────────────────────────

def register_user(email: str, password: str, name: str, role: str = "user") -> dict:
    """
    Register a new user.
    
    Args:
        email: User's email (used as unique ID)
        password: Plain-text password (will be hashed)
        name: Display name
        role: 'user' or 'admin'
    
    Returns:
        dict with status and user info or error
    """
    email = email.strip().lower()
    role = role.strip().lower()
    
    if role not in ("user", "admin"):
        return {"status": "error", "error": "Role must be 'user' or 'admin'"}

    if not email or not password or not name:
        return {"status": "error", "error": "All fields are required"}

    if len(password) < 6:
        return {"status": "error", "error": "Password must be at least 6 characters"}

    users = _load_users()

    if email in users:
        return {"status": "error", "error": "An account with this email already exists"}

    # Create user
    users[email] = {
        "name": name.strip(),
        "role": role,
        "password_hash": _hash_password(password),
        "created_at": time.time()
    }
    _save_users(users)

    print(f"✅ [AUTH] New user registered: {email} ({role})")
    return {
        "status": "success",
        "user": {"email": email, "name": name.strip(), "role": role}
    }


def login_user(email: str, password: str) -> dict:
    """
    Authenticate a user and return a session token.
    
    Returns:
        dict with token, user info, or error
    """
    email = email.strip().lower()
    users = _load_users()

    if email not in users:
        return {"status": "error", "error": "Invalid email or password"}

    user = users[email]
    if not _verify_password(password, user["password_hash"]):
        return {"status": "error", "error": "Invalid email or password"}

    # Create session
    token = _generate_token()
    SESSIONS[token] = {
        "email": email,
        "name": user["name"],
        "role": user["role"],
        "expires": time.time() + (24 * 60 * 60)  # 24 hours
    }

    print(f"✅ [AUTH] Login: {email} ({user['role']})")
    return {
        "status": "success",
        "token": token,
        "user": {
            "email": email,
            "name": user["name"],
            "role": user["role"]
        }
    }


def get_current_user(token: str) -> dict | None:
    """
    Validate a session token and return the user.
    Returns None if invalid/expired.
    """
    if not token:
        return None

    session = SESSIONS.get(token)
    if not session:
        return None

    if time.time() > session["expires"]:
        del SESSIONS[token]
        return None

    return {
        "email": session["email"],
        "name": session["name"],
        "role": session["role"]
    }


def logout_user(token: str) -> bool:
    """Remove a session token."""
    if token in SESSIONS:
        del SESSIONS[token]
        return True
    return False
