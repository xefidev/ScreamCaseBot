import os
import re
import sys
import json
import hmac
import hashlib
import asyncio
import logging
import random
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Message, WebAppInfo, PreCheckoutQuery
from supabase import Client, create_client

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args: Any, **kwargs: Any) -> bool:
        return False

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("screamcase")

# ============================================================================
# 1. ADMIN CONFIGURATION
# ============================================================================
ADMIN_IDS = [7782281997, 5396975347]
ADMIN_ID_SET = set(ADMIN_IDS)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_KEY")
    or os.getenv("VITE_SUPABASE_ANON_KEY")
)

if not BOT_TOKEN:
    logger.critical("TELEGRAM_BOT_TOKEN or BOT_TOKEN is missing")
if not SUPABASE_URL:
    logger.critical("SUPABASE_URL is missing")
if not SUPABASE_KEY:
    logger.critical("SUPABASE_KEY is missing")

WEBAPP_URL = os.getenv("WEBAPP_URL", "https://screamcase.online")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@screamcase")

bot = Bot(token=BOT_TOKEN) if BOT_TOKEN else None
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None

# ============================================================================
# 2. STATIC DATA (GIFTS, CASES, RANGES)
# ============================================================================

GIFTS = [
    {"price": 10, "name": "Мини-крик", "image": "/asset/Gifts/mini_scream.png"},
    {"price": 25, "name": "Крик боли", "image": "/asset/Gifts/pain_scream.png"},
    {"price": 50, "name": "Ужасный крик", "image": "/asset/Gifts/horror_scream.png"},
    {"price": 100, "name": "Крик победы", "image": "/asset/Gifts/victory_scream.png"},
    {"price": 200, "name": "Крик экстаза", "image": "/asset/Gifts/ecstasy_scream.png"},
    {"price": 500, "name": "Апокалиптический крик", "image": "/asset/Gifts/apocalyptic_scream.png"},
    {"price": 1000, "name": "Крик мира", "image": "/asset/Gifts/world_scream.png"},
    {"price": 5000, "name": "Инфернальный крик", "image": "/asset/Gifts/infernal_scream.png"},
    {"price": 10, "name": "Привет", "image": "/asset/Gifts/hello.png"},
    {"price": 25, "name": "Улыбка", "image": "/asset/Gifts/smile.png"},
    {"price": 50, "name": "Смех", "image": "/asset/Gifts/laugh.png"},
    {"price": 100, "name": "Веселье", "image": "/asset/Gifts/fun.png"},
    {"price": 200, "name": "Радость", "image": "/asset/Gifts/joy.png"},
    {"price": 500, "name": "Счастье", "image": "/asset/Gifts/happiness.png"},
    {"price": 1000, "name": "Блаженство", "image": "/asset/Gifts/bliss.png"},
    {"price": 5000, "name": "Эйфория", "image": "/asset/Gifts/euphoria.png"},
    {"price": 10, "name": "Шепот", "image": "/asset/Gifts/whisper.png"},
    {"price": 25, "name": "Голос", "image": "/asset/Gifts/voice.png"},
    {"price": 50, "name": "Песня", "image": "/asset/Gifts/song.png"},
    {"price": 100, "name": "Симфония", "image": "/asset/Gifts/symphony.png"},
    {"price": 200, "name": "Оркестр", "image": "/asset/Gifts/orchestra.png"},
    {"price": 500, "name": "Концерт", "image": "/asset/Gifts/concert.png"},
    {"price": 1000, "name": "Опера", "image": "/asset/Gifts/opera.png"},
    {"price": 5000, "name": "Филармония", "image": "/asset/Gifts/philharmonic.png"},
    {"price": 10, "name": "Пинок", "image": "/asset/Gifts/kick.png"},
    {"price": 25, "name": "Удар", "image": "/asset/Gifts/hit.png"},
    {"price": 50, "name": "Шок", "image": "/asset/Gifts/shock.png"},
    {"price": 100, "name": "Взрыв", "image": "/asset/Gifts/explosion.png"},
    {"price": 200, "name": "Катастрофа", "image": "/asset/Gifts/catastrophe.png"},
    {"price": 500, "name": "Апокалипсис", "image": "/asset/Gifts/apocalypse.png"},
    {"price": 1000, "name": "Чёрная дыра", "image": "/asset/Gifts/black_hole.png"},
    {"price": 5000, "name": "Взрыв сверхновой", "image": "/asset/Gifts/supernova.png"},
    {"price": 10, "name": "Золотой дождь", "image": "/asset/Gifts/gold_rain.png"},
    {"price": 25, "name": "Серебряный ветер", "image": "/asset/Gifts/silver_wind.png"},
    {"price": 50, "name": "Платиновый свет", "image": "/asset/Gifts/platinum_light.png"},
    {"price": 100, "name": "Алмазный блеск", "image": "/asset/Gifts/diamond_shine.png"},
    {"price": 200, "name": "Радуга", "image": "/asset/Gifts/rainbow.png"},
    {"price": 500, "name": "Северное сияние", "image": "/asset/Gifts/northern_lights.png"},
    {"price": 1000, "name": "Млечный путь", "image": "/asset/Gifts/milky_way.png"},
    {"price": 5000, "name": "Космос", "image": "/asset/Gifts/cosmos.png"},
    {"price": 10, "name": "Щипок", "image": "/asset/Gifts/pinch.png"},
    {"price": 25, "name": "Пощёчина", "image": "/asset/Gifts/slap.png"},
    {"price": 50, "name": "Кулак", "image": "/asset/Gifts/fist.png"},
    {"price": 100, "name": "Суперудар", "image": "/asset/Gifts/super_hit.png"},
    {"price": 200, "name": "Мегаудар", "image": "/asset/Gifts/mega_hit.png"},
    {"price": 500, "name": "Гигаудар", "image": "/asset/Gifts/giga_hit.png"},
    {"price": 1000, "name": "Терауар", "image": "/asset/Gifts/tera_hit.png"},
    {"price": 5000, "name": "Петауар", "image": "/asset/Gifts/peta_hit.png"},
]

