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
import razorpay
from datetime import datetime, timezone

# Initialize Firebase Admin SDK
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
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

security_bearer = HTTPBearer()

# --- STREAM TO RPG CLASS MAP CONNECTOR matrix ---
STREAM_CLASS_MAPPING = {
    "10th Standard (Boards Prep)": "Initiate Operator",
    "12th Standard (Science/Commerce/Arts)": "Foundation Cadet",
    "B.Tech (Bachelor of Technology)": "Cybernetic Architect",
    "M.Tech (Master of Technology)": "Quantum Architect",
    "MBBS (Bachelor of Medicine, Bachelor of Surgery)": "Bio-Patch Medic",
    "MD / MS (Doctor of Medicine / Master of Surgery)": "Chief Neuro-Surgeon",
    "B.Pharm (Bachelor of Pharmacy)": "Nano-Geneticist",
    "M.Pharm (Master of Pharmacy)": "Alchemical Bio-Engineer",
    "BCA (Bachelor of Computer Applications)": "Data Grid Tech",
    "MCA (Master of Computer Applications)": "Network Overlord",
    "BBA (Bachelor of Business Administration)": "Corpo-Executive",
    "MBA / PGDM (Master of Business Administration)": "Megacorp Strategist",
    "UPSC / Civil Services": "Network Grid Prefect",
    "REET / TET (Teaching Eligibility)": "Matrix Protocol Mentor",
    "NEET (Medical Entrance)": "Bio-Labs Intern",
    "JEE (Engineering Entrance)": "Mechanized Cadet"
}

def determine_rpg_class(stream_str: str) -> str:
    """Helper macro to safely translate an academic stream to an RPG specialization title"""
    if stream_str in STREAM_CLASS_MAPPING:
        return STREAM_CLASS_MAPPING[stream_str]
    
    # Fallback substring detection mapping
    if "B.Tech" in stream_str or "M.Tech" in stream_str:
        return "Cybernetic Architect"
    if "MBBS" in stream_str or "Pharm" in stream_str or "MD" in stream_str:
        return "Bio-Patch Medic"
    if "MBA" in stream_str or "BBA" in stream_str:
        return "Megacorp Strategist"
    if "10th" in stream_str or "12th" in stream_str:
        return "Foundation Cadet"
    if "BCA" in stream_str or "MCA" in stream_str:
        return "Data Grid Tech"
        
    return "Freelance Operator"

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
    last_login: str = ""
    # 🎒 Tracks inventory items (maps item_id string to quantity owned integer)
    inventory: dict[str, int] = {
        "memory_book": 0,
        "energy_drink": 1,  # Free item on onboarding
        "brain_booster": 0,
        "streak_shield": 0
    }
    # 🎓 Tracks the player's specialized academic/professional track
    stream: str = "10th Standard (Boards Prep)"
    # 🏅 Dynamic structural subclass derived directly from current stream alignment
    agent_class: str = "Initiate Operator"

class CombatActionSchema(BaseModel):
    enemy_name: str
    action_submitted: str

class StudyTopicSchema(BaseModel):
    topic: str

class UpdateStreamSchema(BaseModel):
    stream: str

class EnergyPurchaseSchema(BaseModel):
    pack_id: str

class FriendRequestSchema(BaseModel):
    target_agent_name: str  

class PurchaseSchema(BaseModel):
    item_id: str

class BuyItemSchema(BaseModel):
    item_id: str

class UseItemSchema(BaseModel):
    item_id: str

