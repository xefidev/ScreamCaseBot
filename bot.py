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
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Message, WebAppInfo
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
    logger.critical("Supabase URL/key is missing")
    sys.exit(1)

ROOT_ADMIN_ID = 7782281997
SECOND_ADMIN_ID = 5396975347
ADMIN_BYPASS_IDS = {ROOT_ADMIN_ID, SECOND_ADMIN_ID}
ADMIN_IDS = [ROOT_ADMIN_ID, SECOND_ADMIN_ID]

for env_name in ("ADMIN_IDS", "VITE_ADMIN_IDS"):
    env_admins = os.getenv(env_name, "")
    if env_admins:
        for value in env_admins.split(","):
            value = value.strip()
            if value.isdigit():
                ADMIN_IDS.append(int(value))
ADMIN_IDS = list(dict.fromkeys(ADMIN_IDS))

APP_URL = os.getenv("APP_URL", "https://scream-case-bot.vercel.app")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/ScreamCase")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@ScreamCase")
PORT = int(os.getenv("PORT", "8080"))
KEEP_ALIVE_URL = os.getenv("KEEP_ALIVE_URL", "")
TON_WALLET = os.getenv("TON_WALLET") or os.getenv("VITE_TON_WALLET", "")
TONCENTER_API_KEY = os.getenv("TONCENTER_API_KEY", "")
TONCENTER_BASE_URL = os.getenv("TONCENTER_BASE_URL", "https://toncenter.com/api/v2")
TON_STARS_RATE = int(os.getenv("TON_STARS_RATE", "100"))
INVENTORY_TABLE = os.getenv("INVENTORY_TABLE", "user_inventory")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()


CASE_PRICES: dict[int, int] = {
    1: 0,
    2: 0,
    3: 15,
    4: 25,
    5: 5,
    6: 10,
    7: 50,
    8: 100,
    9: 75,
    10: 150,
}

CASE_RANGES: dict[int, dict[str, int]] = {
    1: {"min": 15, "max": 500},
    2: {"min": 0, "max": 100},
    3: {"min": 100, "max": 667},
    4: {"min": 200, "max": 599},
    5: {"min": 0, "max": 199},
    6: {"min": 0, "max": 50},
    7: {"min": 0, "max": 599},
    8: {"min": 100, "max": 444},
    9: {"min": 50, "max": 222},
    10: {"min": 100, "max": 250},
}

