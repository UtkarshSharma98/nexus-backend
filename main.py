import os
import json
import base64
import hmac
import hashlib
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, auth, firestore_async
from pydantic import BaseModel
from google import genai
from google.genai import types  # Retained for validation compatibility
import uvicorn
import httpx
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

# 🗺️ MISSION-INTEGRATED SKILL TREES MATRIX
STREAM_SKILL_TREES = {
    "10th Standard (Boards Prep)": {
        "sector_name": "The Alpha Outpost",
        "nodes": {
            "node_1": {"title": "Quadratic Equation Arrays", "type": "Core Stance", "unlocked": True, "completed": False, "xp_reward": 400, "required_mission": None},
            "node_2": {"title": "Chemical Redox Systems", "type": "Core Stance", "unlocked": False, "completed": False, "xp_reward": 500, "required_mission": "clear_algebra_basics"},
            "node_3": {"title": "Grammar Syntactic Matrices", "type": "Thrust Stance", "unlocked": False, "completed": False, "xp_reward": 600, "required_mission": "neutralize_redox_glitch"},
            "node_4": {"title": "Trigonometric Geometry Nodes", "type": "Pillar Stance", "unlocked": False, "completed": False, "xp_reward": 800, "required_mission": "decode_syntax_cipher"}
        }
    },
    "12th Standard (Science/Commerce/Arts)": {
        "sector_name": "Foundation Grid Nexus",
        "nodes": {
            "node_1": {"title": "Calculus Vector Streams", "type": "Core Stance", "unlocked": True, "completed": False, "xp_reward": 500, "required_mission": None},
            "node_2": {"title": "Macroeconomic Flow Control", "type": "Pillar Stance", "unlocked": False, "completed": False, "xp_reward": 600, "required_mission": "solve_limits_paradox"},
            "node_3": {"title": "Organic Synthesis Protocols", "type": "Thrust Stance", "unlocked": False, "completed": False, "xp_reward": 700, "required_mission": "balance_fiscal_leak"},
            "node_4": {"title": "Quantum Wave Foundations", "type": "Transformation", "unlocked": False, "completed": False, "xp_reward": 900, "required_mission": "synthesize_carbon_core"}
        }
    },
    "B.Tech (Bachelor of Technology)": {
        "sector_name": "Silicon Foundry Matrix",
        "nodes": {
            "node_1": {"title": "Asymptotic Analysis Stance", "type": "Core Stance", "unlocked": True, "completed": False, "xp_reward": 600, "required_mission": None},
            "node_2": {"title": "Distributed Database Clusters", "type": "Pillar Stance", "unlocked": False, "completed": False, "xp_reward": 800, "required_mission": "optimize_runtime_complexity"},
            "node_3": {"title": "Network Socket Protocols", "type": "Thrust Stance", "unlocked": False, "completed": False, "xp_reward": 1000, "required_mission": "resolve_shard_deadlock"},
            "node_4": {"title": "Automated Deployment Daemons", "type": "Transformation", "unlocked": False, "completed": False, "xp_reward": 1200, "required_mission": "handshake_secure_sockets"}
        }
    },
    "M.Tech (Master of Technology)": {
        "sector_name": "Quantum Singularity Lab",
        "nodes": {
            "node_1": {"title": "Neural Topology Optimization", "type": "Core Stance", "unlocked": True, "completed": False, "xp_reward": 800, "required_mission": None},
            "node_2": {"title": "Distributed Cryptography Chains", "type": "Pillar Stance", "unlocked": False, "completed": False, "xp_reward": 1000, "required_mission": "converge_weights_gradient"},
            "node_3": {"title": "Advanced Quantum Architecture", "type": "Thrust Stance", "unlocked": False, "completed": False, "xp_reward": 1200, "required_mission": "breach_hash_chain"},
            "node_4": {"title": "Fault-Tolerant Compute Swarms", "type": "Transformation", "unlocked": False, "completed": False, "xp_reward": 1500, "required_mission": "entangle_qubit_registers"}
        }
    },
    "MBBS (Bachelor of Medicine, Bachelor of Surgery)": {
        "sector_name": "Bio-Patch Infirmary",
        "nodes": {
            "node_1": {"title": "Gross Anatomy Frameworks", "type": "Core Stance", "unlocked": True, "completed": False, "xp_reward": 600, "required_mission": None},
            "node_2": {"title": "Pathological Identification Stance", "type": "Pillar Stance", "unlocked": False, "completed": False, "xp_reward": 800, "required_mission": "map_skeletal_nexus"},
            "node_3": {"title": "Surgical Precision Vectors", "type": "Thrust Stance", "unlocked": False, "completed": False, "xp_reward": 1000, "required_mission": "isolate_pathogen_strain"},
            "node_4": {"title": "Pharmacology Signal Injection", "type": "Transformation", "unlocked": False, "completed": False, "xp_reward": 1200, "required_mission": "execute_incisional_precision"}
        }
    },
    "MD / MS (Doctor of Medicine / Master of Surgery)": {
        "sector_name": "Sanctum Neuro-Surgical Core",
        "nodes": {
            "node_1": {"title": "Synaptic Re-Routing Stance", "type": "Core Stance", "unlocked": True, "completed": False, "xp_reward": 900, "required_mission": None},
            "node_2": {"title": "Microvascular Anastomosis", "type": "Pillar Stance", "unlocked": False, "completed": False, "xp_reward": 1100, "required_mission": "stabilize_cortex_synapse"},
            "node_3": {"title": "Internal Trauma Override", "type": "Thrust Stance", "unlocked": False, "completed": False, "xp_reward": 1300, "required_mission": "suture_micro_vessel"},
            "node_4": {"title": "Nanobotic Bio-Sealing Arrays", "type": "Transformation", "unlocked": False, "completed": False, "xp_reward": 1600, "required_mission": "halt_arterial_hemorrhage"}
        }
    },
    "B.Pharm (Bachelor of Pharmacy)": {
        "sector_name": "Nano-Chemical Foundry",
        "nodes": {
            "node_1": {"title": "Medicinal Chemistry Blocks", "type": "Core Stance", "unlocked": True, "completed": False, "xp_reward": 550, "required_mission": None},
            "node_2": {"title": "Bio-Pharmaceutics Transport", "type": "Pillar Stance", "unlocked": False, "completed": False, "xp_reward": 750, "required_mission": "isolate_alkaloid_structure"},
            "node_3": {"title": "Toxicology Counter-Measures", "type": "Thrust Stance", "unlocked": False, "completed": False, "xp_reward": 950, "required_mission": "calculate_half_life_clearance"},
            "node_4": {"title": "Assay Analysis Protocols", "type": "Transformation", "unlocked": False, "completed": False, "xp_reward": 1150, "required_mission": "neutralize_cytotoxic_spill"}
        }
    },
    "M.Pharm (Master of Pharmacy)": {
        "sector_name": "Alchemical Production Spire",
        "nodes": {
            "node_1": {"title": "Targeted Molecular Delivery", "type": "Core Stance", "unlocked": True, "completed": False, "xp_reward": 750, "required_mission": None},
            "node_2": {"title": "Clinical Pharmacokinetics", "type": "Pillar Stance", "unlocked": False, "completed": False, "xp_reward": 950, "required_mission": "bind_liposome_receptor"},
            "node_3": {"title": "Industrial Formulation Synthesis", "type": "Thrust Stance", "unlocked": False, "completed": False, "xp_reward": 1150, "required_mission": "model_plasma_concentration"},
            "node_4": {"title": "Polymer Matrix Coatings", "type": "Transformation", "unlocked": False, "completed": False, "xp_reward": 1400, "required_mission": "scale_fluidized_bed_batch"}
        }
    },
    "BCA (Bachelor of Computer Applications)": {
        "sector_name": "Data Grid Sector",
        "nodes": {
            "node_1": {"title": "Linear Data Structures", "type": "Core Stance", "unlocked": True, "completed": False, "xp_reward": 500, "required_mission": None},
            "node_2": {"title": "OOPs Polymorphism Gates", "type": "Pillar Stance", "unlocked": False, "completed": False, "xp_reward": 700, "required_mission": "traverse_linked_array"},
            "node_3": {"title": "OS Memory Allocation Pools", "type": "Thrust Stance", "unlocked": False, "completed": False, "xp_reward": 900, "required_mission": "override_virtual_inheritance"},
            "node_4": {"title": "Relational Query Normalization", "type": "Transformation", "unlocked": False, "completed": False, "xp_reward": 1100, "required_mission": "prevent_heap_overflow"}
        }
    },
    "MCA (Master of Computer Applications)": {
        "sector_name": "Network Overlord Core",
        "nodes": {
            "node_1": {"title": "Enterprise Design Clusters", "type": "Core Stance", "unlocked": True, "completed": False, "xp_reward": 700, "required_mission": None},
            "node_2": {"title": "Full-Stack System Routing", "type": "Pillar Stance", "unlocked": False, "completed": False, "xp_reward": 900, "required_mission": "refactor_singleton_faults"},
            "node_3": {"title": "Distributed Cloud Scalers", "type": "Thrust Stance", "unlocked": False, "completed": False, "xp_reward": 1100, "required_mission": "configure_ingress_proxy"},
            "node_4": {"title": "Predictive AI Sub-Routines", "type": "Transformation", "unlocked": False, "completed": False, "xp_reward": 1350, "required_mission": "balance_load_spike"}
        }
    },
    "BBA (Bachelor of Business Administration)": {
        "sector_name": "Corpo-Executive District",
        "nodes": {
            "node_1": {"title": "Organizational Architecture", "type": "Core Stance", "unlocked": True, "completed": False, "xp_reward": 500, "required_mission": None},
            "node_2": {"title": "Financial Ledger Analysis", "type": "Pillar Stance", "unlocked": False, "completed": False, "xp_reward": 700, "required_mission": "streamline_hr_hierarchy"},
            "node_3": {"title": "Strategic Marketing Pipelines", "type": "Thrust Stance", "unlocked": False, "completed": False, "xp_reward": 900, "required_mission": "reconcile_balance_sheets"},
            "node_4": {"title": "Supply-Chain Grid Optimization", "type": "Transformation", "unlocked": False, "completed": False, "xp_reward": 1100, "required_mission": "launch_campaign_funnel"}
        }
    },
    "MBA / PGDM (Master of Business Administration)": {
        "sector_name": "Megacorp Strategy War-Room",
        "nodes": {
            "node_1": {"title": "Corporate Mergers Stance", "type": "Core Stance", "unlocked": True, "completed": False, "xp_reward": 800, "required_mission": None},
            "node_2": {"title": "Risk Mitigation Matrices", "type": "Pillar Stance", "unlocked": False, "completed": False, "xp_reward": 1000, "required_mission": "execute_hostile_takeover"},
            "node_3": {"title": "Venture Capital Valuation", "type": "Thrust Stance", "unlocked": False, "completed": False, "xp_reward": 1200, "required_mission": "hedging_market_volatility"},
            "node_4": {"title": "Macro Global Expansion Maps", "type": "Transformation", "unlocked": False, "completed": False, "xp_reward": 1500, "required_mission": "audit_series_a_term_sheet"}
        }
    },
    "UPSC / Civil Services": {
        "sector_name": "Network Grid Bureaucracy",
        "nodes": {
            "node_1": {"title": "Constitutional Protocol Matrices", "type": "Core Stance", "unlocked": True, "completed": False, "xp_reward": 750, "required_mission": None},
            "node_2": {"title": "Macro-Geopolitical Alliances", "type": "Pillar Stance", "unlocked": False, "completed": False, "xp_reward": 950, "required_mission": "interpret_article_framework"},
            "node_3": {"title": "Public Policy Implementation", "type": "Thrust Stance", "unlocked": False, "completed": False, "xp_reward": 1150, "required_mission": "negotiate_bilateral_treaty"},
            "node_4": {"title": "Crisis Management Protocols", "type": "Transformation", "unlocked": False, "completed": False, "xp_reward": 1450, "required_mission": "distribute_rural_subsidies"}
        }
    },
    "REET / TET (Teaching Eligibility)": {
        "sector_name": "Matrix Protocol Academy",
        "nodes": {
            "node_1": {"title": "Pedagogical Schema Alignment", "type": "Core Stance", "unlocked": True, "completed": False, "xp_reward": 450, "required_mission": None},
            "node_2": {"title": "Child Cognition Blueprints", "type": "Pillar Stance", "unlocked": False, "completed": False, "xp_reward": 600, "required_mission": "apply_bloom_taxonomy"},
            "node_3": {"title": "Curriculum Design Engines", "type": "Thrust Stance", "unlocked": False, "completed": False, "xp_reward": 750, "required_mission": "analyze_piaget_stages"},
            "node_4": {"title": "Psychometric Testing Nodes", "type": "Transformation", "unlocked": False, "completed": False, "xp_reward": 950, "required_mission": "format_formative_assessment"}
        }
    },
    "NEET (Medical Entrance)": {
        "sector_name": "Bio-Labs Sector",
        "nodes": {
            "node_1": {"title": "Human Anatomy Cells", "type": "Core Stance", "unlocked": True, "completed": False, "xp_reward": 500, "required_mission": None},
            "node_2": {"title": "Organic Reaction Mechanisms", "type": "Pillar Stance", "unlocked": False, "completed": False, "xp_reward": 750, "required_mission": "label_mitochondrial_matrix"},
            "node_3": {"title": "Plant Physiology Matrix", "type": "Thrust Stance", "unlocked": False, "completed": False, "xp_reward": 900, "required_mission": "solve_electrophilic_addition"},
            "node_4": {"title": "Genetics Sequence Parsing", "type": "Transformation", "unlocked": False, "completed": False, "xp_reward": 1100, "required_mission": "decode_calvin_cycle"}
        }
    },
    "JEE (Engineering Entrance)": {
        "sector_name": "Mechanized Cadence Crucible",
        "nodes": {
            "node_1": {"title": "Kinematic Calculus Arrays", "type": "Core Stance", "unlocked": True, "completed": False, "xp_reward": 550, "required_mission": None},
            "node_2": {"title": "Electromagnetic Flux Bounds", "type": "Pillar Stance", "unlocked": False, "completed": False, "xp_reward": 750, "required_mission": "resolve_projectile_vectors"},
            "node_3": {"title": "Aromatic Synthesis Gates", "type": "Thrust Stance", "unlocked": False, "completed": False, "xp_reward": 950, "required_mission": "integrate_gauss_surface"},
            "node_4": {"title": "Permutation Combinatorics", "type": "Transformation", "unlocked": False, "completed": False, "xp_reward": 1200, "required_mission": "isolate_benzene_derivative"}
        }
    }
}

