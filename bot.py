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

# 1. ADMIN CONFIGURATION
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
    sys.exit(1)

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.critical("SUPABASE_URL/VITE_SUPABASE_URL or SUPABASE key is missing")
    sys.exit(1)

APP_URL = os.getenv("APP_URL", "https://scream-case-bot.vercel.app")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/ScreamCase")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@ScreamCase")
PORT = int(os.getenv("PORT", "8080"))
INVENTORY_TABLE = os.getenv("INVENTORY_TABLE", "user_inventory")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

# STATIC DATA
STATIC_CASES: list[dict[str, Any]] = [
    {"id": 1, "name": "Promo Case", "price": 0, "image": "/asset/Gifts/5000S_Case_Original_Case.webp"},
    {"id": 2, "name": "Daily Case", "price": 1, "image": "/asset/Gifts/100S_Red_Star_Original_Red_Star.webp"},
    {"id": 3, "name": "Snoop Case", "price": 667, "image": "/asset/Gifts/1188S_Snoop_Cigar_Original_Snoop_Cigar.webp"},
    {"id": 4, "name": "Lover's Case", "price": 599, "image": "/asset/Gifts/2S_I_love_you_Original_I_love_you.webp"},
    {"id": 5, "name": "Hobo Case", "price": 199, "image": "/asset/Gifts/370S_Instant_Ramen_Original_Instant_Ramen.webp"},
    {"id": 6, "name": "Risky Box", "price": 50, "image": "/asset/Gifts/800S_Evil_Eye_Original_Evil_Eye.webp"},
    {"id": 7, "name": "Scam Box", "price": 111, "image": "/asset/Gifts/850S_Trojan_Horse_Original_Trojan_Horse.webp"},
    {"id": 8, "name": "Ebati Case", "price": 444, "image": "/asset/Gifts/7942S_Diamond_Ring_Original_Diamond_Ring.webp"},
    {"id": 9, "name": "Pussy Case", "price": 222, "image": "/asset/Gifts/3579S_Pink_Bear_Original_Pink_Bear.webp"},
    {"id": 10, "name": "Skolnik Case", "price": 250, "image": "/asset/Gifts/2500S_Pen_Original_Pen.webp"},
]

CASE_RANGES: dict[int, dict[str, int]] = {
    1: {"min": 15, "max": 600},
    2: {"min": 1, "max": 500},
    3: {"min": 15, "max": 2000},
    4: {"min": 15, "max": 1500},
    5: {"min": 15, "max": 400},
    6: {"min": 15, "max": 250},
    7: {"min": 15, "max": 300},
    8: {"min": 15, "max": 1000},
    9: {"min": 15, "max": 500},
    10: {"min": 15, "max": 600},
}