STATIC_CASES = [
    {"id": "bronze", "name": "Бронзовый кейс", "price": 100, "image": "/asset/Case/bronze_case.png"},
    {"id": "silver", "name": "Серебряный кейс", "price": 250, "image": "/asset/Case/silver_case.png"},
    {"id": "gold", "name": "Золотой кейс", "price": 500, "image": "/asset/Case/gold_case.png"},
    {"id": "platinum", "name": "Платиновый кейс", "price": 1000, "image": "/asset/Case/platinum_case.png"},
    {"id": "diamond", "name": "Алмазный кейс", "price": 2500, "image": "/asset/Case/diamond_case.png"},
    {"id": "legendary", "name": "Легендарный кейс", "price": 5000, "image": "/asset/Case/legendary_case.png"},
    {"id": "mythic", "name": "Мифический кейс", "price": 10000, "image": "/asset/Case/mythic_case.png"},
    {"id": "eternal", "name": "Вечный кейс", "price": 25000, "image": "/asset/Case/eternal_case.png"},
    {"id": "cosmic", "name": "Космический кейс", "price": 50000, "image": "/asset/Case/cosmic_case.png"},
    {"id": "void", "name": "Кейс Пустоты", "price": 100000, "image": "/asset/Case/void_case.png"},
]

CASE_RANGES = {
    "bronze": (0, 100),
    "silver": (0, 250),
    "gold": (0, 500),
    "platinum": (0, 1000),
    "diamond": (0, 2500),
    "legendary": (500, 5000),
    "mythic": (1000, 10000),
    "eternal": (5000, 25000),
    "cosmic": (10000, 50000),
    "void": (25000, 100000),
}

AVAILABLE_TASKS = [
    {"id": "referral_1", "name": "Пригласить 1 друга", "description": "Пригласи одного друга", "condition": 1, "reward_stars": 100},
    {"id": "referral_3", "name": "Пригласить 3 друзей", "description": "Пригласи трёх друзей", "condition": 3, "reward_stars": 300},
    {"id": "referral_5", "name": "Пригласить 5 друзей", "description": "Пригласи пятерых друзей", "condition": 5, "reward_stars": 500},
    {"id": "referral_10", "name": "Пригласить 10 друзей", "description": "Пригласи десятерых друзей", "condition": 10, "reward_stars": 1000},
]

INVENTORY_TABLE = "user_inventory"

# ============================================================================
# 3. DATABASE HELPERS
# ============================================================================

