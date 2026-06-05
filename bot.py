import logging
import asyncio
import os
import aiohttp
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from aiohttp import web
import hashlib
import string
import random
from supabase import create_client, Client
from dotenv import load_dotenv
import base64
from pytoniq import Builder
import hmac
import urllib.parse
import json

# --- НАСТРОЙКИ ---
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("VITE_SUPABASE_ANON_KEY")

if not all([TOKEN, SUPABASE_URL, SUPABASE_KEY]):
    logger.error("❌ КРИТИЧЕСКАЯ ОШИБКА: Проверьте переменные окружения TELEGRAM_BOT_TOKEN, VITE_SUPABASE_URL и SUPABASE_KEY")
    import sys
    sys.exit(1)

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    logger.error(f"❌ Failed to initialize Supabase client: {e}")
    import sys
    sys.exit(1)

ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "7782281997,5396975347").split(",") if x.strip().isdigit()]
APP_URL = os.getenv("APP_URL", "https://scream-case-bot.vercel.app")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/ScreamCase")
TON_WALLET = os.getenv("VITE_TON_WALLET", "UQA312HDuwVR-RtbUD6u05RAXF-ExIHxExeCZP32RciryUrp")
TONCENTER_API_KEY = os.getenv("TONCENTER_API_KEY", "")
TONCENTER_BASE_URL = "https://toncenter.com/api/v2"

# --- КОНСТАНТЫ ---
CASES_PRICES = {
    1: 0,    # Promo Case
    2: 1,    # Daily Case (1 ticket)
    3: 15,   # Snoop Case
    4: 25,   # Lover's Case
    5: 5,    # Hobo Case
    6: 10,   # Risky Box
    7: 50,   # Scam Box
    8: 100,  # Ebati Case
    9: 75,   # Pussy Case
    10: 150  # Skolnik Case
}

CASES_DATA = {
    1: {'min': 15, 'max': 500},   # Promo Case
    2: {'min': 0, 'max': 100},    # Daily Case
    3: {'min': 100, 'max': 667},  # Snoop Case
    4: {'min': 200, 'max': 599},  # Lover's Case
    5: {'min': 0, 'max': 199},    # Hobo Case
    6: {'min': 0, 'max': 50},     # Risky Box
    7: {'min': 0, 'max': 599},    # Scam Box
    8: {'min': 100, 'max': 444},  # Ebati Case
    9: {'min': 50, 'max': 222},   # Pussy Case
    10: {'min': 100, 'max': 250}  # Skolnik Case
}

ALL_GIFTS = [
  {"price": 15, "name": "Bear", "image": "/asset/Gifts/15S_Bear_Original_Bear.webp"},
  {"price": 25, "name": "Rosae", "image": "/asset/Gifts/25S_Rosae_Original_Rosae.webp"},
  {"price": 40, "name": "Lol Pops", "image": "/asset/Gifts/40S_Lol_Pops_Original_Lol_Pops.webp"},
  {"price": 50, "name": "Cake", "image": "/asset/Gifts/50S_Cake_Original_Cake.webp"},
  {"price": 50, "name": "GiftBox", "image": "/asset/Gifts/50S_GiftBox_Original_GiftBox.webp"},
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

HYPE_TEMPLATES = [
    "@{username}, 20 секунд назад пользователь id {fake_id} выиграл Astral Shard за 20К ⭐\n\n🔥 Испытай свою удачу, твои шансы на победу в платной рулетке увеличены на 34% (всего на час)!",
    "🚨 СКИДКА ДО КРИТИЧЕСКОГО МИНИМУМА!\n\nТолько в ближайшие 30 минут стоимость открытия 'Scream Case' снижена! Успей забрать топовые подарки, пока админ спит. Шанс дропа окупаемого дропа повышен x2!",
    "🎁 Бонус выходного дня!\n\nКаждый, кто зайдет в приложение прямо сейчас, получит +2 бесплатных тикета на баланс! Не упусти халяву, заходи в профиль!",
    "🌙 Ночной режим активирован.\n\nПо статистике, именно ночью выпадает самый дорогой дроп. Прямо сейчас кто-то крутит рулетку и забирает сочные призы. А чего ждешь ты? Твой бонусный процент на удачу уже активирون!",
]

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def validate_init_data(init_data: str, bot_token: str) -> dict:
    """Валидирует данные от Telegram Web App."""
    if not init_data or not isinstance(init_data, str):
        logger.warning("❌ Пустые или невалидные initData")
        return None
    try:
        vals = {k: v for k, v in urllib.parse.parse_qsl(init_data)}
        if 'hash' not in vals or 'user' not in vals:
            logger.warning("❌ Missing 'hash' or 'user' in initData")
            return None
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(vals.items()) if k != 'hash')
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        h = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if h != vals['hash']:
            logger.warning("❌ InitData hash mismatch")
            return None
        user_data = json.loads(vals.get('user', '{}'))
        if not user_data.get('id'):
            logger.warning("❌ InitData missing user.id")
            return None
        return user_data
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decode error in initData: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Error validating initData: {e}")
        return None

def create_comment_boc(text: str) -> str:
    """Создает BOC с текстовым комментарием для TON."""
    try:
        cell = Builder().store_uint(0, 32).store_string(text).end_cell()
        return base64.b64encode(cell.to_boc(False)).decode('utf-8')
    except Exception as e:
        logger.error(f"Error creating BOC: {e}")
        return ""

def get_user_stars(user_id):
    """Получает баланс пользователя по user_id."""
    try:
        res = supabase.table("users").select("stars, balance").eq("user_id", user_id).execute()
        if res.data:
            u = res.data[0]
            stars = u.get('stars')
            if stars is None:
                stars = u.get('balance', 0)
            return stars
        return 0
    except Exception as e:
        logger.error(f"Error getting user stars: {e}")
        return 0

def register_or_get(user_id, username=None, first_name=None, photo_url=None, referred_by=None):
    try:
        res = supabase.table("users").select("stars, join_date").eq("user_id", user_id).execute()
        if res.data:
            update_user_profile(user_id, username, first_name, photo_url)
            return (res.data[0]['stars'], res.data[0]['join_date']), False

        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        ref_id = None
        if referred_by and str(referred_by).isdigit():
            ref_id = int(referred_by)
            if ref_id == user_id:
                ref_id = None
            else:
                ref_check = supabase.table("users").select("user_id").eq("user_id", ref_id).execute()
                if not ref_check.data:
                    ref_id = None

        user_data = {
            "user_id": user_id,
            "stars": 0,
            "join_date": date,
            "username": username,
            "first_name": first_name,
            "photo_url": photo_url,
            "referred_by": ref_id,
            "tickets": 0
        }
        supabase.table("users").insert(user_data).execute()

        if ref_id:
            ref_user = supabase.table("users").select("tickets").eq("user_id", ref_id).execute()
            if ref_user.data:
                new_tickets = (ref_user.data[0].get('tickets') or 0) + 1
                supabase.table("users").update({"tickets": new_tickets}).eq("user_id", ref_id).execute()
            logger.info(f"User {user_id} joined via referral {ref_id}")

        return (0, date), True
    except Exception as e:
        logger.error(f"Error in register_or_get: {e}")
        return (0, "")

def update_user_profile(user_id, username=None, first_name=None, photo_url=None):
    try:
        updates = {}
        if username: updates["username"] = username
        if first_name: updates["first_name"] = first_name
        if photo_url: updates["photo_url"] = photo_url
        if updates:
            supabase.table("users").update(updates).eq("user_id", user_id).execute()
    except Exception as e:
        logger.error(f"Error in update_user_profile: {e}")


def update_balance(user_id, amount, mode="add", is_donation=False):
    try:
        user_res = supabase.table("users").select("stars, total_donated_stars, referred_by").eq("user_id", user_id).execute()
        if not user_res.data:
            return

        current_stars = user_res.data[0]['stars']
        current_donated = user_res.data[0].get('total_donated_stars') or 0
        ref_id = user_res.data[0].get('referred_by')

        if mode == "add":
            new_stars = current_stars + amount
            updates = {"stars": new_stars}
            if is_donation:
                updates["total_donated_stars"] = current_donated + amount
                if ref_id:
                    reward = int(amount * 0.1)
                    if reward > 0:
                        ref_res = supabase.table("users").select("stars").eq("user_id", ref_id).execute()
                        if ref_res.data:
                            new_ref_stars = ref_res.data[0]['stars'] + reward
                            supabase.table("users").update({"stars": new_ref_stars}).eq("user_id", ref_id).execute()
                            supabase.table("payments").insert({
                                "user_id": ref_id,
                                "amount": reward,
                                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }).execute()
                            logger.info(f"Referrer {ref_id} got {reward} stars from {user_id}'s donation")
            supabase.table("users").update(updates).eq("user_id", user_id).execute()
        else:
            supabase.table("users").update({"stars": amount}).eq("user_id", user_id).execute()

        supabase.table("payments").insert({
            "user_id": user_id,
            "amount": amount if mode == "add" else amount - current_stars,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }).execute()
    except Exception as e:
        logger.error(f"Error in update_balance: {e}")