GIFTS: list[dict[str, Any]] = [
    {"price": 15, "name": "Bear", "image": "/asset/Gifts/15S_Bear_Original_Bear.webp"},
    {"price": 25, "name": "Rosae", "image": "/asset/Gifts/25S_Rosae_Original_Rosae.webp"},
    {"price": 50, "name": "Cake", "image": "/asset/Gifts/50S_Cake_Original_Cake.webp"},
    {"price": 50, "name": "May Bear", "image": "/asset/Gifts/50S_May_Bear_Original_May_Bear.webp"},
    {"price": 100, "name": "Flowers", "image": "/asset/Gifts/100S_Flowers_Original_Flowers.webp"},
    {"price": 300, "name": "Instant Ramens", "image": "/asset/Gifts/300S_Instant_Ramens_Original_Instant_Ramens.webp"},
    {"price": 320, "name": "Spring Baskets", "image": "/asset/Gifts/320S_Spring_Baskets_Original_Spring_Baskets.webp"},
    {"price": 330, "name": "Swag Bags", "image": "/asset/Gifts/330S_Swag_Bags_Original_Swag_Bags.webp"},
    {"price": 340, "name": "Winter Wreaths", "image": "/asset/Gifts/340S_Winter_Wreaths_Original_Winter_Wreaths.webp"},
    {"price": 350, "name": "Jester Hats", "image": "/asset/Gifts/350S_Jester_Hats_Original_Jester_Hats.webp"},
    {"price": 380, "name": "Hex Pots", "image": "/asset/Gifts/380S_Hex_Pots_Original_Hex_Pots.webp"},
    {"price": 400, "name": "Easter Eggs", "image": "/asset/Gifts/400S_Easter_Eggs_Original_Easter_Eggs.webp"},
    {"price": 400, "name": "Pool Floats", "image": "/asset/Gifts/400S_Pool_Floats_Original_Pool_Floats.webp"},
    {"price": 400, "name": "Lol Pops", "image": "/asset/Gifts/40S_Lol_Pops_Original_Lol_Pops.webp"},
    {"price": 400, "name": "Restless Jars", "image": "/asset/Gifts/400S_Restless_Jars_Original_Restless_Jars.webp"},
    {"price": 400, "name": "Witch Hats", "image": "/asset/Gifts/400S_Witch_Hats_Original_Witch_Hats.webp"},
    {"price": 420, "name": "Magic Potions", "image": "/asset/Gifts/420S_Magic_Potions_Original_Magic_Potions.webp"},
    {"price": 420, "name": "Snoop Cigars", "image": "/asset/Gifts/420S_Snoop_Cigars_Original_Snoop_Cigars.webp"},
    {"price": 430, "name": "Desk Calendars", "image": "/asset/Gifts/430S_Desk_Calendars_Original_Desk_Calendars.webp"},
    {"price": 430, "name": "Love Potions", "image": "/asset/Gifts/430S_Love_Potions_Original_Love_Potions.webp"},
    {"price": 440, "name": "Fresh Socks", "image": "/asset/Gifts/440S_Fresh_Socks_Original_Fresh_Socks.webp"},
    {"price": 440, "name": "Westside Signs", "image": "/asset/Gifts/440S_Westside_Signs_Original_Westside_Signs.webp"},
    {"price": 450, "name": "Top Hats", "image": "/asset/Gifts/450S_Top_Hats_Original_Top_Hats.webp"},
    {"price": 480, "name": "Vice Creams", "image": "/asset/Gifts/480S_Vice_Creams_Original_Vice_Creams.webp"},
    {"price": 500, "name": "Ice Creams", "image": "/asset/Gifts/500S_Ice_Creams_Original_Ice_Creams.webp"},
    {"price": 500, "name": "Jolly Chimps", "image": "/asset/Gifts/500S_Jolly_Chimps_Original_Jolly_Chimps.webp"},
    {"price": 500, "name": "Sakura Flowers", "image": "/asset/Gifts/500S_Sakura_Flowers_Original_Sakura_Flowers.webp"},
    {"price": 500, "name": "Swiss Watches", "image": "/asset/Gifts/500S_Swiss_Watches_Original_Swiss_Watches.webp"},
    {"price": 510, "name": "Input Keys", "image": "/asset/Gifts/510S_Input_Keys_Original_Input_Keys.webp"},
    {"price": 550, "name": "Scared Cats", "image": "/asset/Gifts/550S_Scared_Cats_Original_Scared_Cats.webp"},
    {"price": 555, "name": "Clover Pins", "image": "/asset/Gifts/555S_Clover_Pins_Original_Clover_Pins.webp"},
    {"price": 600, "name": "Lush Bouquets", "image": "/asset/Gifts/600S_Lush_Bouquets_Original_Lush_Bouquets.webp"},
    {"price": 600, "name": "Victory Medals", "image": "/asset/Gifts/600S_Victory_Medals_Original_Victory_Medals.webp"},
    {"price": 605, "name": "Hypno Lollipops", "image": "/asset/Gifts/605S_Hypno_Lollipops_Original_Hypno_Lollipops.webp"},
    {"price": 650, "name": "Valentine Boxes", "image": "/asset/Gifts/650S_Valentine_Boxes_Original_Valentine_Boxes.webp"},
    {"price": 666, "name": "Voodoo Dolls", "image": "/asset/Gifts/666S_Voodoo_Dolls_Original_Voodoo_Dolls.webp"},
    {"price": 700, "name": "Heroic Helmets", "image": "/asset/Gifts/700S_Heroic_Helmets_Original_Heroic_Helmets.webp"},
    {"price": 705, "name": "Cookie Hearts", "image": "/asset/Gifts/705S_Cookie_Hearts_Original_Cookie_Hearts.webp"},
    {"price": 750, "name": "Moon Pendants", "image": "/asset/Gifts/750S_Moon_Pendants_Original_Moon_Pendants.webp"},
    {"price": 777, "name": "Trapped Hearts", "image": "/asset/Gifts/777S_Trapped_Hearts_Original_Trapped_Hearts.webp"},
    {"price": 800, "name": "Snake Boxes", "image": "/asset/Gifts/800S_Snake_Boxes_Original_Snake_Boxes.webp"},
    {"price": 850, "name": "Bunny Muffins", "image": "/asset/Gifts/850S_Bunny_Muffins_Original_Bunny_Muffins.webp"},
    {"price": 900, "name": "Bonded Rings", "image": "/asset/Gifts/900S_Bonded_Rings_Original_Bonded_Rings.webp"},
    {"price": 950, "name": "Crystal Balls", "image": "/asset/Gifts/950S_Crystal_Balls_Original_Crystal_Balls.webp"},
    {"price": 990, "name": "Vintage Cigars", "image": "/asset/Gifts/990S_Vintage_Cigars_Original_Vintage_Cigars.webp"},
    {"price": 1000, "name": "Artisan Bricks", "image": "/asset/Gifts/1000S_Artisan_Bricks_Original_Artisan_Bricks.webp"},
    {"price": 1100, "name": "Electric Skulls", "image": "/asset/Gifts/1100S_Electric_Skulls_Original_Electric_Skulls.webp"},
    {"price": 1200, "name": "Diamond Rings", "image": "/asset/Gifts/1200S_Diamond_Rings_Original_Diamond_Rings.webp"},
    {"price": 1300, "name": "Astral Shards", "image": "/asset/Gifts/1300S_Astral_Shards_Original_Astral_Shards.webp"},
    {"price": 1500, "name": "Santa Hats", "image": "/asset/Gifts/1500S_Santa_Hats_Original_Santa_Hats.webp"},
    {"price": 2000, "name": "Light Swords", "image": "/asset/Gifts/2000S_Light_Swords_Original_Light_Swords.webp"},
    {"price": 2500, "name": "Loot Bags", "image": "/asset/Gifts/2500S_Loot_Bags_Original_Loot_Bags.webp"},
    {"price": 3500, "name": "Money Pots", "image": "/asset/Gifts/3500S_Money_Pots_Original_Money_Pots.webp"},
    {"price": 5000, "name": "Genie Lamps", "image": "/asset/Gifts/5000S_Genie_Lamps_Original_Genie_Lamps.webp"},
    {"price": 7500, "name": "Low Riders", "image": "/asset/Gifts/7500S_Low_Riders_Original_Low_Riders.webp"},
    {"price": 12595, "name": "Nail Bracelets", "image": "/asset/Gifts/12595S_Nail_Bracelets_Original_Nail_Bracelets.webp"},
    {"price": 19047, "name": "Stellar Rockets", "image": "/asset/Gifts/19047S_Stellar_Rockets_Original_Stellar_Rockets.webp"},
]

