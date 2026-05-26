import os
import re
import sys
import json
import hmac
import hashlib
import asyncio
import logging
import random
import string
import urllib.parse
from datetime import datetime
from typing import Any

import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    WebAppInfo,
)
from dotenv import load_dotenv
from supabase import Client, create_client


load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("screamcase-bot")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_KEY")
    or os.getenv("VITE_SUPABASE_ANON_KEY")
)

if not TOKEN:
    logger.critical("TELEGRAM_BOT_TOKEN is not configured")
    sys.exit(1)

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.critical("Supabase credentials are not configured")
    sys.exit(1)

ADMIN_IDS = [7782281997]
env_admins = os.getenv("ADMIN_IDS", "")
if env_admins:
    for x in env_admins.split(","):
        if x.strip().isdigit():
            ADMIN_IDS.append(int(x.strip()))
ADMIN_IDS = list(dict.fromkeys(ADMIN_IDS))

APP_URL = os.getenv("APP_URL", "https://scream-case-bot.vercel.app")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/ScreamCase")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@ScreamCase")
PORT = int(os.getenv("PORT", "8080"))

TON_WALLET = os.getenv("VITE_TON_WALLET") or os.getenv("TON_WALLET", "")
TONCENTER_API_KEY = os.getenv("TONCENTER_API_KEY", "")
TONCENTER_BASE_URL = os.getenv("TONCENTER_BASE_URL", "https://toncenter.com/api/v2")
TON_STARS_RATE = int(os.getenv("TON_STARS_RATE", "100"))
KEEP_ALIVE_URL = os.getenv("KEEP_ALIVE_URL", "https://screamcasebot.onrender.com/")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()