def determine_rpg_class(stream_str: str) -> str:
    if stream_str in STREAM_CLASS_MAPPING:
        return STREAM_CLASS_MAPPING[stream_str]
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
    inventory: dict[str, int] = {"memory_book": 0, "energy_drink": 1, "brain_booster": 0, "streak_shield": 0}
    stream: str = "10th Standard (Boards Prep)"
    agent_class: str = "Initiate Operator"
    skill_tree: dict | None = None
    completed_missions: list[str] = []

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

class CompleteMissionSchema(BaseModel):
    mission_id: str

class StudyMaterialRequestSchema(BaseModel):
    node_id: str  

class MCQOption(BaseModel):
    key: str  
    text: str

class MCQResponseSchema(BaseModel):
    question: str
    options: list[MCQOption]
    correct_key: str
    cyber_explanation: str

class FlashcardResponseSchema(BaseModel):
    front_prompt: str
    back_codename: str
    operational_summary: str
    is_revealed: bool = False

class MemoryCardPair(BaseModel):
    id: str
    term: str
    definition: str

class MemoryCardResponseSchema(BaseModel):
    pairs: list[MemoryCardPair]  

# --- POLAR.SH PAYMENT CONFIGURATION ---
# NEVER hardcode the access token here. Set it as an environment variable
# in your deployment (e.g. `POLAR_ACCESS_TOKEN=polar_oat_...`).
POLAR_ACCESS_TOKEN = os.getenv("POLAR_ACCESS_TOKEN", "")
POLAR_WEBHOOK_SECRET = os.getenv("POLAR_WEBHOOK_SECRET", "")
POLAR_SERVER = os.getenv("POLAR_SERVER", "production")  # "production" or "sandbox"
POLAR_API_BASE = "https://sandbox-api.polar.sh/v1" if POLAR_SERVER == "sandbox" else "https://api.polar.sh/v1"
POLAR_SUCCESS_URL = os.getenv("POLAR_SUCCESS_URL", "https://your-frontend.example.com/payment-success?checkout_id={CHECKOUT_ID}")

