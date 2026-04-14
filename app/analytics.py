"""
PostHog Analytics Module for the AI Ticketing System.

Tracks USER-FACING / BUSINESS events only — NOT internal pipeline steps.

Events tracked:
- query_submitted: User submits a support query
- ticket_created: A support ticket is created and emailed to a department
- email_sent: Email successfully delivered to department
- query_resolved: Query was resolved successfully (with response)
- query_escalated: Query escalated to human review
- query_failed: An error occurred while processing the query
"""

import os
from posthog import Posthog
from dotenv import load_dotenv

load_dotenv()

# ─── PostHog Configuration ──────────────────────────────────────────────────────
POSTHOG_API_KEY = os.getenv("POSTHOG_API_KEY", "")
POSTHOG_HOST = os.getenv("POSTHOG_HOST", "https://us.i.posthog.com")

_is_real_key = POSTHOG_API_KEY.startswith("phc_")
_client = None
_enabled = False

if _is_real_key:
    try:
        _client = Posthog(
            project_api_key=POSTHOG_API_KEY,
            host=POSTHOG_HOST,
            debug=os.getenv("POSTHOG_DEBUG", "false").lower() == "true"
        )
        _enabled = True
        print("✅ [PostHog] Analytics enabled")
    except Exception as e:
        print(f"⚠️ [PostHog] Failed to initialize: {e}")
else:
    if POSTHOG_API_KEY and not _is_real_key:
        print("⚠️ [PostHog] Invalid API key (must start with 'phc_'). Analytics disabled.")
    else:
        print("⚠️ [PostHog] No API key found — analytics disabled. Set POSTHOG_API_KEY in .env")


def _safe_capture(distinct_id: str, event: str, properties: dict):
    """Safely send event to PostHog. Never crashes the app."""
    if not _enabled or not _client:
        return
    try:
        _client.capture(
            distinct_id=distinct_id,
            event=event,
            properties=properties
        )
    except Exception as e:
        print(f"⚠️ [PostHog] Failed to track '{event}': {e}")


def _get_distinct_id(user_id: str = None) -> str:
    return user_id or "anonymous_user"


def identify_user(user_email: str, name: str = None, role: str = None):
    """
    Identify a user in PostHog so events are linked to a real person.
    Call this on login/register to associate the distinct_id with user traits.
    
    Uses capture() with $set to set person properties, which is the
    standard approach in the PostHog Python SDK.
    """
    if not _enabled or not _client:
        return
    try:
        person_properties = {}
        if name:
            person_properties["name"] = name
        if role:
            person_properties["role"] = role
        person_properties["email"] = user_email

        _client.capture(
            distinct_id=user_email,
            event="$identify",
            properties={
                "$set": person_properties
            }
        )
        print(f"✅ [PostHog] Identified user: {user_email} (role={role})")
    except Exception as e:
        print(f"⚠️ [PostHog] Failed to identify user: {e}")


# ─── USER-FACING BUSINESS EVENTS ────────────────────────────────────────────────

def track_query_submitted(query: str, user_id: str = None):
    """User submitted a support query."""
    _safe_capture(
        distinct_id=_get_distinct_id(user_id),
        event="query_submitted",
        properties={
            "query": query,
            "query_length": len(query),
        }
    )


def track_ticket_created(service: str, department: str, department_email: str, 
                          query: str, user_id: str = None):
    """A support ticket was created and emailed to the department."""
    _safe_capture(
        distinct_id=_get_distinct_id(user_id),
        event="ticket_created",
        properties={
            "service": service,
            "department": department,
            "department_email": department_email,
            "query": query,
        }
    )


def track_email_sent(to_email: str, subject: str, department: str = None, user_id: str = None):
    """Email was successfully sent to a department."""
    _safe_capture(
        distinct_id=_get_distinct_id(user_id),
        event="email_sent",
        properties={
            "to_email": to_email,
            "subject": subject,
            "department": department or "Unknown",
        }
    )


def track_query_resolved(query: str, service: str, department: str,
                          tickets_count: int, duration_seconds: float, user_id: str = None):
    """Query was fully resolved — user got a response."""
    _safe_capture(
        distinct_id=_get_distinct_id(user_id),
        event="query_resolved",
        properties={
            "query": query,
            "service": service,
            "department": department,
            "tickets_created": tickets_count,
            "duration_seconds": round(duration_seconds, 2),
        }
    )


def track_query_escalated(query: str, reason: str, user_id: str = None):
    """Query was escalated to human review."""
    _safe_capture(
        distinct_id=_get_distinct_id(user_id),
        event="query_escalated",
        properties={
            "query": query,
            "reason": reason,
        }
    )


def track_query_failed(query: str, error: str, user_id: str = None):
    """An error occurred while processing the query."""
    _safe_capture(
        distinct_id=_get_distinct_id(user_id),
        event="query_failed",
        properties={
            "query": query,
            "error": error,
        }
    )


def shutdown():
    """Flush and shut down PostHog cleanly."""
    if not _enabled or not _client:
        return
    try:
        _client.flush()
        _client.shutdown()
    except Exception as e:
        print(f"⚠️ [PostHog] Shutdown error (safe to ignore): {e}")