GIFTS: list[dict[str, Any]] = [
    {"price": 15, "name": "Bear", "image": "/asset/Gifts/15S_Bear_Original_Bear.webp"},
    {"price": 25, "name": "Rosae", "image": "/asset/Gifts/25S_Rosae_Original_Rosae.webp"},
    {"price": 40, "name": "Lol Pops", "image": "/asset/Gifts/40S_Lol_Pops_Original_Lol_Pops.webp"},
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


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


def is_admin(user_id: int | None) -> bool:
    return user_id is not None and int(user_id) in ADMIN_IDS


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


def extract_bearer_init_data(request: web.Request) -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.removeprefix("Bearer ").strip()
    return request.headers.get("X-Telegram-Init-Data")


def validate_init_data(init_data: str | None) -> dict[str, Any] | None:
    values = parse_init_data(init_data)
    user = parse_user_from_init_data(init_data)
    if not values or not user:
        return None

    user_id = parse_int(user.get("id"))
    if user_id in ADMIN_BYPASS_IDS:
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


def admin_id_from_unverified_request(request: web.Request, body: dict[str, Any]) -> int | None:
    candidates = [
        body.get("user_id"),
        body.get("id"),
        request.query.get("user_id"),
        request.query.get("id"),
        request.headers.get("X-User-Id"),
        request.headers.get("X-Telegram-User-Id"),
    ]
    for candidate in candidates:
        user_id = parse_int(candidate)
        if user_id in ADMIN_BYPASS_IDS:
            return user_id
    return None


@web.middleware
async def cors_middleware(request: web.Request, handler: Any) -> web.StreamResponse:
    if request.method == "OPTIONS":
        response = web.Response(status=204)
    else:
        response = await handler(request)

    response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Telegram-Init-Data, X-User-Id, X-Telegram-User-Id"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@web.middleware
async def auth_middleware(request: web.Request, handler: Any) -> web.StreamResponse:
    if not request.path.startswith("/api/"):
        return await handler(request)

    body = await read_json(request) if request.method in {"POST", "PUT", "PATCH"} else {}
    init_data = body.get("initData") or request.query.get("initData") or extract_bearer_init_data(request)
    telegram_user = validate_init_data(init_data)

    if telegram_user:
        request["telegram_user"] = telegram_user
        request["user_id"] = int(telegram_user["id"])
        return await handler(request)

    admin_id = admin_id_from_unverified_request(request, body)
    if admin_id in ADMIN_BYPASS_IDS:
        request["telegram_user"] = {"id": admin_id, "username": "admin"}
        request["user_id"] = admin_id
        return await handler(request)

    return web.json_response({"error": "Вы не авторизованы"}, status=401)


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
            except Exception as exc:
                logger.debug("Username update failed for %s: %s", user_id, exc)
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
    checks = [
        ("users", supabase.table("users").select("id", count="exact").limit(1)),
        ("promo_codes", supabase.table("promo_codes").select("code", count="exact").limit(1)),
        ("promo_uses", supabase.table("promo_uses").select("id", count="exact").limit(1)),
        ("user_deposits", supabase.table("user_deposits").select("id", count="exact").limit(1)),
    ]
    for table_name, query in checks:
        try:
            await execute(query)
            logger.info("Supabase table verified: %s", table_name)
        except Exception as exc:
            logger.error("Supabase table check failed for %s: %s", table_name, exc)


def normalize_asset_path(value: Any) -> str:
    if not value:
        return "/asset/Gifts/default.webp"
    filename = str(value).replace("\\", "/").split("/")[-1]
    if not filename or "." not in filename:
        return "/asset/Gifts/default.webp"
    return f"/asset/Gifts/{filename}"


def limit_to_int(value: Any) -> int:
    if value is None:
        return -1
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


def normalize_case_row(row: dict[str, Any]) -> dict[str, Any]:
    case_row = dict(row)
    raw_case_id = case_row.get("id") or case_row.get("case_id")
    case_id = parse_int(raw_case_id)
    name = str(case_row.get("name") or case_row.get("title") or "").lower()

    case_row["remaining_limit"] = limit_to_int(case_row.get("remaining_limit"))
    case_row["total_limit"] = limit_to_int(case_row.get("total_limit"))

    if case_id == 1 or "promo" in name:
        promo_asset = "/asset/Gifts/5000S_Case_Original_Case.webp"
        case_row["asset"] = promo_asset
        case_row["asset_url"] = promo_asset
        case_row["image"] = promo_asset
        case_row["image_url"] = promo_asset
    else:
        for key in ("asset", "asset_url", "image", "image_url"):
            if key in case_row:
                case_row[key] = normalize_asset_path(case_row[key])

    return case_row


async def get_case_row(case_id: int) -> dict[str, Any] | None:
    try:
        result = await execute(supabase.table("cases").select("*").eq("id", int(case_id)).limit(1))
        if result.data:
            return normalize_case_row(result.data[0])
    except Exception as exc:
        logger.debug("Case row lookup failed for %s: %s", case_id, exc)
    return None


async def get_case_price(case_id: int) -> int:
    case_row = await get_case_row(case_id)
    if case_row:
        for field in ("price", "stars_price", "cost", "open_price"):
            price = parse_int(case_row.get(field))
            if price is not None:
                return max(0, price)
    return int(CASE_PRICES.get(int(case_id), 0))


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


async def consume_case_limit(case_id: int) -> bool:
    result = await execute(supabase.rpc("consume_case_limit", {"p_case_id": int(case_id)}))
    data = result.data

    if isinstance(data, bool):
        return data
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, bool):
            return first
        if isinstance(first, dict) and False in first.values():
            return False
    if isinstance(data, dict) and False in data.values():
        return False
    return data is not False


async def add_inventory_item(user_id: int, item: dict[str, Any], case_id: int, promo_code: str | None) -> None:
    base_payload = {
        "user_id": int(user_id),
        "case_id": int(case_id),
        "name": item.get("name"),
        "image": normalize_asset_path(item.get("image")),
        "price": int(item.get("price") or 0),
        "promo_code": promo_code,
        "created_at": iso_now(),
    }
    fallback_payload = {
        "user_id": int(user_id),
        "item_name": item.get("name"),
        "item_image": normalize_asset_path(item.get("image")),
        "item_price": int(item.get("price") or 0),
        "created_at": iso_now(),
    }

    for payload in (base_payload, fallback_payload):
        try:
            await execute(supabase.table(INVENTORY_TABLE).insert(payload))
            return
        except Exception as exc:
            logger.debug("Inventory insert attempt failed: %s", exc)