# Map your in-game item IDs to Polar Product IDs (create these Products in your Polar dashboard first).
POLAR_PRODUCT_MAP = {
    "premium_tier": os.getenv("POLAR_PRODUCT_PREMIUM_TIER", ""),
    "energy_pack_100": os.getenv("POLAR_PRODUCT_ENERGY_100", ""),
    "energy_pack_50": os.getenv("POLAR_PRODUCT_ENERGY_50", ""),
}

POLAR_ITEM_LABELS = {
    "premium_tier": "Nexus Premium Upgrade",
    "energy_pack_100": "100 Matrix Energy Pack",
    "energy_pack_50": "50 Matrix Energy Pack",
}


class PolarWebhookVerificationError(Exception):
    pass


def verify_polar_webhook(raw_body: bytes, headers) -> dict:
    """
    Verifies a Polar.sh webhook using the Standard Webhooks signing scheme.
    Expects headers: webhook-id, webhook-timestamp, webhook-signature.
    """
    if not POLAR_WEBHOOK_SECRET:
        raise PolarWebhookVerificationError("POLAR_WEBHOOK_SECRET is not configured on the server.")

    webhook_id = headers.get("webhook-id")
    webhook_timestamp = headers.get("webhook-timestamp")
    webhook_signature = headers.get("webhook-signature")

    if not (webhook_id and webhook_timestamp and webhook_signature):
        raise PolarWebhookVerificationError("Missing required webhook signature headers.")

    # Polar-specific quirk: unlike Svix/Clerk, Polar does NOT base64-decode
    # the webhook secret before use. Use the full secret string (including
    # any "whsec_" / "polar_whs_" prefix) as raw UTF-8 bytes for the HMAC key.
    secret_bytes = POLAR_WEBHOOK_SECRET.encode("utf-8")

    signed_content = f"{webhook_id}.{webhook_timestamp}.{raw_body.decode('utf-8')}".encode("utf-8")
    expected_signature = base64.b64encode(
        hmac.new(secret_bytes, signed_content, hashlib.sha256).digest()
    ).decode()

    provided_signatures = [
        part.split(",", 1)[-1] for part in webhook_signature.split(" ") if part
    ]

    if not any(hmac.compare_digest(expected_signature, sig) for sig in provided_signatures):
        raise PolarWebhookVerificationError("Webhook signature verification failed.")

    return json.loads(raw_body)