CASES_PRICES: dict[int, int] = {
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

CASES_DATA: dict[int, dict[str, int]] = {
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

ALL_GIFTS: list[dict[str, Any]] = [
    {"price": 15, "name": "Bear", "image": "/asset/Gifts/15S_Bear_Original_Bear.webp"},
    {"price": 25, "name": "Rosae", "image": "/asset/Gifts/25S_Rosae_Original_Rosae.webp"},
    {"price": 40, "name": "Lol Pops", "image": "/asset/Gifts/40S_Lol_Pops_Original_Lol_Pops.webp"},
    {"price": 50, "name": "Cake", "image": "/asset/Gifts/50S_Cake_Original_Cake.webp"},
    {"price": 50, "name": "May Bear", "image": "/asset/Gifts/50S_May_Bear_Original_May_Bear.webp"},
    {"price": 100, "name": "Flowers", "image": "/asset/Gifts/100S_Flowers_Original_Flowers.webp"},
    {"price": 300, "name": "Instant Ramens", "image": "/asset/Gifts/300S_Instant_Ramens_Original_Instant_Ramens.webp"},
    {"price": 300, "name": "Xmas Stockings", "image": "/asset/Gifts/300S_Xmas_Stockings_Original_Xmas_Stockings.webp"},
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
    {"price": 800, "name": "Tama Gadgets", "image": "/asset/Gifts/800S_Tama_Gadgets_Original_Tama_Gadgets.webp"},
    {"price": 850, "name": "Bunny Muffins", "image": "/asset/Gifts/850S_Bunny_Muffins_Original_Bunny_Muffins.webp"},
    {"price": 880, "name": "Faith Amulets", "image": "/asset/Gifts/880S_Faith_Amulets_Original_Faith_Amulets.webp"},
    {"price": 900, "name": "Bonded Rings", "image": "/asset/Gifts/900S_Bonded_Rings_Original_Bonded_Rings.webp"},
    {"price": 900, "name": "Timeless Books", "image": "/asset/Gifts/900S_Timeless_Books_Original_Timeless_Books.webp"},
    {"price": 950, "name": "Crystal Balls", "image": "/asset/Gifts/950S_Crystal_Balls_Original_Crystal_Balls.webp"},
    {"price": 950, "name": "Hearth", "image": "/asset/Gifts/950S_Hearth_Original_Hearth.webp"},
    {"price": 950, "name": "Holiday Drinks", "image": "/asset/Gifts/950S_Holiday_Drinks_Original_Holiday_Drinks.webp"},
    {"price": 990, "name": "Vintage Cigars", "image": "/asset/Gifts/990S_Vintage_Cigars_Original_Vintage_Cigars.webp"},
    {"price": 1000, "name": "Artisan Bricks", "image": "/asset/Gifts/1000S_Artisan_Bricks_Original_Artisan_Bricks.webp"},
    {"price": 1100, "name": "Electric Skulls", "image": "/asset/Gifts/1100S_Electric_Skulls_Original_Electric_Skulls.webp"},
    {"price": 1100, "name": "Gem Signets", "image": "/asset/Gifts/1100S_Gem_Signets_Original_Gem_Signets.webp"},
    {"price": 1100, "name": "Neko Helmets", "image": "/asset/Gifts/1100S_Neko_Helmets_Original_Neko_Helmets.webp"},
    {"price": 1200, "name": "Diamond Rings", "image": "/asset/Gifts/1200S_Diamond_Rings_Original_Diamond_Rings.webp"},
    {"price": 1200, "name": "Heart Lockets", "image": "/asset/Gifts/1200S_Heart_Lockets_Original_Heart_Lockets.webp"},
    {"price": 1200, "name": "Star Notepads", "image": "/asset/Gifts/1200S_Star_Notepads_Original_Star_Notepads.webp"},
    {"price": 1300, "name": "Astral Shards", "image": "/asset/Gifts/1300S_Astral_Shards_Original_Astral_Shards.webp"},
    {"price": 1300, "name": "Signet Rings", "image": "/asset/Gifts/1300S_Signet_Rings_Original_Signet_Rings.webp"},
    {"price": 1300, "name": "Skull Flowers", "image": "/asset/Gifts/1300S_Skull_Flowers_Original_Skull_Flowers.webp"},
    {"price": 1400, "name": "Ion Gems", "image": "/asset/Gifts/1400S_Ion_Gems_Original_Ion_Gems.webp"},
    {"price": 1400, "name": "Party Sparklers", "image": "/asset/Gifts/1400S_Party_Sparklers_Original_Party_Sparklers.webp"},
    {"price": 1500, "name": "Berry Boxes", "image": "/asset/Gifts/1500S_Berry_Boxes_Original_Berry_Boxes.webp"},
    {"price": 1500, "name": "Cupid Charms", "image": "/asset/Gifts/1500S_Cupid_Charms_Original_Cupid_Charms.webp"},
    {"price": 1500, "name": "Mighty Arms", "image": "/asset/Gifts/1500S_Mighty_Arms_Original_Mighty_Arms.webp"},
    {"price": 1500, "name": "Santa Hats", "image": "/asset/Gifts/1500S_Santa_Hats_Original_Santa_Hats.webp"},
    {"price": 1600, "name": "Sky Stilettos", "image": "/asset/Gifts/1600S_Sky_Stilettos_Original_Sky_Stilettos.webp"},
    {"price": 1800, "name": "Rare Birds", "image": "/asset/Gifts/1800S_Rare_Birds_Original_Rare_Birds.webp"},
    {"price": 1800, "name": "Snow Mittens", "image": "/asset/Gifts/1800S_Snow_Mittens_Original_Snow_Mittens.webp"},
    {"price": 1900, "name": "Mood Packs", "image": "/asset/Gifts/1900S_Mood_Packs_Original_Mood_Packs.webp"},
    {"price": 2000, "name": "Light Swords", "image": "/asset/Gifts/2000S_Light_Swords_Original_Light_Swords.webp"},
    {"price": 2026, "name": "Big Years", "image": "/asset/Gifts/2026S_Big_Years_Original_Big_Years.webp"},
    {"price": 2100, "name": "Hanging Stars", "image": "/asset/Gifts/2100S_Hanging_Stars_Original_Hanging_Stars.webp"},
    {"price": 2100, "name": "Record Players", "image": "/asset/Gifts/2100S_Record_Players_Original_Record_Players.webp"},
    {"price": 2200, "name": "Jingle Bells", "image": "/asset/Gifts/2200S_Jingle_Bells_Original_Jingle_Bells.webp"},
    {"price": 2200, "name": "Mini Oscars", "image": "/asset/Gifts/2200S_Mini_Oscars_Original_Mini_Oscars.webp"},
    {"price": 2300, "name": "Spy Agarics", "image": "/asset/Gifts/2300S_Spy_Agarics_Original_Spy_Agarics.webp"},
    {"price": 2400, "name": "Sleigh Bells", "image": "/asset/Gifts/2400S_Sleigh_Bells_Original_Sleigh_Bells.webp"},
    {"price": 2500, "name": "Loot Bags", "image": "/asset/Gifts/2500S_Loot_Bags_Original_Loot_Bags.webp"},
    {"price": 2600, "name": "Precious Peaches", "image": "/asset/Gifts/2600S_Precious_Peaches_Original_Precious_Peaches.webp"},
    {"price": 2800, "name": "Kissed Frogs", "image": "/asset/Gifts/2800S_Kissed_Frogs_Original_Kissed_Frogs.webp"},
    {"price": 3100, "name": "Mad Pumpkins", "image": "/asset/Gifts/3100S_Mad_Pumpkins_Original_Mad_Pumpkins.webp"},
    {"price": 3300, "name": "Ionic Dryers", "image": "/asset/Gifts/3300S_Ionic_Dryers_Original_Ionic_Dryers.webp"},
    {"price": 3500, "name": "Money Pots", "image": "/asset/Gifts/3500S_Money_Pots_Original_Money_Pots.webp"},
    {"price": 4500, "name": "Flying Brooms", "image": "/asset/Gifts/4500S_Flying_Brooms_Original_Flying_Brooms.webp"},
    {"price": 4799, "name": "Toy Bears", "image": "/asset/Gifts/4799S_Toy_Bears_Original_Toy_Bears.webp"},
    {"price": 5000, "name": "Genie Lamps", "image": "/asset/Gifts/5000S_Genie_Lamps_Original_Genie_Lamps.webp"},
    {"price": 7500, "name": "Low Riders", "image": "/asset/Gifts/7500S_Low_Riders_Original_Low_Riders.webp"},
    {"price": 12595, "name": "Nail Bracelets", "image": "/asset/Gifts/12595S_Nail_Bracelets_Original_Nail_Bracelets.webp"},
    {"price": 19047, "name": "Stellar Rockets", "image": "/asset/Gifts/19047S_Stellar_Rockets_Original_Stellar_Rockets.webp"},
]

REFERRAL_QUESTS: list[dict[str, Any]] = [
    {"id": "referral_1", "title": "Пригласить 1 друга", "goal": 1, "reward": 1},
    {"id": "referral_2", "title": "Пригласить 2 друзей", "goal": 2, "reward": 2},
    {"id": "referral_3", "title": "Пригласить 3 друзей", "goal": 3, "reward": 3},
    {"id": "referral_4", "title": "Пригласить 4 друзей", "goal": 4, "reward": 4},
    {"id": "referral_5", "title": "Пригласить 5 друзей", "goal": 5, "reward": 5},
]

ACHIEVEMENTS: list[dict[str, Any]] = [
    {"id": "first_step", "title": "Первый шаг", "goal": 1, "reward": 1},
    {"id": "upgrade_master", "title": "Мастер апгрейдов", "goal": 3, "reward": 15},
    {"id": "ludoman", "title": "Истинный лудоман", "goal": 10, "reward": 10},
]

HYPE_TEMPLATES: list[str] = [
    "@{username}, 20 секунд назад пользователь id {fake_id} выиграл Astral Shard за 20К ⭐\n\n🔥 Испытай свою удачу, твои шансы на победу в платной рулетке увеличены на 34% (всего на час)!",
    "🚨 СКИДКА ДО КРИТИЧЕСКОГО МИНИМУМА!\n\nТолько в ближайшие 30 минут стоимость открытия 'Scream Case' снижена! Успей забрать топовые подарки, пока админ спит. Шанс дропа окупаемого дропа повышен x2!",
    "🎁 Бонус выходного дня!\n\nКаждый, кто зайдет в приложение прямо сейчас, получит +2 бесплатных тикета на баланс! Не упусти халяву, заходи в профиль!",
    "🌙 Ночной режим активирован.\n\nПо статистике, именно ночью выпадает самый дорогой дроп. Прямо сейчас кто-то крутит рулетку и забирает сочные призы. А чего ждешь ты? Твой бонусный процент на удачу уже активирован!",
]


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_admin(user_id: int | None) -> bool:
    if user_id is None:
        return False
    return int(user_id) in ADMIN_IDS


def parse_positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
        return parsed if parsed > 0 else None
    except (TypeError, ValueError):
        return None


async def db_execute(query):
    return await asyncio.to_thread(query.execute)


async def request_json(request: web.Request) -> dict[str, Any]:
    if "json_body" in request:
        return request["json_body"]
    try:
        data = await request.json()
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    request["json_body"] = data
    return data


def validate_init_data(init_data: str | None) -> dict[str, Any] | None:
    if not init_data:
        return None

    try:
        vals = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        received_hash = vals.pop("hash", None)
        if not received_hash:
            return None

        data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(vals.items()))
        secret_key = hmac.new(b"WebAppData", TOKEN.encode("utf-8"), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            return None

        user_data = json.loads(vals.get("user", "{}"))
        if not isinstance(user_data, dict) or not user_data.get("id"):
            return None
        return user_data
    except Exception as exc:
        logger.warning("Failed to validate initData: %s", exc)
        return None


def extract_auth_header(request: web.Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth.replace("Bearer ", "", 1).strip()
    return request.headers.get("X-Telegram-Init-Data")


@web.middleware
async def cors_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        response = web.Response(status=204)
    else:
        response = await handler(request)

    response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Telegram-Init-Data"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@web.middleware
async def auth_middleware(request: web.Request, handler):
    if request.path.startswith("/api/"):
        data = await request_json(request) if request.method in {"POST", "PUT", "PATCH"} else {}
        init_data = data.get("initData") or request.query.get("initData") or extract_auth_header(request)
        user_data = validate_init_data(init_data)

        if not user_data:
            return web.json_response(
                {"error": "unauthorized", "message": "Invalid or expired Telegram initData"},
                status=401,
            )

        request["user_id"] = int(user_data["id"])
        request["user_data"] = user_data

    return await handler(request)


async def fetch_user(user_id: int) -> dict[str, Any] | None:
    res = await db_execute(supabase.table("users").select("*").eq("id", int(user_id)).limit(1))
    return res.data[0] if res.data else None


async def safe_update_user_fields(user_id: int, fields: dict[str, Any]) -> None:
    clean_fields = {k: v for k, v in fields.items() if v is not None}
    if not clean_fields:
        return
    try:
        await db_execute(supabase.table("users").update(clean_fields).eq("id", int(user_id)))
    except Exception as exc:
        logger.debug("Optional user field update skipped for %s: %s", user_id, exc)


async def insert_payment(user_id: int, amount: int) -> None:
    try:
        await db_execute(
            supabase.table("payments").insert(
                {"user_id": int(user_id), "amount": int(amount), "date": now_str()}
            )
        )
    except Exception as exc:
        logger.debug("Payment log insert skipped for %s: %s", user_id, exc)


async def register_or_get(
    user_id: int,
    username: str | None = None,
    first_name: str | None = None,
    referred_by: str | int | None = None,
) -> tuple[dict[str, Any], bool]:
    user_id = int(user_id)
    existing = await fetch_user(user_id)
    if existing:
        await safe_update_user_fields(
            user_id,
            {"username": username, "first_name": first_name, "last_seen": now_str()},
        )
        return existing, False

    ref_id: int | None = None
    if referred_by and str(referred_by).isdigit():
        candidate = int(referred_by)
        if candidate != user_id and await fetch_user(candidate):
            ref_id = candidate

    await db_execute(supabase.table("users").insert({"id": user_id, "stars": 0, "referred_by": ref_id}))
    await safe_update_user_fields(
        user_id,
        {
            "username": username,
            "first_name": first_name,
            "join_date": now_str(),
            "tickets": 0,
            "promo_opened": 0,
            "total_spent": 0,
            "total_donated_stars": 0,
        },
    )

    if ref_id:
        ref_user = await fetch_user(ref_id)
        if ref_user:
            await safe_update_user_fields(ref_id, {"tickets": int(ref_user.get("tickets") or 0) + 1})
            try:
                await bot.send_message(ref_id, "🎉 По вашей ссылке пришел новый пользователь! Вам начислен +1 билет.")
            except Exception as exc:
                logger.debug("Failed to notify referrer %s: %s", ref_id, exc)

    created = await fetch_user(user_id)
    return created or {"id": user_id, "stars": 0, "referred_by": ref_id}, True


async def update_balance(user_id: int, amount: int, mode: str = "add", is_donation: bool = False) -> int:
    user_id = int(user_id)
    amount = int(amount)
    user = await fetch_user(user_id)
    if not user:
        raise RuntimeError("user_not_found")

    current_stars = int(user.get("stars") or 0)
    new_stars = current_stars + amount if mode == "add" else amount
    if new_stars < 0:
        raise RuntimeError("insufficient_funds")

    await db_execute(supabase.table("users").update({"stars": new_stars}).eq("id", user_id))
    await insert_payment(user_id, amount if mode == "add" else new_stars - current_stars)

    if is_donation and amount > 0:
        donated_total = int(user.get("total_donated_stars") or 0) + amount
        await safe_update_user_fields(user_id, {"total_donated_stars": donated_total})

        ref_id = user.get("referred_by")
        if ref_id:
            reward = int(amount * 0.1)
            if reward > 0:
                try:
                    await update_balance(int(ref_id), reward, "add", is_donation=False)
                except Exception as exc:
                    logger.debug("Referral reward failed for %s: %s", ref_id, exc)

    return new_stars


async def init_db() -> None:
    try:
        await db_execute(supabase.table("users").select("id", count="exact").limit(1))
        logger.info("Supabase connection verified")
    except Exception as exc:
        logger.critical("Supabase initialization failed: %s", exc)
        raise


async def count_referrals(user_id: int) -> int:
    res = await db_execute(
        supabase.table("users").select("id", count="exact").eq("referred_by", int(user_id)).limit(1)
    )
    return int(res.count or 0)


async def fetch_all_users() -> list[dict[str, Any]]:
    users: list[dict[str, Any]] = []
    limit = 1000
    offset = 0

    while True:
        res = await db_execute(supabase.table("users").select("*").range(offset, offset + limit - 1))
        batch = res.data or []
        users.extend(batch)
        if len(batch) < limit:
            break
        offset += limit

    return users


def normalize_asset(path: str | None) -> str:
    if not path:
        return "/asset/Gifts/default.webp"
    filename = str(path).replace("\\", "/").split("/")[-1]
    if not filename or "." not in filename:
        return "/asset/Gifts/default.webp"
    return f"/asset/Gifts/{filename}"


def get_random_gift(min_price: int, max_price: int) -> dict[str, Any]:
    drop_items = [gift for gift in ALL_GIFTS if min_price <= int(gift["price"]) <= max_price]
    if not drop_items:
        drop_items = ALL_GIFTS[:10]

    cheap = [item for item in drop_items if int(item["price"]) <= 50]
    mid = [item for item in drop_items if 50 < int(item["price"]) <= 150]
    jackpot = [item for item in drop_items if int(item["price"]) > 150]

    roll = random.random() * 100
    if roll < 85 and cheap:
        item = random.choice(cheap)
    elif roll < 97 and mid:
        item = random.choice(mid)
    elif jackpot:
        item = random.choice(jackpot)
    else:
        item = random.choice(drop_items)

    result = dict(item)
    result["image"] = normalize_asset(result.get("image"))
    return result


async def increment_achievement_progress(user_id: int, achievement_type: str) -> None:
    mapping = {
        "cases_opened": ["first_step", "ludoman"],
        "upgrades_successful": ["upgrade_master"],
    }

    for achievement_id in mapping.get(achievement_type, []):
        try:
            res = await db_execute(
                supabase.table("user_achievements")
                .select("progress")
                .eq("user_id", int(user_id))
                .eq("achievement_id", achievement_id)
                .limit(1)
            )
            if res.data:
                progress = int(res.data[0].get("progress") or 0) + 1
                await db_execute(
                    supabase.table("user_achievements")
                    .update({"progress": progress})
                    .eq("user_id", int(user_id))
                    .eq("achievement_id", achievement_id)
                )
            else:
                await db_execute(
                    supabase.table("user_achievements").insert(
                        {"user_id": int(user_id), "achievement_id": achievement_id, "progress": 1}
                    )
                )
        except Exception as exc:
            logger.debug("Achievement progress skipped for %s/%s: %s", user_id, achievement_id, exc)


async def consume_case_limit(case_id: int) -> bool:
    res = await db_execute(supabase.rpc("consume_case_limit", {"p_case_id": int(case_id)}))
    data = res.data

    if data is False:
        return False
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

    return True


def limit_to_int(value: Any) -> int:
    if value is None:
        return -1
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


def normalize_case_row(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    raw_case_id = item.get("id") or item.get("case_id")
    try:
        case_id = int(raw_case_id)
    except (TypeError, ValueError):
        case_id = None

    case_name = str(item.get("name") or item.get("title") or "").lower()
    item["remaining_limit"] = limit_to_int(item.get("remaining_limit"))
    item["total_limit"] = limit_to_int(item.get("total_limit"))

    if case_id == 1 or "promo" in case_name:
        promo_asset = "/asset/Gifts/5000S_Case_Original_Case.webp"
        item["asset"] = promo_asset
        item["asset_url"] = promo_asset
        item["image"] = promo_asset
        item["image_url"] = promo_asset
    else:
        for key in ("asset", "asset_url", "image", "image_url"):
            if key in item and item[key]:
                item[key] = normalize_asset(str(item[key]))

    return item


def daily_wait_seconds(user: dict[str, Any]) -> int:
    last_daily = user.get("last_daily")
    if not last_daily or last_daily == "1970-01-01 00:00:00":
        return 0
    try:
        last_dt = datetime.strptime(str(last_daily), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return 0
    elapsed = (datetime.now() - last_dt).total_seconds()
    return max(0, int(86400 - elapsed))


def extract_ton_comment(in_msg: dict[str, Any]) -> str:
    comment = str(in_msg.get("message") or "").strip()
    msg_data = in_msg.get("msg_data") or {}

    if not comment and msg_data.get("@type") == "msg.dataText":
        comment = str(msg_data.get("text") or "").strip()

    if comment and len(comment) % 2 == 0 and all(char in string.hexdigits for char in comment):
        try:
            decoded = bytes.fromhex(comment).decode("utf-8", errors="ignore").strip()
            if decoded:
                return decoded
        except Exception:
            pass

    return comment


async def check_ton_transactions() -> None:
    if not TON_WALLET:
        logger.warning("TON wallet is not configured; TON monitor is disabled")
        return

    logger.info("TON monitor started for wallet %s", TON_WALLET)
    timeout = aiohttp.ClientTimeout(total=15)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        while True:
            try:
                if not TONCENTER_API_KEY:
                    logger.warning("TONCENTER_API_KEY is not set; skipping TON verification iteration")
                    await asyncio.sleep(300)
                    continue

                params = {"address": TON_WALLET, "limit": 20}
                headers = {"X-API-Key": TONCENTER_API_KEY}

                async with session.get(f"{TONCENTER_BASE_URL}/getTransactions", params=params, headers=headers) as resp:
                    if resp.status == 401:
                        logger.warning("Toncenter API returned 401 Unauthorized; skipping iteration")
                        await asyncio.sleep(300)
                        continue
                    if resp.status != 200:
                        logger.warning("Toncenter API returned %s", resp.status)
                        await asyncio.sleep(60)
                        continue

                    payload = await resp.json()

                for tx in payload.get("result") or []:
                    in_msg = tx.get("in_msg") or {}
                    value = int(in_msg.get("value") or 0)
                    if value <= 0:
                        continue

                    tx_id = (tx.get("transaction_id") or {}).get("hash")
                    if not tx_id:
                        continue

                    comment = extract_ton_comment(in_msg)
                    if not comment.startswith("SC_"):
                        continue

                    parts = comment.split("_")
                    if len(parts) < 2 or not parts[1].isdigit():
                        continue

                    user_id = int(parts[1])

                    try:
                        existing = await db_execute(
                            supabase.table("ton_transactions").select("tx_id").eq("tx_id", tx_id).limit(1)
                        )
                        if existing.data:
                            continue
                    except Exception as exc:
                        logger.debug("TON transaction duplicate check skipped: %s", exc)

                    amount_ton = value / 1_000_000_000
                    stars_to_add = int(amount_ton * TON_STARS_RATE)
                    if stars_to_add <= 0:
                        continue

                    try:
                        await db_execute(
                            supabase.table("ton_transactions").insert(
                                {"tx_id": tx_id, "user_id": user_id, "amount": amount_ton, "date": now_str()}
                            )
                        )
                    except Exception as exc:
                        logger.debug("TON transaction insert skipped: %s", exc)

                    await update_balance(user_id, stars_to_add, "add", is_donation=True)
                    user = await fetch_user(user_id)
                    if user:
                        await safe_update_user_fields(
                            user_id,
                            {"total_donated_ton": float(user.get("total_donated_ton") or 0.0) + amount_ton},
                        )

                    try:
                        await bot.send_message(
                            user_id,
                            f"✅ Оплата TON подтверждена!\n\nНа баланс зачислено {stars_to_add} ⭐",
                        )
                    except Exception as exc:
                        logger.debug("Failed to notify TON payer %s: %s", user_id, exc)

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("TON monitor iteration failed: %s", exc)
                await asyncio.sleep(60)

            await asyncio.sleep(30)


async def keep_alive_task() -> None:
    while True:
        try:
            await asyncio.sleep(600)
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
                async with session.get(KEEP_ALIVE_URL) as response:
                    logger.info("Keep-alive ping status: %s", response.status)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.debug("Keep-alive ping failed: %s", exc)


@router.message(Command("start"))
async def start_cmd(message: Message, command: CommandObject) -> None:
    user = message.from_user
    if not user:
        return

    profile, is_new = await register_or_get(
        user.id,
        username=user.username,
        first_name=user.first_name,
        referred_by=command.args,
    )

    if is_new:
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"🚀 Новый пользователь\n\nИмя: {user.full_name}\nID: {user.id}\nUsername: @{user.username}",
                )
            except Exception as exc:
                logger.debug("Failed to notify admin %s: %s", admin_id, exc)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Открыть ScreamCase", web_app=WebAppInfo(url=APP_URL))],
            [InlineKeyboardButton(text="📢 Канал", url=CHANNEL_URL)],
        ]
    )
    await message.answer(f"Привет! Твой баланс: {int(profile.get('stars') or 0)} ⭐", reply_markup=keyboard)


@router.message(Command("help"))
async def help_cmd(message: Message) -> None:
    text = "📖 Команды бота\n\n/start — запуск приложения\n/help — справка"
    if message.from_user and is_admin(message.from_user.id):
        text += (
            "\n\nАдмин-команды:"
            "\n/+ AMOUNT — выдать звезды себе или пользователю через reply"
            "\n/+ USER_ID AMOUNT — выдать звезды пользователю"
            "\n/setbalance USER_ID AMOUNT — установить баланс"
            "\n/user USER_ID — информация о пользователе"
            "\n/stats — статистика"
            "\n/admin_send TEXT — рассылка всем пользователям"
            "\n/hype NUMBER — запуск hype-шаблона 1-4"
        )
    await message.answer(text)


@router.message(F.text.regexp(r"^\/\+\s*(?:(\d+)\s+)?(\d+)"))
async def admin_add(message: Message) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        await message.answer("❌ Вы не администратор.")
        return

    match = re.match(r"^\/\+\s*(?:(\d+)\s+)?(\d+)", message.text or "")
    if not match:
        await message.answer("❌ Пример: /+ 100 или /+ 123456789 100")
        return

    target_arg, amount_arg = match.groups()
    amount = int(amount_arg)
    target_user_id = int(target_arg) if target_arg else None

    if target_user_id is None:
        if message.reply_to_message and message.reply_to_message.from_user:
            target_user_id = int(message.reply_to_message.from_user.id)
        else:
            target_user_id = int(message.from_user.id)

    try:
        await update_balance(target_user_id, amount, "add")
    except Exception as exc:
        await message.answer(f"❌ Ошибка БД: {exc}")
        return

    await message.answer(f"✅ Добавлено {amount} ⭐ пользователю {target_user_id}")


@router.message(Command("setbalance"))
async def admin_setbalance(message: Message) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        await message.answer("❌ Вы не администратор.")
        return

    parts = (message.text or "").split()
    if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
        await message.answer("❌ Пример: /setbalance 123456789 500")
        return

    target_user_id = int(parts[1])
    amount = int(parts[2])

    try:
        await update_balance(target_user_id, amount, "set")
    except Exception as exc:
        await message.answer(f"❌ Ошибка БД: {exc}")
        return

    await message.answer(f"✅ Баланс пользователя {target_user_id} установлен на {amount} ⭐")


@router.message(Command("user"))
async def admin_user_info(message: Message) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        await message.answer("❌ Вы не администратор.")
        return

    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("❌ Пример: /user 123456789")
        return

    user_id = int(parts[1])
    user = await fetch_user(user_id)
    if not user:
        await message.answer("❌ Пользователь не найден.")
        return

    await message.answer(
        "\n".join(
            [
                "👤 Пользователь",
                f"ID: {user.get('id')}",
                f"Username: @{user.get('username')}" if user.get("username") else "Username: -",
                f"Баланс: {int(user.get('stars') or 0)} ⭐",
                f"Реферер: {user.get('referred_by') or '-'}",
                f"Донат Stars: {int(user.get('total_donated_stars') or 0)}",
                f"Потрачено: {int(user.get('total_spent') or 0)}",
            ]
        )
    )


@router.message(Command("stats"))
async def admin_stats(message: Message) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        await message.answer("❌ Вы не администратор.")
        return

    users = await fetch_all_users()
    total_users = len(users)
    total_stars = sum(int(user.get("stars") or 0) for user in users)
    total_donated = sum(int(user.get("total_donated_stars") or 0) for user in users)

    total_issued = 0
    try:
        limit = 1000
        offset = 0
        while True:
            res = await db_execute(
                supabase.table("payments").select("amount").gt("amount", 0).range(offset, offset + limit - 1)
            )
            batch = res.data or []
            total_issued += sum(int(row.get("amount") or 0) for row in batch)
            if len(batch) < limit:
                break
            offset += limit
    except Exception as exc:
        logger.debug("Payment stats skipped: %s", exc)

    await message.answer(
        "\n".join(
            [
                "📊 Статистика",
                f"Пользователей: {total_users}",
                f"Звезд на балансах: {total_stars}",
                f"Звезд выдано: {total_issued}",
                f"Звезд задоначено: {total_donated}",
            ]
        )
    )


@router.message(Command("admin_send"))
async def admin_send(message: Message, command: CommandObject) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        await message.answer("❌ Вы не администратор.")
        return

    text_to_send = (command.args or "").strip()
    if not text_to_send:
        await message.answer("❌ Пример: /admin_send Текст рассылки")
        return

    users = await fetch_all_users()
    sent = 0
    failed = 0
    await message.answer("⏳ Рассылка запущена...")

    for user in users:
        try:
            await bot.send_message(int(user["id"]), text_to_send)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await message.answer(f"✅ Рассылка завершена.\nДоставлено: {sent}\nОшибок: {failed}")


@router.message(Command("hype"))
async def admin_hype(message: Message, command: CommandObject) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        await message.answer("❌ Вы не администратор.")
        return

    template_number = parse_positive_int((command.args or "").strip())
    if not template_number or template_number > len(HYPE_TEMPLATES):
        await message.answer("❌ Пример: /hype 1\nДоступные шаблоны: 1-4")
        return

    users = await fetch_all_users()
    template = HYPE_TEMPLATES[template_number - 1]
    sent = 0
    failed = 0
    await message.answer(f"⏳ Hype-рассылка #{template_number} запущена...")

    for user in users:
        try:
            username = str(user.get("username") or user.get("first_name") or "игрок").strip().lstrip("@")
            text = template.format(username=username, fake_id=random.randint(100000000, 9999999999))
            await bot.send_message(int(user["id"]), text)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await message.answer(f"✅ Hype-рассылка завершена.\nДоставлено: {sent}\nОшибок: {failed}")


@router.pre_checkout_query()
async def checkout(query: types.PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message) -> None:
    payment = message.successful_payment
    if not payment:
        return

    parts = payment.invoice_payload.split("_")
    if len(parts) != 3 or parts[0] != "stars" or not parts[1].isdigit() or not parts[2].isdigit():
        await message.answer("❌ Некорректный платеж.")
        return

    user_id = int(parts[1])
    amount = int(parts[2])
    if not message.from_user or int(message.from_user.id) != user_id:
        await message.answer("❌ Платеж не совпадает с пользователем.")
        return

    try:
        await update_balance(user_id, amount, "add", is_donation=True)
    except Exception as exc:
        logger.error("Payment balance update failed: %s", exc)
        await message.answer("❌ Платеж получен, но баланс не обновился. Напишите администратору.")
        return

    await message.answer(f"✅ Спасибо за покупку! +{amount} ⭐")


async def check_membership(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=int(user_id))
        return member.status in {"member", "administrator", "creator"}
    except Exception as exc:
        logger.debug("Membership check failed for %s: %s", user_id, exc)
        return False


async def api_heartbeat(request: web.Request) -> web.Response:
    return web.json_response({"status": "alive", "timestamp": datetime.now().isoformat()})


async def root_handler(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "service": "ScreamCase bot"})


async def api_check_sub(request: web.Request) -> web.Response:
    uid = request.get("user_id")
    return web.json_response({"is_subscribed": await check_membership(int(uid))})


async def api_balance(request: web.Request) -> web.Response:
    uid = int(request.get("user_id"))
    query_uid = request.query.get("user_id")
    if query_uid and int(query_uid) != uid:
        return web.json_response({"error": "forbidden"}, status=403)

    user = await fetch_user(uid)
    if not user:
        return web.json_response({"error": "user_not_found"}, status=404)

    return web.json_response(
        {
            "stars": int(user.get("stars") or 0),
            "tickets": int(user.get("tickets") or 0),
            "donor": int(user.get("total_donated_stars") or 0),
            "spent": int(user.get("total_spent") or 0),
            "promo_opened": int(user.get("promo_opened") or 0),
        }
    )


async def api_referrals(request: web.Request) -> web.Response:
    uid = int(request.get("user_id"))
    res = await db_execute(supabase.table("users").select("*").eq("referred_by", uid))
    referrals = [
        {
            "user_id": row.get("id"),
            "username": row.get("username"),
            "first_name": row.get("first_name"),
            "photo_url": row.get("photo_url"),
            "donated": int(row.get("total_donated_stars") or 0),
        }
        for row in (res.data or [])
    ]
    return web.json_response({"count": len(referrals), "referrals": referrals})


async def api_cases(request: web.Request) -> web.Response:
    try:
        res = await db_execute(supabase.table("cases").select("*"))
        cases = [normalize_case_row(row) for row in (res.data or [])]
        return web.json_response(cases)
    except Exception as exc:
        logger.error("Cases query failed: %s", exc)
        return web.json_response({"error": "server_error"}, status=500)


async def api_open_case(request: web.Request) -> web.Response:
    uid = int(request.get("user_id"))
    data = await request_json(request)

    body_uid = data.get("user_id")
    if body_uid and int(body_uid) != uid:
        return web.json_response({"error": "forbidden"}, status=403)

    case_id = parse_positive_int(data.get("case_id"))
    if not case_id or case_id not in CASES_PRICES:
        return web.json_response({"error": "invalid_case"}, status=400)

    user = await fetch_user(uid)
    if not user:
        return web.json_response({"error": "user_not_found"}, status=404)

    case_info = CASES_DATA.get(case_id)
    if not case_info:
        return web.json_response({"error": "case_data_missing"}, status=500)

    if case_id == 2:
        wait_seconds = daily_wait_seconds(user)
        if wait_seconds > 0:
            return web.json_response(
                {"error": "daily_cooldown_active", "wait_seconds": wait_seconds},
                status=403,
            )

        try:
            if not await consume_case_limit(case_id):
                return web.json_response({"error": "Cases of this type are sold out."}, status=400)
        except Exception as exc:
            logger.error("Case limit consume failed: %s", exc)
            return web.json_response({"error": "server_error"}, status=500)

        await safe_update_user_fields(uid, {"last_daily": now_str()})
        await safe_update_user_fields(uid, {"cases_opened_count": int(user.get("cases_opened_count") or 0) + 1})
        await increment_achievement_progress(uid, "cases_opened")
        return web.json_response({"success": True, "item": get_random_gift(case_info["min"], case_info["max"]), "deducted": 0})

    price = int(CASES_PRICES[case_id])
    balance = int(user.get("stars") or 0)
    if case_id == 1 and int(user.get("promo_opened") or 0) == 1:
        return web.json_response({"error": "already_opened"}, status=403)
    if balance < price:
        return web.json_response({"error": "insufficient_funds"}, status=403)

    try:
        if not await consume_case_limit(case_id):
            return web.json_response({"error": "Cases of this type are sold out."}, status=400)
    except Exception as exc:
        logger.error("Case limit consume failed: %s", exc)
        return web.json_response({"error": "server_error"}, status=500)

    if price > 0:
        await db_execute(supabase.table("users").update({"stars": balance - price}).eq("id", uid))
        await insert_payment(uid, -price)

    won_item = get_random_gift(case_info["min"], case_info["max"])
    await safe_update_user_fields(
        uid,
        {
            "promo_opened": 1 if case_id == 1 else user.get("promo_opened"),
            "total_spent": int(user.get("total_spent") or 0) + price,
            "cases_opened_count": int(user.get("cases_opened_count") or 0) + 1,
        },
    )
    await increment_achievement_progress(uid, "cases_opened")

    return web.json_response({"success": True, "item": won_item, "deducted": price})


async def api_claim_daily(request: web.Request) -> web.Response:
    data = await request_json(request)
    data["case_id"] = 2
    request["json_body"] = data
    return await api_open_case(request)


async def api_invoice(request: web.Request) -> web.Response:
    uid = int(request.get("user_id"))
    data = await request_json(request)
    body_uid = data.get("user_id")
    if body_uid and int(body_uid) != uid:
        return web.json_response({"error": "forbidden"}, status=403)

    amount = parse_positive_int(data.get("amount"))
    if not amount:
        return web.json_response({"error": "no_amount"}, status=400)

    payment_type = data.get("payment_type", "stars")
    user = await fetch_user(uid)
    if not user:
        return web.json_response({"error": "user_not_found"}, status=404)

    if payment_type == "stars":
        try:
            invoice_url = await bot.create_invoice_link(
                title="Пополнение баланса",
                description=f"Покупка {amount} звёзд",
                payload=f"stars_{uid}_{amount}",
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label="Telegram Stars", amount=int(amount))],
            )
            return web.json_response({"invoice_url": invoice_url, "url": invoice_url, "link": invoice_url})
        except Exception as exc:
            logger.error("Telegram invoice creation failed: %s", exc)
            return web.json_response({"error": f"Telegram API error: {exc}"}, status=500)

    random_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    comment = f"SC_{uid}_{random_part}"
    return web.json_response({"wallet": TON_WALLET, "comment": comment, "rate": TON_STARS_RATE})


