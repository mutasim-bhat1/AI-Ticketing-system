from fastapi import FastAPI
from pydantic import BaseModel
from app.agent import handle_query

app = FastAPI()

class QueryRequest(BaseModel):
    query: str

@app.post("/query")
def route_query(payload: QueryRequest):
    return handle_query(payload.query)
