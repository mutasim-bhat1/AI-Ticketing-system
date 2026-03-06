from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.agent import handle_query

app = FastAPI(title="AI Ticketing System")

# CORS — allow frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

class QueryRequest(BaseModel):
    query: str

@app.get("/")
def serve_dashboard():
    """Serve the main dashboard UI."""
    return FileResponse("static/index.html")

@app.post("/query")
def route_query(payload: QueryRequest):
    return handle_query(payload.query)