async def api_ton_success(request: web.Request) -> web.Response:
    return web.json_response({"success": True, "message": "TON verification runs in background."})


async def api_upgrade(request: web.Request) -> web.Response:
    uid = int(request.get("user_id"))
    data = await request_json(request)

    body_uid = data.get("user_id")
    if body_uid and int(body_uid) != uid:
        return web.json_response({"error": "forbidden"}, status=403)

    cost = int(data.get("cost") or 0)
    chance = float(data.get("chance") or 0)
    item_price = int(data.get("item_price") or 0)
    if cost <= 0 or chance <= 0:
        return web.json_response({"error": "invalid_data"}, status=400)

    user = await fetch_user(uid)
    if not user:
        return web.json_response({"error": "user_not_found"}, status=404)

    balance = int(user.get("stars") or 0)
    if balance < cost:
        return web.json_response({"error": "insufficient_funds"}, status=403)

    success = random.random() * 100 < chance
    await db_execute(supabase.table("users").update({"stars": balance - cost}).eq("id", uid))
    await insert_payment(uid, -cost)
    await safe_update_user_fields(uid, {"total_spent": int(user.get("total_spent") or 0) + cost})

    consolation = None
    if success:
        await safe_update_user_fields(
            uid,
            {"successful_upgrades_count": int(user.get("successful_upgrades_count") or 0) + 1},
        )
        await increment_achievement_progress(uid, "upgrades_successful")
    elif item_price > 100:
        consolation = {"type": "poor_case", "item": get_random_gift(0, 100)}

    return web.json_response({"success": success, "consolation": consolation})