async def get_valid_promo_code(code: str) -> dict[str, Any] | None:
    result = await execute(
        supabase.table("promo_codes")
        .select("code, expires_at, reward_stars, is_active")
        .eq("code", code)
        .eq("is_active", True)
        .gt("expires_at", iso_now())
        .limit(1)
    )
    return result.data[0] if result.data else None


async def check_toncenter_once(session: aiohttp.ClientSession) -> None:
    if not TONCENTER_API_KEY or not TON_WALLET:
        return

    headers = {"X-API-Key": TONCENTER_API_KEY}
    params = {"address": TON_WALLET, "limit": 1}
    async with session.get(f"{TONCENTER_BASE_URL}/getTransactions", headers=headers, params=params) as response:
        if response.status == 401:
            logger.warning("Toncenter API returned 401 Unauthorized")
            return
        if response.status >= 400:
            logger.warning("Toncenter API returned %s", response.status)
            return
        await response.json()


async def toncenter_monitor() -> None:
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        while True:
            try:
                await check_toncenter_once(session)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.debug("Toncenter monitor iteration failed: %s", exc)
            await asyncio.sleep(300)


async def keep_alive_task() -> None:
    if not KEEP_ALIVE_URL:
        return

    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        while True:
            try:
                await asyncio.sleep(600)
                async with session.get(KEEP_ALIVE_URL) as response:
                    logger.info("Keep-alive status: %s", response.status)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.debug("Keep-alive failed: %s", exc)


@router.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject) -> None:
    if not message.from_user:
        return

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
    text = "Команды:\n/start - открыть приложение\n/help - помощь"
    if message.from_user and is_admin(message.from_user.id):
        text += (
            "\n\nАдмин:"
            "\n/create_promo CODE REWARD_STARS DURATION_HOURS"
            "\n/+ USER_ID AMOUNT"
            "\n/+ AMOUNT в reply"
            "\n/stats"
        )
    await message.answer(text)


@router.message(Command("create_promo"))
async def cmd_create_promo(message: Message) -> None:
    if not message.from_user or int(message.from_user.id) != ROOT_ADMIN_ID:
        await message.answer("❌ Недостаточно прав.")
        return

    parts = (message.text or "").split(maxsplit=3)
    if len(parts) != 4:
        await message.answer("❌ Формат: /create_promo CODE REWARD_STARS DURATION_HOURS")
        return

    code = parts[1].strip()
    reward = parse_positive_int(parts[2])
    duration_hours = parse_positive_int(parts[3])
    if not code or reward is None or duration_hours is None:
        await message.answer("❌ Проверьте CODE, REWARD_STARS и DURATION_HOURS.")
        return

    expires_at = (utc_now() + timedelta(hours=duration_hours)).isoformat()
    try:
        await execute(
            supabase.table("promo_codes").upsert(
                {
                    "code": code,
                    "expires_at": expires_at,
                    "reward_stars": int(reward),
                    "is_active": True,
                },
                on_conflict="code",
            )
        )
    except Exception as exc:
        logger.exception("Promo creation failed")
        await message.answer(f"❌ Ошибка БД: {exc}")
        return

    await message.answer(f"✅ Промокод {code} создан: +{reward} ⭐, срок {duration_hours} ч.")


@router.message(F.text.regexp(r"^\/\+\s*(?:(\d+)\s+)?(\d+)"))
async def cmd_add_stars(message: Message) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        await message.answer("❌ Недостаточно прав.")
        return

    match = re.match(r"^\/\+\s*(?:(\d+)\s+)?(\d+)", message.text or "")
    if not match:
        await message.answer("❌ Формат: /+ USER_ID AMOUNT или /+ AMOUNT в reply.")
        return

    target_raw, amount_raw = match.groups()
    amount = int(amount_raw)
    if target_raw:
        target_user_id = int(target_raw)
    elif message.reply_to_message and message.reply_to_message.from_user:
        target_user_id = int(message.reply_to_message.from_user.id)
    else:
        target_user_id = int(message.from_user.id)

    try:
        await ensure_user(target_user_id)
        await update_balance(target_user_id, amount, "add")
    except Exception as exc:
        await message.answer(f"❌ Ошибка БД: {exc}")
        return

    await message.answer(f"✅ Добавлено {amount} ⭐ пользователю {target_user_id}")


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        await message.answer("❌ Недостаточно прав.")
        return

    try:
        users = await execute(supabase.table("users").select("id, stars", count="exact").limit(1000))
        deposits = await execute(supabase.table("user_deposits").select("amount").limit(1000))
        total_users = int(users.count or len(users.data or []))
        total_stars = sum(int(row.get("stars") or 0) for row in (users.data or []))
        total_deposits = sum(int(row.get("amount") or 0) for row in (deposits.data or []))
    except Exception as exc:
        await message.answer(f"❌ Ошибка БД: {exc}")
        return

    await message.answer(
        f"📊 Статистика\nПользователей: {total_users}\nЗвёзд на балансах: {total_stars}\nДепозитов: {total_deposits} ⭐"
    )