CASE_RANGES: dict[int, dict[str, int]] = {
    1: {"min": 15, "max": 600},
    2: {"min": 1, "max": 500},
    3: {"min": 15, "max": 2000},
    4: {"min": 15, "max": 1500},
    5: {"min": 15, "max": 400},
    6: {"min": 15, "max": 250},
    7: {"min": 15, "max": 300},
    8: {"min": 15, "max": 1000},
    9: {"min": 15, "max": 500},
    10: {"min": 15, "max": 600},
}

# UTILS
def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def iso_now() -> str:
    return utc_now().isoformat()

def is_admin(user_id: int | None) -> bool:
    return user_id is not None and int(user_id) in ADMIN_ID_SET

def parse_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def parse_positive_int(value: Any) -> int | None:
    parsed = parse_int(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed

async def execute(query: Any) -> Any:
    return await asyncio.to_thread(query.execute)

async def read_json(request: web.Request) -> dict[str, Any]:
    if "json_body" in request:
        return request["json_body"]
    try:
        data = await request.json()
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    request["json_body"] = data
    return data

def parse_init_data(init_data: str | None) -> dict[str, str]:
    if not init_data:
        return {}
    try:
        return dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    except Exception:
        return {}

def parse_user_from_init_data(init_data: str | None) -> dict[str, Any] | None:
    values = parse_init_data(init_data)
    raw_user = values.get("user")
    if not raw_user:
        return None
    try:
        user = json.loads(raw_user)
    except Exception:
        return None
    if not isinstance(user, dict) or parse_int(user.get("id")) is None:
        return None
    return user

# 1. AUTH BYPASS FOR ADMINS
def validate_init_data(init_data: str | None) -> dict[str, Any] | None:
    if not init_data:
        return None

    # Железобетонный обход для админов: если строка содержит ID админа, сразу пускаем
    try:
        unquoted = urllib.parse.unquote(init_data)
        for aid in ADMIN_IDS:
            if str(aid) in unquoted:
                return {"id": aid, "username": "Admin"}
    except Exception:
        pass

    values = parse_init_data(init_data)
    user = parse_user_from_init_data(init_data)
    if not values or not user:
        return None

    user_id = parse_int(user.get("id"))
    if user_id in ADMIN_ID_SET:
        return user

    received_hash = values.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        return None
    return user

def extract_init_data(request: web.Request) -> str | None:
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        return authorization.removeprefix("Bearer ").strip()
    return request.headers.get("X-Telegram-Init-Data")

@web.middleware
async def cors_middleware(request: web.Request, handler: Any) -> web.StreamResponse:
    if request.method == "OPTIONS":
        response = web.Response(status=204)
    else:
        response = await handler(request)

    response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Telegram-Init-Data, X-User-Id"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

@web.middleware
async def auth_middleware(request: web.Request, handler: Any) -> web.StreamResponse:
    if not request.path.startswith("/api/"):
        return await handler(request)

    body = await read_json(request) if request.method in {"POST", "PUT", "PATCH"} else {}
    init_data = body.get("initData") or request.query.get("initData") or extract_init_data(request)
    
    telegram_user = validate_init_data(init_data)
    
    # Дополнительный резервный слой авторизации админа на случай локальных тестов
    if not telegram_user:
        uid_str = request.headers.get("X-User-Id") or request.query.get("user_id") or body.get("user_id")
        uid = parse_int(uid_str)
        if uid in ADMIN_ID_SET:
            telegram_user = {"id": uid, "username": "Admin"}

    if telegram_user:
        user_id = int(telegram_user["id"])
        request["telegram_user"] = telegram_user
        request["user_id"] = user_id
        return await handler(request)

    return web.json_response({"error": "Вы не авторизованы"}, status=401)

# DB HELPERS
async def get_user(user_id: int) -> dict[str, Any] | None:
    result = await execute(
        supabase.table("users")
        .select("id, stars, referred_by, username, join_date")
        .eq("id", int(user_id))
        .limit(1)
    )
    return result.data[0] if result.data else None

async def ensure_user(user_id: int, username: str | None = None, referred_by: int | None = None) -> dict[str, Any]:
    user_id = int(user_id)
    user = await get_user(user_id)
    if user:
        if username and username != user.get("username"):
            try:
                await execute(supabase.table("users").update({"username": username}).eq("id", user_id))
                user["username"] = username
            except Exception:
                pass
        return user

    payload = {
        "id": user_id,
        "stars": 0,
        "referred_by": referred_by,
        "username": username,
        "join_date": iso_now(),
    }
    await execute(supabase.table("users").insert(payload))
    return payload

async def update_balance(user_id: int, amount: int, mode: str = "add") -> int:
    user = await get_user(int(user_id))
    if not user:
        raise RuntimeError("Пользователь не найден")

    current_stars = int(user.get("stars") or 0)
    amount = int(amount)
    new_stars = current_stars + amount if mode == "add" else amount
    if new_stars < 0:
        raise RuntimeError("Недостаточно звёзд")

    await execute(supabase.table("users").update({"stars": new_stars}).eq("id", int(user_id)))
    return new_stars

async def insert_deposit(user_id: int, amount: int) -> None:
    await execute(
        supabase.table("user_deposits").insert(
            {"user_id": int(user_id), "amount": int(amount), "created_at": iso_now()}
        )
    )

async def deposits_sum_last_24h(user_id: int) -> int:
    since = (utc_now() - timedelta(hours=24)).isoformat()
    result = await execute(
        supabase.table("user_deposits")
        .select("amount")
        .eq("user_id", int(user_id))
        .gte("created_at", since)
    )
    return sum(int(row.get("amount") or 0) for row in (result.data or []))

async def init_db() -> None:
    tables = ["users", "promo_codes", "promo_uses", "user_deposits", INVENTORY_TABLE]
    for table in tables:
        try:
            await execute(supabase.table(table).select("id").limit(1))
            logger.info("Table %s verified", table)
        except Exception as e:
            logger.warning("Table %s check failed: %s", table, e)

# CASE OPENING LOGIC
def normalize_asset_path(value: Any) -> str:
    if not value:
        return "/asset/Gifts/default.webp"
    filename = str(value).replace("\\", "/").split("/")[-1]
    return f"/asset/Gifts/{filename}"

def get_case_price(case_id: int) -> int:
    for case_row in STATIC_CASES:
        if int(case_row["id"]) == int(case_id):
            return int(case_row.get("price") or 0)
    return 0

def random_gift(case_id: int) -> dict[str, Any]:
    case_range = CASE_RANGES.get(int(case_id), {"min": 0, "max": 100})
    pool = [gift for gift in GIFTS if case_range["min"] <= int(gift["price"]) <= case_range["max"]]
    if not pool:
        pool = GIFTS

    cheap = [gift for gift in pool if int(gift["price"]) <= 50]
    mid = [gift for gift in pool if 50 < int(gift["price"]) <= 150]
    expensive = [gift for gift in pool if int(gift["price"]) > 150]
    roll = random.random() * 100

    if roll < 85 and cheap:
        gift = random.choice(cheap)
    elif roll < 97 and mid:
        gift = random.choice(mid)
    elif expensive:
        gift = random.choice(expensive)
    else:
        gift = random.choice(pool)

    result = dict(gift)
    result["image"] = normalize_asset_path(result.get("image"))
    return result

async def consume_case_limit_rpc(case_id: int) -> bool:
    result = await execute(supabase.rpc("consume_case_limit", {"c_id": int(case_id)}))
    return bool(result.data)

async def add_inventory_item(user_id: int, item: dict[str, Any], case_id: int, promo_code: str | None) -> None:
    payload = {
        "user_id": int(user_id),
        "case_id": int(case_id),
        "item_name": item.get("name"),
        "item_image": item.get("image"),
        "item_price": int(item.get("price") or 0),
        "promo_code": promo_code,
        "created_at": iso_now(),
    }
    try:
        await execute(supabase.table(INVENTORY_TABLE).insert(payload))
    except Exception as e:
        logger.error("Inventory insert failed: %s", e)

# PROMO RECORD
async def create_promo_record(code: str, min_stars_24h: int, duration_hours: int) -> None:
    expires_at = (utc_now() + timedelta(hours=int(duration_hours))).isoformat()
    await execute(
        supabase.table("promo_codes").insert(
            {
                "code": code,
                "min_stars_donated_24h": int(min_stars_24h),
                "expires_at": expires_at,
                "reward_stars": 0,
                "is_active": True,
            }
        )
    )

# BOT HANDLERS
@router.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject) -> None:
    referred_by = None
    if command.args and command.args.isdigit():
        candidate = int(command.args)
        if candidate != int(message.from_user.id) and await get_user(candidate):
            referred_by = candidate

    user = await ensure_user(
        message.from_user.id,
        username=message.from_user.username,
        referred_by=referred_by,
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть ScreamCase", web_app=WebAppInfo(url=APP_URL))],
            [InlineKeyboardButton(text="Канал", url=CHANNEL_URL)],
        ]
    )
    await message.answer(f"Привет! Баланс: {int(user.get('stars') or 0)} ⭐", reply_markup=keyboard)