async def get_current_user(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_bearer)]) -> dict:
    token = credentials.credentials
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid security authorization layer token.")

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
        if "completed_missions" not in player_data:
            player_data["completed_missions"] = []
            
        user_stream = player_data.get("stream", "10th Standard (Boards Prep)")
        
        current_tree = player_data.get("skill_tree", {})
        expected_sector = STREAM_SKILL_TREES.get(user_stream, STREAM_SKILL_TREES["10th Standard (Boards Prep)"])["sector_name"]
        
        if "skill_tree" not in player_data or current_tree.get("sector_name") != expected_sector:
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
            "skill_tree": STREAM_SKILL_TREES[default_stream],
            "completed_missions": []
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
async def update_player_stream(payload: UpdateStreamSchema, user: Annotated[dict, Depends(get_current_user)]):
    uid = user["uid"]
    doc_ref = db.collection("users").document(uid)
    calculated_class = determine_rpg_class(payload.stream)
    new_skill_tree = STREAM_SKILL_TREES.get(payload.stream, STREAM_SKILL_TREES["10th Standard (Boards Prep)"])
    
    await doc_ref.set({
        "stream": payload.stream,
        "agent_class": calculated_class,
        "skill_tree": new_skill_tree
    }, merge=True)
    return {"message": f"Core domain alignment altered to {payload.stream}.", "unlocked_class": calculated_class}