def _get_random_gift(min_p, max_p):
    drop_items = [g for g in ALL_GIFTS if g['price'] >= min_p and g['price'] <= max_p]
    if not drop_items:
        drop_items = ALL_GIFTS[:10]

    cheap = [i for i in drop_items if i['price'] <= 50]
    mid = [i for i in drop_items if 50 < i['price'] <= 150]
    jackpot = [i for i in drop_items if i['price'] > 150]

    rand = random.random() * 100
    if rand < 85 and cheap:
        return random.choice(cheap)
    elif rand < 97 and mid:
        return random.choice(mid)
    elif jackpot:
        return random.choice(jackpot)
    else:
        return random.choice(drop_items)


def _increment_achievement_progress(user_id, achievement_type):
    mapping = {
        'cases_opened': ['first_step', 'ludoman'],
        'upgrades_successful': ['upgrade_master']
    }
    a_ids = mapping.get(achievement_type, [])
    for aid in a_ids:
        try:
            res = supabase.table("user_achievements").select("progress").eq("user_id", user_id).eq("achievement_id", aid).execute()
            if res.data:
                new_prog = (res.data[0]['progress'] or 0) + 1
                supabase.table("user_achievements").update({"progress": new_prog}).eq("user_id", user_id).eq("achievement_id", aid).execute()
            else:
                supabase.table("user_achievements").insert({"user_id": user_id, "achievement_id": aid, "progress": 1}).execute()
        except Exception as e:
            logger.error(f"Error incrementing achievement {aid} for {user_id}: {e}")


# --- БАЗА ДАННЫХ ---
def init_db():
    try:
        supabase.table("users").select("count", count="exact").limit(1).execute()
        logger.info("✅ Supabase connection verified")

        referral_tasks = [
            {"id": 1, "title": "Пригласить 1 друга", "reward": 1, "type": "referral_1", "url": "", "chat_id": ""},
            {"id": 2, "title": "Пригласить 2 друзей", "reward": 2, "type": "referral_2", "url": "", "chat_id": ""},
            {"id": 3, "title": "Пригласить 3 друзей", "reward": 3, "type": "referral_3", "url": "", "chat_id": ""},
            {"id": 4, "title": "Пригласить 4 друзей", "reward": 4, "type": "referral_4", "url": "", "chat_id": ""},
            {"id": 5, "title": "Пригласить 5 друзей", "reward": 5, "type": "referral_5", "url": "", "chat_id": ""},
        ]
        supabase.table("tasks").upsert(referral_tasks).execute()
        logger.info("✅ Base tasks initialized in Supabase")
    except Exception as e:
        logger.error(f"❌ Supabase initialization error: {e}")


# --- БЛОКЧЕЙН МОНИТОРИНГ ---
async def check_ton_transactions():
    """Фоновая задача для автоматической проверки платежей TON."""
    logger.info(f"📡 Запущен мониторинг TON кошелька: {TON_WALLET}")
    consecutive_errors = 0
    max_consecutive_errors = 5

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                params = {
                    "address": TON_WALLET,
                    "limit": 20,
                    "api_key": TONCENTER_API_KEY
                }
                async with session.get(
                    f"{TONCENTER_BASE_URL}/getTransactions",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"⚠️ Ошибка Toncenter API: {resp.status}")
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            logger.error("⚠️ Слишком много ошибок. Ждём 5 минут...")
                            await asyncio.sleep(300)
                            consecutive_errors = 0
                        else:
                            await asyncio.sleep(60)
                        continue

                    consecutive_errors = 0
                    result = await resp.json()
                    transactions = result.get("result", [])

                    for tx in transactions:
                        in_msg = tx.get("in_msg", {})
                        value = int(in_msg.get("value", 0))
                        if value == 0:
                            continue

                        tx_hash = tx.get("transaction_id", {}).get("hash")
                        comment = in_msg.get("message", "").strip()
                        if not comment and in_msg.get("msg_data", {}).get("@type") == "msg.dataText":
                            comment = in_msg.get("msg_data", {}).get("text", "").strip()

                        try:
                            if all(c in string.hexdigits for c in comment) and len(comment) % 2 == 0:
                                decoded = bytes.fromhex(comment).decode('utf-8', errors='ignore')
                                if "SC_" in decoded:
                                    comment = decoded
                        except:
                            pass

                        if not comment or not comment.startswith("SC_"):
                            continue

                        try:
                            parts = comment.split("_")
                            if len(parts) < 2:
                                continue
                            user_id = int(parts[1])

                            existing = supabase.table("ton_transactions").select("tx_id").eq("tx_id", tx_hash).execute()
                            if existing.data:
                                continue

                            amount_ton = value / 1_000_000_000
                            stars_to_add = int(amount_ton * 100)
                            if stars_to_add <= 0:
                                continue

                            logger.info(f"💰 Найдена оплата: {amount_ton} TON от {user_id} (TX: {tx_hash[:10]}...)")

                            supabase.table("ton_transactions").insert({
                                "tx_id": tx_hash,
                                "user_id": user_id,
                                "amount": amount_ton,
                                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }).execute()

                            user_res = supabase.table("users").select("stars, total_donated_ton").eq("user_id", user_id).execute()
                            if user_res.data:
                                u = user_res.data[0]
                                new_stars = u['stars'] + stars_to_add
                                new_donated_ton = (u.get('total_donated_ton') or 0.0) + amount_ton
                                supabase.table("users").update({
                                    "stars": new_stars,
                                    "total_donated_ton": new_donated_ton
                                }).eq("user_id", user_id).execute()

                                supabase.table("payments").insert({
                                    "user_id": user_id,
                                    "amount": stars_to_add,
                                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }).execute()

                                # Log deposit for promo-gate (last-24h tracking)
                                try:
                                    supabase.table("stars_deposits").insert({
                                        "user_id": user_id,
                                        "amount": int(stars_to_add),
                                        "source": "ton",
                                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    }).execute()
                                except Exception as _e:
                                    logger.warning(f"stars_deposits insert (ton) failed: {_e}")

                                try:
                                    await bot.send_message(user_id, f"✅ Оплата TON подтверждена!\n\nНа ваш баланс зачислено {stars_to_add} ⭐")
                                    logger.info(f"📩 Пользователь {user_id} уведомлен о зачислении.")
                                except Exception as e:
                                    logger.error(f"❌ Не удалось отправить сообщение юзеру: {e}")
                        except Exception as e:
                            logger.error(f"❌ Ошибка обработки транзакции {tx_hash}: {e}")

            except asyncio.TimeoutError:
                logger.warning("⚠️ Timeout при запросе к Toncenter")
                consecutive_errors += 1
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"❌ Ошибка мониторинга TON: {e}")
                consecutive_errors += 1
                await asyncio.sleep(60)

            await asyncio.sleep(30)


# --- ANTI-SLEEP SELF-PING ---
async def self_ping_task():
    """Пингует свой же /api/ping каждые 10 мин чтобы Render Free не засыпал."""
    base_url = os.getenv("RENDER_EXTERNAL_URL", "https://screamcasebot.onrender.com")
    ping_url = f"{base_url}/api/ping"

    await asyncio.sleep(30)
    logger.info(f"🔄 Self-ping запущен на {ping_url} (каждые 10 мин)")

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(ping_url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        logger.debug(f"✅ Self-ping ok ({resp.status})")
                    else:
                        logger.warning(f"⚠️ Self-ping вернул {resp.status}")
            except asyncio.TimeoutError:
                logger.warning("⚠️ Self-ping timeout")
            except Exception as e:
                logger.warning(f"⚠️ Self-ping error: {e}")

            await asyncio.sleep(600)


# --- MIDDLEWARE ---
@web.middleware
async def cors_middleware(request, handler):
    if request.method == 'OPTIONS':
        response = web.Response(status=200)
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
        response.headers['Access-Control-Allow-Headers'] = request.headers.get(
            'Access-Control-Request-Headers',
            'Content-Type, Authorization, X-Requested-With'
        )
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Max-Age'] = '86400'
        return response

    try:
        response = await handler(request)
    except web.HTTPException as ex:
        response = ex

    origin = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response


@web.middleware
async def auth_middleware(request, handler):
    if request.path in ['/', '/health', '/api/ping']:
        return await handler(request)

    if request.path.startswith('/api/'):
        init_data = None
        user_id_from_query = request.query.get("user_id")
        user_id_from_body = None
        body_json = None

        try:
            if request.method == 'POST':
                body_json = await request.json()
                request['body_json'] = body_json
                user_id_from_body = body_json.get("user_id")
                init_data = body_json.get('initData') or request.headers.get('Authorization', '').replace('Bearer ', '')
            else:
                init_data = request.query.get('initData') or request.headers.get('Authorization', '').replace('Bearer ', '')
        except Exception as e:
            logger.debug(f"Error extracting initData in middleware: {e}")
            init_data = request.headers.get('Authorization', '').replace('Bearer ', '')

        user_data = validate_init_data(init_data, TOKEN)

        # SECURITY: fallback to query/body user_id is gated behind DEBUG_AUTH env var.
        # In production (DEBUG_AUTH unset/false) ANY request without a valid initData signature is rejected.
        # Previously this fallback allowed full account takeover by passing arbitrary user_id.
        DEBUG_AUTH = os.getenv("DEBUG_AUTH", "").lower() in ("1", "true", "yes")
        if DEBUG_AUTH:
            if not user_data and request.method == 'GET' and user_id_from_query:
                try:
                    user_id_int = int(user_id_from_query)
                    logger.warning(f"⚠️ DEBUG: GET {request.path}: InitData invalid, using query user_id fallback (user={user_id_int})")
                    request['user_id'] = user_id_int
                    request['user_data'] = {'id': user_id_int}
                    return await handler(request)
                except (ValueError, TypeError):
                    pass

            if not user_data and request.method == 'POST' and user_id_from_body:
                try:
                    user_id_int = int(user_id_from_body)
                    logger.warning(f"⚠️ DEBUG: POST {request.path}: InitData invalid, using body user_id fallback (user={user_id_int})")
                    request['user_id'] = user_id_int
                    request['user_data'] = {'id': user_id_int}
                    return await handler(request)
                except (ValueError, TypeError):
                    pass

        if not user_data:
            logger.warning(f"❌ Unauthorized access attempt to {request.path} ({request.method})")
            return web.json_response({"error": "unauthorized", "message": "Invalid or expired authorization"}, status=401)

        request['user_id'] = int(user_data.get('id')) if user_data.get('id') else None
        request['user_data'] = user_data

    return await handler(request)

# --- БОТ ---
bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def start_cmd(message: types.Message, command: CommandObject):
    try:
        referred_by = command.args if command.args else None

        data, is_new = register_or_get(
            message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            photo_url=message.from_user.photo_url if hasattr(message.from_user, 'photo_url') else None,
            referred_by=referred_by
        )

        logger.info(f"User {message.from_user.id} balance: {data[0]} Stars")

        if is_new:
            logger.info(f"New user registered: {message.from_user.id} - {message.from_user.full_name}")
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id,
                        f"🚀 **Новый пользователь!**\n\n👤 Имя: {message.from_user.full_name}\n🆔 ID: `{message.from_user.id}`\n🏷 Юзернейм: @{message.from_user.username}",
                        parse_mode="Markdown")
                except Exception as e:
                    logger.error(f"Failed to notify admin: {e}")

            if referred_by and str(referred_by).isdigit():
                ref_id = int(referred_by)
                if ref_id != message.from_user.id:
                    try:
                        await bot.send_message(ref_id, f"🎉 По вашей ссылке перешел новый пользователь! Вы получили +1 билет 🎫")
                    except Exception as e:
                        logger.error(f"Failed to notify referrer: {e}")

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Открыть ScreamCase", web_app=WebAppInfo(url=APP_URL))],
            [InlineKeyboardButton(text="📢 Канал", url=CHANNEL_URL)]
        ])
        await message.answer(f"Привет! Твой баланс: {data[0]} ⭐", reply_markup=kb)
    except Exception as e:
        logger.error(f"Error in start_cmd: {e}")
        await message.answer("❌ Ошибка при запуске. Попробуйте позже.")