@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    help_text = (
        "ℹ️ **Доступные команды:**\n"
        "/start - Запустить бота и открыть Mini App\n"
        "/help - Показать список команд\n"
    )
    if message.from_user.id in ADMIN_ID_SET:
        help_text += (
            "\n👑 **Команды администратора:**\n"
            "/create_promo <code> <min_stars_24h> <hours> - Создать промокод\n"
            "/+ <amount> - Выдать звёзды (ответом на сообщение юзера)\n"
            "/+ <user_id> <amount> - Выдать звёзды по ID\n"
        )
    await message.answer(help_text, parse_mode="Markdown")

@router.message(F.text.startswith("/+"))
async def cmd_add_stars_shortcut(message: Message) -> None:
    if message.from_user.id not in ADMIN_ID_SET:
        return
    parts = message.text.split()
    if len(parts) == 2 and message.reply_to_message:
        amount = parse_int(parts[1])
        target_id = message.reply_to_message.from_user.id
    elif len(parts) == 3:
        target_id = parse_int(parts[1])
        amount = parse_int(parts[2])
    else:
        await message.answer("❌ Формат: `/+ <количество>` (ответом) или `/+ <user_id> <количество>`", parse_mode="Markdown")
        return
        
    if not target_id or amount is None:
        await message.answer("❌ Ошибка ввода параметров.")
        return
        
    try:
        await ensure_user(target_id)
        new_stars = await update_balance(target_id, amount, "add")
        await message.answer(f"✅ Зачислено {amount} ⭐. Текущий баланс пользователя: {new_stars} ⭐")
    except Exception as e:
        await message.answer(f"❌ Ошибка изменения баланса: {e}")