@app.post("/api/combat/analyze")
async def process_combat_encounter(action_data: CombatActionSchema, user: Annotated[dict, Depends(get_current_user)]):
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
        f"Determine if they succeeded or failed. Provide a dramatic text battle output flavor text packed with high-tech cyberpunk terminology. "
        f"End your response with exactly: 'SCORE: <0 to 100>' indicating action efficacy."
    )

    try:
        response = gemini_client.models.generate_content(model="gemini-2.5-flash", contents=prompt_context)
        ai_response_text = response.text
    except Exception as gemini_err:
        print(f"Gemini combat failure/429 fallback activated: {gemini_err}")
        ai_response_text = (
            f"NEXUS SAFEGUARD ACTIVE: Due to connection shielding (Rate limit/429), your terminal "
            f"has simulated an offline tactical maneuver! Your tactical input bypassed the "
            f"perimeter network of '{action_data.enemy_name}' with high efficiency.\n"
            f"SCORE: 88"
        )

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
    return {"battle_log": ai_response_text.split("SCORE:")[0].strip(), "score": calculated_score, "rewards": {"xp": xp_gained, "coins": coins_gained}, "updated_player": player_data}

@app.post("/api/study/explain")
async def process_study_module(payload: StudyTopicSchema, user: Annotated[dict, Depends(get_current_user)]):
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
        response = gemini_client.models.generate_content(model="gemini-2.5-flash", contents=prompt_context)
        ai_explanation = response.text
    except Exception as gemini_err:
        print(f"Gemini study explanation failure/429 fallback activated: {gemini_err}")
        ai_explanation = (
            f"### [NEXUS COMPENDIUM ARCHIVE ACTIVE - LOCAL MODULE LOADED]\n\n"
            f"Live neural uplink is currently optimizing payload rates (API Quota Exceeded/429). "
            f"Here is your offline reference dossier for: **{payload.topic}** within **{player_stream}**.\n\n"
            f"#### Structural Summary\n"
            f"This segment regulates core calculations and structural formulas in your stream. "
            f"Understanding this concept requires isolating key variables to minimize error degradation "
            f"and streamline functional performance under high computational friction.\n\n"
            f"**Understanding Check:**\n"
            f"What is the primary factor limiting latency scaling in offline matrix buffers?"
        )

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
    return {"explanation": ai_explanation, "rewards": {"xp": xp_gained, "coins": coins_gained}, "updated_player": player_data}

@app.get("/api/leaderboard")
async def get_global_leaderboard(user: Annotated[dict, Depends(get_current_user)]):
    try:
        leaderboard_query = db.collection("users").order_by("level", direction="DESCENDING").order_by("xp", direction="DESCENDING").limit(10)
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
        raise HTTPException(status_code=500, detail="Failed to query network scoreboard records.")

@app.post("/api/store/buy-energy")
async def purchase_energy_pack(payload: EnergyPurchaseSchema, user: Annotated[dict, Depends(get_current_user)]):
    uid = user["uid"]
    doc_ref = db.collection("users").document(uid)
    doc_snap = await doc_ref.get()
    if not doc_snap.exists:
        raise HTTPException(status_code=404, detail="Player data stream missing.")
    player_data = doc_snap.to_dict()

    if player_data.get("isPremium", False):
        return {"message": "Infinite matrix energy active. Consumables redundant.", "updated_player": player_data}

    energy_amount = 50 if payload.pack_id == "energy_pack_50" else 100 if payload.pack_id == "energy_pack_100" else 0
    if not energy_amount:
        raise HTTPException(status_code=400, detail="Invalid energy pack classification ID.")

    player_data["energy"] = min(player_data.get("energy", 100) + energy_amount, 100)
    await doc_ref.set(player_data, merge=True)
    return {"message": f"Payment Verified! Added {energy_amount} Energy to your profile matrix.", "updated_player": player_data}

@app.post("/api/store/activate-premium")
async def activate_premium_license(user: Annotated[dict, Depends(get_current_user)]):
    uid = user["uid"]
    doc_ref = db.collection("users").document(uid)
    await doc_ref.set({"isPremium": True}, merge=True)
    return {"status": "success", "message": "Premium status permanent override synchronized successfully."}

@app.post("/api/social/request")
async def send_friend_request(payload: FriendRequestSchema, user: Annotated[dict, Depends(get_current_user)]):
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
        "uid": sender_uid, "agent_name": sender_data.get("agent_name", "Unknown Operator"),
        "avatar_icon": sender_data.get("avatar_icon", "fa-user-ninja"), "theme_color": sender_data.get("theme_color", "#00f0ff"), "status": "pending_incoming"
    })
    await users_ref.document(sender_uid).collection("friends").document(target_uid).set({
        "uid": target_uid, "agent_name": target_name,
        "avatar_icon": target_docs[0].to_dict().get("avatar_icon", "fa-user-ninja"), "theme_color": target_docs[0].to_dict().get("theme_color", "#00f0ff"), "status": "pending_outgoing"
    })
    return {"message": f"Uplink request transmitted to {target_name}."}