@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    try:
        text = "📖 **Команды бота**\n\n"
        text += "• `/start` — Запуск приложения\n"
        text += "• `/help` — Справка по командам\n"
        text += "• `/luck` — Уровень удачи\n"

        if message.from_user.id in ADMIN_IDS:
            text += "\n🛠 **Админ-панель:**\n"
            text += "• `/+ <число>` — Добавить себе звезд\n"
            text += "• `/setbalance <ID> <число>` — Установить баланс пользователю\n"
            text += "• `/user <ID>` — Информация об игроке\n"
            text += "• `/stats` — Общая статистика\n"
            text += "• `/admin_send <текст>` — Рассылка всем пользователям\n"
            text += "• `/hype <номер_шаблона>` — Маркетинговая рассылка\n"
            text += "\n🎟 **Промокоды:**\n"
            text += "• `/promo CODE MIN_DEPOSIT_24H DURATION_H` — Создать промокод\n"
            text += "  Юзер должен пополнить ≥MIN_DEPOSIT⭐ за 24ч; код живёт DURATION_H часов\n"
            text += "  Пример: `/promo WELCOME 50 24`\n"
            text += "• `/listpromo` — Список промокодов (топ 20)\n"
            text += "• `/delpromo CODE` — Деактивировать промокод\n"

        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in help_cmd: {e}")
        await message.answer("❌ Ошибка при получении справки.")


@dp.message(Command("luck"))
async def luck_cmd(message: types.Message):
    try:
        uid = message.from_user.id
        # Get user luck level
        user_res = supabase.table("users").select("luck_level").eq("user_id", uid).limit(1).execute()
        if not user_res.data:
            await message.answer("❌ Пользователь не найден. Запустите бота через /start")
            return

        luck = user_res.data[0].get("luck_level") or 0

        # Luck description
        luck_text = {
            0: "🎲 Обычная удача",
            1: "🍀 Слегка везучий",
            2: "✨ Везучий",
            3: "🌟 Очень везучий",
            4: "💎 Ультра везучий",
            5: "👑 Бог удачи"
        }.get(luck, "🎲 Обычная удача")

        await message.answer(f"🎯 **Ваш уровень удачи: {luck}**\n\n{luck_text}\n\nУдача влияет на шансы выпадения редких предметов из кейсов.")
    except Exception as e:
        logger.error(f"Error in luck_cmd: {e}")
        await message.answer("❌ Ошибка при получении уровня удачи.")



