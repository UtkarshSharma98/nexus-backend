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

# --- STREAM TO RPG CLASS MAP CONNECTOR MATRIX ---
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

# --- GLOBAL CLASS ARENA ENEMY MATRIX ---
CLASS_ENEMY_MATRIX = {
    "Initiate Operator": ["Homework Overload Drone", "Pop Quiz Sentinel", "Procrastination Phantom"],
    "Foundation Cadet": ["Algebraic Matrix Golem", "Grammar Error Glitch", "Syllabus Behemoth"],
    "Cybernetic Architect": ["Legacy Loop Bug", "Memory Leak Phantom", "Null Pointer Spectre", "Merge Conflict Titan"],
    "Quantum Architect": ["Distributed System Chaos", "Concurrency Deadlock", "Asymptotic Complexity Demon"],
    "Bio-Patch Medic": ["Pathogen Logic Bomb", "Anatomy Memory Wipe", "Clinical Trial Aberration"],
    "Chief Neuro-Surgeon": ["Malpractice Mirage", "Systemic Synapse Collapse", "Bio-Metric Override Overlord"],
    "Nano-Geneticist": ["Mutated Sequence Glitch", "Enzyme Inhibitor Spectre", "Chemical Spill Hazard"],
    "Alchemical Bio-Engineer": ["Formulation Volatility Void", "Batch Contamination Beast"],
    "Data Grid Tech": ["Uncompiled Stack Overflow", "Spaghetti Code Hydra", "Database Dropout"],
    "Network Overlord": ["Distributed DoS Swarm", "Packet Loss Wraith", "Root Cert Expiry Dragon"],
    "Corpo-Executive": ["Quarterly Review Reaper", "Micro-Management Drone", "Spreadsheet Vortex"],
    "Megacorp Strategist": ["Corpo Budget Auditor", "Market Deflation Specter", "Liquidity Crunch Titan"],
    "Network Grid Prefect": ["Bureaucracy Red-Tape Hydra", "Public Policy Paradox", "Civics Evaluation Sentinel"],
    "Matrix Protocol Mentor": ["Lesson Plan Disruption", "Evaluation Metric Anomalies", "Curriculum Shift Spec"]
}