@app.post("/api/social/accept")
async def accept_friend_request(payload: FriendRequestSchema, user: Annotated[dict, Depends(get_current_user)]):
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
    return [doc.to_dict() for doc in docs]

@app.post("/api/billing/create-checkout")
async def create_order(payload: PurchaseSchema, user: Annotated[dict, Depends(get_current_user)]):
    """
    Creates a Polar.sh Checkout Session for the requested item and returns
    a hosted checkout_url. The frontend should redirect the user to this URL
    (e.g. window.location.href = checkout_url) instead of opening an inline widget.
    Fulfillment happens asynchronously via the /api/billing/webhook endpoint.
    """
    item = payload.item_id
    if item not in POLAR_ITEM_LABELS:
        raise HTTPException(status_code=400, detail="Invalid item ID catalog entry.")

    if not POLAR_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="Polar access token not configured on the server.")

    product_id = POLAR_PRODUCT_MAP.get(item)
    if not product_id:
        raise HTTPException(status_code=500, detail=f"No Polar product configured for '{item}'. Set the corresponding env var.")

    checkout_payload = {
        "product_id": product_id,
        "success_url": POLAR_SUCCESS_URL,
        "customer_external_id": user["uid"],
        "metadata": {
            "player_uid": user["uid"],
            "purchased_item": item
        }
    }

    async with httpx.AsyncClient(timeout=15.0) as http_client:
        try:
            resp = await http_client.post(
                f"{POLAR_API_BASE}/checkouts/",
                headers={
                    "Authorization": f"Bearer {POLAR_ACCESS_TOKEN}",
                    "Content-Type": "application/json"
                },
                json=checkout_payload
            )
            resp.raise_for_status()
            checkout_data = resp.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"Polar checkout creation failed: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return {
        "checkout_id": checkout_data.get("id"),
        "checkout_url": checkout_data.get("url"),
        "product_name": POLAR_ITEM_LABELS[item]
    }


@app.post("/api/billing/webhook")
async def polar_webhook(request: Request):
    """
    Receives Polar.sh webhook events and fulfills the purchase server-side.
    Configure this URL (https://your-domain.com/api/billing/webhook) in your
    Polar dashboard's webhook settings, and set POLAR_WEBHOOK_SECRET to the
    signing secret Polar gives you there.
    """
    raw_body = await request.body()
    try:
        event = verify_polar_webhook(raw_body, request.headers)
    except PolarWebhookVerificationError as e:
        raise HTTPException(status_code=403, detail=str(e))

    event_type = event.get("type", "")
    data = event.get("data", {}) or {}
    metadata = data.get("metadata", {}) or {}
    player_uid = metadata.get("player_uid")
    purchased_item = metadata.get("purchased_item")

    is_success_event = event_type in ("order.paid",) or (
        event_type == "checkout.updated" and data.get("status") == "succeeded"
    )

    if is_success_event and player_uid and purchased_item:
        doc_ref = db.collection("users").document(player_uid)
        doc_snap = await doc_ref.get()
        if doc_snap.exists:
            player_data = doc_snap.to_dict()

            if purchased_item == "premium_tier":
                player_data["isPremium"] = True
            elif purchased_item == "energy_pack_100":
                player_data["energy"] = min(player_data.get("energy", 100) + 100, 100)
            elif purchased_item == "energy_pack_50":
                player_data["energy"] = min(player_data.get("energy", 100) + 50, 100)

            await doc_ref.set(player_data, merge=True)

    return {"received": True}

@app.post("/api/store/buy-item")
async def purchase_inventory_item(payload: BuyItemSchema, user: Annotated[dict, Depends(get_current_user)]):
    uid = user["uid"]
    doc_ref = db.collection("users").document(uid)
    doc_snap = await doc_ref.get()
    if not doc_snap.exists:
        raise HTTPException(status_code=404, detail="Player node missing.")
    player_data = doc_snap.to_dict()

    ITEM_PRICES = {"memory_book": 500, "energy_drink": 200, "brain_booster": 1200, "streak_shield": 1500}
    item = payload.item_id
    if item not in ITEM_PRICES:
        raise HTTPException(status_code=400, detail="Item not found in database registry catalog.")
        
    item_cost = ITEM_PRICES[item]
    if player_data.get("coins", 0) < item_cost:
        raise HTTPException(status_code=400, detail="Insufficient coin reserves for transaction.")
        
    player_data["coins"] -= item_cost
    inventory = player_data.get("inventory", {})
    inventory[item] = inventory.get(item, 0) + 1
    player_data["inventory"] = inventory
    
    await doc_ref.set(player_data, merge=True)
    return {"message": f"Successfully acquired {item.replace('_', ' ').title()}!", "updated_player": player_data}

@app.post("/api/inventory/consume")
async def consume_backpack_item(payload: UseItemSchema, user: Annotated[dict, Depends(get_current_user)]):
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

    if item == "energy_drink":
        player_data["energy"] = min(player_data.get("energy", 100) + 3, 100)
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
    return {"message": execution_message, "updated_player": player_data}

