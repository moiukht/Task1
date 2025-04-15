from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import json
import os
from datetime import datetime
from nlp import handle_user_message
from db.connection import database_connect
import nltk
app = FastAPI()
@app.get('/')


async def root():
    return {"message": "Welcome to Savory Haven API"}

#MONGODB CONNECTION
db = database_connect() 

# input schema
class UserMessage(BaseModel):
    message: str
    user_id: str = "user123"
    session_id: str = "sess456"


@app.post("/api/chat")
async def chat_endpoint(payload: UserMessage):
    
    result, entities = handle_user_message(
        user_input=payload.message,
        user_id=payload.user_id,
        session_id=payload.session_id
    )
    log_data = {
        "query": payload.message,
        "intent": result.get("intent"),
        "entities": entities,
        "chatbot_response": result.get("response"),
        "sessionID": payload.session_id,
        "userID": payload.user_id,
        "timestamp": datetime.now().isoformat()  # Use the current timestamp
    }

    db.log_interactions.insert_one(log_data)  # Insert the log data into MongoDB collection
    return result

