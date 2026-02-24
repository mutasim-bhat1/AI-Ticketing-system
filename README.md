# 🎫 AI Ticketing System

A professional, agentic customer support system that uses AI to understand, route, and resolve user queries.

---

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Streamlit
- **AI Model**: Groq / Llama 3.3 (High-speed LLM)
- **Embeddings**: Sentence-Transformers (`all-MiniLM-L6-v2`)
- **Orchestration**: LangChain
- **Email**: SMTP Integration (Gmail/App Passwords)
- **Package Manager**: UV (Modern Python packaging)

---

## 🧠 How it Works

The system follows a three-step agentic workflow for every query:

1.  **Semantic Search**:
    - Replaced simple keyword matching with **Cosine Similarity** using embeddings.
    - Matches queries based on *meaning* (e.g., matching "where is my money" to "Refunds" automatically).
    - Includes a **Confidence Threshold** (default: 0.35) to ensure accurate routing.

2.  **Internal Ticketing**:
    - Once a department is identified, the system **automatically sends a professional email ticket** to that department.
    - If no department is found above the confidence threshold, it routes to **General Support**.

3.  **Dynamic AI Resolution**:
    - Unlike hardcoded responses, the system uses the LLM to **synthesize a personalized answer**.
    - It combines the user's specific query with factual "Resolutions" from the Knowledge Base to provide an instant, helpful guide.

---

## 🏗️ Core Architecture Improvements

- **Closure-Based Tools**: No global variables. All dependencies (KB, SMTP, LLM) are injected via factory functions, making the code testable and thread-safe.
- **Optimized Performance**: `.env` and `SentenceTransformers` are loaded once at startup, ensuring fast response times.
- **Privacy Protection**: Internal routing details (like department emails) are hidden from the end-user.
- **Smart Orchestration**: Manual tool handling replaces standard agents to ensure 100% compatibility with Groq and faster execution.

---

## 🚀 Getting Started

### 1. Requirements
- Python 3.10+
- [UV Package Manager](https://astral.sh/uv)

### 2. Environment Setup
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_groq_key
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
GENERAL_SUPPORT_EMAIL=support@example.com
CONFIDENCE_THRESHOLD=0.35
```

### 3. Installation
```bash
uv sync
```

### 4. Running the Application
You need to run two processes:

**Backend (FastAPI):**
```bash
uv run uvicorn app.main:app --reload
```

**Frontend (Streamlit):**
```bash
uv run streamlit run streamlit_app.py
```

---

## 📂 Project Structure
- `app/agent.py`: Core logic and orchestrator.
- `app/tools.py`: Tool definitions (Email, Search, Generate).
- `app/kb.json`: The "Brain" - contains departments, services, and resolutions.
- `streamlit_app.py`: The user interface.

---

## 🔒 Safety & Guardrails
- **No Hallucinations**: The AI is strictly instructed to only use facts from the Knowledge Base.
- **Privacy**: No internal emails or sensitive routing data are leaked to the frontend.
- **Timeout Handling**: Streamlit is configured with a 120s timeout to handle intensive AI tasks.