async def ensure_user(user_id: int, username: str = "", referred_by: int = None):
    """Ensure user exists in database (upsert)."""
    try:
        data = {
            "id": user_id,
            "username": username,
            "stars": 0,
            "referred_by": referred_by,
            "join_date": datetime.now(timezone.utc).isoformat(),
        }
        result = supabase.table("users").upsert(data, on_conflict="id").execute()
        logger.info(f"User {user_id} ensured in DB")
        return result.data
    except Exception as e:
        logger.error(f"Error ensuring user {user_id}: {e}")
        return None


async def get_user(user_id: int):
    """Get user from database."""
    try:
        result = supabase.table("users").select("*").eq("id", user_id).execute()
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        return None


async def update_balance(user_id: int, amount: int, mode: str = "add"):
    """Update user's star balance. mode='add' or 'set'."""
    try:
        if mode == "add":
            result = supabase.rpc("increment_stars", {"user_id": user_id, "amount": amount}).execute()
        elif mode == "set":
            result = supabase.table("users").update({"stars": amount}).eq("id", user_id).execute()
        logger.info(f"User {user_id} balance updated: {mode} {amount}")
        return result.data
    except Exception as e:
        logger.error(f"Error updating balance for {user_id}: {e}")
        return None


async def deposits_sum_last_24h(user_id: int) -> int:
    """Get total deposits from last 24 hours."""
    try:
        cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        result = supabase.table("user_deposits").select("amount").eq("user_id", user_id).gte("created_at", cutoff_time).execute()
        total = sum(item["amount"] for item in result.data) if result.data else 0
        return total
    except Exception as e:
        logger.error(f"Error getting deposits for {user_id}: {e}")
        return 0