@router.message(Command("create_promo"))
async def cmd_create_promo(message: Message) -> None:
    if message.from_user.id not in ADMIN_ID_SET:
        return

    parts = message.text.split()
    if len(parts) != 4:
        await message.answer("❌ Формат: /create_promo <code> <min_stars_24h> <hours>")
        return

    code = parts[1]
    min_stars = parse_int(parts[2])
    hours = parse_int(parts[3])

    if min_stars is None or hours is None:
        await message.answer("❌ Некорректные параметры.")
        return

    try:
        await create_promo_record(code, min_stars, hours)
        await message.answer(f"✅ Промокод `{code}` создан на {hours}ч. (Мин. пополнение: {min_stars} ⭐)", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment(message: Message) -> None:
    payload = message.successful_payment.invoice_payload
    parts = payload.split("_")
    if len(parts) != 3 or parts[0] != "stars":
        return

    user_id = int(parts[1])
    amount = int(parts[2])
    
    await ensure_user(user_id, username=message.from_user.username)
    await update_balance(user_id, amount, "add")
    await insert_deposit(user_id, amount)
    await message.answer(f"✅ Оплата прошла! Баланс пополнен на {amount} ⭐")

# API HANDLERS
async def api_heartbeat(request: web.Request) -> web.Response:
    return web.json_response({"status": "alive", "timestamp": iso_now()})

async def api_balance(request: web.Request) -> web.Response:
    user_id = int(request["user_id"])
    user = await get_user(user_id)
    return web.json_response({"stars": int(user.get("stars") or 0) if user else 0})

async def api_cases(request: web.Request) -> web.Response:
    return web.json_response(STATIC_CASES)

async def api_open_case(request: web.Request) -> web.Response:
    user_id = int(request["user_id"])
    body = await read_json(request)
    case_id = parse_positive_int(body.get("case_id"))
    promo_code = str(body.get("promo_code") or "").strip() or None

    if case_id is None:
        return web.json_response({"error": "Некорректный кейс"}, status=400)

    if not await consume_case_limit_rpc(case_id):
        return web.json_response({"error": "Кейсы этого типа закончились"}, status=400)

    user = await get_user(user_id)
    use_promo = False

    if promo_code:
        res = await execute(
            supabase.table("promo_codes")
            .select("*")
            .eq("code", promo_code)
            .eq("is_active", True)
            .gt("expires_at", iso_now())
            .limit(1)
        )
        promo = res.data[0] if res.data else None
        if not promo:
            return web.json_response({"error": "Неверный или истекший промокод"}, status=400)

        res = await execute(
            supabase.table("promo_uses")
            .select("id")
            .eq("user_id", user_id)
            .eq("code", promo_code)
            .limit(1)
        )
        if res.data:
            return web.json_response({"error": "Вы уже активировали этот промокод"}, status=400)

        min_required = int(promo.get("min_stars_donated_24h") or 0)
        total_deposited = await deposits_sum_last_24h(user_id)
        if total_deposited < min_required:
            return web.json_response(
                {"error": f"Для открытия кейса по этому промокоду необходимо пополнить баланс минимум на {min_required} звёзд за последние 24 часа"},
                status=400
            )

        await execute(supabase.table("promo_uses").insert({"user_id": user_id, "code": promo_code}))
        use_promo = True

    price = get_case_price(case_id)
    if not use_promo:
        if int(user.get("stars") or 0) < price:
            return web.json_response({"error": "Недостаточно звёзд"}, status=400)
        await update_balance(user_id, -price, "add")

    item = random_gift(case_id)
    await add_inventory_item(user_id, item, case_id, promo_code)

    return web.json_response({"success": True, "item": item, "stars": await update_balance(user_id, 0, "add")})

# ЭНДПОИНТ КОЛЕСА ФОРТУНЫ
async def api_spin_wheel(request: web.Request) -> web.Response:
    user_id = int(request["user_id"])
    user = await get_user(user_id)
    if not user:
        return web.json_response({"error": "Пользователь не найден"}, status=404)
        
    current_stars = int(user.get("stars") or 0)
    cost = 20  # Стоимость одной прокрутки
    
    if current_stars < cost and user_id not in ADMIN_ID_SET:
        return web.json_response({"error": "Недостаточно звёзд для прокрутки колеса"}, status=400)
        
    if user_id not in ADMIN_ID_SET:
        current_stars = await update_balance(user_id, -cost, "add")
        
    # Сектора со скриншота: 25, 420, 500, 550, 600, 7500
    roll = random.random() * 100
    if roll < 1:
        win = 7500
    elif roll < 15:
        win = 600
    elif roll < 35:
        win = 550
    elif roll < 55:
        win = 500
    elif roll < 75:
        win = 420
    else:
        win = 25
        
    new_stars = await update_balance(user_id, win, "add")
    
    return web.json_response({
        "success": True,
        "reward": win,
        "stars": new_stars,
        "new_balance": new_stars,
        "item": {"name": f"{win} ⭐", "price": win, "image": "/asset/Gifts/100S_Red_Star_Original_Red_Star.webp"}
    })

async def api_admin_create_promo(request: web.Request) -> web.Response:
    if request["user_id"] not in ADMIN_ID_SET:
        return web.json_response({"error": "Forbidden"}, status=403)

    body = await read_json(request)
    code = body.get("code")
    min_stars = parse_int(body.get("min_stars_donated_24h"))
    hours = parse_int(body.get("duration_hours"))

    if not code or min_stars is None or hours is None:
        return web.json_response({"error": "Invalid payload"}, status=400)

    await create_promo_record(code, min_stars, hours)
    return web.json_response({"success": True})

async def api_invoice(request: web.Request) -> web.Response:
    user_id = int(request["user_id"])
    body = await read_json(request)
    amount = parse_positive_int(body.get("amount"))
    if not amount:
        return web.json_response({"error": "Invalid amount"}, status=400)

    invoice_url = await bot.create_invoice_link(
        title="Пополнение ScreamCase",
        description=f"Покупка {amount} звёзд",
        payload=f"stars_{user_id}_{amount}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Stars", amount=amount)],
    )
    return web.json_response({"invoice_url": invoice_url})