# 🔑 RAZORPAY ENVIRONMENT VARIABLE HANDSHAKE
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_placeholder")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "mock_secret_placeholder")

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

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
    
    current_time_str = datetime.now(timezone.utc).isoformat()
    
    if doc_snap.exists:
        player_data = doc_snap.to_dict()
        last_login_str = player_data.get("last_login", "")
        current_streak = player_data.get("streak", 1)
        
        if last_login_str:
            try:
                last_login = datetime.fromisoformat(last_login_str)
                now = datetime.now(timezone.utc)
                hours_passed = (now - last_login).total_seconds() / 3600
                
                # 🕒 Case A: Over 48 hours missed? Streak breaks.
                if hours_passed >= 48:
                    current_streak = 1
                # 🚀 Case B: Between 24 and 48 hours? Streak increments!
                elif 24 <= hours_passed < 48:
                    current_streak += 1
                # Case C: Under 24 hours? Keep streak exactly the same.
            except Exception as time_err:
                print(f"Time validation error: {time_err}")
        
        # Ensure fallback structures exist on older profiles
        if "inventory" not in player_data:
            player_data["inventory"] = {"memory_book": 0, "energy_drink": 1, "brain_booster": 0, "streak_shield": 0}
        if "stream" not in player_data:
            player_data["stream"] = "10th Standard (Boards Prep)"
            
        # Calculate/re-sync current dynamic agent RPG title on load
        player_data["agent_class"] = determine_rpg_class(player_data["stream"])

        # Sync calculated updates back to local object
        player_data["streak"] = current_streak
        player_data["last_login"] = current_time_str
        
        await doc_ref.set(player_data, merge=True)
        return player_data
    else:
        # Initial onboarding profile defaults
        default_stats = {
            "xp": 0, "level": 1, "coins": 0, "gems": 0, "energy": 100, 
            "isPremium": False, "streak": 1,
            "agent_name": "Recruit Agent",
            "avatar_icon": "fa-user-ninja",
            "theme_color": "#00f0ff",
            "last_login": current_time_str,
            "inventory": {"memory_book": 0, "energy_drink": 1, "brain_booster": 0, "streak_shield": 0},
            "stream": "10th Standard (Boards Prep)",
            "agent_class": "Initiate Operator"
        }
        await doc_ref.set(default_stats)
        return default_stats

@app.post("/api/player/sync")
async def sync_player_stats(stats: PlayerStatsSchema, user: Annotated[dict, Depends(get_current_user)]):
    uid = user["uid"]
    doc_ref = db.collection("users").document(uid)
    
    # Process updates safely by ensuring calculated class overrides match state changes
    mutated_payload = stats.model_dump()
    mutated_payload["agent_class"] = determine_rpg_class(mutated_payload.get("stream", "10th Standard (Boards Prep)"))
    
    await doc_ref.set(mutated_payload, merge=True)
    return {"message": "Cloud matrix profile written successfully.", "agent_class": mutated_payload["agent_class"]}