async def add_inventory_item(user_id: int, case_id: str, item_name: str, item_image: str, item_price: int, promo_code: str = None):
    """Add item to user inventory."""
    try:
        data = {
            "user_id": user_id,
            "case_id": case_id,
            "item_name": item_name,
            "item_image": item_image,
            "item_price": item_price,
            "promo_code": promo_code,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = supabase.table(INVENTORY_TABLE).insert([data]).execute()
        logger.info(f"Item added to inventory for user {user_id}: {item_name}")
        return result.data
    except Exception as e:
        logger.error(f"Error adding inventory item for {user_id}: {e}")
        return None


async def get_user_inventory(user_id: int):
    """Get user's inventory."""
    try:
        result = supabase.table(INVENTORY_TABLE).select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return result.data if result.data else []
    except Exception as e:
        logger.error(f"Error getting inventory for {user_id}: {e}")
        return []


# ============================================================================
# 4. PROMO CODE HELPERS
# ============================================================================

async def create_promo_record(code: str, reward_stars: int, duration_hours: int, max_uses: int):
    """Create a new promo code record."""
    try:
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=duration_hours)).isoformat()
        data = {
            "code": code,
            "stars_reward": reward_stars,
            "max_uses": max_uses,
            "uses_count": 0,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = supabase.table("promo_codes").insert([data]).execute()
        logger.info(f"Promo code created: {code}")
        return result.data
    except Exception as e:
        logger.error(f"Error creating promo code {code}: {e}")
        return None


async def get_promo_code(code: str):
    """Get promo code details."""
    try:
        result = supabase.table("promo_codes").select("*").eq("code", code).execute()
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting promo code {code}: {e}")
        return None


async def has_user_used_promo(user_id: int, code: str) -> bool:
    """Check if user has already used this promo code."""
    try:
        result = supabase.table("promo_uses").select("*").eq("user_id", user_id).eq("code", code).execute()
        return len(result.data) > 0
    except Exception as e:
        logger.error(f"Error checking promo usage for {user_id}, {code}: {e}")
        return False


async def record_promo_use(user_id: int, code: str):
    """Record that user has used a promo code."""
    try:
        data = {
            "user_id": user_id,
            "code": code,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        supabase.table("promo_uses").insert([data]).execute()
        
        # Increment uses_count
        supabase.rpc("increment_promo_uses", {"code": code, "amount": 1}).execute()
        logger.info(f"Promo use recorded: user {user_id}, code {code}")
        return True
    except Exception as e:
        logger.error(f"Error recording promo use: {e}")
        return False


# ============================================================================
# 5. QUEST/TASK HELPERS
# ============================================================================

async def get_user_task_status(user_id: int, task_id: str):
    """Get user's task completion status."""
    try:
        result = supabase.table("user_tasks").select("*").eq("user_id", user_id).eq("task_id", task_id).execute()
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting task status for {user_id}, {task_id}: {e}")
        return None


async def mark_task_completed(user_id: int, task_id: str, reward_stars: int):
    """Mark task as completed and award stars."""
    try:
        # Insert task completion
        data = {
            "user_id": user_id,
            "task_id": task_id,
            "completed": True,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        supabase.table("user_tasks").insert([data]).execute()
        
        # Award stars
        await update_balance(user_id, reward_stars, "add")
        logger.info(f"Task {task_id} completed for user {user_id}, awarded {reward_stars} stars")
        return True
    except Exception as e:
        logger.error(f"Error marking task completed: {e}")
        return False


async def count_user_referrals(user_id: int) -> int:
    """Count number of referrals for a user."""
    try:
        result = supabase.table("users").select("id").eq("referred_by", user_id).execute()
        return len(result.data) if result.data else 0
    except Exception as e:
        logger.error(f"Error counting referrals for {user_id}: {e}")
        return 0


# ============================================================================
# 6. CASE OPENING
# ============================================================================

def get_case_price(case_id: str) -> int:
    """Get case price from static data."""
    for case in STATIC_CASES:
        if case["id"] == case_id:
            return case["price"]
    return 0


def random_gift(case_id: str) -> dict:
    """Select random gift from pool based on case price range."""
    if case_id not in CASE_RANGES:
        return GIFTS[0]
    
    min_price, max_price = CASE_RANGES[case_id]
    available = [g for g in GIFTS if min_price <= g["price"] <= max_price]
    
    if not available:
        available = GIFTS
    
    return random.choice(available)


async def api_open_case(request: web.Request) -> web.Response:
    """Open a case and get a random gift."""
    try:
        user_id = int(request["user_id"])
        body = request.get("_body_dict", {})
        
        case_id = body.get("case_id")
        promo_code = body.get("promo_code")
        
        if not case_id:
            return web.json_response({"error": "Missing case_id"}, status=400)
        
        # Get case price
        price = get_case_price(case_id)
        if price == 0:
            return web.json_response({"error": "Invalid case_id"}, status=400)
        
        # Get user data
        user = await get_user(user_id)
        if not user:
            return web.json_response({"error": "User not found"}, status=404)
        
        current_stars = user.get("stars", 0)
        
        # Handle promo code or deduct stars
        if promo_code:
            promo = await get_promo_code(promo_code)
            if not promo:
                return web.json_response({"error": "Invalid promo code"}, status=400)
            
            # Check expiry
            if datetime.fromisoformat(promo["expires_at"]) < datetime.now(timezone.utc):
                return web.json_response({"error": "Promo code expired"}, status=400)
            
            # Check max uses
            if promo["uses_count"] >= promo["max_uses"]:
                return web.json_response({"error": "Promo code limit reached"}, status=400)
            
            # Check single-use per user
            if await has_user_used_promo(user_id, promo_code):
                return web.json_response({"error": "You already used this promo"}, status=400)
            
            # Award stars instead of deduction
            await record_promo_use(user_id, promo_code)
            await update_balance(user_id, promo["stars_reward"], "add")
            price = promo["stars_reward"]
        else:
            # Check balance
            if current_stars < price:
                return web.json_response({"error": "Insufficient stars"}, status=400)
            
            # Deduct stars
            await update_balance(user_id, -price, "add")
        
        # Get random gift
        gift = random_gift(case_id)
        
        # Add to inventory
        await add_inventory_item(user_id, case_id, gift["name"], gift["image"], gift["price"], promo_code)
        
        return web.json_response({
            "success": True,
            "gift": gift,
            "case_id": case_id,
        })
    
    except Exception as e:
        logger.error(f"Error opening case: {e}")
        return web.json_response({"error": str(e)}, status=500)


# ============================================================================
# 7. PROMO ACTIVATION
# ============================================================================

async def api_activate_promo(request: web.Request) -> web.Response:
    """Activate a promo code."""
    try:
        user_id = int(request["user_id"])
        body = request.get("_body_dict", {})
        code = body.get("code")
        
        if not code:
            return web.json_response({"error": "Missing code"}, status=400)
        
        promo = await get_promo_code(code)
        if not promo:
            return web.json_response({"error": "Invalid promo code"}, status=400)
        
        # Check expiry
        if datetime.fromisoformat(promo["expires_at"]) < datetime.now(timezone.utc):
            return web.json_response({"error": "Promo code expired"}, status=400)
        
        # Check max uses
        if promo["uses_count"] >= promo["max_uses"]:
            return web.json_response({"error": "Promo code limit reached"}, status=400)
        
        # Check single-use per user
        if await has_user_used_promo(user_id, code):
            return web.json_response({"error": "You already used this promo"}, status=400)
        
        # Record use and award stars
        await record_promo_use(user_id, code)
        await update_balance(user_id, promo["stars_reward"], "add")
        
        return web.json_response({
            "success": True,
            "stars_awarded": promo["stars_reward"],
        })
    
    except Exception as e:
        logger.error(f"Error activating promo: {e}")
        return web.json_response({"error": str(e)}, status=500)


# ============================================================================
# 8. QUESTS/TASKS
# ============================================================================

async def api_get_tasks(request: web.Request) -> web.Response:
    """Get all available tasks with user's completion status."""
    try:
        user_id = int(request["user_id"])
        
        tasks_response = []
        for task in AVAILABLE_TASKS:
            status = await get_user_task_status(user_id, task["id"])
            completed = status is not None and status.get("completed", False)
            
            # Count referrals for referral tasks
            referral_count = 0
            if task["id"].startswith("referral_"):
                referral_count = await count_user_referrals(user_id)
            
            tasks_response.append({
                "id": task["id"],
                "name": task["name"],
                "description": task["description"],
                "reward_stars": task["reward_stars"],
                "completed": completed,
                "referral_count": referral_count,
                "condition": task["condition"],
            })
        
        return web.json_response({"tasks": tasks_response})
    
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def api_claim_task(request: web.Request) -> web.Response:
    """Claim reward for completed task."""
    try:
        user_id = int(request["user_id"])
        body = request.get("_body_dict", {})
        task_id = body.get("task_id")
        
        if not task_id:
            return web.json_response({"error": "Missing task_id"}, status=400)
        
        # Find task
        task = None
        for t in AVAILABLE_TASKS:
            if t["id"] == task_id:
                task = t
                break
        
        if not task:
            return web.json_response({"error": "Task not found"}, status=404)
        
        # Check if already completed
        status = await get_user_task_status(user_id, task_id)
        if status and status.get("completed"):
            return web.json_response({"error": "Task already completed"}, status=400)
        
        # For referral tasks, verify condition
        if task_id.startswith("referral_"):
            referral_count = await count_user_referrals(user_id)
            if referral_count < task["condition"]:
                return web.json_response({
                    "error": f"Not enough referrals. Need {task['condition']}, have {referral_count}"
                }, status=400)
        
        # Mark task as completed and award stars
        await mark_task_completed(user_id, task_id, task["reward_stars"])
        
        return web.json_response({
            "success": True,
            "task_id": task_id,
            "reward_stars": task["reward_stars"],
        })
    
    except Exception as e:
        logger.error(f"Error claiming task: {e}")
        return web.json_response({"error": str(e)}, status=500)


# ============================================================================
# 9. ADDITIONAL API HANDLERS (cases list, user profile)
# ============================================================================

async def api_get_inventory(request: web.Request) -> web.Response:
    """Get user's inventory. BUG FIX #3: was using asyncio.run() inside async context → RuntimeError."""
    try:
        user_id = int(request["user_id"])
        inventory = await get_user_inventory(user_id)
        return web.json_response({"inventory": inventory})
    except Exception as e:
        logger.error(f"Error getting inventory: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def api_get_cases(request: web.Request) -> web.Response:
    """Return list of all available cases (BUG FIX #4: this endpoint was missing → 404)."""
    return web.json_response({"cases": STATIC_CASES})


async def api_get_user(request: web.Request) -> web.Response:
    """Return current user's profile and balance (BUG FIX #4: this endpoint was missing → 404)."""
    try:
        user_id = int(request["user_id"])
        user = await get_user(user_id)
        if not user:
            return web.json_response({"error": "User not found"}, status=404)
        referrals = await count_user_referrals(user_id)
        return web.json_response({
            "id": user["id"],
            "username": user.get("username", ""),
            "stars": user.get("stars", 0),
            "referrals": referrals,
        })
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return web.json_response({"error": str(e)}, status=500)

def validate_init_data(init_data: str, bot_token: str) -> dict:
    """Validate Telegram init_data using HMAC signature."""
    try:
        parsed = urllib.parse.parse_qs(init_data, keep_blank_values=True)
        signature = parsed.get("hash", [""])[0]

        if not signature:
            logger.warning("validate_init_data: no hash in init_data")
            return None

        # Rebuild data string without hash
        query_data = {k: v[0] for k, v in parsed.items() if k != "hash"}
        sorted_pairs = "\n".join(f"{k}={v}" for k, v in sorted(query_data.items()))

        # BUG FIX #1 (guard): correct Telegram HMAC chain
        # Step 1: secret = HMAC-SHA256(key="WebAppData", msg=bot_token)
        # Step 2: hash   = HMAC-SHA256(key=secret,       msg=data_check_string)
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        computed_hash = hmac.new(secret_key, sorted_pairs.encode(), hashlib.sha256).hexdigest()

        if computed_hash != signature:
            logger.warning("validate_init_data: signature mismatch")
            return None

        # BUG FIX #5: return None (falsy) on empty data, not empty dict
        return query_data if query_data else None
    except Exception as e:
        logger.error(f"Init data validation failed: {e}")
        return None


@web.middleware
async def cors_middleware(request: web.Request, handler) -> web.Response:
    """Add CORS headers. Handle OPTIONS preflight immediately to avoid auth blocking."""
    # BUG FIX #2: OPTIONS preflight must be answered before auth_middleware runs.
    # Previously, OPTIONS was passed to handler → auth_middleware → 401 → browser blocked all requests.
    if request.method == "OPTIONS":
        return web.Response(
            status=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Telegram-Init-Data",
                "Access-Control-Max-Age": "86400",
            },
        )
    response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Telegram-Init-Data"
    return response


@web.middleware
async def auth_middleware(request: web.Request, handler) -> web.Response:
    """Authenticate user via Telegram init_data."""
    
    # Public endpoints don't need auth
    if request.path in ["/health", "/metrics"]:
        return await handler(request)
    
    # Parse request body safely
    body = {}
    if request.method in {"POST", "PUT", "PATCH"}:
        try:
            body = await request.json()
        except Exception:
            body = {}
    
    # Multi-source initData extraction
    init_data = (
        body.get("initData")
        or request.query.get("initData")
        or (request.headers.get("Authorization") or "").replace("Bearer ", "")
        or request.headers.get("X-Telegram-Init-Data")
    )
    
    if not init_data:
        return web.json_response({"error": "Missing auth"}, status=401)
    
    # Validate signature
    user_data = validate_init_data(init_data, BOT_TOKEN)
    if not user_data:
        return web.json_response({"error": "Invalid auth"}, status=401)
    
    # Extract user info
    try:
        telegram_user = json.loads(user_data.get("user", "{}"))
        user_id = telegram_user.get("id")
        
        if not user_id or int(user_id) not in ADMIN_ID_SET:
            # Non-admin: validate timestamp
            auth_date = int(user_data.get("auth_date", 0))
            if datetime.now().timestamp() - auth_date > 86400:
                return web.json_response({"error": "Auth expired"}, status=401)
        
        # Ensure user in DB
        username = telegram_user.get("username", "")
        referred_by = request.query.get("ref")
        if referred_by:
            try:
                referred_by = int(referred_by)
            except ValueError:
                referred_by = None
        
        await ensure_user(user_id, username, referred_by)
        
        # Store in request for handler
        request["user_id"] = user_id
        request["telegram_user"] = telegram_user
        request["_body_dict"] = body
        
        return await handler(request)
    
    except Exception as e:
        logger.error(f"Auth middleware error: {e}")
        return web.json_response({"error": "Auth error"}, status=401)


# ============================================================================
# 10. TELEGRAM BOT HANDLERS
# ============================================================================

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🎮 Play ScreamCase",
            web_app=WebAppInfo(url=f"{WEBAPP_URL}?ref={message.from_user.id}")
        )]
    ])
    await message.answer(
        f"Welcome to ScreamCase! 🎉\n\n"
        f"Open cases and collect gifts using your stars!\n\n"
        f"Your ID: {message.from_user.id}",
        reply_markup=keyboard
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command."""
    help_text = """
ScreamCase Commands:
/start - Open the app
/help - This message
/profile - Your profile
/+ <amount> - Get stars (admin only)
/create_promo <code> <stars> <hours> <max_uses> - Create promo
    """
    await message.answer(help_text)


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    """Handle /profile command."""
    if not supabase:
        await message.answer("Database not configured")
        return
    
    user = await get_user(message.from_user.id)
    if user:
        stars = user.get("stars", 0)
        referrals = await count_user_referrals(message.from_user.id)
        await message.answer(
            f"👤 Profile\n"
            f"⭐ Stars: {stars}\n"
            f"👥 Referrals: {referrals}"
        )
    else:
        await message.answer("User not found")


@router.message(F.text.startswith("/+"))
async def cmd_add_stars(message: Message):
    """Admin command: add stars to user."""
    if message.from_user.id not in ADMIN_ID_SET:
        await message.answer("Admin only")
        return
    
    if not supabase:
        await message.answer("Database not configured")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("Usage: /+ <amount> or /+ <user_id> <amount>")
            return
        
        if len(parts) == 2:
            amount = int(parts[1])
            user_id = message.from_user.id
        else:
            user_id = int(parts[1])
            amount = int(parts[2])
        
        await update_balance(user_id, amount, "add")
        await message.answer(f"✅ Added {amount} stars to user {user_id}")
    except Exception as e:
        logger.error(f"Error adding stars: {e}")
        await message.answer(f"Error: {e}")


@router.message(F.text.startswith("/create_promo"))
async def cmd_create_promo(message: Message):
    """Admin command: create promo code."""
    if message.from_user.id not in ADMIN_ID_SET:
        await message.answer("Admin only")
        return
    
    if not supabase:
        await message.answer("Database not configured")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 5:
            await message.answer("Usage: /create_promo <code> <stars> <hours> <max_uses>")
            return
        
        code = parts[1].upper()
        stars = int(parts[2])
        hours = int(parts[3])
        max_uses = int(parts[4])
        
        await create_promo_record(code, stars, hours, max_uses)
        await message.answer(f"✅ Promo created: {code}")
    except Exception as e:
        logger.error(f"Error creating promo: {e}")
        await message.answer(f"Error: {e}")


# ============================================================================
# 11. HTTP SERVER SETUP
# ============================================================================

async def init_db():
    """Initialize database schema (if needed)."""
    logger.info("Database initialized")


async def main():
    """Main server entry point."""
    if not BOT_TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
        logger.critical("Missing required environment variables")
        return
    
    # Initialize DB
    await init_db()
    
    # Create web app
    app = web.Application(middlewares=[cors_middleware, auth_middleware])
    
    # Add routes
    # ── Case opening ──────────────────────────────────────────────────────────
    app.router.add_post("/api/open_case", api_open_case)

    # ── Cases list (BUG FIX #4: was missing → 404 on frontend load) ──────────
    app.router.add_get("/api/cases", api_get_cases)

    # ── User profile + balance (BUG FIX #4: was missing → frontend can't show stars) ──
    app.router.add_get("/api/user", api_get_user)

    # ── Promo codes ───────────────────────────────────────────────────────────
    app.router.add_post("/api/activate_promo", api_activate_promo)

    # ── Tasks / Quests ────────────────────────────────────────────────────────
    app.router.add_get("/api/tasks", api_get_tasks)
    app.router.add_post("/api/claim_task", api_claim_task)

    # ── Inventory (BUG FIX #3: was asyncio.run() inside async context → RuntimeError 500) ──
    app.router.add_get("/api/inventory", api_get_inventory)

    # ── Health check (no auth required) ──────────────────────────────────────
    app.router.add_get("/health", lambda r: web.json_response({"status": "ok"}))

    # ── OPTIONS preflight catch-all (BUG FIX #2 redundant guard) ─────────────
    app.router.add_route("OPTIONS", "/{path_info:.*}", lambda r: web.Response(
        status=204,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Telegram-Init-Data",
        },
    ))
    
    # Start HTTP server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8000)
    await site.start()
    logger.info("HTTP server started on 0.0.0.0:8000")
    
    # Start Telegram bot
    if bot:
        dp = Dispatcher()
        dp.include_router(router)
        
        try:
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        except Exception as e:
            logger.error(f"Bot polling error: {e}")
    
    # Keep alive
    try:
        await asyncio.sleep(float("inf"))
    except KeyboardInterrupt:
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)