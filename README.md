# 🎫 AI Ticketing System

An intelligent customer support ticketing system that automatically routes queries to the appropriate department using AI.

## 🚀 Features

- ✅ **Automatic Ticket Routing** - Matches user queries to the right department
- ✅ **Email Integration** - Sends tickets via email to departments
- ✅ **Knowledge Base** - Configurable services and departments
- ✅ **Auto-Reply** - Optional automatic responses for common queries
- ✅ **RESTful API** - Easy integration with FastAPI
- ✅ **Groq AI** - Fast, free LLM for query processing

## 📋 Services Supported

- **IT Support** - Password resets, login issues
- **Finance** - Refunds, payments
- **Library** - Book issues, library cards
- **Transport** - Bus passes, routes
- **Academics** - Course registration, grades, results

## 🛠️ Tech Stack

- **Backend**: FastAPI
- **AI**: Groq (Llama 3.3 70B)
- **Email**: SMTP (Gmail)
- **Package Manager**: UV
- **Tools**: LangChain

## 📦 Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd AI-ticketing-system
```

2. **Install UV** (if not installed)
```bash
# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux/Mac
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. **Install dependencies**
```bash
uv sync
```

4. **Set up environment variables**

Create a `.env` file:
```env
# Groq API Key (get from https://console.groq.com/keys)
GROQ_API_KEY=your_groq_api_key_here

# Email Configuration
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
GENERAL_SUPPORT_EMAIL=support@example.com
```

**Note:** For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833), not your regular password.

## 🚀 Running the Server

```bash
uv run uvicorn app.main:app --reload
```

Server will start at: `http://localhost:8000`

## 📖 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔧 API Usage

### Send a Query

**Endpoint:** `POST /query`

**Request:**
```json
{
  "query": "I want to reset my password"
}
```

**Response:**
```json
{
  "status": "success",
  "response": "Thank you for contacting us. Your request has been received and noted. Our team will review your query and take appropriate action. You will receive a response shortly.\n\nYour ticket has been created and forwarded to IT Support (IT Helpdesk). Ticket reference: Password Reset.\n\n✅ Email ticket sent successfully to mutasimbhat1@gmail.com",
  "query": "I want to reset my password"
}
```

## 📝 Configuration

### Adding New Services

Edit `app/kb.json`:

```json
{
  "service": "Your Service Name",
  "department": "Department Name",
  "email": "department@example.com",
  "authority": "Department Head",
  "auto_reply_allowed": true,
  "keywords": ["keyword1", "keyword2", "keyword3"]
}
```

### Configuration Options

- **`auto_reply_allowed: true`** - Sends friendly auto-reply + email
- **`auto_reply_allowed: false`** - Sends formal confirmation + email

## 🏗️ Project Structure

```
AI-ticketing-system/
├── app/
│   ├── main.py          # FastAPI app
│   ├── agent.py         # Query handling logic
│   ├── tools.py         # Tool functions (search, email, etc.)
│   └── kb.json          # Knowledge base
├── .env                 # Environment variables (not in git)
├── .gitignore
├── pyproject.toml       # UV dependencies
└── README.md
```

## 🔒 Security

- ✅ API keys stored in `.env` (excluded from git)
- ✅ SMTP credentials in environment variables
- ✅ No hardcoded secrets in code

## 🎯 Code Quality

- ✅ **No global variables** - Uses closures for dependency injection
- ✅ **Environment-based config** - All settings in `.env`
- ✅ **Optimized** - `load_dotenv()` called once at startup
- ✅ **Production-ready** - Clean architecture and error handling

## 📚 Documentation

See the `/docs` directory for detailed documentation:
- `REFACTORING_EXPLAINED.md` - Code improvements explained
- `AGENT_IMPROVEMENTS.md` - Agent architecture details
- `COMPATIBILITY_FIX.md` - LangChain version notes

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - feel free to use this project!

## 🙏 Acknowledgments

- **Groq** - For free, fast LLM API
- **LangChain** - For AI tooling framework
- **FastAPI** - For the amazing web framework

---

Made with ❤️ for better customer support