async def api_check_sub(request: web.Request) -> web.Response:
    user_id = int(request["user_id"])
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        is_subscribed = member.status in {"member", "administrator", "creator"}
    except Exception:
        is_subscribed = False
    return web.json_response({"is_subscribed": is_subscribed})

async def api_referrals(request: web.Request) -> web.Response:
    user_id = int(request["user_id"])
    result = await execute(supabase.table("users").select("id, username, join_date").eq("referred_by", user_id))
    referrals = result.data or []
    return web.json_response({"count": len(referrals), "referrals": referrals})

# 4. ANTI-SLEEP (Keep-Alive)
async def self_ping_loop() -> None:
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(APP_URL) as response:
                    logger.info("Self-ping status: %s", response.status)
        except Exception as e:
            logger.error("Self-ping error: %s", e)
        await asyncio.sleep(600)

async def start_background_tasks(app: web.Application) -> None:
    app["self_ping"] = asyncio.create_task(self_ping_loop())

async def cleanup_background_tasks(app: web.Application) -> None:
    task = app.get("self_ping")
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

def setup_routes(app: web.Application) -> None:
    app.router.add_get("/", lambda r: web.Response(text="ScreamCase API"))
    app.router.add_post("/api/heartbeat", api_heartbeat)
    app.router.add_get("/api/balance", api_balance)
    app.router.add_get("/api/cases", api_cases)
    app.router.add_post("/api/open_case", api_open_case)
    app.router.add_post("/api/invoice", api_invoice)
    app.router.add_post("/api/admin/create_promo", api_admin_create_promo)
    app.router.add_get("/api/check_sub", api_check_sub)
    app.router.add_get("/api/referrals", api_referrals)
    
    # Резервные роуты для колеса, чтобы перекрыть любые запросы с фронта
    app.router.add_post("/api/spin_wheel", api_spin_wheel)
    app.router.add_post("/api/wheel/spin", api_spin_wheel)
    app.router.add_post("/api/wheel", api_spin_wheel)
    app.router.add_post("/api/spin", api_spin_wheel)

async def main() -> None:
    await init_db()
    dp.include_router(router)
    
    app = web.Application(middlewares=[cors_middleware, auth_middleware])
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    setup_routes(app)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())