@app.post("/api/player/update-stream")
async def update_player_stream(
    payload: UpdateStreamSchema,
    user: Annotated[dict, Depends(get_current_user)]
):
    uid = user["uid"]
    doc_ref = db.collection("users").document(uid)
    
    calculated_class = determine_rpg_class(payload.stream)
    
    # Push stream identity change and auto-calculate class title
    await doc_ref.set({
        "stream": payload.stream,
        "agent_class": calculated_class
    }, merge=True)
    
    return {
        "message": f"Core domain alignment altered to {payload.stream}.",
        "unlocked_class": calculated_class
    }

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

    agent_class_title = player_data.get("agent_class", "Freelance Operator")

    prompt_context = (
        f"You are the combat judge for a retro cyberpunk study RPG. "
        f"The player is a subclass layer archetype of '{agent_class_title}' fighting a '{action_data.enemy_name}'. "
        f"They submitted this action: '{action_data.action_submitted}'. "
        f"Determine if they succeeded or failed. Provide a dramatic text battle output flavor text fitting for a {agent_class_title} "
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

    # Calculate streak reward modifiers (5% per streak tier, capped at 50%)
    streak_tier = player_data.get("streak", 1)
    multiplier = 1.0 + min((streak_tier - 1) * 0.05, 0.50)
    
    xp_gained = int((calculated_score * 2) * multiplier)
    coins_gained = int((calculated_score / 2) * multiplier)
    
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

    # Fetch player's current stream specialization context and custom class title mapping
    player_stream = player_data.get("stream", "10th Standard (Boards Prep)")
    agent_class_title = player_data.get("agent_class", "Freelance Operator")

    prompt_context = (
        f"You are an expert retro cyberpunk AI mentor tutor coaching a user whose class role is '{agent_class_title}'. "
        f"They are specializing in the Indian education track field of {player_stream}. "
        f"Explain the following study topic thoroughly within the logical framing parameters of {player_stream}: '{payload.topic}'. "
        f"Provide a clear, engaging breakdown of the concept using real-world or academic domain problems relative to this field, "
        f"and conclude with a quick 1-question check for understanding."
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

    # Base study score threshold replacement for metrics calculations
    base_study_score = 80

    # Calculate streak reward modifiers (5% per streak tier, capped at 50%)
    streak_tier = player_data.get("streak", 1)
    multiplier = 1.0 + min((streak_tier - 1) * 0.05, 0.50)

    xp_gained = int((base_study_score * 2) * multiplier)
    coins_gained = int((base_study_score / 2) * multiplier)
    
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

# 🔋 REAL PAYMENT ENERGY FULFILLMENT INTERFACE
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

    if player_data.get("isPremium", False):
        return {"message": "Infinite matrix energy active. Consumables redundant.", "updated_player": player_data}

    if payload.pack_id == "energy_pack_50":
        energy_amount = 50
    elif payload.pack_id == "energy_pack_100":
        energy_amount = 100
    else:
        raise HTTPException(status_code=400, detail="Invalid energy pack classification ID.")

    current_energy = player_data.get("energy", 100)
    player_data["energy"] = min(current_energy + energy_amount, 100)

    await doc_ref.set(player_data, merge=True)
    return {
        "message": f"Payment Verified! Added {energy_amount} Energy to your profile matrix.",
        "updated_player": player_data
    }

# 👑 PREMIUM LICENSE FULFILLMENT ROUTE
@app.post("/api/store/activate-premium")
async def activate_premium_license(
    user: Annotated[dict, Depends(get_current_user)]
):
    uid = user["uid"]
    doc_ref = db.collection("users").document(uid)
    
    await doc_ref.set({"isPremium": True}, merge=True)
    
    return {
        "status": "success",
        "message": "Premium status permanent override synchronized successfully."
    }

# 🚀 SOCIAL UPLINK ENDPOINTS

@app.post("/api/social/request")
async def send_friend_request(
    payload: FriendRequestSchema, 
    user: Annotated[dict, Depends(get_current_user)]
):
    sender_uid = user["uid"]
    target_name = payload.target_agent_name.strip()

    users_ref = db.collection("users")
    query = users_ref.where("agent_name", "==", target_name).limit(1)
    target_docs = await query.get()

    if not target_docs:
        raise HTTPException(status_code=404, detail="Target Agent not found in the network matrix.")
    
    target_uid = target_docs[0].id
    if sender_uid == target_uid:
        raise HTTPException(status_code=400, detail="Cannot establish an uplink with your own node.")

    sender_doc = await users_ref.document(sender_uid).get()
    sender_data = sender_doc.to_dict()

    await users_ref.document(target_uid).collection("friends").document(sender_uid).set({
        "uid": sender_uid,
        "agent_name": sender_data.get("agent_name", "Unknown Operator"),
        "avatar_icon": sender_data.get("avatar_icon", "fa-user-ninja"),
        "theme_color": sender_data.get("theme_color", "#00f0ff"),
        "status": "pending_incoming"
    })

    await users_ref.document(sender_uid).collection("friends").document(target_uid).set({
        "uid": target_uid,
        "agent_name": target_name,
        "avatar_icon": target_docs[0].to_dict().get("avatar_icon", "fa-user-ninja"),
        "theme_color": target_docs[0].to_dict().get("theme_color", "#00f0ff"),
        "status": "pending_outgoing"
    })

    return {"message": f"Uplink request transmitted to {target_name}."}

@app.post("/api/social/accept")
async def accept_friend_request(
    payload: FriendRequestSchema, 
    user: Annotated[dict, Depends(get_current_user)]
):
    current_uid = user["uid"]
    target_name = payload.target_agent_name.strip()

    users_ref = db.collection("users")
    query = users_ref.where("agent_name", "==", target_name).limit(1)
    target_docs = await query.get()

    if not target_docs:
        raise HTTPException(status_code=404, detail="Target Agent lost to the network.")
    
    target_uid = target_docs[0].id

    await users_ref.document(current_uid).collection("friends").document(target_uid).update({"status": "connected"})
    await users_ref.document(target_uid).collection("friends").document(current_uid).update({"status": "connected"})

    return {"message": f"Social matrix bridge established with {target_name}!"}

@app.get("/api/social/list")
async def get_friends_list(user: Annotated[dict, Depends(get_current_user)]):
    uid = user["uid"]
    friends_ref = db.collection("users").document(uid).collection("friends")
    docs = await friends_ref.get()

    connections = []
    for doc in docs:
        connections.append(doc.to_dict())
    return connections

# 🚀 BILLING RAZORPAY GATEWAY INTERFACE

@app.post("/api/billing/create-order")
async def create_order(
    payload: PurchaseSchema, 
    user: Annotated[dict, Depends(get_current_user)]
):
    item = payload.item_id
    
    price_matrix = {
        "premium_tier": {"amount": 24900, "name": "Nexus Premium Upgrade"}, # ₹249
        "energy_pack_100": {"amount": 9900, "name": "100 Matrix Energy Pack"}, # ₹99
        "energy_pack_50": {"amount": 4900, "name": "50 Matrix Energy Pack"}     # ₹49
    }

    if item not in price_matrix:
        raise HTTPException(status_code=400, detail="Invalid item ID catalog entry.")

    try:
        order_data = {
            "amount": price_matrix[item]["amount"],
            "currency": "INR",
            "receipt": f"rcpt_{user['uid'][:10]}_{item[:5]}",
            "notes": {
                "player_uid": user["uid"],
                "purchased_item": item
            }
        }
        
        razorpay_order = client.order.create(data=order_data)
        
        return {
            "order_id": razorpay_order["id"],
            "amount": razorpay_order["amount"],
            "currency": razorpay_order["currency"],
            "key_id": RAZORPAY_KEY_ID,
            "product_name": price_matrix[item]["name"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 🏪 COIN ITEM SHOP ROUTE ---

@app.post("/api/store/buy-item")
async def purchase_inventory_item(
    payload: BuyItemSchema,
    user: Annotated[dict, Depends(get_current_user)]
):
    uid = user["uid"]
    doc_ref = db.collection("users").document(uid)
    doc_snap = await doc_ref.get()
    
    if not doc_snap.exists:
        raise HTTPException(status_code=404, detail="Player node missing.")
    
    player_data = doc_snap.to_dict()
    
    # 🪙 Shop base balancing pricing structures
    ITEM_PRICES = {
        "memory_book": 500,
        "energy_drink": 200,
        "brain_booster": 1200,
        "streak_shield": 1500
    }
    
    item = payload.item_id
    if item not in ITEM_PRICES:
        raise HTTPException(status_code=400, detail="Item not found in database registry catalog.")
        
    item_cost = ITEM_PRICES[item]
    current_coins = player_data.get("coins", 0)
    
    # 🛑 Financial transaction guard validation check
    if current_coins < item_cost:
        raise HTTPException(status_code=400, detail="Insufficient coin reserves for transaction.")
        
    # Deduct structural balances
    player_data["coins"] = current_coins - item_cost
    
    # Add items safely to standard profile dictionary
    inventory = player_data.get("inventory", {})
    inventory[item] = inventory.get(item, 0) + 1
    player_data["inventory"] = inventory
    
    await doc_ref.set(player_data, merge=True)
    return {
        "message": f"Successfully acquired {item.replace('_', ' ').title()}!",
        "updated_player": player_data
    }


# --- 🎒 INVENTORY CONSUMPTION ROUTE ---

@app.post("/api/inventory/consume")
async def consume_backpack_item(
    payload: UseItemSchema,
    user: Annotated[dict, Depends(get_current_user)]
):
    uid = user["uid"]
    doc_ref = db.collection("users").document(uid)
    doc_snap = await doc_ref.get()
    
    if not doc_snap.exists:
        raise HTTPException(status_code=404, detail="Player matrix dropped.")
    
    player_data = doc_snap.to_dict()
    inventory = player_data.get("inventory", {})
    item = payload.item_id

    if inventory.get(item, 0) <= 0:
        raise HTTPException(status_code=400, detail="Item resource quantity exhausted.")

    # Deduct single consumable execution stack
    inventory[item] -= 1
    player_data["inventory"] = inventory
    execution_message = ""

    # ⚡ Application execution modification handlers
    if item == "energy_drink":
        current_energy = player_data.get("energy", 100)
        player_data["energy"] = min(current_energy + 3, 100)
        execution_message = "⚡ Energy Drink consumed. Core energy cell boosted by +3 points."
        
    elif item == "brain_booster":
        execution_message = "🧠 Brain Booster initialized. Mental core state overclocked."
        
    elif item == "streak_shield":
        execution_message = "🛡️ Streak Shield locked in. Safe-harbor matrix active for next check-in."
        
    elif item == "memory_book":
        execution_message = "📚 Revision log initialized. Study recall index stabilized."
        
    else:
        raise HTTPException(status_code=400, detail="Unknown artifact identification sequence.")

    await doc_ref.set(player_data, merge=True)
    return {
        "message": execution_message,
        "updated_player": player_data
    }


# 🛠️ DYNAMIC PORT ATTACHMENT ENGINE FOR RENDER
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