async def api_wheel_spin(request: web.Request) -> web.Response:
    uid = int(request.get("user_id"))
    data = await request_json(request)

    body_uid = data.get("user_id")
    if body_uid and int(body_uid) != uid:
        return web.json_response({"error": "forbidden"}, status=403)

    cost = 50
    user = await fetch_user(uid)
    if not user:
        return web.json_response({"error": "user_not_found"}, status=404)

    balance = int(user.get("stars") or 0)
    if balance < cost:
        return web.json_response({"error": "insufficient_funds"}, status=403)

    segments = [15, 50, 20, 100, 25, 200, 30, 300, 40, 500, 50, 150]
    roll = random.random() * 100
    if roll < 0.8:
        prize_index = 9
    elif roll < 15:
        prize_index = random.choice([3, 5, 7, 11])
    else:
        prize_index = random.choice([0, 1, 2, 4, 6, 8, 10])

    prize = int(segments[prize_index])
    new_balance = balance - cost + prize
    await db_execute(supabase.table("users").update({"stars": new_balance}).eq("id", uid))
    await safe_update_user_fields(uid, {"total_spent": int(user.get("total_spent") or 0) + cost})
    await insert_payment(uid, -cost)
    await insert_payment(uid, prize)

    return web.json_response(
        {"success": True, "win_amount": prize, "prize_index": prize_index, "new_balance": new_balance}
    )


