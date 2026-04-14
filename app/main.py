from fastapi import FastAPI, Request, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from app.agent import handle_query
from app.analytics import shutdown as analytics_shutdown, identify_user
from app.auth import register_user, login_user, get_current_user, logout_user
from app.db import get_tickets, update_ticket_status, create_ticket

app = FastAPI(title="AI Ticketing System")

@app.on_event("shutdown")
def shutdown_event():
    """Flush PostHog events on server shutdown."""
    analytics_shutdown()

# CORS — allow frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ─── Request Models ─────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str
    user_email: Optional[str] = None

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str = "user"

class LoginRequest(BaseModel):
    email: str
    password: str


# ─── Page Routes ────────────────────────────────────────────────────────────────

@app.get("/")
def serve_login():
    """Serve the login/register page."""
    return FileResponse("static/login.html")

@app.get("/dashboard")
def serve_dashboard():
    """Serve the main dashboard UI."""
    return FileResponse("static/index.html")


# ─── Auth Endpoints ─────────────────────────────────────────────────────────────

@app.post("/api/register")
def api_register(payload: RegisterRequest):
    """Register a new user account."""
    result = register_user(
        email=payload.email,
        password=payload.password,
        name=payload.name,
        role=payload.role
    )
    if result["status"] == "success":
        # Identify the user in PostHog upon registration
        identify_user(
            user_email=result["user"]["email"],
            name=result["user"]["name"],
            role=result["user"]["role"]
        )
    return result

@app.post("/api/login")
def api_login(payload: LoginRequest):
    """Log in and receive a session token."""
    result = login_user(email=payload.email, password=payload.password)
    if result["status"] == "success":
        # Identify the user in PostHog upon login
        identify_user(
            user_email=result["user"]["email"],
            name=result["user"]["name"],
            role=result["user"]["role"]
        )
    return result

@app.get("/api/me")
def api_me(authorization: Optional[str] = Header(None)):
    """Get current user info from session token."""
    if not authorization:
        return {"status": "error", "error": "Not authenticated"}
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    if not user:
        return {"status": "error", "error": "Session expired or invalid"}
    
    return {"status": "success", "user": user}

@app.get("/api/tickets")
def api_get_tickets(authorization: Optional[str] = Header(None)):
    """Fetch tickets for the current user or all for admin."""
    if not authorization:
        return {"status": "error", "error": "Not authenticated"}
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    if not user:
        return {"status": "error", "error": "Invalid session"}
    
    tickets = get_tickets(user_email=user["email"], is_admin=(user["role"] == "admin"))
    return {"status": "success", "tickets": tickets}

@app.post("/api/tickets/{ticket_id}/resolve")
def api_resolve_ticket(ticket_id: str, authorization: Optional[str] = Header(None)):
    """Mark a ticket as resolved (Admin only)."""
    if not authorization:
        return {"status": "error", "error": "Not authenticated"}
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    if not user or user["role"] != "admin":
        return {"status": "error", "error": "Unauthorized"}
    
    update_ticket_status(ticket_id, "resolved")
    return {"status": "success"}

# ─── Query Endpoint (now user-aware and persistent) ────────────────────────────

@app.post("/query")
def route_query(payload: QueryRequest):
    result = handle_query(payload.query, user_id=payload.user_email)
    
    # If tickets were created, save them to the database
    if result["status"] == "success" and payload.user_email:
        for t in result.get("tickets_created", []):
            # We map the agent's ticket format to our DB format
            # The agent doesn't provide an ID, so we'll generate or use a simple counter
            # In a real app, we'd use a UUID. Here we'll generate a simple one.
            import uuid
            ticket_id = str(uuid.uuid4())[:8].upper()
            
            db_ticket = {
                "id": ticket_id,
                "subject": t.get("service") or t.get("intent") or payload.query[:50],
                "department": t.get("department") or "General Support",
                "email": t.get("email"),
                "status": "open",
                "priority": "medium", # Could be parsed from intent later
                "response": result["response"],
                "log": t.get("log")
            }
            create_ticket(db_ticket, payload.user_email)
            
    return result
