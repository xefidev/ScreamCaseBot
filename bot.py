import logging
import asyncio
import os
import aiohttp
from datetime import datetime
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

# --- CONFIGURATION ---
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
    logger.error("❌ CRITICAL ERROR: Missing environment variables")
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

# --- CONSTANTS ---
CASES_PRICES = {1: 0, 2: 1, 3: 667, 4: 599, 5: 199, 6: 50, 7: 599, 8: 444, 9: 222, 10: 250}
CASES_DATA = {
    1: {'min': 15, 'max': 500},
    2: {'min': 0, 'max': 100},
    3: {'min': 100, 'max': 667},
    4: {'min': 200, 'max': 599},
    5: {'min': 0, 'max': 199},
    6: {'min': 0, 'max': 50},
    7: {'min': 0, 'max': 599},
    8: {'min': 100, 'max': 444},
    9: {'min': 50, 'max': 222},
    10: {'min': 100, 'max': 250}
}

HYPE_TEMPLATES = [
    "@{username}, 20 секунд назад пользователь id {fake_id} выиграл Astral Shard за 20К ⭐\n\n🔥 Испытай свою удачу, твои шансы на победу в платной рулетке увеличены на 34% (всего на час)!",
    "🚨 СКИДКА ДО КРИТИЧЕСКОГО МИНИМУМА!\n\nТолько в ближайшие 30 минут стоимость открытия 'Scream Case' снижена! Успей забрать топовые подарки, пока админ спит. Шанс дропа окупаемого дропа повышен x2!",
    "🎁 Бонус выходного дня!\n\nКаждый, кто зайдет в приложение прямо сейчас, получит +2 бесплатных тикета на баланс! Не упусти халяву, заходи в профиль!",
    "🌙 Ночной режим активирован.\n\nПо статистике, именно ночью выпадает самый дорогой дроп. Прямо сейчас кто-то крутит рулетку и забирает сочные призы. А чего ждешь ты? Твой бонусный процент на удачу уже активирован!",
]

ALL_GIFTS = [
  {"price": 15, "name": "Bear", "image": "/asset/Gifts/15S_Bear_Original_Bear.webp"},
  {"price": 25, "name": "Rosae", "image": "/asset/Gifts/25S_Rosae_Original_Rosae.webp"},
  {"price": 40, "name": "Lol Pops", "image": "/asset/Gifts/40S_Lol_Pops_Original_Lol_Pops.webp"},
  {"price": 50, "name": "Cake", "image": "/asset/Gifts/50S_Cake_Original_Cake.webp"},
  {"price": 100, "name": "Flowers", "image": "/asset/Gifts/100S_Flowers_Original_Flowers.webp"},
  {"price": 300, "name": "Instant Ramens", "image": "/asset/Gifts/300S_Instant_Ramens_Original_Instant_Ramens.webp"},
  {"price": 500, "name": "Swiss Watches", "image": "/asset/Gifts/500S_Swiss_Watches_Original_Swiss_Watches.webp"},
  {"price": 1300, "name": "Astral Shards", "image": "/asset/Gifts/1300S_Astral_Shards_Original_Astral_Shards.webp"},
  {"price": 5000, "name": "Genie Lamps", "image": "/asset/Gifts/5000S_Genie_Lamps_Original_Genie_Lamps.webp"},
  {"price": 19047, "name": "Stellar Rockets", "image": "/asset/Gifts/19047S_Stellar_Rockets_Original_Stellar_Rockets.webp"},
]

# --- HELPERS ---
def validate_init_data(init_data: str, bot_token: str) -> dict:
    if not init_data or not isinstance(init_data, str): return None
    try:
        vals = {k: v for k, v in urllib.parse.parse_qsl(init_data)}
        if 'hash' not in vals or 'user' not in vals: return None
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(vals.items()) if k != 'hash')
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        h = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if h != vals['hash']: return None
        return json.loads(vals.get('user', '{}'))
    except Exception: return None

def create_comment_boc(text: str) -> str:
    try:
        cell = Builder().store_uint(0, 32).store_string(text).end_cell()
        return base64.b64encode(cell.to_boc(False)).decode('utf-8')
    except Exception: return ""