@router.pre_checkout_query()
async def pre_checkout(query: types.PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message) -> None:
    if not message.successful_payment:
        return

    payload = message.successful_payment.invoice_payload
    parts = payload.split("_")
    if len(parts) != 3 or parts[0] != "stars" or not parts[1].isdigit() or not parts[2].isdigit():
        await message.answer("❌ Некорректный payload платежа.")
        return

    user_id = int(parts[1])
    amount = int(parts[2])
    if not message.from_user or int(message.from_user.id) != user_id:
        await message.answer("❌ Пользователь платежа не совпадает.")
        return

    try:
        await ensure_user(user_id, username=message.from_user.username)
        await update_balance(user_id, amount, "add")
        await insert_deposit(user_id, amount)
    except Exception as exc:
        logger.exception("Payment processing failed")
        await message.answer(f"❌ Платёж получен, но произошла ошибка БД: {exc}")
        return

    await message.answer(f"✅ Оплата прошла! Баланс пополнен на {amount} ⭐")


async def root_handler(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "service": "ScreamCase"})


async def api_heartbeat(request: web.Request) -> web.Response:
    return web.json_response({"status": "alive", "timestamp": iso_now()})


async def api_check_sub(request: web.Request) -> web.Response:
    user_id = int(request["user_id"])
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        is_subscribed = member.status in {"member", "administrator", "creator"}
    except Exception:
        is_subscribed = False
    return web.json_response({"is_subscribed": is_subscribed})


async def api_balance(request: web.Request) -> web.Response:
    user_id = int(request["user_id"])
    telegram_user = request.get("telegram_user") or {}
    user = await ensure_user(user_id, username=telegram_user.get("username"))
    return web.json_response({"stars": int(user.get("stars") or 0)})


async def api_invoice(request: web.Request) -> web.Response:
    user_id = int(request["user_id"])
    body = await read_json(request)
    amount = parse_positive_int(body.get("amount"))
    if amount is None:
        return web.json_response({"error": "Некорректная сумма"}, status=400)

    telegram_user = request.get("telegram_user") or {}
    await ensure_user(user_id, username=telegram_user.get("username"))
    try:
        invoice_url = await bot.create_invoice_link(
            title="Пополнение ScreamCase",
            description=f"Покупка {amount} звёзд",
            payload=f"stars_{user_id}_{amount}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Telegram Stars", amount=int(amount))],
        )
    except Exception as exc:
        logger.exception("Invoice creation failed")
        return web.json_response({"error": f"Ошибка Telegram API: {exc}"}, status=500)

    return web.json_response({"invoice_url": invoice_url, "url": invoice_url, "link": invoice_url})


async def api_claim_promo(request: web.Request) -> web.Response:
    user_id = int(request["user_id"])
    body = await read_json(request)
    code = str(body.get("code") or "").strip()
    if not code:
        return web.json_response({"error": "Введите промокод"}, status=400)

    promo = await get_valid_promo_code(code)
    if not promo:
        return web.json_response({"error": "Неверный или истекший промокод"}, status=400)

    used = await execute(
        supabase.table("promo_uses")
        .select("id")
        .eq("user_id", user_id)
        .eq("code", code)
        .limit(1)
    )
    if used.data:
        return web.json_response({"error": "Вы уже активировали этот промокод"}, status=400)

    if code == "Im GAY":
        deposited = await deposits_sum_last_24h(user_id)
        if deposited < 50:
            return web.json_response(
                {"error": "Для активации этого промокода необходимо пополнить баланс минимум на 50 звёзд за последние 24 часа"},
                status=403,
            )

    reward = int(promo.get("reward_stars") or 0)
    try:
        telegram_user = request.get("telegram_user") or {}
        await ensure_user(user_id, username=telegram_user.get("username"))
        await update_balance(user_id, reward, "add")
        await execute(supabase.table("promo_uses").insert({"user_id": user_id, "code": code}))
    except Exception as exc:
        logger.exception("Promo claim failed")
        return web.json_response({"error": f"Ошибка БД: {exc}"}, status=500)

    return web.json_response({"success": True, "reward": reward})