@dp.message(Command("+"))
async def admin_add(message: types.Message):
    try:
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("❌ Вы не администратор.")
            return

        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("❌ Пример: `/+ 100`", parse_mode="Markdown")
            return

        amount = int(parts[1])
        if amount <= 0:
            await message.answer("❌ Количество должно быть > 0.")
            return

        user_id = message.from_user.id
        res = supabase.table("users").select("stars").eq("user_id", user_id).execute()

        if not res.data:
            await message.answer("❌ Пользователь не найден в БД.")
            return

        current_stars = res.data[0].get('stars', 0)
        new_stars = current_stars + amount

        supabase.table("users").update({"stars": new_stars}).eq("user_id", user_id).execute()
        supabase.table("payments").insert({
            "user_id": user_id,
            "amount": amount,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }).execute()

        logger.info(f"✅ Admin {user_id} added {amount} stars. New balance: {new_stars}")
        await message.answer(f"✅ Добавлено {amount} ⭐\n💫 Новый баланс: {new_stars} ⭐")
    except ValueError:
        await message.answer("❌ Некорректное число. Пример: `/+ 100`", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in admin_add: {e}")
        await message.answer("❌ Ошибка при добавлении звезд.")


@dp.message(Command("setbalance"))
async def admin_set(message: types.Message):
    try:
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("❌ Вы не администратор.")
            return

        parts = message.text.split()
        if len(parts) < 3:
            await message.answer("❌ Пример: `/setbalance 123456 500`", parse_mode="Markdown")
            return

        target_id = int(parts[1])
        amount = int(parts[2])

        if amount < 0:
            await message.answer("❌ Количество не может быть отрицательным.")
            return

        update_balance(target_id, amount, "set")
        logger.info(f"Admin {message.from_user.id} set balance for {target_id} to {amount}")
        await message.answer(f"✅ Баланс ID `{target_id}` установлен на `{amount}` ⭐", parse_mode="Markdown")
    except ValueError:
        await message.answer("❌ Некорректные параметры.", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in admin_set: {e}")
        await message.answer("❌ Ошибка при установке баланса.")


@dp.message(Command("user"))
async def admin_user_info(message: types.Message):
    try:
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("❌ Вы не администратор.")
            return

        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("❌ Пример: `/user 123456`", parse_mode="Markdown")
            return

        user_id = int(parts[1])
        res = supabase.table("users").select("user_id, stars, join_date, total_donated_stars, total_donated_ton, tickets").eq("user_id", user_id).execute()

        if not res.data:
            await message.answer(f"❌ Пользователь `{user_id}` не найден.", parse_mode="Markdown")
            return

        user = res.data[0]
        text = f"""👤 **Информация о пользователе**
🆔 ID: `{user['user_id']}`
⭐ Баланс: `{user['stars']}`
🎫 Билеты: `{user.get('tickets', 0)}`
📅 Дата присоединения: `{user['join_date']}`
💎 Всего пожертвовано звёзд: `{user.get('total_donated_stars', 0)}`
💰 Всего пожертвовано TON: `{user.get('total_donated_ton', 0.0):.4f}`"""
        await message.answer(text, parse_mode="Markdown")
    except ValueError:
        await message.answer("❌ Некорректный ID пользователя.", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in admin_user_info: {e}")
        await message.answer("❌ Ошибка при получении информации.")


@dp.message(Command("stats"))
async def admin_stats(message: types.Message):
    try:
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("❌ Вы не администратор.")
            return

        count_res = supabase.table("users").select("*", count="exact").limit(1).execute()
        total_users = count_res.count if count_res.count is not None else 0

        total_stars = 0
        total_donated_stars = 0
        total_ton = 0.0

        limit = 1000
        offset = 0
        while True:
            batch = supabase.table("users").select("stars, total_donated_stars, total_donated_ton").range(offset, offset + limit - 1).execute()
            if not batch.data:
                break
            for u in batch.data:
                total_stars += u.get('stars', 0) or 0
                total_donated_stars += u.get('total_donated_stars', 0) or 0
                total_ton += u.get('total_donated_ton', 0.0) or 0.0
            if len(batch.data) < limit:
                break
            offset += limit

        total_issued = 0
        p_offset = 0
        while True:
            p_batch = supabase.table("payments").select("amount").gt("amount", 0).range(p_offset, p_offset + limit - 1).execute()
            if not p_batch.data:
                break
            total_issued += sum(p['amount'] for p in p_batch.data)
            if len(p_batch.data) < limit:
                break
            p_offset += limit

        text = f"""📊 **Глобальная статистика (Live)**
👥 Всего пользователей: `{total_users}`
⭐ Звёзд на балансах: `{total_stars}`
🎁 Звёзд выдано: `{total_issued}`
💎 Всего пополнено (Stars): `{total_donated_stars}`
💰 Всего пополнено (TON): `{total_ton:.4f}`"""

        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in admin_stats: {e}")
        await message.answer(f"❌ Ошибка при получении статистики: {e}")


@dp.message(Command("admin_send"))
async def admin_send(message: types.Message, command: CommandObject):
    try:
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("❌ Вы не администратор.")
            return

        text_to_send = (command.args or "").strip()
        if not text_to_send:
            await message.answer("❌ Пример: `/admin_send Текст рассылки`", parse_mode="Markdown")
            return

        await message.answer("⏳ Рассылка запущена...")

        res = supabase.table("users").select("user_id").execute()
        users = res.data

        sent = 0
        failed = 0
        for u in users:
            uid = u['user_id']
            try:
                await bot.send_message(uid, text_to_send)
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed += 1

        await message.answer(f"✅ Рассылка завершена.\nДоставлено: `{sent}`\nОшибок: `{failed}`", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in admin_send: {e}")
        await message.answer("❌ Ошибка при рассылке.")


@dp.message(Command("hype"))
async def admin_hype(message: types.Message, command: CommandObject):
    try:
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("❌ Вы не администратор.")
            return

        try:
            template_number = int((command.args or "").strip())
        except ValueError:
            await message.answer("❌ Пример: `/hype 1`\nДоступные шаблоны: 1-4", parse_mode="Markdown")
            return

        if template_number < 1 or template_number > len(HYPE_TEMPLATES):
            await message.answer("❌ Доступные шаблоны: 1-4")
            return

        template_index = template_number - 1
        await message.answer(f"⏳ Hype-рассылка #{template_number} запущена...")

        template = HYPE_TEMPLATES[template_index]

        res = supabase.table("users").select("user_id, username, first_name").execute()
        users = res.data

        sent = 0
        failed = 0
        for u in users:
            uid, username, first_name = u['user_id'], u.get('username'), u.get('first_name')
            try:
                clean_username = (username or first_name or "игрок").strip() or "игрок"
                text = template.format(
                    username=clean_username.lstrip("@"),
                    fake_id=random.randint(100000000, 9999999999),
                )
                await bot.send_message(uid, text)
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed += 1

        await message.answer(f"✅ Hype-рассылка завершена.\nДоставлено: `{sent}`\nОшибок: `{failed}`", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in admin_hype: {e}")
        await message.answer("❌ Ошибка при запуске hype-рассылки.")
async def check_membership(user_id: int):
    try:
        member = await bot.get_chat_member(chat_id="@ScreamCase", user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking membership for {user_id}: {e}")
        return False

# --- ПЛАТЁЖНАЯ СИСТЕМА TELEGRAM STARS ---

@dp.pre_checkout_query()
async def checkout(q: types.PreCheckoutQuery):
    try:
        await q.answer(ok=True)
        logger.info(f"Pre-checkout query approved for user {q.from_user.id}")
    except Exception as e:
        logger.error(f"Error in checkout: {e}")
        await q.answer(ok=False, error_message="Server error")

@dp.message(F.successful_payment)
async def success_pay(m: types.Message):
    try:
        payload = m.successful_payment.invoice_payload
        parts = payload.split("_")

        if len(parts) < 3 or parts[0] != "stars":
            logger.error(f"Invalid payload format: {payload}")
            await m.answer("❌ Ошибка при обработке платежа.")
            return

        user_id = int(parts[1])
        amount = int(parts[2])

        if user_id != m.from_user.id:
            logger.warning(f"Payment mismatch: payload={user_id}, sender={m.from_user.id}")
            await m.answer("❌ Ошибка при обработке платежа.")
            return

        update_balance(user_id, amount, "add", is_donation=True)
        # Log deposit for promo-gate (last-24h tracking)
        try:
            supabase.table("stars_deposits").insert({
                "user_id": user_id,
                "amount": int(amount),
                "source": "stars",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }).execute()
        except Exception as _e:
            logger.warning(f"stars_deposits insert (stars) failed: {_e}")
        logger.info(f"Payment successful for user {user_id}: +{amount} stars")
        await m.answer(f"✅ Спасибо за покупку! +{amount} ⭐")

        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id,
                    f"💰 **Новое пополнение!**\n👤 Юзер: {m.from_user.full_name} (`{user_id}`)\n⭐ Количество: `{amount}` звёзд",
                    parse_mode="Markdown")
            except:
                pass
    except Exception as e:
        logger.error(f"Error in success_pay: {e}")
        await m.answer("❌ Ошибка при обработке платежа.")

# --- API HANDLERS ---

async def api_heartbeat(request):
    try:
        uid = data.get('user_id') or data.get('uid')
        if uid:
            logger.debug(f"💓 Heartbeat от юзера {uid}")
        return web.json_response({"status": "alive", "timestamp": datetime.now().isoformat()})
    except Exception as e:
        logger.error(f"Error in heartbeat: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_check_sub(request):
    try:
        uid = request.query.get("user_id")
        if not uid:
            return web.json_response({"error": "no_id"}, status=400)
        is_member = await check_membership(int(uid))
        return web.json_response({"is_subscribed": is_member})
    except Exception as e:
        logger.error(f"Error in api_check_sub: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_balance(request):
    try:
        uid = data.get('user_id') or data.get('uid') or request.query.get("user_id")
        if not uid:
            return web.json_response({"error": "no_id", "ok": False}, status=400)

        uid = int(uid)
        res = supabase.table("users").select("stars, tickets, total_donated_stars, total_spent, promo_opened").eq("user_id", uid).execute()

        if not res.data:
            return web.json_response({"ok": True, "stars": 0, "tickets": 0, "donor": 0, "spent": 0, "promo_opened": 0})

        u = res.data[0]
        return web.json_response({
            "ok": True,
            "stars": u.get('stars', 0),
            "tickets": u.get('tickets', 0),
            "donor": u.get('total_donated_stars', 0),
            "spent": u.get('total_spent', 0),
            "promo_opened": u.get('promo_opened', 0)
        })
    except Exception as e:
        logger.error(f"Error in api_balance: {e}")
        return web.json_response({"error": "server_error", "ok": False}, status=500)

_bot_username_cache = None

async def _get_bot_username():
    """Caches bot username to avoid hitting Telegram API on every request."""
    global _bot_username_cache
    if _bot_username_cache:
        return _bot_username_cache
    try:
        me = await bot.get_me()
        _bot_username_cache = me.username
        return _bot_username_cache
    except Exception as e:
        logger.error(f"Failed to fetch bot username: {e}")
        return None

async def api_referral_link(request):
    """Returns the user's personal referral deeplink: t.me/<bot>?start=<uid>."""
    try:
        uid = request.query.get("user_id") or request.get('user_id')
        if not uid:
            return web.json_response({"error": "no_id"}, status=400)
        uid = int(uid)
        username = await _get_bot_username()
        if not username:
            return web.json_response({"error": "bot_unavailable"}, status=503)
        link = f"https://t.me/{username}?start={uid}"
        return web.json_response({"link": link, "bot_username": username, "user_id": uid})
    except Exception as e:
        logger.error(f"Error in api_referral_link: {e}")
        return web.json_response({"error": "server_error"}, status=500)


async def api_referrals(request):
    try:
        uid = request.query.get("user_id")
        if not uid:
            return web.json_response({"error": "no_id"}, status=400)

        uid = int(uid)
        res = supabase.table("users").select("user_id, username, first_name, photo_url, total_donated_stars").eq("referred_by", uid).execute()

        referrals = [{
            "user_id": r['user_id'],
            "username": r.get('username'),
            "first_name": r.get('first_name'),
            "photo_url": r.get('photo_url'),
            "donated": r.get('total_donated_stars', 0)
        } for r in res.data]

        return web.json_response({"count": len(referrals), "referrals": referrals})
    except Exception as e:
        logger.error(f"Error in api_referrals: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_open_case(request):
    try:
        data = request.get('body_json') or await request.json()
        uid = data.get('user_id') or data.get('uid')
        case_id = data.get("case_id")

        if not uid or case_id is None:
            return web.json_response({"error": "invalid_data", "ok": False}, status=400)

        case_id = int(case_id)
        uid = int(uid)

        if case_id == 2:
            res = await api_claim_daily_internal(uid)
            if res.status == 200:
                case_info = CASES_DATA.get(2)
                won_item = _get_random_gift(case_info['min'], case_info['max'])
                _increment_achievement_progress(uid, 'cases_opened')
                try:
                    supabase.rpc("increment_case_quests", {"p_user_id": uid}).execute()
                except Exception as e:
                    logger.error(f"Failed to increment case quests: {e}")
                logger.info(f"✅ User {uid} opened Daily Case, won: {won_item['name']}")
                return web.json_response({"ok": True, "success": True, "item": won_item, "deducted": 1})
            return res

        price = CASES_PRICES.get(case_id)
        if price is None:
            return web.json_response({"error": "invalid_case", "ok": False}, status=400)

        user_res = supabase.table("users").select("stars, total_spent, cases_opened_count").eq("user_id", uid).execute()
        if not user_res.data:
            return web.json_response({"error": "user_not_found", "ok": False}, status=404)

        u = user_res.data[0]
        balance = u.get('stars', 0)

        # PROMO CASE — server-side promo_code validation
        if case_id == 1:
            promo_code = (data.get("promo_code") or "").strip().upper()
            if not promo_code:
                return web.json_response({"error": "promo_code_required", "ok": False, "message": "Введите промокод"}, status=400)

            promo_res = supabase.table("promo_codes").select("code, min_deposit_24h, duration_hours, created_at, is_active").eq("code", promo_code).eq("is_active", True).execute()
            if not promo_res.data:
                return web.json_response({"error": "promo_invalid", "ok": False, "message": "Неверный промокод"}, status=403)

            promo = promo_res.data[0]
            # Duration window check (active for duration_hours hours since created_at)
            try:
                created_at = datetime.fromisoformat(str(promo['created_at']).replace('Z', '+00:00'))
                expires_at = created_at + timedelta(hours=int(promo.get('duration_hours') or 0))
                now_utc = datetime.now(timezone.utc)
                if now_utc > expires_at:
                    return web.json_response({"error": "promo_expired", "ok": False, "message": "Промокод истёк"}, status=403)
            except Exception as e:
                logger.warning(f"Promo duration check failed: {e}")

            # Deposit gate: user must have deposited >= min_deposit_24h within duration window (or last 24h)
            min_dep = int(promo.get('min_deposit_24h') or 0)
            if min_dep > 0:
                window_start = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
                dep_res = supabase.table("stars_deposits").select("amount").eq("user_id", uid).gte("created_at", window_start).execute()
                total_dep = sum(int(d.get('amount') or 0) for d in (dep_res.data or []))
                if total_dep < min_dep:
                    return web.json_response({
                        "error": "deposit_required", "ok": False,
                        "message": f"Требуется депозит {min_dep}⭐ за 24ч (у вас {total_dep}⭐)"
                    }, status=403)

            price = 0

        if balance < price:
            return web.json_response({
                "error": "insufficient_funds", "ok": False,
                "message": "Недостаточно звёзд для открытия кейса",
                "required": price, "balance": balance
            }, status=403)

        case_info = CASES_DATA.get(case_id)
        if not case_info:
            return web.json_response({"error": "case_data_missing", "ok": False}, status=500)

        won_item = _get_random_gift(case_info['min'], case_info['max'])
        new_spent = (u.get('total_spent') or 0) + price
        new_count = (u.get('cases_opened_count') or 0) + 1

        # Race-safe atomic decrement: only succeeds if stars are still >= price
        upd = supabase.table("users").update({
            "stars": balance - price,
            "total_spent": new_spent,
            "cases_opened_count": new_count
        }).eq("user_id", uid).eq("stars", balance).execute()
        if not upd.data:
            # Concurrent request modified balance between our read and write — abort
            logger.warning(f"User {uid} open_case race lost (concurrent balance change)")
            return web.json_response({"error": "concurrent_modification", "ok": False, "message": "Попробуйте ещё раз"}, status=409)

        try:
            supabase.table("user_inventory").insert({
                "user_id": uid,
                "case_id": case_id,
                "item_name": won_item['name'],
                "item_image": won_item['image'],
                "item_price": won_item['price'],
                "opened_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }).execute()
        except Exception as e:
            logger.error(f"Failed to save to user_inventory: {e}")

        supabase.table("payments").insert({
            "user_id": uid,
            "amount": -price,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }).execute()

        _increment_achievement_progress(uid, 'cases_opened')
        try:
            supabase.rpc("increment_case_quests", {"p_user_id": uid}).execute()
        except Exception as e:
            logger.error(f"Failed to increment case quests: {e}")

        logger.info(f"✅ User {uid} opened case {case_id}: won {won_item['name']} ({won_item['price']}). New balance: {balance - price}")

        return web.json_response({
            "ok": True, "success": True,
            "item": won_item, "deducted": price,
            "new_balance": balance - price
        })
    except Exception as e:
        logger.error(f"Error in api_open_case: {e}")
        return web.json_response({"error": "server_error", "ok": False}, status=500)

async def api_upgrade(request):
    """
    Server-authoritative upgrade:
    - Validates user OWNS source_item_id from inventory (no client trust)
    - Recomputes chance from real prices (ignores client chance)
    - Removes source from inventory on ANY outcome
    - Adds upgraded item to inventory on success only
    """
    try:
        data = request.get('body_json') or await request.json()
        uid = data.get('user_id') or data.get('uid')
        source_inv_id = data.get("source_inventory_id")
        target_name = (data.get("target_name") or "").strip()
        target_price = int(data.get("target_price", 0))

        if not uid or source_inv_id is None or not target_name or target_price <= 0:
            return web.json_response({"error": "invalid_data", "ok": False}, status=400)

        uid = int(uid)

        # 1) Verify user owns the source inventory item AND it has not been used
        inv_res = supabase.table("user_inventory").select("id, case_id, item_name, item_image, item_price, withdrawn").eq("user_id", uid).eq("id", source_inv_id).execute()
        if not inv_res.data:
            return web.json_response({"error": "source_not_found", "ok": False, "message": "Предмет не найден в инвентаре"}, status=404)

        source_item = inv_res.data[0]
        if source_item.get("withdrawn"):
            return web.json_response({"error": "source_used", "ok": False, "message": "Предмет уже использован"}, status=403)

        source_price = int(source_item.get("item_price") or 0)
        if source_price <= 0:
            return web.json_response({"error": "invalid_source_price", "ok": False}, status=400)

        # 2) Target must be strictly more expensive than source
        if target_price <= source_price:
            return web.json_response({"error": "invalid_target", "ok": False, "message": "Цель должна быть дороже"}, status=400)

        # 3) Recompute chance on server (ignore client)
        real_chance = (source_price / target_price) * 100.0
        # Cap to sane range
        if real_chance < 1: real_chance = 1.0
        if real_chance > 95: real_chance = 95.0

        # 4) Charge a small upgrade fee (10% of price diff, min 1 star)
        price_diff = target_price - source_price
        cost = max(1, int(price_diff * 0.10))

        user_res = supabase.table("users").select("stars, total_spent, successful_upgrades_count").eq("user_id", uid).execute()
        if not user_res.data:
            return web.json_response({"error": "user_not_found", "ok": False}, status=404)
        u = user_res.data[0]
        balance = int(u.get('stars') or 0)
        if balance < cost:
            return web.json_response({"error": "insufficient_funds", "ok": False, "message": f"Нужно {cost}⭐", "required": cost}, status=403)

        # 5) Roll
        success = random.random() * 100 < real_chance

        # 6) ALWAYS consume source item (mark withdrawn so it cannot be reused)
        supabase.table("user_inventory").update({"withdrawn": True}).eq("id", source_inv_id).eq("user_id", uid).execute()

        # 7) Apply outcome
        consolation = None
        new_spent = (u.get('total_spent') or 0) + cost
        updates = {"stars": balance - cost, "total_spent": new_spent}

        if success:
            updates["successful_upgrades_count"] = (u.get('successful_upgrades_count') or 0) + 1
            # Add upgraded item to inventory
            try:
                supabase.table("user_inventory").insert({
                    "user_id": uid,
                    "case_id": source_item.get("case_id") if isinstance(source_item, dict) else None,
                    "item_name": target_name,
                    "item_image": data.get("target_image") or "",
                    "item_price": target_price,
                    "opened_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }).execute()
            except Exception as e:
                logger.error(f"Failed to insert upgraded item: {e}")
            _increment_achievement_progress(uid, 'upgrades_successful')
        else:
            # Consolation if target was expensive
            if target_price > 100:
                consolation_item = _get_random_gift(0, 100)
                consolation = {"type": "poor_case", "item": consolation_item}
                try:
                    supabase.table("user_inventory").insert({
                        "user_id": uid,
                        "case_id": None,
                        "item_name": consolation_item['name'],
                        "item_image": consolation_item['image'],
                        "item_price": consolation_item['price'],
                        "opened_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }).execute()
                except Exception as e:
                    logger.error(f"Failed to insert consolation: {e}")

        supabase.table("users").update(updates).eq("user_id", uid).execute()
        supabase.table("payments").insert({
            "user_id": uid,
            "amount": -cost,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }).execute()

        logger.info(f"Upgrade user={uid} src={source_price}⭐ tgt={target_price}⭐ chance={real_chance:.1f}% cost={cost} success={success}")

        return web.json_response({
            "ok": True,
            "success": success,
            "chance": real_chance,
            "cost": cost,
            "consolation": consolation,
            "new_balance": balance - cost
        })
    except Exception as e:
        logger.error(f"Error in api_upgrade: {e}")
        return web.json_response({"error": "server_error", "ok": False}, status=500)

async def api_wheel_spin(request):
    """Wheel spin - drops ITEMS (not stars) into inventory."""
    try:
        data = request.get('body_json') or await request.json()
        uid = data.get('user_id') or data.get('uid')
        if not uid:
            return web.json_response({"error": "no_id"}, status=400)

        uid = int(uid)
        cost = 50

        WHEEL_SEGMENTS = [
            {"min": 15,   "max": 30,   "weight": 35.0},
            {"min": 30,   "max": 60,   "weight": 25.0},
            {"min": 60,   "max": 120,  "weight": 18.0},
            {"min": 120,  "max": 200,  "weight": 12.0},
            {"min": 200,  "max": 400,  "weight": 6.5},
            {"min": 400,  "max": 800,  "weight": 2.5},
            {"min": 800,  "max": 1500, "weight": 0.8},
            {"min": 1500, "max": 3000, "weight": 0.2},
        ]

        user_res = supabase.table("users").select("stars, total_spent").eq("user_id", uid).execute()
        if not user_res.data:
            return web.json_response({"error": "user_not_found"}, status=404)

        u = user_res.data[0]
        balance = u['stars']
        if balance < cost:
            return web.json_response({"error": "insufficient_funds"}, status=403)

        total_weight = sum(seg["weight"] for seg in WHEEL_SEGMENTS)
        rand = random.random() * total_weight
        acc = 0
        prize_index = 0
        for i, seg in enumerate(WHEEL_SEGMENTS):
            acc += seg["weight"]
            if rand <= acc:
                prize_index = i
                break

        seg = WHEEL_SEGMENTS[prize_index]
        gift = _get_random_gift(seg["min"], seg["max"])
        if not gift:
            return web.json_response({"error": "no_items_available"}, status=500)

        new_balance = balance - cost
        new_spent = (u.get('total_spent') or 0) + cost

        # Race-safe: only proceed if stars still equal what we read
        supabase.table("user_inventory").insert({
            "user_id": uid,
            "case_id": None,
            "item_name": gift["name"],
            "item_price": gift["price"],
            "item_image": gift["image"],
            "opened_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }).execute()

        # Deduct stars after successful inventory insert
        upd_u = supabase.table("users").update({"stars": new_balance, "total_spent": new_spent}).eq("user_id", uid).eq("stars", balance).execute()
        if not upd_u.data:
            logger.warning(f"User {uid} wheel_spin race lost (concurrent balance change)")
            return web.json_response({"error": "concurrent_modification"}, status=409)

        logger.info(f"User {uid} spun wheel: won {gift['name']} ({gift['price']} stars)")
        return web.json_response({
            "success": True,
            "prize_index": prize_index,
            "item": {
                "name": gift["name"],
                "price": gift["price"],
                "image": gift["image"]
            },
            "new_balance": new_balance
        })
    except Exception as e:
        logger.error(f"Error in api_wheel_spin: {e}", exc_info=True)
        return web.json_response({"error": "server_error"}, status=500)

async def api_claim_daily_internal(uid):
    """Daily case claim — 24h cooldown enforced via conditional update.
    Race-safe: UPDATE WHERE last_daily = <captured_value>. If 0 rows updated,
    another concurrent request already claimed.
    """
    try:
        uid = int(uid)
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        user_res = supabase.table("users").select("last_daily").eq("user_id", uid).execute()
        if not user_res.data:
            return web.json_response({"error": "user_not_found"}, status=404)

        last_daily_str = user_res.data[0].get('last_daily')

        # Cooldown check (pre-flight)
        if last_daily_str and last_daily_str != "1970-01-01 00:00:00":
            try:
                # Tolerate both "YYYY-MM-DD HH:MM:SS" and ISO formats
                ld_clean = last_daily_str.replace('T', ' ').split('.')[0].split('+')[0]
                last_daily = datetime.strptime(ld_clean, "%Y-%m-%d %H:%M:%S")
                time_diff = (now - last_daily).total_seconds()
                if time_diff < 86400:
                    wait_seconds = int(86400 - time_diff)
                    return web.json_response({"error": "daily_cooldown_active", "wait_seconds": wait_seconds}, status=403)
            except (ValueError, AttributeError):
                pass

        # Atomic conditional update: only succeeds if last_daily still equals what we read
        old_val = last_daily_str if last_daily_str else "1970-01-01 00:00:00"
        upd = supabase.table("users") \
            .update({"last_daily": now_str}) \
            .eq("user_id", uid) \
            .eq("last_daily", old_val) \
            .execute()

        if not upd.data:
            # Lost the race — another request updated last_daily between our read and write
            logger.info(f"User {uid} daily race lost (concurrent claim)")
            return web.json_response({"error": "daily_cooldown_active", "wait_seconds": 86400}, status=403)

        logger.info(f"User {uid} claimed daily case")
        return web.json_response({"success": True})
    except Exception as e:
        logger.error(f"Error in api_claim_daily_internal: {e}", exc_info=True)
        return web.json_response({"error": "server_error"}, status=500)

async def api_claim_daily(request):
    try:
        data = request.get('body_json') or await request.json()
        uid = data.get('user_id') or data.get('uid')
        if not uid:
            return web.json_response({"error": "unauthorized"}, status=401)
        return await api_claim_daily_internal(uid)
    except Exception as e:
        logger.error(f"Error in api_claim_daily: {e}")
        return web.json_response({"error": "server_error"}, status=500)
async def api_ton_success(request):
    try:
        uid = data.get('user_id') or data.get('uid')
        logger.info(f"🔄 Получено ручное уведомление об оплате от {uid}. Ожидаем подтверждения блокчейна...")
        return web.json_response({"success": True, "message": "Verification is now automatic. Please wait."})
    except Exception as e:
        logger.error(f"api_ton_success error: {e}")
        return web.json_response({"success": True})

async def api_invoice(request):
    """Генерирует данные для оплаты через TON."""
    try:
        data = request.get('body_json') or await request.json()
        user_id = request.get('user_id')

        if not user_id:
            return web.json_response({"error": "no_user_id"}, status=400)

        user_id = int(user_id)
        user_check = supabase.table("users").select("user_id").eq("user_id", user_id).limit(1).execute()
        if not user_check.data:
            return web.json_response({"error": "user_not_found"}, status=404)

        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        comment = f"SC_{user_id}_{random_str}"
        payload_boc = create_comment_boc(comment)

        logger.info(f"📝 Создан TON инвойс для {user_id}: {comment}")

        return web.json_response({
            "wallet": TON_WALLET,
            "comment": comment,
            "payload_boc": payload_boc,
            "rate": 100
        })
    except Exception as e:
        logger.error(f"Error in api_invoice: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_create_stars_invoice(request):
    """Generates a Telegram Stars (XTR) invoice with validation."""
    try:
        data = request.get('body_json') or await request.json()
        uid = data.get('user_id') or data.get('uid')
        amount = int(data.get("amount", 100))

        if not uid:
            return web.json_response({"error": "unauthorized"}, status=401)
        if amount < 1 or amount > 100000:
            return web.json_response({"error": "invalid_amount"}, status=400)

        link = await bot.create_invoice_link(
            title="Пополнение ⭐",
            description=f"Покупка {amount} звёзд для ScreamCase",
            payload=f"stars_{uid}_{amount}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=f"{amount} ⭐", amount=amount)]
        )
        logger.info(f"✅ Stars invoice created for user {uid}: {amount} stars")
        return web.json_response({"ok": True, "invoice_link": link})
    except Exception as e:
        logger.error(f"Stars invoice error: {e}", exc_info=True)
        return web.json_response({"error": "invoice_creation_failed", "details": str(e)}, status=500)

async def api_get_achievements(request):
    try:
        uid = data.get('user_id') or data.get('uid') or request.query.get("user_id")
        if not uid:
            return web.json_response({"error": "no_id"}, status=400)

        uid = int(uid)
        ACHIEVEMENTS = [
            {'id': 'first_step', 'title': 'Первый шаг', 'goal': 1, 'reward': 1},
            {'id': 'upgrade_master', 'title': 'Мастер Апгрейдов', 'goal': 3, 'reward': 15},
            {'id': 'ludoman', 'title': 'Истинный Лудоман', 'goal': 10, 'reward': 10}
        ]

        for a in ACHIEVEMENTS:
            try:
                supabase.table("user_achievements").upsert({"user_id": uid, "achievement_id": a['id']}, on_conflict="user_id,achievement_id").execute()
            except:
                pass

        res = supabase.table("user_achievements").select("achievement_id, progress, is_claimed").eq("user_id", uid).execute()

        data = []
        for r in res.data:
            aid, prog, claimed = r['achievement_id'], r['progress'], r['is_claimed']
            info = next((a for a in ACHIEVEMENTS if a['id'] == aid), None)
            if info:
                data.append({**info, "progress": prog or 0, "is_claimed": bool(claimed)})

        return web.json_response(data)
    except Exception as e:
        logger.error(f"Error in api_get_achievements: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_claim_achievement(request):
    try:
        data = request.get('body_json') or await request.json()
        uid = data.get('user_id') or data.get('uid')
        aid = data.get("achievement_id")

        if not uid or not aid:
            return web.json_response({"error": "invalid_data"}, status=400)

        ACHIEVEMENTS = [
            {'id': 'first_step', 'title': 'Первый шаг', 'goal': 1, 'reward': 1},
            {'id': 'upgrade_master', 'title': 'Мастер Апгрейдов', 'goal': 3, 'reward': 15},
            {'id': 'ludoman', 'title': 'Истинный Лудоман', 'goal': 10, 'reward': 10}
        ]

        info = next((a for a in ACHIEVEMENTS if a['id'] == aid), None)
        if not info:
            return web.json_response({"error": "achievement_not_found"}, status=404)

        uid = int(uid)
        res = supabase.table("user_achievements").select("progress, is_claimed").eq("user_id", uid).eq("achievement_id", aid).execute()
        if not res.data:
            return web.json_response({"error": "not_found"}, status=404)

        a_status = res.data[0]
        if a_status['is_claimed']:
            return web.json_response({"error": "already_claimed"}, status=400)
        if a_status['progress'] < info['goal']:
            return web.json_response({"error": "not_reached"}, status=400)

        # Race-safe: only the request that flips is_claimed 0->1 grants the reward
        claim_upd = supabase.table("user_achievements").update({"is_claimed": 1}) \
            .eq("user_id", uid).eq("achievement_id", aid).eq("is_claimed", 0).execute()
        if not claim_upd.data:
            return web.json_response({"error": "already_claimed"}, status=400)

        user_res = supabase.table("users").select("stars").eq("user_id", uid).execute()
        if user_res.data:
            new_stars = user_res.data[0]['stars'] + info['reward']
            supabase.table("users").update({"stars": new_stars}).eq("user_id", uid).execute()
            supabase.table("payments").insert({
                "user_id": uid,
                "amount": info['reward'],
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }).execute()

        return web.json_response({"success": True, "reward": info['reward']})
    except Exception as e:
        logger.error(f"Error in api_claim_achievement: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_get_quests(request):
    try:
        uid = data.get('user_id') or data.get('uid')
        if not uid:
            return web.json_response({"error": "unauthorized"}, status=401)
        uid = int(uid)

        res = supabase.table("user_quests").select("quest_id, progress, is_completed, reward_claimed").eq("user_id", uid).execute()
        quests_data = {row['quest_id']: row for row in res.data} if res.data else {}

        QUESTS = [
            {'id': 'open_1', 'title': 'Открыть 1 кейс', 'goal': 1, 'reward': 10},
            {'id': 'open_5', 'title': 'Открыть 5 кейсов', 'goal': 5, 'reward': 50},
            {'id': 'open_10', 'title': 'Открыть 10 кейсов', 'goal': 10, 'reward': 150}
        ]

        response_data = []
        for q in QUESTS:
            user_q = quests_data.get(q['id'], {})
            response_data.append({
                "id": q['id'], "title": q['title'], "goal": q['goal'], "reward": q['reward'],
                "progress": user_q.get('progress', 0),
                "is_completed": user_q.get('is_completed', False),
                "is_claimed": user_q.get('reward_claimed', False)
            })

        return web.json_response(response_data)
    except Exception as e:
        logger.error(f"Error in api_get_quests: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_claim_quest(request):
    try:
        data = request.get('body_json') or await request.json()
        uid = data.get('user_id') or data.get('uid')
        quest_id = data.get("quest_id")

        if not uid or not quest_id:
            return web.json_response({"error": "invalid_data"}, status=400)
        uid = int(uid)

        QUESTS = {
            'open_1': {'goal': 1, 'reward': 10},
            'open_5': {'goal': 5, 'reward': 50},
            'open_10': {'goal': 10, 'reward': 150}
        }

        info = QUESTS.get(quest_id)
        if not info:
            return web.json_response({"error": "quest_not_found"}, status=404)

        res = supabase.table("user_quests").select("is_completed, reward_claimed").eq("user_id", uid).eq("quest_id", quest_id).execute()
        if not res.data:
            return web.json_response({"error": "not_found"}, status=404)

        q_status = res.data[0]
        if q_status['reward_claimed']:
            return web.json_response({"error": "already_claimed"}, status=400)
        if not q_status['is_completed']:
            return web.json_response({"error": "not_reached"}, status=400)

        # Race-safe: only the request that flips reward_claimed false->true grants
        claim_upd = supabase.table("user_quests").update({"reward_claimed": True}) \
            .eq("user_id", uid).eq("quest_id", quest_id).eq("reward_claimed", False).execute()
        if not claim_upd.data:
            return web.json_response({"error": "already_claimed"}, status=400)

        user_res = supabase.table("users").select("stars").eq("user_id", uid).execute()
        if user_res.data:
            new_stars = user_res.data[0]['stars'] + info['reward']
            supabase.table("users").update({"stars": new_stars}).eq("user_id", uid).execute()
            supabase.table("payments").insert({
                "user_id": uid,
                "amount": info['reward'],
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }).execute()

        return web.json_response({"success": True, "reward": info['reward']})
    except Exception as e:
        logger.error(f"Error in api_claim_quest: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_cases(request):
    try:
        CASES_LIST = [
            {"id": 1, "name": "Promo Case", "price": 0, "color": "#FFD700", "icon": "🎁", "description": "Бесплатный кейс (один раз)"},
            {"id": 2, "name": "Daily Case", "price": 1, "color": "#87CEEB", "icon": "📅", "description": "Ежедневный кейс"},
            {"id": 3, "name": "Snoop Case", "price": 15, "color": "#00AA00", "icon": "😎", "description": "Кейс Snoop Dogg"},
            {"id": 4, "name": "Lover's Case", "price": 25, "color": "#FF1493", "icon": "💕", "description": "Любовный кейс"},
            {"id": 5, "name": "Hobo Case", "price": 5, "color": "#8B8B8B", "icon": "🧤", "description": "Бродяжный кейс"},
            {"id": 6, "name": "Risky Box", "price": 10, "color": "#FF8C00", "icon": "⚡", "description": "Рискованный ящик"},
            {"id": 7, "name": "Scam Box", "price": 50, "color": "#DC143C", "icon": "⚠️", "description": "Подозрительный ящик"},
            {"id": 8, "name": "Ebati Case", "price": 100, "color": "#4B0082", "icon": "👑", "description": "Королевский кейс"},
            {"id": 9, "name": "Pussy Case", "price": 75, "color": "#FF69B4", "icon": "🐱", "description": "Кошачий кейс"},
            {"id": 10, "name": "Skolnik Case", "price": 150, "color": "#FFD700", "icon": "🎓", "description": "Элитный кейс"}
        ]

        response = []
        for case_id, case_data in CASES_DATA.items():
            case_info = next((c for c in CASES_LIST if c["id"] == case_id), None)
            if case_info:
                response.append({**case_info, "min_drop": case_data['min'], "max_drop": case_data['max']})

        return web.json_response(sorted(response, key=lambda x: x['id']))
    except Exception as e:
        logger.error(f"Error in api_cases: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_inventory(request):
    try:
        uid = data.get('user_id') or data.get('uid')
        if not uid:
            return web.json_response({"error": "unauthorized"}, status=401)

        uid = int(uid)
        res = supabase.table("user_inventory").select("*").eq("user_id", uid).execute()

        if not res.data:
            return web.json_response({"user_id": uid, "total_items": 0, "items": []})

        items_by_name = {}
        for item in res.data:
            name = item.get('item_name')
            if name not in items_by_name:
                items_by_name[name] = {
                    "name": name, "image": item.get('item_image'),
                    "price": item.get('item_price', 0), "count": 0, "items": []
                }
            items_by_name[name]["count"] += 1
            items_by_name[name]["items"].append({
                "id": item.get('id'), "case_id": item.get('case_id'), "opened_at": item.get('opened_at')
            })

        inventory = list(items_by_name.values())
        return web.json_response({
            "user_id": uid,
            "total_items": sum(item['count'] for item in inventory),
            "total_value": sum(item['count'] * item['price'] for item in inventory),
            "items": inventory
        })
    except Exception as e:
        logger.error(f"Error in api_inventory: {e}")
        return web.json_response({"error": "server_error"}, status=500)

# --- ФОНОВЫЕ ЗАДАЧИ И ЗАПУСК ---

async def background_tasks(app):
    app['ton_monitor'] = asyncio.create_task(check_ton_transactions())
    app['self_ping'] = asyncio.create_task(self_ping_task())
    yield
    for task_name in ('ton_monitor', 'self_ping'):
        if task_name in app:
            app[task_name].cancel()
            try:
                await app[task_name]
            except asyncio.CancelledError:
                pass

async def root_handler(request):
    return web.Response(text="OK", status=200)

async def health_handler(request):
    return web.json_response({"status": "healthy", "timestamp": datetime.now().isoformat()})

async def api_ping(request):
    return web.json_response({
        "ok": True, "status": "pong",
        "timestamp": datetime.now().isoformat(),
        "message": "Сервер активен"
    })


# ============================================
# PROMO CODES
# ============================================

@dp.message(Command("promo"))
async def admin_create_promo(message: types.Message):
    """Admin: /promo CODE MIN_DEPOSIT_24H DURATION_HOURS
    CODE              - alphanumeric (uppercased)
    MIN_DEPOSIT_24H   - минимум ⭐ пополнений за последние 24ч до активации
    DURATION_HOURS    - срок жизни промокода в часах (общий)
    Пример: /promo PROMO 50 1  →  код PROMO, нужно ≥50⭐/24ч, действует 1ч.
    """
    try:
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("❌ Вы не администратор.")
            return

        parts = message.text.split()
        # Accept: /promo CODE MIN_DEPOSIT DURATION_H  (4 parts incl. command)
        # Also accept: /promo CODE MIN_DEPOSIT USES DURATION_H (5 parts, legacy STARS USES DAYS form — middle arg ignored)
        if len(parts) not in (4, 5):
            await message.answer(
                "❌ Использование: `/promo CODE MIN_DEPOSIT_24H DURATION_HOURS`\n"
                "Пример: `/promo PROMO 50 1`\n"
                "→ код `PROMO`, нужно ≥50⭐ депозитов за 24ч, действует 1ч.",
                parse_mode="Markdown"
            )
            return

        code = parts[1].strip().upper()
        if not code.isalnum() or len(code) > 32:
            await message.answer("❌ Код должен быть alphanumeric, до 32 символов.")
            return

        try:
            if len(parts) == 4:
                min_deposit = int(parts[2])
                duration_h = int(parts[3])
            else:  # 5 parts: CODE MIN_DEP <ignored> DURATION_H
                min_deposit = int(parts[2])
                duration_h = int(parts[4])
        except ValueError:
            await message.answer("❌ MIN_DEPOSIT_24H и DURATION_HOURS должны быть числами.")
            return
        if min_deposit < 0 or min_deposit > 1000000:
            await message.answer("❌ MIN_DEPOSIT_24H должно быть 0..1000000.")
            return
        if duration_h <= 0 or duration_h > 8760:
            await message.answer("❌ DURATION_HOURS должно быть 1..8760.")
            return

        existing = supabase.table("promo_codes").select("id").eq("code", code).limit(1).execute()
        if existing.data:
            await message.answer(f"❌ Код `{code}` уже существует.", parse_mode="Markdown")
            return

        supabase.table("promo_codes").insert({
            "code": code,
            "min_deposit_24h": min_deposit,
            "duration_hours": duration_h,
            "created_by": message.from_user.id,
            "is_active": True
        }).execute()

        await message.answer(
            f"✅ Промокод создан\n"
            f"🔑 `{code}`\n"
            f"💰 мин. пополнение за 24ч: {min_deposit}⭐\n"
            f"⏰ срок жизни: {duration_h}ч",
            parse_mode="Markdown"
        )
        logger.info(f"Admin {message.from_user.id} created promo {code}: min_deposit={min_deposit}, duration={duration_h}h")
    except ValueError:
        await message.answer("❌ Некорректные числа.")
    except Exception as e:
        logger.error(f"Error in admin_create_promo: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {e}")


@dp.message(Command("listpromo"))
async def admin_list_promo(message: types.Message):
    try:
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("❌ Вы не администратор.")
            return

        res = supabase.table("promo_codes").select("code, min_deposit_24h, duration_hours, created_at, is_active").order("created_at", desc=True).limit(20).execute()
        if not res.data:
            await message.answer("📭 Промокодов нет.")
            return

        now = datetime.now()
        lines_out = ["🎟 *Промокоды (последние 20):*\n"]
        for p in res.data:
            alive = "🟢"
            try:
                created = datetime.strptime(str(p['created_at']).replace('T', ' ').split('.')[0].split('+')[0], "%Y-%m-%d %H:%M:%S")
                expires = created + timedelta(hours=int(p['duration_hours']))
                if (now > expires) or (not p['is_active']):
                    alive = "🔴"
            except Exception:
                alive = "🟢" if p['is_active'] else "🔴"
            lines_out.append(f"{alive} `{p['code']}` — мин. {p['min_deposit_24h']}⭐/24ч — живёт {p['duration_hours']}ч")

        await message.answer("\n".join(lines_out), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in admin_list_promo: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {e}")


@dp.message(Command("delpromo"))
async def admin_delete_promo(message: types.Message):
    try:
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("❌ Вы не администратор.")
            return
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("❌ Использование: `/delpromo CODE`", parse_mode="Markdown")
            return
        code = parts[1].strip().upper()
        res = supabase.table("promo_codes").update({"is_active": False}).eq("code", code).execute()
        if not res.data:
            await message.answer(f"❌ Код `{code}` не найден.", parse_mode="Markdown")
            return
        await message.answer(f"✅ Промокод `{code}` деактивирован.", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in admin_delete_promo: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {e}")


async def api_redeem_promo(request):
    """POST /api/redeem_promo  body: {code: str}
    Promo v2: код валиден IFF
      (a) is_active = TRUE,
      (b) created_at + duration_hours ещё не истёк (общий срок жизни),
      (c) у юзера ≥ min_deposit_24h ⭐ пополнений за последние 24 часа.
    На успех: открывает PROMO CASE → случайный гифт 0..599⭐, кладёт в инвентарь.
    """
    try:
        data = request.get('body_json') or await request.json()
        uid = data.get('user_id') or data.get('uid')
        if not uid:
            return web.json_response({"success": False, "error": "unauthorized"}, status=401)
        uid = int(uid)

        code = (data.get("code") or "").strip().upper()
        if not code or not code.isalnum() or len(code) > 32:
            return web.json_response({"success": False, "error": "invalid_code"}, status=400)

        # Fetch promo
        promo_res = supabase.table("promo_codes").select("*").eq("code", code).eq("is_active", True).limit(1).execute()
        if not promo_res.data:
            return web.json_response({"success": False, "error": "code_not_found"}, status=404)
        promo = promo_res.data[0]

        # Global lifetime
        try:
            created = datetime.strptime(str(promo['created_at']).replace('T', ' ').split('.')[0].split('+')[0], "%Y-%m-%d %H:%M:%S")
            expires = created + timedelta(hours=int(promo['duration_hours']))
            if datetime.now() > expires:
                return web.json_response({"success": False, "error": "code_expired"}, status=403)
        except Exception as e:
            logger.warning(f"promo lifetime parse error for {code}: {e}")

        # Auto-create user if missing
        user_res = supabase.table("users").select("stars").eq("user_id", uid).limit(1).execute()
        if not user_res.data:
            try:
                supabase.table("users").insert({"user_id": uid, "stars": 0}).execute()
                current_stars = 0
                logger.info(f"Auto-created user {uid} during promo redemption")
            except Exception as e:
                logger.error(f"Failed to auto-create user {uid}: {e}")
                return web.json_response({"success": False, "error": "user_not_found"}, status=404)
        else:
            current_stars = int(user_res.data[0].get('stars', 0))

        # Deposit gate
        min_dep = int(promo.get('min_deposit_24h') or 0)
        if min_dep > 0:
            since = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
            dep_res = supabase.table("stars_deposits").select("amount").eq("user_id", uid).gte("created_at", since).execute()
            total_dep = sum(int(r.get("amount", 0)) for r in (dep_res.data or []))
            if total_dep < min_dep:
                return web.json_response({
                    "success": False,
                    "error": "insufficient_deposit",
                    "required": min_dep,
                    "have": total_dep
                }, status=403)

        # Open PROMO CASE → случайный гифт 0..599⭐
        reward_value = random.randint(0, 599)
        gift = {
            "name": f"Подарок {reward_value}⭐",
            "price": reward_value,
            "image": "/asset/Gifts/Case.webp"
        }

        try:
            supabase.table("user_inventory").insert({
                "user_id": uid,
                "case_id": 1,
                "item_name": gift["name"],
                "item_price": gift["price"],
                "item_image": gift["image"],
                "opened_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }).execute()
        except Exception as e:
            logger.error(f"Failed to grant PROMO CASE gift to {uid}: {e}")
            return web.json_response({"success": False, "error": "server_error"}, status=500)

        logger.info(f"User {uid} opened PROMO CASE via code {code} -> {reward_value}⭐ gift")
        
        # Mark promo case as opened
        supabase.table("users").update({"promo_opened": True}).eq("user_id", uid).execute()
        return web.json_response({
            "success": True,
            "code": code,
            "item": gift,
            "new_balance": current_stars
        })
    except Exception as e:
        logger.error(f"Error in api_redeem_promo: {e}", exc_info=True)
        return web.json_response({"success": False, "error": "server_error"}, status=500)



async def main():
    init_db()

    # ВАЖНО: cors_middleware ДОЛЖЕН быть первым
    app = web.Application(middlewares=[cors_middleware, auth_middleware])
    app.cleanup_ctx.append(background_tasks)

    app.router.add_get('/', root_handler)
    app.router.add_get('/health', health_handler)
    app.router.add_get('/api/ping', api_ping)
    app.router.add_post('/api/heartbeat', api_heartbeat)
    app.router.add_get('/api/check_sub', api_check_sub)
    app.router.add_get('/api/balance', api_balance)
    app.router.add_get('/api/referrals', api_referrals)
    app.router.add_get('/api/referral_link', api_referral_link)
    app.router.add_get('/api/cases', api_cases)
    app.router.add_get('/api/inventory', api_inventory)
    app.router.add_post('/api/open_case', api_open_case)
    app.router.add_post('/api/claim_daily', api_claim_daily)
    app.router.add_post('/api/redeem_promo', api_redeem_promo)
    app.router.add_post('/api/create_invoice', api_invoice)              # TON оплата
    app.router.add_post('/api/create_stars_invoice', api_create_stars_invoice)  # Telegram Stars
    app.router.add_post('/api/ton_success', api_ton_success)
    app.router.add_post('/api/wheel/spin', api_wheel_spin)
    app.router.add_post('/api/upgrade', api_upgrade)
    app.router.add_get('/api/achievements', api_get_achievements)
    app.router.add_post('/api/achievements/claim', api_claim_achievement)
    app.router.add_get('/api/quests', api_get_quests)
    app.router.add_post('/api/quests/claim', api_claim_quest)

    port = int(os.getenv("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"✅ API сервер запущен на порту {port}")

    logger.info("✅ Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