@app.post("/api/skills/unlock-node")
async def unlock_skill_tree_node(payload: UnlockNodeSchema, user: Annotated[dict, Depends(get_current_user)]):
    uid = user["uid"]
    doc_ref = db.collection("users").document(uid)
    doc_snap = await doc_ref.get()
    
    if not doc_snap.exists:
        raise HTTPException(status_code=404, detail="Player entry dropped.")
        
    player_data = doc_snap.to_dict()
    user_stream = player_data.get("stream", "10th Standard (Boards Prep)")
    
    lookup_stream = user_stream if user_stream in STREAM_SKILL_TREES else "10th Standard (Boards Prep)"
    user_tree = player_data.get("skill_tree", STREAM_SKILL_TREES[lookup_stream])
    nodes = user_tree.get("nodes", {})
    target_node = payload.node_id
    
    if target_node not in nodes:
        raise HTTPException(status_code=404, detail="Target map node coordinate missing.")
        
    node_data = nodes[target_node]
    if not node_data.get("unlocked", False):
        raise HTTPException(status_code=400, detail="Target sequence gate locked by parent process conditions.")
        
    if node_data.get("completed", False):
        return {"message": "Node already fully synthesized.", "updated_player": player_data}
        
    required_mission = node_data.get("required_mission")
    if required_mission:
        completed_missions = player_data.get("completed_missions", [])
        if required_mission not in completed_missions:
            raise HTTPException(
                status_code=400, 
                detail=f"Locked! Clear the mission objective milestone: '{required_mission.replace('_', ' ').title()}' to awaken this node."
            )
        
    nodes[target_node]["completed"] = True
    xp_earned = node_data["xp_reward"]
    
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
    return {"message": f"Successfully completed {node_data['title']}!", "xp_earned": xp_earned, "updated_player": player_data}

@app.post("/api/missions/complete")
async def complete_mission(payload: CompleteMissionSchema, user: Annotated[dict, Depends(get_current_user)]):
    uid = user["uid"]
    doc_ref = db.collection("users").document(uid)
    doc_snap = await doc_ref.get()
    
    if not doc_snap.exists:
        raise HTTPException(status_code=404, detail="Player profile not found.")
        
    player_data = doc_snap.to_dict()
    completed_missions = player_data.get("completed_missions", [])
    
    if payload.mission_id not in completed_missions:
        completed_missions.append(payload.mission_id)
        player_data["completed_missions"] = completed_missions
        player_data["coins"] = player_data.get("coins", 0) + 100 
        
        await doc_ref.set(player_data, merge=True)
        return {
            "message": f"Mission '{payload.mission_id.replace('_', ' ').title()}' cleared! Gateway unlocked.",
            "updated_player": player_data
        }
        
    return {"message": "Mission already cleared.", "updated_player": player_data}

# --- GENERATOR CHANNELS (RE-ENGINEERED WITH RATE LIMIT / 429 SHIELDS) ---

@app.post("/api/study/generate-mcq", response_model=MCQResponseSchema)
async def generate_stream_mcq(payload: StudyMaterialRequestSchema, user: Annotated[dict, Depends(get_current_user)]):
    uid = user["uid"]
    doc_snap = await db.collection("users").document(uid).get()
    if not doc_snap.exists:
        raise HTTPException(status_code=404, detail="Player entry dropped.")
    
    player_data = doc_snap.to_dict()
    user_stream = player_data.get("stream", "10th Standard (Boards Prep)")
    
    lookup_stream = user_stream if user_stream in STREAM_SKILL_TREES else "10th Standard (Boards Prep)"
    nodes = STREAM_SKILL_TREES[lookup_stream].get("nodes", {})
    topic_title = nodes.get(payload.node_id, {}).get("title", "Core System Core Operations")

    prompt = (
        f"You are a terminal matrix testing engine for a retro-cyberpunk educational game.\n"
        f"Generate exactly one high-quality Multiple Choice Question (MCQ) suited specifically for the academic level of: '{user_stream}'.\n"
        f"The question MUST focus directly on the concept: '{topic_title}'.\n"
        f"You MUST respond ONLY with a raw JSON object containing exactly these fields:\n"
        f"{{\n"
        f"  \"question\": \"The question text\",\n"
        f"  \"options\": [\n"
        f"    {{\"key\": \"A\", \"text\": \"First option\"}},\n"
        f"    {{\"key\": \"B\", \"text\": \"Second option\"}},\n"
        f"    {{\"key\": \"C\", \"text\": \"Third option\"}},\n"
        f"    {{\"key\": \"D\", \"text\": \"Fourth option\"}}\n"
        f"  ],\n"
        f"  \"correct_key\": \"A\",\n"
        f"  \"cyber_explanation\": \"A concise explanation detailing why the key is correct.\"\n"
        f"}}\n"
        f"Do not include markdown codeblocks, prefix text, or trailing symbols."
    )

    try:
        response = gemini_client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        clean_text = response.text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        return json.loads(clean_text.strip())
    except Exception as e:
        print(f"MCQ Schema Fallback (429/Quota limit caught): {e}")
        # Dynamic fallback parameters matching the target user topic
        return {
            "question": f"In the academic scope of {user_stream}, which core parameter governs the primary application vectors of '{topic_title}'?",
            "options": [
                {"key": "A", "text": "Alternative operational masking and static structural bounds."},
                {"key": "B", "text": "Functional synthesis alignment parameters regulating core vectors."},
                {"key": "C", "text": "Dynamic buffering modules overriding system compilation lag."},
                {"key": "D", "text": "Isotopic scale metrics and metadata distribution matrices."}
            ],
            "correct_key": "B",
            "cyber_explanation": f"Understanding '{topic_title}' under the {user_stream} guidelines requires tracking the direct vector alignment of functional components to achieve clean, optimized scaling."
        }