async def api_get_achievements(request: web.Request) -> web.Response:
    uid = int(request.get("user_id"))
    try:
        existing = await db_execute(
            supabase.table("user_achievements").select("*").eq("user_id", uid)
        )
        existing_by_id = {row.get("achievement_id"): row for row in (existing.data or [])}

        response = []
        for achievement in ACHIEVEMENTS:
            row = existing_by_id.get(achievement["id"]) or {}
            response.append(
                {
                    **achievement,
                    "progress": int(row.get("progress") or 0),
                    "is_claimed": bool(row.get("is_claimed")),
                }
            )
        return web.json_response(response)
    except Exception as exc:
        logger.error("Achievements query failed: %s", exc)
        return web.json_response({"error": "server_error"}, status=500)


async def api_claim_achievement(request: web.Request) -> web.Response:
    uid = int(request.get("user_id"))
    data = await request_json(request)
    achievement_id = data.get("achievement_id")
    achievement = next((item for item in ACHIEVEMENTS if item["id"] == achievement_id), None)
    if not achievement:
        return web.json_response({"error": "achievement_not_found"}, status=404)

    try:
        res = await db_execute(
            supabase.table("user_achievements")
            .select("*")
            .eq("user_id", uid)
            .eq("achievement_id", achievement_id)
            .limit(1)
        )
        if not res.data:
            return web.json_response({"error": "not_found"}, status=404)

        row = res.data[0]
        if bool(row.get("is_claimed")):
            return web.json_response({"error": "already_claimed"}, status=400)
        if int(row.get("progress") or 0) < int(achievement["goal"]):
            return web.json_response({"error": "not_reached"}, status=400)

        await db_execute(
            supabase.table("user_achievements")
            .update({"is_claimed": True})
            .eq("user_id", uid)
            .eq("achievement_id", achievement_id)
        )
        await update_balance(uid, int(achievement["reward"]), "add")
        return web.json_response({"success": True, "reward": int(achievement["reward"])})
    except Exception as exc:
        logger.error("Achievement claim failed: %s", exc)
        return web.json_response({"error": "server_error"}, status=500)


