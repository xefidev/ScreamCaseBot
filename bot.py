import logging
import asyncio
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from aiohttp import web
import aiohttp_cors
import hashlib
import string
import random
from supabase import create_client, Client
from dotenv import load_dotenv

# --- НАСТРОЙКИ ---
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = [7782281997, 5396975347]
APP_URL = os.getenv("APP_URL", "https://scream-case-bot.vercel.app")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/ScreamCase")

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("VITE_SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logging.error("Supabase URL or Key is missing. Check your .env file.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

HYPE_TEMPLATES = [
    "@{username}, 20 секунд назад пользователь id {fake_id} выиграл Astral Shard за 20К ⭐\n\n🔥 Испытай свою удачу, твои шансы на победу в платной рулетке увеличены на 34% (всего на час)!",
    "🚨 СКИДКА ДО КРИТИЧЕСКОГО МИНИМУМА!\n\nТолько в ближайшие 30 минут стоимость открытия 'Scream Case' снижена! Успей забрать топовые подарки, пока админ спит. Шанс дропа окупаемого дропа повышен x2!",
    "🎁 Бонус выходного дня!\n\nКаждый, кто зайдет в приложение прямо сейчас, получит +2 бесплатных тикета на баланс! Не упусти халяву, заходи в профиль!",
    "🌙 Ночной режим активирован.\n\nПо статистике, именно ночью выпадает самый дорогой дроп. Прямо сейчас кто-то крутит рулетку и забирает сочные призы. А чего ждешь ты? Твой бонусный процент на удачу уже активирован!",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN)
dp = Dispatcher()

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

def get_gifts_in_range(min_p, max_p):
    return [g for g in ALL_GIFTS if g['price'] >= min_p and g['price'] <= max_p]

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
        return (0, ""), False

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

# --- CASE DATA (Server Side) ---
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

CASES_PRICES = {
    1: 0,   # Promo Case (Free once)
    2: 1,   # Daily Case (1 Star)
    3: 667, # Snoop Case
    4: 599, # Lover's Case
    5: 199, # Hobo Case
    6: 50,  # Risky Box
    7: 111, # Scam Box
    8: 444, # Ebati Case
    9: 222, # Pussy Case
    10: 250 # Skolnik Case
}

# --- ОБРАБОТКА КОМАНД ---

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
        
        if message.from_user.id in ADMIN_IDS:
            text += "\n🛠 **Админ-панель:**\n"
            text += "• `/+ <число>` — Добавить себе звезд\n"
            text += "• `/setbalance <ID> <число>` — Установить баланс пользователю\n"
            text += "• `/user <ID>` — Информация об игроке\n"
            text += "• `/stats` — Общая статистика\n"
            text += "• `/admin_send <текст>` — Рассылка всем пользователям\n"
            text += "• `/hype <номер_шаблона>` — Маркетинговая рассылка\n"
        
        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in help_cmd: {e}")
        await message.answer("❌ Ошибка при получении справки.")

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
        
        update_balance(message.from_user.id, amount, "add")
        logger.info(f"Admin {message.from_user.id} added {amount} stars to themselves")
        await message.answer(f"✅ Добавлено {amount} ⭐")
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
🎫 Билеты: `{user['tickets']}`
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
        
        # 1. Получаем точное количество пользователей
        count_res = supabase.table("users").select("*", count="exact").limit(1).execute()
        total_users = count_res.count if count_res.count is not None else 0

        # 2. Считаем суммы через пагинацию (Supabase возвращает максимум 1000 строк за раз)
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
                total_stars += u.get('stars', 0)
                total_donated_stars += u.get('total_donated_stars', 0)
                total_ton += u.get('total_donated_ton', 0.0)
            
            if len(batch.data) < limit:
                break
            offset += limit

        # 3. Считаем выданные звезды из таблицы платежей
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

# --- API ДЛЯ САЙТА ---

async def api_check_sub(request):
    try:
        uid = request.query.get("user_id")
        if not uid: return web.json_response({"error": "no_id"}, status=400)
        
        is_member = await check_membership(int(uid))
        return web.json_response({"is_subscribed": is_member})
    except Exception as e:
        logger.error(f"Error in api_check_sub: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_balance(request):
    try:
        uid = request.query.get("user_id")
        if not uid:
            return web.json_response({"error": "no_id"}, status=400)
        
        res = supabase.table("users").select("stars, tickets, total_donated_stars, total_spent, promo_opened").eq("user_id", int(uid)).execute()
        
        if not res.data:
            return web.json_response({"stars": 0, "tickets": 0, "donor": 0, "spent": 0, "promo_opened": 0})
            
        u = res.data[0]
        return web.json_response({
            "stars": u['stars'], 
            "tickets": u['tickets'],
            "donor": u.get('total_donated_stars', 0),
            "spent": u.get('total_spent', 0),
            "promo_opened": u.get('promo_opened', 0)
        })
    except ValueError:
        return web.json_response({"error": "invalid_user_id"}, status=400)
    except Exception as e:
        logger.error(f"Error in api_balance: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_referrals(request):
    try:
        uid = request.query.get("user_id")
        if not uid:
            return web.json_response({"error": "no_id"}, status=400)
        
        uid = int(uid)
        res = supabase.table("users").select("user_id, username, first_name, photo_url, total_donated_stars").eq("referred_by", uid).execute()
        
        referrals = [
            {
                "user_id": r['user_id'],
                "username": r.get('username'),
                "first_name": r.get('first_name'),
                "photo_url": r.get('photo_url'),
                "donated": r.get('total_donated_stars', 0)
            } for r in res.data
        ]
        
        return web.json_response({
            "count": len(referrals),
            "referrals": referrals
        })
    except ValueError:
        return web.json_response({"error": "invalid_user_id"}, status=400)
    except Exception as e:
        logger.error(f"Error in api_referrals: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_open_case(request):
    try:
        data = await request.json()
        uid = data.get("user_id")
        case_id = data.get("case_id")
        
        if not uid or case_id is None:
            return web.json_response({"error": "invalid_data"}, status=400)
        
        case_id = int(case_id)
        uid = int(uid)
        
        # Daily Case
        if case_id == 2: 
            res = await api_claim_daily_internal(uid)
            if res.status == 200:
                case_info = CASES_DATA.get(2)
                won_item = _get_random_gift(case_info['min'], case_info['max'])
                _increment_achievement_progress(uid, 'cases_opened')
                return web.json_response({"success": True, "item": won_item, "deducted": 1})
            return res

        price = CASES_PRICES.get(case_id)
        if price is None:
            return web.json_response({"error": "invalid_case"}, status=400)
        
        user_res = supabase.table("users").select("stars, promo_opened, total_spent, cases_opened_count").eq("user_id", uid).execute()
        if not user_res.data: return web.json_response({"error": "user_not_found"}, status=404)
        
        u = user_res.data[0]
        balance = u['stars']
        promo_opened = u.get('promo_opened', 0)
        
        # Promo Case
        if case_id == 1:
            if promo_opened:
                return web.json_response({"error": "already_opened"}, status=403)
            supabase.table("users").update({"promo_opened": 1}).eq("user_id", uid).execute()
            price = 0

        if balance < price:
            return web.json_response({"error": "insufficient_funds"}, status=403)
        
        case_info = CASES_DATA.get(case_id)
        if not case_info:
            return web.json_response({"error": "case_data_missing"}, status=500)
        
        won_item = _get_random_gift(case_info['min'], case_info['max'])

        new_spent = (u.get('total_spent') or 0) + price
        new_count = (u.get('cases_opened_count') or 0) + 1
        supabase.table("users").update({
            "stars": balance - price, 
            "total_spent": new_spent, 
            "cases_opened_count": new_count
        }).eq("user_id", uid).execute()

        supabase.table("payments").insert({
            "user_id": uid, 
            "amount": -price, 
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }).execute()
        
        _increment_achievement_progress(uid, 'cases_opened')
        
        logger.info(f"User {uid} opened case {case_id}: won {won_item['name']} ({won_item['price']}).")
        
        return web.json_response({
            "success": True, 
            "item": won_item,
            "deducted": price
        })
    except Exception as e:
        logger.error(f"Error in api_open_case: {e}")
        return web.json_response({"error": "server_error"}, status=500)

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

async def api_upgrade(request):
    try:
        data = await request.json()
        uid = data.get("user_id")
        cost = int(data.get("cost", 0))
        chance = float(data.get("chance", 0))
        item_price = int(data.get("item_price", 0))
        
        if not uid: return web.json_response({"error": "no_id"}, status=400)
        
        user_res = supabase.table("users").select("stars, total_spent, successful_upgrades_count").eq("user_id", int(uid)).execute()
        if not user_res.data: return web.json_response({"error": "user_not_found"}, status=404)
        
        u = user_res.data[0]
        balance = u['stars']
        if balance < cost:
            return web.json_response({"error": "insufficient_funds"}, status=403)
        
        success = random.random() * 100 < chance
        
        consolation = None
        if not success and item_price > 100:
            consolation_item = _get_random_gift(0, 100)
            consolation = {
                "type": "poor_case",
                "item": consolation_item
            }

        new_spent = (u.get('total_spent') or 0) + cost
        updates = {"stars": balance - cost, "total_spent": new_spent}
        
        if success:
            updates["successful_upgrades_count"] = (u.get('successful_upgrades_count') or 0) + 1
            _increment_achievement_progress(int(uid), 'upgrades_successful')

        supabase.table("users").update(updates).eq("user_id", int(uid)).execute()
        supabase.table("payments").insert({
            "user_id": int(uid), 
            "amount": -cost, 
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }).execute()
            
        return web.json_response({"success": success, "consolation": consolation})
    except Exception as e:
        logger.error(f"Error in api_upgrade: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_wheel_spin(request):
    try:
        data = await request.json()
        uid = data.get("user_id")
        if not uid:
            return web.json_response({"error": "no_id"}, status=400)
        
        uid = int(uid)
        cost = 50
        
        SEGMENTS = [15, 50, 20, 100, 25, 200, 30, 300, 40, 500, 50, 150]
        
        user_res = supabase.table("users").select("stars, total_spent").eq("user_id", uid).execute()
        if not user_res.data:
            return web.json_response({"error": "user_not_found"}, status=404)
        
        u = user_res.data[0]
        balance = u['stars']
        if balance < cost:
            return web.json_response({"error": "insufficient_funds"}, status=403)
        
        rand = random.random() * 100
        if rand < 0.8:
            prize_index = 9
        elif rand < 15:
            prize_index = random.choice([3, 5, 7, 11])
        else:
            prize_index = random.choice([0, 1, 2, 4, 6, 8, 10])
        
        prize = SEGMENTS[prize_index]
        
        new_balance = balance - cost + prize
        new_spent = (u.get('total_spent') or 0) + cost
        
        supabase.table("users").update({"stars": new_balance, "total_spent": new_spent}).eq("user_id", uid).execute()
        
        supabase.table("payments").insert([
            {"user_id": uid, "amount": -cost, "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            {"user_id": uid, "amount": prize, "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        ]).execute()
        
        logger.info(f"User {uid} spun wheel: won {prize}")
            
        return web.json_response({
            "success": True,
            "win_amount": prize,
            "prize_index": prize_index,
            "new_balance": new_balance
        })
    except Exception as e:
        logger.error(f"Error in api_wheel_spin: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_claim_daily_internal(uid):
    try:
        uid = int(uid)
        now = datetime.now()
        
        user_res = supabase.table("users").select("last_daily").eq("user_id", uid).execute()
        if not user_res.data:
            return web.json_response({"error": "user_not_found"}, status=404)
        
        last_daily_str = user_res.data[0].get('last_daily')
        
        if last_daily_str and last_daily_str != "1970-01-01 00:00:00":
            try:
                last_daily = datetime.strptime(last_daily_str, "%Y-%m-%d %H:%M:%S")
                time_diff = (now - last_daily).total_seconds()
                
                if time_diff < 86400:
                    wait_seconds = int(86400 - time_diff)
                    logger.info(f"User {uid} attempted daily claim too soon. Wait: {wait_seconds}s")
                    return web.json_response({
                        "error": "daily_cooldown_active",
                        "wait_seconds": wait_seconds
                    }, status=403)
            except ValueError:
                pass
        
        supabase.table("users").update({"last_daily": now.strftime("%Y-%m-%d %H:%M:%S")}).eq("user_id", uid).execute()
        logger.info(f"User {uid} claimed daily case")
        
        return web.json_response({"success": True})
    
    except Exception as e:
        logger.error(f"Error in api_claim_daily_internal: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_claim_daily(request):
    try:
        data = await request.json()
        return await api_claim_daily_internal(data.get("user_id"))
    except Exception as e:
        logger.error(f"Error in api_claim_daily: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_ton_success(request):
    try:
        data = await request.json()
        uid = data.get("user_id")
        amount_ton = data.get("amount")
        tx_hash = data.get("tx_id") or data.get("boc")
        
        if not uid or amount_ton is None or not tx_hash:
            logger.warning(f"Incomplete TON payment data: user_id={uid}, amount={amount_ton}, tx_hash={bool(tx_hash)}")
            return web.json_response({"error": "invalid_data"}, status=400)
        
        uid = int(uid)
        
        try:
            amount_ton = float(amount_ton)
            if amount_ton <= 0:
                return web.json_response({"error": "invalid_amount"}, status=400)
        except ValueError:
            return web.json_response({"error": "invalid_amount"}, status=400)
        
        tx_hash_normalized = hashlib.sha256(str(tx_hash).encode()).hexdigest()
        stars_to_add = int(amount_ton * 100)
        
        existing = supabase.table("ton_transactions").select("tx_id").eq("tx_id", tx_hash_normalized).execute()
        if existing.data:
            logger.warning(f"Duplicate TON transaction detected: {tx_hash_normalized}")
            return web.json_response({"error": "transaction_already_processed"}, status=400)
        
        supabase.table("ton_transactions").insert({
            "tx_id": tx_hash_normalized, 
            "user_id": uid, 
            "amount": amount_ton, 
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }).execute()
        
        user_res = supabase.table("users").select("stars, total_donated_ton").eq("user_id", uid).execute()
        if user_res.data:
            u = user_res.data[0]
            new_stars = u['stars'] + stars_to_add
            new_donated_ton = (u.get('total_donated_ton') or 0.0) + amount_ton
            supabase.table("users").update({"stars": new_stars, "total_donated_ton": new_donated_ton}).eq("user_id", uid).execute()
            
            supabase.table("payments").insert({
                "user_id": uid, 
                "amount": stars_to_add, 
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }).execute()
            
            logger.info(f"TON payment processed: User {uid}, {amount_ton} TON = {stars_to_add} stars")
        
        try:
            await bot.send_message(uid, f"✅ Пополнение успешно! +{stars_to_add} ⭐")
        except Exception as e:
            logger.error(f"Failed to send user notification: {e}")
        
        try:
            for admin_id in ADMIN_IDS:
                await bot.send_message(admin_id, f"💰 User {uid} topped up: {amount_ton} TON = {stars_to_add} ⭐")
        except Exception as e:
            logger.error(f"Failed to notify admins: {e}")
        
        return web.json_response({"success": True, "stars_added": stars_to_add})
    
    except Exception as e:
        logger.error(f"Error in api_ton_success: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_invoice(request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        amount = data.get("amount")
        
        if not user_id or not amount:
            return web.json_response({"error": "invalid_data"}, status=400)
        
        try:
            amount = int(amount)
            if amount <= 0:
                return web.json_response({"error": "invalid_amount"}, status=400)
        except ValueError:
            return web.json_response({"error": "invalid_amount"}, status=400)
        
        try:
            link = await bot.create_invoice_link(
                title="Пополнение Stars",
                description=f"Покупка {amount} звёзд",
                payload=f"stars_{user_id}_{amount}",
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label="Stars", amount=amount)]
            )
            logger.info(f"Invoice created for user {user_id}: {amount} stars")
            return web.json_response({"link": link})
        except Exception as e:
            logger.error(f"Failed to create invoice: {e}")
            return web.json_response({"error": "invoice_creation_failed"}, status=500)
    
    except Exception as e:
        logger.error(f"Error in api_invoice: {e}")
        return web.json_response({"error": "server_error"}, status=500)

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
        logger.info(f"Payment successful for user {user_id}: +{amount} stars")
        await m.answer(f"✅ Спасибо за покупку! +{amount} ⭐")
        
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, f"💰 **Новое пополнение!**\n👤 Юзер: {m.from_user.full_name} (`{user_id}`)\n⭐ Количество: `{amount}` звёзд", parse_mode="Markdown")
            except: pass
            
    except Exception as e:
        logger.error(f"Error in success_pay: {e}")
        await m.answer("❌ Ошибка при обработке платежа.")

async def api_get_achievements(request):
    try:
        uid = request.query.get("user_id")
        if not uid: return web.json_response({"error": "no_id"}, status=400)
        
        uid = int(uid)
        ACHIEVEMENTS = [
            {'id': 'first_step', 'title': 'Первый шаг', 'goal': 1, 'reward': 1},
            {'id': 'upgrade_master', 'title': 'Мастер Апгрейдов', 'goal': 3, 'reward': 15},
            {'id': 'ludoman', 'title': 'Истинный Лудоман', 'goal': 10, 'reward': 10}
        ]
        
        # Ensure achievements exist in user_achievements
        for a in ACHIEVEMENTS:
            try:
                supabase.table("user_achievements").upsert({"user_id": uid, "achievement_id": a['id']}, on_conflict="user_id,achievement_id").execute()
            except: pass
        
        res = supabase.table("user_achievements").select("achievement_id, progress, is_claimed").eq("user_id", uid).execute()
            
        data = []
        for r in res.data:
            aid, prog, claimed = r['achievement_id'], r['progress'], r['is_claimed']
            info = next((a for a in ACHIEVEMENTS if a['id'] == aid), None)
            if info:
                data.append({
                    **info,
                    "progress": prog or 0,
                    "is_claimed": bool(claimed)
                })
        
        return web.json_response(data)
    except Exception as e:
        logger.error(f"Error in api_get_achievements: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_claim_achievement(request):
    try:
        data = await request.json()
        uid = data.get("user_id")
        aid = data.get("achievement_id")
        
        if not uid or not aid: return web.json_response({"error": "invalid_data"}, status=400)
        
        ACHIEVEMENTS = [
            {'id': 'first_step', 'title': 'Первый шаг', 'goal': 1, 'reward': 1},
            {'id': 'upgrade_master', 'title': 'Мастер Апгрейдов', 'goal': 3, 'reward': 15},
            {'id': 'ludoman', 'title': 'Истинный Лудоман', 'goal': 10, 'reward': 10}
        ]
        
        info = next((a for a in ACHIEVEMENTS if a['id'] == aid), None)
        if not info: return web.json_response({"error": "achievement_not_found"}, status=404)

        uid = int(uid)
        res = supabase.table("user_achievements").select("progress, is_claimed").eq("user_id", uid).eq("achievement_id", aid).execute()
        if not res.data: return web.json_response({"error": "not_found"}, status=404)
        
        a_status = res.data[0]
        prog, claimed = a_status['progress'], a_status['is_claimed']
        if claimed: return web.json_response({"error": "already_claimed"}, status=400)
        if prog < info['goal']: return web.json_response({"error": "not_reached"}, status=400)
        
        supabase.table("user_achievements").update({"is_claimed": 1}).eq("user_id", uid).eq("achievement_id", aid).execute()
        
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

async def main():
    init_db()
    
    app = web.Application()
    
    app.router.add_get('/api/check_sub', api_check_sub)
    app.router.add_get('/api/balance', api_balance)
    app.router.add_get('/api/referrals', api_referrals)
    app.router.add_post('/api/open_case', api_open_case)
    app.router.add_post('/api/claim_daily', api_claim_daily)
    app.router.add_post('/api/create_invoice', api_invoice)
    app.router.add_post('/api/ton_success', api_ton_success)
    app.router.add_post('/api/wheel/spin', api_wheel_spin)
    app.router.add_post('/api/upgrade', api_upgrade)
    app.router.add_get('/api/achievements', api_get_achievements)
    app.router.add_post('/api/achievements/claim', api_claim_achievement)
    
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*"
        )
    })
    for route in list(app.router.routes()):
        cors.add(route)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    logger.info("✅ API server started on port 8080")
    
    logger.info("✅ Bot polling started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