@app.post("/api/study/generate-flashcard", response_model=FlashcardResponseSchema)
async def generate_stream_flashcard(payload: StudyMaterialRequestSchema, user: Annotated[dict, Depends(get_current_user)]):
    uid = user["uid"]
    doc_snap = await db.collection("users").document(uid).get()
    if not doc_snap.exists:
        raise HTTPException(status_code=404, detail="Player entry dropped.")
    
    player_data = doc_snap.to_dict()
    user_stream = player_data.get("stream", "10th Standard (Boards Prep)")
    
    lookup_stream = user_stream if user_stream in STREAM_SKILL_TREES else "10th Standard (Boards Prep)"
    topic_title = STREAM_SKILL_TREES[lookup_stream].get("nodes", {}).get(payload.node_id, {}).get("title", "Core System Operations")

    prompt = (
        f"Create an educational flashcard for a student studying: '{user_stream}' targeting the specific concept: '{topic_title}'.\n"
        f"You MUST respond ONLY with a raw JSON object containing exactly these fields:\n"
        f"{{\n"
        f"  \"front_prompt\": \"The query, term, or question statement on the front of the flashcard\",\n"
        f"  \"back_codename\": \"The exact direct code name answer or solution core phrase\",\n"
        f"  \"operational_summary\": \"A short contextual description or calculation parameter logic sheet summarizing the core operation.\"\n"
        f"}}\n"
        f"Do not include markdown codeblocks or extra symbols."
    )

    try:
        response = gemini_client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        clean_text = response.text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        data = json.loads(clean_text.strip())
        data["is_revealed"] = False
        return data
    except Exception as e:
        print(f"Flashcard Schema Fallback (429/Quota limit caught): {e}")
        return {
            "front_prompt": f"What variable regulates core system constraints within '{topic_title}'?",
            "back_codename": "Matrix Boundary Parameters",
            "operational_summary": f"Initial baselines inside '{topic_title}' allocate structural parameters recursively to prevent memory leaks and maintain steady progression.",
            "is_revealed": False
        }

@app.post("/api/study/generate-memory-cards", response_model=MemoryCardResponseSchema)
async def generate_stream_memory_cards(payload: StudyMaterialRequestSchema, user: Annotated[dict, Depends(get_current_user)]):
    uid = user["uid"]
    doc_snap = await db.collection("users").document(uid).get()
    if not doc_snap.exists:
        raise HTTPException(status_code=404, detail="Player entry dropped.")
    
    player_data = doc_snap.to_dict()
    user_stream = player_data.get("stream", "10th Standard (Boards Prep)")
    
    lookup_stream = user_stream if user_stream in STREAM_SKILL_TREES else "10th Standard (Boards Prep)"
    topic_title = STREAM_SKILL_TREES[lookup_stream].get("nodes", {}).get(payload.node_id, {}).get("title", "Core System Operations")

    prompt = (
        f"Generate exactly 4 matching pairs of educational technical terms and definitions suitable for a memory/match card game.\n"
        f"Academic Field/Stream: '{user_stream}'. Specific Sub-topic focus: '{topic_title}'.\n"
        f"Ensure terms are brief formulas, vocabulary words, or components, and definitions are short and concrete.\n"
        f"You MUST respond ONLY with a raw JSON object matching this exact shape:\n"
        f"{{\n"
        f"  \"pairs\": [\n"
        f"    {{\"id\": \"1\", \"term\": \"Term A\", \"definition\": \"Definition for A\"}},\n"
        f"    {{\"id\": \"2\", \"term\": \"Term B\", \"definition\": \"Definition for B\"}},\n"
        f"    {{\"id\": \"3\", \"term\": \"Term C\", \"definition\": \"Definition for C\"}},\n"
        f"    {{\"id\": \"4\", \"term\": \"Term D\", \"definition\": \"Definition for D\"}}\n"
        f"  ]\n"
        f"}}\n"
        f"Do not include markdown codeblocks or extra symbols."
    )

    try:
        response = gemini_client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        clean_text = response.text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        return json.loads(clean_text.strip())
    except Exception as e:
        print(f"Memory Matrix Fallback (429/Quota limit caught): {e}")
        return {
            "pairs": [
                {"id": "pair_1", "term": f"{topic_title} Base", "definition": f"The foundational functional blueprint Layer regulating '{topic_title}' concepts."},
                {"id": "pair_2", "term": "Vector Alignment", "definition": f"Synchronizing interface structures under the {user_stream} framework."},
                {"id": "pair_3", "term": "Synthesis Node", "definition": "An active educational juncture processing system parameters."},
                {"id": "pair_4", "term": "Buffer Reserve", "definition": "Bypassing network latency limits to guarantee immediate load states."}
            ]
        }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