def _update_quest_progress(user_id, quest_type):
    configs = {'open_cases': [{'id': 'open_1', 'goal': 1}, {'id': 'open_5', 'goal': 5}, {'id': 'open_10', 'goal': 10}]}
    for q in configs.get(quest_type, []):
        try:
            res = supabase.table("user_quests").select("progress, is_completed").eq("user_id", user_id).eq("quest_id", q['id']).execute()
            if res.data:
                if not res.data[0]['is_completed']:
                    new_prog = (res.data[0]['progress'] or 0) + 1
                    supabase.table("user_quests").update({"progress": new_prog, "is_completed": new_prog >= q['goal']}).eq("user_id", user_id).eq("quest_id", q['id']).execute()
            else:
                supabase.table("user_quests").insert({"user_id": user_id, "quest_id": q['id'], "progress": 1, "is_completed": 1 >= q['goal']}).execute()
        except: pass

def get_user_stars(user_id):
    try:
        res = supabase.table("users").select("stars, balance").eq("user_id", user_id).execute()
        if res.data:
            u = res.data[0]
            return u.get('stars') if u.get('stars') is not None else u.get('balance', 0)
        return 0
    except: return 0

def register_or_get(user_id, username=None, first_name=None, referred_by=None):
    try:
        res = supabase.table("users").select("stars, balance, join_date").eq("user_id", user_id).execute()
        if res.data:
            u = res.data[0]
            stars = u.get('stars') if u.get('stars') is not None else u.get('balance', 0)
            return (stars, u.get('join_date')), False
        
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        supabase.table("users").insert({
            "user_id": user_id, "stars": 0, "balance": 0, "join_date": date, 
            "username": username, "first_name": first_name, "referred_by": referred_by, "tickets": 0
        }).execute()
        return (0, date), True
    except Exception as e:
        logger.error(f"Error in register_or_get: {e}")
        return (0, ""), False

def update_balance(user_id, amount, mode="add"):
    try:
        res = supabase.table("users").select("stars, balance").eq("user_id", user_id).execute()
        if not res.data: return
        
        current = res.data[0].get('stars') if res.data[0].get('stars') is not None else res.data[0].get('balance', 0)
        new_total = current + amount if mode == "add" else amount
        
        supabase.table("users").update({"stars": new_total, "balance": new_total}).eq("user_id", user_id).execute()
        
        supabase.table("payments").insert({
            "user_id": user_id, 
            "amount": amount if mode == "add" else amount - current, 
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }).execute()
    except Exception as e:
        logger.error(f"Error in update_balance: {e}")

async def check_membership(user_id: int):
    try:
        member = await bot.get_chat_member(chat_id="@ScreamCase", user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except: return False

# --- MIDDLEWARE ---
async def cors_middleware(app, handler):
    async def middleware(request):
        if request.method == 'OPTIONS':
            resp = web.Response(status=200)
            resp.headers['Access-Control-Allow-Origin'] = '*'
            resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return resp
        return await handler(request)
    return middleware

async def auth_middleware(app, handler):
    async def middleware(request):
        if request.path in ['/', '/health', '/api/ping']: return await handler(request)
        if request.path.startswith('/api/'):
            init_data = request.headers.get('Authorization', '').replace('Bearer ', '') or request.query.get('initData')
            if request.method == 'POST' and not init_data:
                try:
                    if 'body_json' not in request:
                        request['body_json'] = await request.json()
                    init_data = request['body_json'].get('initData')
                except: pass
            
            user_data = validate_init_data(init_data, TOKEN)
            if not user_data:
                uid = request.query.get('user_id') or (request.get('body_json', {}).get('user_id') if request.method == 'POST' else None)
                if uid:
                    request['user_id'] = int(uid)
                    return await handler(request)
                return web.json_response({"error": "unauthorized"}, status=401)
            request['user_id'] = int(user_data.get('id'))
        return await handler(request)
    return middleware

# --- BOT ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_cmd(message: types.Message, command: CommandObject):
    ref = command.args if command.args and command.args.isdigit() else None
    data, is_new = register_or_get(message.from_user.id, message.from_user.username, message.from_user.first_name, ref)
    
    if is_new and ref:
        try:
            await bot.send_message(int(ref), "🎉 По вашей ссылке перешел новый пользователь! Вы получили +1 билет 🎫")
            ref_res = supabase.table("users").select("tickets").eq("user_id", int(ref)).execute()
            if ref_res.data:
                new_tickets = (ref_res.data[0].get('tickets') or 0) + 1
                supabase.table("users").update({"tickets": new_tickets}).eq("user_id", int(ref)).execute()
        except: pass

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Открыть ScreamCase", web_app=WebAppInfo(url=APP_URL))],
        [InlineKeyboardButton(text="📢 Канал", url=CHANNEL_URL)]
    ])
    await message.answer(f"Привет, {message.from_user.first_name}! 👋\n\nТвой баланс: {data[0]} ⭐\n\nИспытай свою удачу в лучшем симуляторе кейсов!", reply_markup=kb)

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
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