async def api_cases(request: web.Request) -> web.Response:
    try:
        result = await execute(supabase.table("cases").select("*"))
        cases = [normalize_case_row(row) for row in (result.data or [])]
    except Exception as exc:
        logger.exception("Cases query failed")
        return web.json_response({"error": f"Ошибка БД: {exc}"}, status=500)

    return web.json_response(cases)


async def api_open_case(request: web.Request) -> web.Response:
    user_id = int(request["user_id"])
    body = await read_json(request)
    case_id = parse_positive_int(body.get("case_id"))
    promo_code = str(body.get("promo_code") or "").strip() or None

    if case_id is None:
        return web.json_response({"error": "Некорректный кейс"}, status=400)

    telegram_user = request.get("telegram_user") or {}
    user = await ensure_user(user_id, username=telegram_user.get("username"))

    use_promo_pass = False
    if promo_code:
        promo = await get_valid_promo_code(promo_code)
        if not promo:
            return web.json_response({"error": "Неверный или истекший промокод"}, status=400)

        deposited = await deposits_sum_last_24h(user_id)
        if deposited < 50:
            return web.json_response(
                {"error": "Для открытия кейса по этому промокоду необходимо пополнить баланс минимум на 50 звёзд за последние 24 часа"},
                status=403,
            )
        use_promo_pass = True

    price = await get_case_price(case_id)
    if not use_promo_pass and int(user.get("stars") or 0) < price:
        return web.json_response({"error": "Недостаточно звёзд"}, status=403)

    try:
        available = await consume_case_limit(case_id)
    except Exception as exc:
        logger.exception("consume_case_limit failed")
        return web.json_response({"error": f"Ошибка лимита кейса: {exc}"}, status=500)

    if not available:
        return web.json_response({"error": "Кейсы этого типа закончились"}, status=400)

    if not use_promo_pass and price > 0:
        try:
            await update_balance(user_id, -price, "add")
        except Exception as exc:
            return web.json_response({"error": str(exc)}, status=403)

    item = random_gift(case_id)
    await add_inventory_item(user_id, item, case_id, promo_code)

    return web.json_response(
        {
            "success": True,
            "item": item,
            "deducted": 0 if use_promo_pass else price,
            "promo_used": bool(use_promo_pass),
        }
    )


async def api_referrals(request: web.Request) -> web.Response:
    user_id = int(request["user_id"])
    result = await execute(
        supabase.table("users")
        .select("id, username, join_date")
        .eq("referred_by", user_id)
    )
    referrals = result.data or []
    return web.json_response({"count": len(referrals), "referrals": referrals})


async def api_tasks(request: web.Request) -> web.Response:
    return web.json_response([])


async def api_verify_task(request: web.Request) -> web.Response:
    return web.json_response({"error": "task_not_found"}, status=404)


async def api_ton_invoice(request: web.Request) -> web.Response:
    user_id = int(request["user_id"])
    random_part = random.randint(100000, 999999)
    return web.json_response(
        {
            "wallet": TON_WALLET,
            "comment": f"SC_{user_id}_{random_part}",
            "rate": TON_STARS_RATE,
        }
    )


async def api_ton_success(request: web.Request) -> web.Response:
    return web.json_response({"success": True, "message": "TON verification is handled in background."})


async def start_background_tasks(app: web.Application) -> None:
    app["toncenter_monitor"] = asyncio.create_task(toncenter_monitor())
    app["keep_alive"] = asyncio.create_task(keep_alive_task())


async def cleanup_background_tasks(app: web.Application) -> None:
    tasks = [app.get("toncenter_monitor"), app.get("keep_alive")]
    tasks = [task for task in tasks if task is not None]
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


def setup_routes(app: web.Application) -> None:
    app.router.add_get("/", root_handler)
    app.router.add_post("/api/heartbeat", api_heartbeat)
    app.router.add_get("/api/check_sub", api_check_sub)
    app.router.add_get("/api/balance", api_balance)
    app.router.add_post("/api/invoice", api_invoice)
    app.router.add_post("/api/create_invoice", api_invoice)
    app.router.add_post("/api/claim_promo", api_claim_promo)
    app.router.add_get("/api/cases", api_cases)
    app.router.add_post("/api/open_case", api_open_case)
    app.router.add_get("/api/referrals", api_referrals)
    app.router.add_get("/api/tasks", api_tasks)
    app.router.add_post("/api/tasks/verify", api_verify_task)
    app.router.add_post("/api/ton_invoice", api_ton_invoice)
    app.router.add_post("/api/ton_success", api_ton_success)


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
    logger.info("aiohttp API started on port %s", PORT)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Telegram polling started")
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
