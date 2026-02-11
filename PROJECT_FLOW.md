# AI Ticketing System - Complete Flow

## 🎯 Project Overview
An intelligent customer support system that automatically routes tickets to the right department using AI.

---

## 📋 System Architecture

```
User Request → FastAPI Endpoint → AI Agent → Tools → Response
```

---

## 🔄 Detailed Flow

### 1. **User Sends Query**
```json
POST /query
{
  "query": "I forgot my password"
}
```

### 2. **FastAPI Endpoint** (`main.py`)
- Validates the request using `QueryRequest` Pydantic model
- Extracts the query string
- Calls `handle_query(query)`

### 3. **AI Agent** (`agent.py`)
The agent is the "brain" that decides what to do:

**Components:**
- **LLM (Gemini)**: The AI model that understands the query
- **System Prompt**: Instructions telling the AI how to behave
- **Tools**: Functions the AI can call to take actions
- **Knowledge Base (KB)**: JSON file with service information

**Agent Decision Process:**
```
Query → AI analyzes → Searches KB → Decides action:
  ├─ Auto-reply (if allowed)
  ├─ Send email to department
  └─ Escalate to human
```

### 4. **Tools** (`tools.py`)
Functions the AI can use:

#### a. `search_kb(query)`
- Searches `kb.json` for matching services
- Matches keywords in the query
- Returns service details (department, email, etc.)

#### b. `generate_reply(query)`
- Creates a generic response
- Used when auto-reply is allowed

#### c. `send_email(email, subject, body)`
- Sends email to the department
- Currently just prints (will use SMTP later)

#### d. `escalate(reason)`
- Escalates complex queries to humans
- Returns escalation message

### 5. **Knowledge Base** (`kb.json`)
Database of services with:
- Service name
- Department
- Contact email
- Keywords for matching
- Auto-reply permission

---

## 🎬 Example Scenarios

### Scenario 1: Password Reset (Auto-Reply Allowed)
```
1. User: "I forgot my password"
2. Agent searches KB → finds "Password Reset" service
3. Checks: auto_reply_allowed = true
4. Agent calls generate_reply()
5. Returns: "Thank you for contacting us. Your request has been received..."
```

### Scenario 2: Academic Results (Email Required)
```
1. User: "I want to see my 8th class results"
2. Agent searches KB → finds "Academic Support" service
3. Checks: auto_reply_allowed = false
4. Agent calls send_email(
     email="academics@example.com",
     subject="New Ticket: Academic Support - Grade Query",
     body="User Query: I want to see my 8th class results\n\nRequires academic office review."
   )
5. Returns: "✅ Email ticket sent successfully to academics@example.com"
6. Email is printed to terminal (will use SMTP later)
```

### Scenario 3: Generic Query (No KB Match)
```
1. User: "What time does the cafeteria open?"
2. Agent searches KB → no matching service found
3. Agent is smart: creates general support ticket
4. Agent calls send_email(
     email="support@example.com",
     subject="General Support Request",
     body="User Query: What time does the cafeteria open?\n\nNo specific department match."
   )
5. Returns: "✅ Email ticket sent successfully to support@example.com"
6. Query is handled, not lost!
```

### Scenario 4: Spam/Nonsense (Escalation)
```
1. User: "asdfghjkl qwerty 12345"
2. Agent searches KB → no match
3. Agent analyzes: this is nonsensical
4. Agent calls escalate("Query appears to be spam or nonsensical")
5. Returns: "⚠️ Escalated for human review. Reason: ..."
```

---

## 🏗️ File Structure

```
AI ticketing system/
├── app/
│   ├── main.py          # FastAPI endpoint
│   ├── agent.py         # AI agent logic
│   ├── tools.py         # Agent tools/functions
│   └── kb.json          # Knowledge base
├── .env                 # API keys
└── PROJECT_FLOW.md      # This file
```

---

## 🔧 Current Response Format Issue

**Problem:** The response contains LangChain's internal message structure with extras/signature.

**Solution:** Extract just the text content from the AI response.

---

## 🚀 Next Steps

1. **Fix response format** - Extract clean text from agent response
2. **Add SMTP** - Actually send emails instead of printing
3. **Improve KB matching** - Use semantic search instead of keyword matching
4. **Add logging** - Track all queries and actions
5. **Add authentication** - Secure the API endpoint