@dp.message(Command("+"))
async def admin_add(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    parts = message.text.split()
    if len(parts) < 2: return
    try:
        amount = int(parts[1])
        update_balance(message.from_user.id, amount, "add")
        new_stars = get_user_stars(message.from_user.id)
        await message.answer(f"✅ Добавлено {amount} ⭐\n💫 Новый баланс: {new_stars} ⭐")
    except: pass

@dp.message(Command("setbalance"))
async def admin_set(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    parts = message.text.split()
    if len(parts) < 3: return
    try:
        target_id, amount = int(parts[1]), int(parts[2])
        update_balance(target_id, amount, "set")
        await message.answer(f"✅ Баланс ID `{target_id}` установлен на `{amount}` ⭐", parse_mode="Markdown")
    except: pass

@dp.message(Command("user"))
async def admin_user_info(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    parts = message.text.split()
    if len(parts) < 2: return
    try:
        uid = int(parts[1])
        res = supabase.table("users").select("*").eq("user_id", uid).execute()
        if not res.data:
            await message.answer("❌ Пользователь не найден.")
            return
        u = res.data[0]
        stars = u.get('stars') if u.get('stars') is not None else u.get('balance', 0)
        text = f"👤 **Инфо: {uid}**\n⭐ Звезд: {stars}\n🎫 Билетов: {u.get('tickets', 0)}\n📅 Дата: {u.get('join_date')}"
        await message.answer(text, parse_mode="Markdown")
    except: pass

@dp.message(Command("stats"))
async def admin_stats(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        res = supabase.table("users").select("stars, balance", count="exact").execute()
        total_users = res.count
        total_stars = sum(u.get('stars') if u.get('stars') is not None else u.get('balance', 0) for u in res.data)
        await message.answer(f"📊 **Статистика**\n👥 Юзеров: {total_users}\n⭐ Всего звезд: {total_stars}", parse_mode="Markdown")
    except: pass

@dp.message(Command("admin_send"))
async def admin_send(message: types.Message, command: CommandObject):
    if message.from_user.id not in ADMIN_IDS: return
    text = command.args
    if not text: return
    res = supabase.table("users").select("user_id").execute()
    sent, failed = 0, 0
    for u in res.data:
        try:
            await bot.send_message(u['user_id'], text)
            sent += 1
            await asyncio.sleep(0.05)
        except: failed += 1
    await message.answer(f"✅ Рассылка: {sent} ок, {failed} ошибка.")

@dp.message(Command("hype"))
async def admin_hype(message: types.Message, command: CommandObject):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        idx = int(command.args) - 1
        if 0 <= idx < len(HYPE_TEMPLATES):
            template = HYPE_TEMPLATES[idx]
            res = supabase.table("users").select("user_id, username, first_name").execute()
            for u in res.data:
                try:
                    name = u.get('username') or u.get('first_name') or "игрок"
                    text = template.format(username=name.lstrip("@"), fake_id=random.randint(100000000, 999999999))
                    await bot.send_message(u['user_id'], text)
                    await asyncio.sleep(0.05)
                except: pass
            await message.answer("✅ Hype запущен.")
    except: pass

# --- API HANDLERS ---
async def api_balance(request):
    uid = request.get('user_id')
    res = supabase.table("users").select("*").eq("user_id", uid).execute()
    if not res.data: return web.json_response({"ok": False}, status=404)
    u = res.data[0]
    stars = u.get('stars') if u.get('stars') is not None else u.get('balance', 0)
    return web.json_response({"ok": True, "stars": stars, "tickets": u.get('tickets', 0), "spent": u.get('total_spent', 0), "promo_opened": u.get('promo_opened', 0)})

async def api_cases(request):
    cases = [{"id": i, "name": n, "price": CASES_PRICES[i]} for i, n in enumerate(["", "Promo Case", "Daily Case", "Snoop Case", "Lover's Case", "Hobo Case", "Risky Box", "Scam Box", "Ebati Case", "Pussy Case", "Skolnik Case"]) if i > 0]
    return web.json_response(cases)

async def api_open_case(request):
    data = request.get('body_json') or await request.json()
    uid = request.get('user_id')
    case_id = int(data.get("case_id", 0))
    price = CASES_PRICES.get(case_id, 9999)
    current_stars = get_user_stars(uid)
    if current_stars < price: return web.json_response({"error": "insufficient_funds"}, status=403)
    case_info = CASES_DATA.get(case_id, {'min': 0, 'max': 100})
    won_item = random.choice([g for g in ALL_GIFTS if case_info['min'] <= g['price'] <= case_info['max']] or ALL_GIFTS[:1])
    update_balance(uid, -price, "add")
    _update_quest_progress(uid, 'open_cases')
    return web.json_response({"ok": True, "item": won_item, "new_balance": current_stars - price})

async def api_inventory(request):
    uid = request.get('user_id')
    return web.json_response({"user_id": uid, "items": []})

async def api_quests(request):
    uid = request.get('user_id')
    res = supabase.table("user_quests").select("*").eq("user_id", uid).execute()
    quests_data = {r['quest_id']: r for r in res.data}
    QUESTS = [{'id': 'open_1', 'title': 'Открыть 1 кейс', 'goal': 1, 'reward': 10}, {'id': 'open_5', 'title': 'Открыть 5 кейсов', 'goal': 5, 'reward': 50}, {'id': 'open_10', 'title': 'Открыть 10 кейсов', 'goal': 10, 'reward': 150}]
    results = [{**q, "progress": quests_data.get(q['id'], {}).get('progress', 0), "is_completed": quests_data.get(q['id'], {}).get('is_completed', False), "is_claimed": quests_data.get(q['id'], {}).get('reward_claimed', False)} for q in QUESTS]
    return web.json_response(results)

async def api_create_invoice(request):
    try:
        data = request.get('body_json') or await request.json()
        uid, amount, curr = request.get('user_id'), int(data.get("amount", 100)), data.get("currency", "XTR")
        if curr == "TON":
            comment = f"SC_{uid}_{random.randint(1000, 9999)}"
            return web.json_response({"wallet": TON_WALLET, "comment": comment, "payload_boc": create_comment_boc(comment)})
        link = await bot.create_invoice_link(title="Звезды", description=f"{amount} ⭐", payload=f"stars_{uid}_{amount}", provider_token="", currency="XTR", prices=[LabeledPrice(label="⭐", amount=amount)])
        return web.json_response({"ok": True, "invoice_link": link})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

@dp.pre_checkout_query()
async def checkout(q: types.PreCheckoutQuery): await q.answer(ok=True)

@dp.message(F.successful_payment)
async def success_pay(m: types.Message):
    try:
        parts = m.successful_payment.invoice_payload.split("_")
        if parts[0] == "stars":
            uid, amount = int(parts[1]), int(parts[2])
            update_balance(uid, amount, "add")
            await m.answer(f"✅ Зачислено {amount} ⭐")
    except: pass

# --- MAIN ---
async def main():
    app = web.Application(middlewares=[cors_middleware, auth_middleware])
    app.router.add_get('/', lambda r: web.Response(text="OK"))
    app.router.add_get('/health', lambda r: web.json_response({"status": "ok"}))
    app.router.add_get('/api/ping', lambda r: web.json_response({"ok": True}))
    app.router.add_get('/api/balance', api_balance)
    app.router.add_get('/api/cases', api_cases)
    app.router.add_get('/api/quests', api_quests)
    app.router.add_get('/api/inventory', api_inventory)
    app.router.add_post('/api/open_case', api_open_case)
    app.router.add_post('/api/create_invoice', api_create_invoice)
    
    port = int(os.getenv("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', port).start()
    logger.info(f"Server started on port {port}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
