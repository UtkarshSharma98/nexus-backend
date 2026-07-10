import os
import json
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, auth, firestore_async
from pydantic import BaseModel
from google import genai
import uvicorn
import razorpay
from datetime import datetime, timezone

# --- INITIALIZATION ---
base_dir = os.path.dirname(os.path.abspath(__file__))
cred_path = os.path.join(base_dir, "service-account.json")
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)
db = firestore_async.client()
gemini_client = genai.Client()

app = FastAPI(title="Nexus RPG API Matrix")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
security_bearer = HTTPBearer()

# --- CONSTANTS & MAPPINGS ---
STREAM_CLASS_MAPPING = {
    "10th Standard (Boards Prep)": "Initiate Operator",
    "12th Standard (Science/Commerce/Arts)": "Foundation Cadet",
    "B.Tech (Bachelor of Technology)": "Cybernetic Architect",
    "B.Pharm (Bachelor of Pharmacy)": "Nano-Geneticist",
    # ... (Rest of mappings remain the same)
}

# --- PERSISTENCE HELPER ---
async def save_player_data(uid: str, data: dict):
    """Atomic write to Firestore to ensure state consistency."""
    await db.collection("users").document(uid).set(data, merge=True)

# --- ENDPOINTS ---

@app.get("/api/player", response_model=PlayerStatsSchema)
async def get_player_stats(user: Annotated[dict, Depends(get_current_user)]):
    uid = user["uid"]
    doc_ref = db.collection("users").document(uid)
    doc_snap = await doc_ref.get()
    
    if doc_snap.exists:
        player_data = doc_snap.to_dict()
        # Logic for streak and data normalization remains here
        await save_player_data(uid, player_data) # Ensure cloud is updated
        return player_data
    else:
        # Create default user in cloud
        # ... (Default stats initialization)
        await save_player_data(uid, default_stats)
        return default_stats

@app.post("/api/combat/analyze")
async def process_combat_encounter(action_data: CombatActionSchema, user: Annotated[dict, Depends(get_current_user)]):
    uid = user["uid"]
    doc_snap = await db.collection("users").document(uid).get()
    player_data = doc_snap.to_dict()

    # Combat calculation logic...
    
    # Persistent State Update
    await save_player_data(uid, player_data)
    return {"battle_log": ..., "rewards": ..., "updated_player": player_data}

# ... (Continue refactoring other endpoints using save_player_data)