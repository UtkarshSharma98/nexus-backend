import os
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, auth, firestore_async
from pydantic import BaseModel
from google import genai
import uvicorn

# Initialize Firebase Admin SDK
# CHANGE THIS:
cred = credentials.Certificate("./service-account.json")

# TO THIS:
base_dir = os.path.dirname(os.path.abspath(__file__))
cred_path = os.path.join(base_dir, "service-account.json")
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)
db = firestore_async.client()

# Initialize Gemini Client SDK
gemini_client = genai.Client()

app = FastAPI(title="Nexus RPG API Matrix")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security_bearer = HTTPBearer()

# --- VALIDATION SCHEMAS ---

class PlayerStatsSchema(BaseModel):
    xp: int
    level: int
    coins: int
    gems: int
    energy: int
    isPremium: bool
    streak: int
    agent_name: str = "Unknown Agent"
    avatar_icon: str = "fa-user-ninja"
    theme_color: str = "#00f0ff"

class CombatActionSchema(BaseModel):
    enemy_name: str
    action_submitted: str

class StudyTopicSchema(BaseModel):
    topic: str

# --- DEPENDENCIES ---

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_bearer)]
) -> dict:
    token = credentials.credentials
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid security authorization layer token.",
        )

# --- REST ENDPOINTS ---

@app.get("/")
async def health_check():
    return {"status": "online", "system": "Nexus Core"}

@app.get("/api/player", response_model=PlayerStatsSchema)
async def get_player_stats(user: Annotated[dict, Depends(get_current_user)]):
    uid = user["uid"]
    doc_ref = db.collection("users").document(uid)
    doc_snap = await doc_ref.get()
    
    if doc_snap.exists:
        return doc_snap.to_dict()
    else:
        default_stats = {
            "xp": 0, "level": 1, "coins": 0, "gems": 0, "energy": 100, 
            "isPremium": False, "streak": 1,
            "agent_name": "Recruit Agent",
            "avatar_icon": "fa-user-ninja",
            "theme_color": "#00f0ff"
        }
        await doc_ref.set(default_stats)
        return default_stats

@app.post("/api/player/sync")
async def sync_player_stats(stats: PlayerStatsSchema, user: Annotated[dict, Depends(get_current_user)]):
    uid = user["uid"]
    doc_ref = db.collection("users").document(uid)
    await doc_ref.set(stats.model_dump(), merge=True)
    return {"message": "Cloud matrix profile written successfully."}

@app.post("/api/combat/analyze")
async def process_combat_encounter(
    action_data: CombatActionSchema,
    user: Annotated[dict, Depends(get_current_user)]
):
    uid = user["uid"]
    doc_ref = db.collection("users").document(uid)
    doc_snap = await doc_ref.get()
    if not doc_snap.exists:
        raise HTTPException(status_code=404, detail="Player data stream missing.")
    player_data = doc_snap.to_dict()

    if not player_data.get("isPremium", False) and player_data.get("energy", 100) < 10:
        raise HTTPException(status_code=400, detail="Insufficient action energy.")

    prompt_context = (
        f"You are the combat judge for a retro cyberpunk study RPG. "
        f"The player is fighting a '{action_data.enemy_name}'. "
        f"They submitted this action: '{action_data.action_submitted}'. "
        f"Determine if they succeeded or failed. Provide a dramatic text battle output "
        f"and end your response with exactly: 'SCORE: <0 to 100>' indicating action efficacy."
    )

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_context
        )
        ai_response_text = response.text
    except Exception as gemini_err:
        print(f"Gemini processing failure: {gemini_err}")
        raise HTTPException(status_code=502, detail="AI interpretation layer timed out.")

    calculated_score = 50
    if "SCORE:" in ai_response_text:
        try:
            score_string = ai_response_text.split("SCORE:")[-1].strip()
            calculated_score = int(''.join(filter(str.isdigit, score_string)))
        except ValueError:
            pass

    xp_gained = int(calculated_score * 2)
    coins_gained = int(calculated_score / 2)
    
    new_xp = player_data.get("xp", 0) + xp_gained
    next_level_threshold = player_data.get("level", 1) * 1000
    leveled_up = new_xp >= next_level_threshold

    player_data["xp"] = new_xp - next_level_threshold if leveled_up else new_xp
    player_data["level"] = player_data.get("level", 1) + 1 if leveled_up else player_data.get("level", 1)
    player_data["coins"] = player_data.get("coins", 0) + coins_gained
    if not player_data.get("isPremium", False):
        player_data["energy"] = max(player_data.get("energy", 100) - 10, 0)

    await doc_ref.set(player_data)

    return {
        "battle_log": ai_response_text.split("SCORE:")[0].strip(),
        "score": calculated_score,
        "rewards": {"xp": xp_gained, "coins": coins_gained},
        "updated_player": player_data
    }