# 🗺️ Structural Sector maps corresponding directly to stream choices
STREAM_SKILL_TREES = {
    "NEET (Medical Entrance)": {
        "sector_name": "Bio-Labs Nexus",
        "nodes": {
            "node_1": {"title": "Human Anatomy Cells", "type": "Core Core", "unlocked": True, "completed": False, "xp_reward": 500},
            "node_2": {"title": "Organic Reaction Mechanisms", "type": "Alchemical", "unlocked": False, "completed": False, "xp_reward": 750},
            "node_3": {"title": "Plant Physiology Matrix", "type": "Bio-Botany", "unlocked": False, "completed": False, "xp_reward": 900}
        }
    },
    "BCA (Bachelor of Computer Applications)": {
        "sector_name": "Data Grid Sector",
        "nodes": {
            "node_1": {"title": "Linear Data Structures", "type": "Sub-Routine", "unlocked": True, "completed": False, "xp_reward": 500},
            "node_2": {"title": "OOPs Polymorphism Gates", "type": "Compiler", "unlocked": False, "completed": False, "xp_reward": 750},
            "node_3": {"title": "OS Memory Allocation Pools", "type": "Kernel Layer", "unlocked": False, "completed": False, "xp_reward": 950}
        }
    },
    "B.Tech (Bachelor of Technology)": {
        "sector_name": "Silicon Foundry Matrix",
        "nodes": {
            "node_1": {"title": "Asymptotic Analysis", "type": "Algorithm Core", "unlocked": True, "completed": False, "xp_reward": 600},
            "node_2": {"title": "Distributed Database Clusters", "type": "Data Mesh", "unlocked": False, "completed": False, "xp_reward": 800},
            "node_3": {"title": "Network Socket Protocols", "type": "Cybercomms", "unlocked": False, "completed": False, "xp_reward": 1000}
        }
    },
    "10th Standard (Boards Prep)": {
        "sector_name": "The Alpha Outpost",
        "nodes": {
            "node_1": {"title": "Quadratic Equation Arrays", "type": "Algebra Core", "unlocked": True, "completed": False, "xp_reward": 400},
            "node_2": {"title": "Chemical Redox Systems", "type": "Elemental Lab", "unlocked": False, "completed": False, "xp_reward": 600},
            "node_3": {"title": "Grammar Syntactic Matrices", "type": "Linguistic Node", "unlocked": False, "completed": False, "xp_reward": 600}
        }
    }
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
    inventory: dict[str, int] = {
        "memory_book": 0,
        "energy_drink": 1,
        "brain_booster": 0,
        "streak_shield": 0
    }
    stream: str = "10th Standard (Boards Prep)"
    agent_class: str = "Initiate Operator"
    skill_tree: dict | None = None

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

class UnlockNodeSchema(BaseModel):
    node_id: str

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
                
                if hours_passed >= 48:
                    current_streak = 1
                elif 24 <= hours_passed < 48:
                    current_streak += 1
            except Exception as time_err:
                print(f"Time validation error: {time_err}")
        
        if "inventory" not in player_data:
            player_data["inventory"] = {"memory_book": 0, "energy_drink": 1, "brain_booster": 0, "streak_shield": 0}
        if "stream" not in player_data:
            player_data["stream"] = "10th Standard (Boards Prep)"
            
        # Dynamic structural skill tree validation fallback logic
        user_stream = player_data.get("stream", "10th Standard (Boards Prep)")
        if "skill_tree" not in player_data:
            fallback_stream = user_stream if user_stream in STREAM_SKILL_TREES else "10th Standard (Boards Prep)"
            player_data["skill_tree"] = STREAM_SKILL_TREES[fallback_stream]
            
        player_data["agent_class"] = determine_rpg_class(player_data["stream"])
        player_data["streak"] = current_streak
        player_data["last_login"] = current_time_str
        
        await doc_ref.set(player_data, merge=True)
        return player_data
    else:
        default_stream = "10th Standard (Boards Prep)"
        default_stats = {
            "xp": 0, "level": 1, "coins": 0, "gems": 0, "energy": 100, 
            "isPremium": False, "streak": 1,
            "agent_name": "Recruit Agent",
            "avatar_icon": "fa-user-ninja",
            "theme_color": "#00f0ff",
            "last_login": current_time_str,
            "inventory": {"memory_book": 0, "energy_drink": 1, "brain_booster": 0, "streak_shield": 0},
            "stream": default_stream,
            "agent_class": "Initiate Operator",
            "skill_tree": STREAM_SKILL_TREES[default_stream]
        }
        await doc_ref.set(default_stats)
        return default_stats

@app.post("/api/player/sync")
async def sync_player_stats(stats: PlayerStatsSchema, user: Annotated[dict, Depends(get_current_user)]):
    uid = user["uid"]
    doc_ref = db.collection("users").document(uid)
    
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
    new_skill_tree = STREAM_SKILL_TREES.get(payload.stream, STREAM_SKILL_TREES["10th Standard (Boards Prep)"])
    
    await doc_ref.set({
        "stream": payload.stream,
        "agent_class": calculated_class,
        "skill_tree": new_skill_tree
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
        f"The player is a subclass layer archetype of '{agent_class_title}' fighting a specialized sector boss threat: '{action_data.enemy_name}'. "
        f"They submitted this action context or academic verification strategy statement: '{action_data.action_submitted}'. "
        f"Determine if they succeeded or failed. Provide a dramatic text battle output flavor text packed with high-tech cyberpunk terminology "
        f"and conceptual elements relative to a {agent_class_title} combating a {action_data.enemy_name}. "
        f"End your response with exactly: 'SCORE: <0 to 100>' indicating action efficacy."
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

    base_study_score = 80
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

@app.post("/api/billing/create-order")
async def create_order(
    payload: PurchaseSchema, 
    user: Annotated[dict, Depends(get_current_user)]
):
    item = payload.item_id
    price_matrix = {
        "premium_tier": {"amount": 24900, "name": "Nexus Premium Upgrade"},
        "energy_pack_100": {"amount": 9900, "name": "100 Matrix Energy Pack"},
        "energy_pack_50": {"amount": 4900, "name": "50 Matrix Energy Pack"}
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
    
    if current_coins < item_cost:
        raise HTTPException(status_code=400, detail="Insufficient coin reserves for transaction.")
        
    player_data["coins"] = current_coins - item_cost
    inventory = player_data.get("inventory", {})
    inventory[item] = inventory.get(item, 0) + 1
    player_data["inventory"] = inventory
    
    await doc_ref.set(player_data, merge=True)
    return {
        "message": f"Successfully acquired {item.replace('_', ' ').title()}!",
        "updated_player": player_data
    }

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

    inventory[item] -= 1
    player_data["inventory"] = inventory
    execution_message = ""

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

@app.post("/api/skills/unlock-node")
async def unlock_skill_tree_node(
    payload: UnlockNodeSchema,
    user: Annotated[dict, Depends(get_current_user)]
):
    uid = user["uid"]
    doc_ref = db.collection("users").document(uid)
    doc_snap = await doc_ref.get()
    
    if not doc_snap.exists:
        raise HTTPException(status_code=404, detail="Player entry dropped.")
        
    player_data = doc_snap.to_dict()
    user_stream = player_data.get("stream", "10th Standard (Boards Prep)")
    
    if user_stream not in STREAM_SKILL_TREES:
        raise HTTPException(status_code=400, detail="No sector maps mapped to this profile stream context.")
        
    user_tree = player_data.get("skill_tree", STREAM_SKILL_TREES[user_stream])
    nodes = user_tree.get("nodes", {})
    target_node = payload.node_id
    
    if target_node not in nodes:
        raise HTTPException(status_code=404, detail="Target map node coordinate missing.")
        
    if not nodes[target_node]["unlocked"]:
        raise HTTPException(status_code=400, detail="Target sequence gate locked by parent process conditions.")
        
    if nodes[target_node]["completed"]:
        return {"message": "Node already fully synthesized.", "updated_player": player_data}
        
    nodes[target_node]["completed"] = True
    xp_earned = nodes[target_node]["xp_reward"]
    
    current_index = int(target_node.split("_")[-1])
    next_node_id = f"node_{current_index + 1}"
    
    if next_node_id in nodes:
        nodes[next_node_id]["unlocked"] = True
        
    player_data["skill_tree"] = user_tree
    player_data["xp"] = player_data.get("xp", 0) + xp_earned
    
    next_level_threshold = player_data.get("level", 1) * 1000
    if player_data["xp"] >= next_level_threshold:
        player_data["xp"] -= next_level_threshold
        player_data["level"] = player_data.get("level", 1) + 1
        
    await doc_ref.set(player_data, merge=True)
    return {
        "message": f"Successfully completed {nodes[target_node]['title']} node block grid sector!",
        "xp_earned": xp_earned,
        "updated_player": player_data
    }

# 🛠️ DYNAMIC PORT ATTACHMENT ENGINE FOR RENDER
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
