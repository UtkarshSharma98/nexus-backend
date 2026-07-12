import os
import json
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import firebase_admin
from firebase_admin import credentials, firestore_async
from google import genai
import uvicorn

# --- INITIALIZATION ---
base_dir = os.path.dirname(os.path.abspath(__file__))
cred_path = os.path.join(base_dir, "service-account.json")
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)
db = firestore_async.client()
gemini_client = genai.Client()

# Polar Configuration
POLAR_API_KEY = "polar_oat_ipUvMbh0gVCVPWO2USbv8cZxUCbeNTh4jITRD4P8tNK"
POLAR_WEBHOOK_SECRET = os.getenv("POLAR_WEBHOOK_SECRET", "your_webhook_secret_here")

app = FastAPI(title="Nexus RPG API Matrix")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
security_bearer = HTTPBearer()

# --- PERSISTENCE UTILITY ---
async def save_player_data(uid: str, data: dict):
    """Atomic write to Firestore master record."""
    await db.collection("users").document(uid).set(data, merge=True)

# --- POLAR WEBHOOK ---
@app.post("/api/webhooks/polar")
async def handle_polar_webhook(request: Request):
    """
    Handles subscription/purchase events from Polar.sh.
    """
    payload = await request.body()
    data = await request.json()
    event_type = data.get("type")
    
    # Process event (e.g., subscription.created)
    if event_type and "subscription" in event_type:
        email = data.get("data", {}).get("customer", {}).get("email")
        # Update user tier in Firestore via email lookup
        # ... logic to find user by email and set 'is_premium': True
        
    return {"status": "received"}

# --- EXAMPLE ENDPOINT WITH PERSISTENCE ---
@app.post("/api/player/force-sync")
async def force_sync(stats: dict, user: Annotated[dict, Depends(lambda: {"uid": "example_uid"})]):
    """Forcefully aligns local client state with cloud record."""
    uid = user["uid"]
    await save_player_data(uid, stats)
    return {"status": "synchronized"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