@app.post("/api/study/explain")
async def process_study_module(
    payload: StudyTopicSchema,
    user: Annotated[dict, Depends(get_current_user)]
):
    uid = user["uid"]
    doc_ref = db.collection("users").document(uid)
    doc_snap = await doc_ref.get()
    if not doc_snap.exists:
        raise HTTPException(status_code=404, detail="Player data stream missing.")
    player_data = doc_snap.to_dict()

    if not player_data.get("isPremium", False) and player_data.get("energy", 100) < 5:
        raise HTTPException(status_code=400, detail="Insufficient action energy to study.")

    prompt_context = (
        f"You are an expert retro cyberpunk AI mentor tutor. Explain the following study topic "
        f"thoroughly but in an engaging, stylized way: '{payload.topic}'. "
        f"Provide a clear breakdown of the concept and conclude with a quick 1-question check for understanding."
    )

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_context
        )
        ai_explanation = response.text
    except Exception as gemini_err:
        print(f"Gemini processing failure: {gemini_err}")
        raise HTTPException(status_code=502, detail="AI interpretation layer timed out.")

    xp_gained = 150
    coins_gained = 25
    
    new_xp = player_data.get("xp", 0) + xp_gained
    next_level_threshold = player_data.get("level", 1) * 1000
    leveled_up = new_xp >= next_level_threshold

    player_data["xp"] = new_xp - next_level_threshold if leveled_up else new_xp
    player_data["level"] = player_data.get("level", 1) + 1 if leveled_up else player_data.get("level", 1)
    player_data["coins"] = player_data.get("coins", 0) + coins_gained
    if not player_data.get("isPremium", False):
        player_data["energy"] = max(player_data.get("energy", 100) - 5, 0)

    await doc_ref.set(player_data)

    return {
        "explanation": ai_explanation,
        "rewards": {"xp": xp_gained, "coins": coins_gained},
        "updated_player": player_data
    }

@app.get("/api/leaderboard")
async def get_global_leaderboard(user: Annotated[dict, Depends(get_current_user)]):
    """
    Fetches the top 10 ranking agents across the network, 
    ordered sequentially by Level and Experience.
    """
    try:
        leaderboard_query = (
            db.collection("users")
            .order_by("level", direction="DESCENDING")
            .order_by("xp", direction="DESCENDING")
            .limit(10)
        )
        
        docs = await leaderboard_query.get()
        rankings = []
        
        for index, doc in enumerate(docs):
            data = doc.to_dict()
            rankings.append({
                "rank": index + 1,
                "agent_name": data.get("agent_name", "Unknown Operator"),
                "avatar_icon": data.get("avatar_icon", "fa-user-ninja"),
                "theme_color": data.get("theme_color", "#00f0ff"),
                "level": data.get("level", 1),
                "xp": data.get("xp", 0)
            })
            
        return rankings
    except Exception as e:
        print(f"Leaderboard extraction matrix failure: {e}")
        raise HTTPException(status_code=500, detail="Failed to query network scoreboard records.")

# 🛒 STORE SCHEMAS
class EnergyPurchaseSchema(BaseModel):
    pack_id: str

# 🚀 PREMIUM STORE ENDPOINTS

@app.post("/api/store/buy-energy")
async def purchase_energy_pack(
    payload: EnergyPurchaseSchema,
    user: Annotated[dict, Depends(get_current_user)]
):
    uid = user["uid"]
    doc_ref = db.collection("users").document(uid)
    doc_snap = await doc_ref.get()
    
    if not doc_snap.exists:
        raise HTTPException(status_code=404, detail="Player data stream missing.")
    player_data = doc_snap.to_dict()

    if payload.pack_id == "pack_small":
        energy_amount = 25
    elif payload.pack_id == "pack_large":
        energy_amount = 100
    else:
        raise HTTPException(status_code=400, detail="Invalid product classification pack ID.")

    if player_data.get("isPremium", False):
        return {"message": "Infinite matrix energy active. Consumables redundant.", "updated_player": player_data}

    current_energy = player_data.get("energy", 100)
    player_data["energy"] = min(current_energy + energy_amount, 100)

    await doc_ref.set(player_data, merge=True)
    return {
        "message": f"Successfully processed transaction. Charged INR via simulated node pipeline. Added {energy_amount} Energy.",
        "updated_player": player_data
    }

@app.post("/api/store/buy-premium")
async def purchase_premium_tier(user: Annotated[dict, Depends(get_current_user)]):
    uid = user["uid"]
    doc_ref = db.collection("users").document(uid)
    doc_snap = await doc_ref.get()
    
    if not doc_snap.exists:
        raise HTTPException(status_code=404, detail="Player data stream missing.")
    player_data = doc_snap.to_dict()

    if player_data.get("isPremium", False):
        return {"message": "License layer already active.", "updated_player": player_data}

    player_data["isPremium"] = True
    player_data["energy"] = 100

    await doc_ref.set(player_data, merge=True)
    return {
        "message": "💥 Network access upgraded to Premium! Charged INR 249. Infinite operation energy unlocked.",
        "updated_player": player_data
    }

# 🛠️ DYNAMIC PORT ATTACHMENT ENGINE FOR RENDER
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