async def api_get_quests(request: web.Request) -> web.Response:
    uid = int(request.get("user_id"))
    referral_count = await count_referrals(uid)

    try:
        res = await db_execute(supabase.table("user_quests").select("*").eq("user_id", uid))
        claimed_by_id = {row.get("quest_id"): bool(row.get("reward_claimed")) for row in (res.data or [])}
    except Exception as exc:
        logger.debug("Quest status read failed: %s", exc)
        claimed_by_id = {}

    response = []
    for quest in REFERRAL_QUESTS:
        response.append(
            {
                **quest,
                "progress": min(referral_count, int(quest["goal"])),
                "is_completed": referral_count >= int(quest["goal"]),
                "is_claimed": bool(claimed_by_id.get(quest["id"], False)),
            }
        )

    return web.json_response(response)


async def api_claim_quest(request: web.Request) -> web.Response:
    uid = int(request.get("user_id"))
    data = await request_json(request)
    quest_id = data.get("quest_id")
    quest = next((item for item in REFERRAL_QUESTS if item["id"] == quest_id), None)
    if not quest:
        return web.json_response({"error": "quest_not_found"}, status=404)

    referral_count = await count_referrals(uid)
    if referral_count < int(quest["goal"]):
        return web.json_response({"error": "not_reached"}, status=400)

    try:
        existing = await db_execute(
            supabase.table("user_quests")
            .select("*")
            .eq("user_id", uid)
            .eq("quest_id", quest_id)
            .limit(1)
        )
        if existing.data and bool(existing.data[0].get("reward_claimed")):
            return web.json_response({"error": "already_claimed"}, status=400)

        payload = {
            "user_id": uid,
            "quest_id": quest_id,
            "progress": referral_count,
            "is_completed": True,
            "reward_claimed": True,
        }
        await db_execute(
            supabase.table("user_quests").upsert(payload, on_conflict="user_id,quest_id")
        )
        await update_balance(uid, int(quest["reward"]), "add")
        return web.json_response({"success": True, "reward": int(quest["reward"])})
    except Exception as exc:
        logger.error("Quest claim failed: %s", exc)
        return web.json_response({"error": "server_error"}, status=500)


async def start_background_tasks(app: web.Application) -> None:
    app["ton_monitor"] = asyncio.create_task(check_ton_transactions())
    app["keep_alive"] = asyncio.create_task(keep_alive_task())


async def cleanup_background_tasks(app: web.Application) -> None:
    tasks = [app.get("ton_monitor"), app.get("keep_alive")]
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
    app.router.add_get("/api/referrals", api_referrals)
    app.router.add_get("/api/cases", api_cases)
    app.router.add_post("/api/open_case", api_open_case)
    app.router.add_post("/api/claim_daily", api_claim_daily)
    app.router.add_post("/api/create_invoice", api_invoice)
    app.router.add_post("/api/ton_success", api_ton_success)
    app.router.add_post("/api/upgrade", api_upgrade)
    app.router.add_post("/api/wheel/spin", api_wheel_spin)
    app.router.add_get("/api/achievements", api_get_achievements)
    app.router.add_post("/api/achievements/claim", api_claim_achievement)
    app.router.add_get("/api/quests", api_get_quests)
    app.router.add_post("/api/quests/claim", api_claim_quest)


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
