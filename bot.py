import logging
import asyncio
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from aiohttp import web
import aiohttp_cors

# --- НАСТРОЙКИ ---
TOKEN = "8660260631:AAF9yETvvFVrIUUsP5twUZtPzik-0jaJUog"
ADMIN_IDS = [7782281997, 5396975347]
APP_URL = "https://scream-case-bot.vercel.app"
CHANNEL_URL = "https://t.me/ScreamCase"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def init_db():
    with sqlite3.connect('database.db') as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users 
                        (user_id INTEGER PRIMARY KEY, 
                         stars INTEGER DEFAULT 0, 
                         join_date TEXT, 
                         last_daily TEXT,
                         total_donated_stars INTEGER DEFAULT 0,
                         total_donated_ton REAL DEFAULT 0.0)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS payments 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, date TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS promocodes 
                        (code TEXT PRIMARY KEY, 
                         reward INTEGER, 
                         type TEXT, 
                         active BOOLEAN DEFAULT 1,
                         min_donation_24h INTEGER DEFAULT 0,
                         expires_at TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS ton_transactions 
                        (tx_id TEXT PRIMARY KEY, user_id INTEGER, amount REAL, date TEXT)''')
        
        # Миграции
        try: conn.execute("ALTER TABLE users ADD COLUMN total_donated_stars INTEGER DEFAULT 0")
        except: pass
        try: conn.execute("ALTER TABLE users ADD COLUMN total_donated_ton REAL DEFAULT 0.0")
        except: pass
        try: conn.execute("ALTER TABLE users ADD COLUMN last_daily TEXT")
        except: pass
        try: conn.execute("ALTER TABLE promocodes ADD COLUMN min_donation_24h INTEGER DEFAULT 0")
        except: pass
        try: conn.execute("ALTER TABLE promocodes ADD COLUMN expires_at TEXT")
        except: pass

    print("✅ База данных полностью готова")

def register_or_get(user_id):
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT stars, join_date FROM users WHERE user_id = ?", (user_id,))
        res = cur.fetchone()
        if res:
            return res, False
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("INSERT INTO users (user_id, stars, join_date) VALUES (?, 0, ?)", (user_id, date))
        conn.commit()
        return (0, date), True

def update_balance(user_id, amount, mode="add", is_donation=False):
    with sqlite3.connect('database.db') as conn:
        if mode == "add":
            conn.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (amount, user_id))
            if is_donation:
                conn.execute("UPDATE users SET total_donated_stars = total_donated_stars + ? WHERE user_id = ?", (amount, user_id))
        else:
            conn.execute("UPDATE users SET stars = ? WHERE user_id = ?", (amount, user_id))
        
        conn.execute("INSERT INTO payments (user_id, amount, date) VALUES (?, ?, ?)", 
                     (user_id, amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()

# --- ЦЕНЫ КЕЙСОВ ---
CASES_PRICES = {
    1: 0,   # Promo Case
    2: 0,   # Daily Case
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
async def start_cmd(message: types.Message):
    data, is_new = register_or_get(message.from_user.id)
    
    if is_new:
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, 
                    f"🚀 **Новый пользователь!**\n\n👤 Имя: {message.from_user.full_name}\n🆔 ID: `{message.from_user.id}`\n🏷 Юзернейм: @{message.from_user.username}", 
                    parse_mode="Markdown")
            except: pass

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Открыть ScreamCase", web_app=WebAppInfo(url=APP_URL))],
        [InlineKeyboardButton(text="📢 Канал", url=CHANNEL_URL)]
    ])
    await message.answer(f"Привет! Твой баланс: {data[0]} ⭐", reply_markup=kb)

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    text = "📖 **Команды бота**\n\n"
    text += "• `/start` — Запуск приложения\n"
    if message.from_user.id in ADMIN_IDS:
        text += "\n🛠 **Админ-панель:**\n"
        text += "• `/+ [число]` — Добавить себе звезд\n"
        text += "• `/setbalance [ID] [число]` — Установить баланс\n"
        text += "• `/user [ID]` — Инфо об игроке\n"
        text += "• `/stats` — Общая статистика\n"
        text += "• `/broadcast [текст]` — Рассылка"
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("+"))
async def admin_add(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        amount = int(message.text.split()[1])
        update_balance(message.from_user.id, amount, "add")
        await message.answer(f"✅ Добавлено {amount} ⭐")
    except: await message.answer("Ошибка. Пример: `/+ 100`")

@dp.message(Command("setbalance"))
async def admin_set(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        _, target_id, amount = message.text.split()
        update_balance(int(target_id), int(amount), "set")
        await message.answer(f"✅ Баланс ID `{target_id}` теперь `{amount}` ⭐", parse_mode="Markdown")
    except: await message.answer("Пример: `/setbalance ID 500`")

# --- API ДЛЯ САЙТА ---
async def api_balance(request):
    uid = request.query.get("user_id")
    if not uid: return web.json_response({"error": "no_id"}, status=400)
    with sqlite3.connect('database.db') as conn:
        res = conn.execute("SELECT stars FROM users WHERE user_id = ?", (int(uid),)).fetchone()
    return web.json_response({"stars": res[0] if res else 0})

async def api_leaderboard(request):
    with sqlite3.connect('database.db') as conn:
        # Топ 10 по суммарным донатам
        res = conn.execute("SELECT user_id, total_donated_stars FROM users ORDER BY total_donated_stars DESC LIMIT 10").fetchall()
    leaderboard = [{"user_id": r[0], "donated": r[1]} for r in res]
    return web.json_response(leaderboard)

async def api_open_case(request):
    data = await request.json()
    uid = data.get("user_id")
    case_id = data.get("case_id")
    if not uid or case_id is None: return web.json_response({"error": "invalid_data"}, status=400)
    
    price = CASES_PRICES.get(int(case_id))
    if price is None: return web.json_response({"error": "invalid_case"}, status=400)
    
    # Handle Daily and Promo cases separately
    if int(case_id) == 2:
        return await _handle_claim_daily(uid)
    if int(case_id) == 1:
        return await _handle_claim_promo(uid, data.get("code"))

    with sqlite3.connect('database.db') as conn:
        res = conn.execute("SELECT stars FROM users WHERE user_id = ?", (int(uid),)).fetchone()
        if not res or res[0] < price:
            return web.json_response({"error": "insufficient_funds"}, status=403)
        
        conn.execute("UPDATE users SET stars = stars - ? WHERE user_id = ?", (price, uid))
        conn.commit()
    return web.json_response({"success": True})

async def _handle_claim_daily(uid):
    with sqlite3.connect('database.db') as conn:
        res = conn.execute("SELECT last_daily FROM users WHERE user_id = ?", (int(uid),)).fetchone()
        now = datetime.now()
        if res and res[0]:
            last_daily = datetime.strptime(res[0], "%Y-%m-%d %H:%M:%S")
            if (now - last_daily).total_seconds() < 86400:
                return web.json_response({"error": "Wait 24h"}, status=403)
        
        conn.execute("UPDATE users SET last_daily = ? WHERE user_id = ?", (now.strftime("%Y-%m-%d %H:%M:%S"), uid))
        conn.commit()
    return web.json_response({"success": True})

async def _handle_claim_promo(uid, code):
    if not code: return web.json_response({"error": "invalid_data"}, status=400)
    with sqlite3.connect('database.db') as conn:
        promo = conn.execute("SELECT reward, type, active, min_donation_24h, expires_at FROM promocodes WHERE code = ?", (code,)).fetchone()
        if not promo:
            return web.json_response({"error": "Invalid Code"}, status=404)
        if not promo[2]:
            return web.json_response({"error": "Promo inactive"}, status=403)
        if promo[4]:
            expiry = datetime.strptime(promo[4], "%Y-%m-%d %H:%M:%S")
            if datetime.now() > expiry:
                return web.json_response({"error": "Promo expired"}, status=403)
        if promo[3] > 0:
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
            donated = conn.execute("SELECT SUM(amount) FROM payments WHERE user_id = ? AND date > ?", (uid, yesterday)).fetchone()[0] or 0
            if donated < promo[3]:
                return web.json_response({"error": "Minimum donation required", "required": promo[3]}, status=403)

        if promo[1] == "stars":
            update_balance(uid, promo[0], "add")
    return web.json_response({"success": True, "reward": promo[0], "type": promo[1]})

async def api_claim_daily(request):
    data = await request.json()
    return await _handle_claim_daily(data.get("user_id"))

async def api_claim_promo(request):
    data = await request.json()
    return await _handle_claim_promo(data.get("user_id"), data.get("code"))

async def api_ton_success(request):
    data = await request.json()
    uid = data.get("user_id")
    amount_ton = data.get("amount") # В тонах
    tx_id = data.get("tx_id")
    
    if not uid or not amount_ton or not tx_id:
        return web.json_response({"error": "invalid_data"}, status=400)

    stars_to_add = int(float(amount_ton) * 100) # Примерный курс
    
    with sqlite3.connect('database.db') as conn:
        # Verify transaction
        existing = conn.execute("SELECT tx_id FROM ton_transactions WHERE tx_id = ?", (tx_id,)).fetchone()
        if existing:
            return web.json_response({"error": "Transaction already processed"}, status=400)
        
        conn.execute("INSERT INTO ton_transactions (tx_id, user_id, amount, date) VALUES (?, ?, ?, ?)",
                     (tx_id, uid, amount_ton, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        conn.execute("UPDATE users SET stars = stars + ?, total_donated_ton = total_donated_ton + ? WHERE user_id = ?", 
                     (stars_to_add, amount_ton, uid))
        conn.commit()
    return web.json_response({"success": True})

async def api_invoice(request):
    data = await request.json()
    try:
        link = await bot.create_invoice_link(
            title="Пополнение Stars",
            description=f"Покупка {data['amount']} звёзд",
            payload=f"stars_{data['user_id']}_{data['amount']}",
            provider_token="", currency="XTR",
            prices=[LabeledPrice(label="Stars", amount=int(data['amount']))]
        )
        return web.json_response({"link": link})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

@dp.pre_checkout_query()
async def checkout(q: types.PreCheckoutQuery): await q.answer(ok=True)

@dp.message(F.successful_payment)
async def success_pay(m: types.Message):
    _, uid, amt = m.successful_payment.invoice_payload.split("_")
    update_balance(int(uid), int(amt), "add", is_donation=True)
    await m.answer(f"✅ Оплата принята! +{amt} ⭐")

async def main():
    init_db()
    app = web.Application()
    app.router.add_get('/api/balance', api_balance)
    app.router.add_get('/api/leaderboard', api_leaderboard)
    app.router.add_post('/api/open_case', api_open_case)
    app.router.add_post('/api/claim_promo', api_claim_promo)
    app.router.add_post('/api/create_invoice', api_invoice)
    app.router.add_post('/api/admin/create_promo', api_admin_create_promo)
    app.router.add_post('/api/ton_success', api_ton_success)
    
    cors = aiohttp_cors.setup(app, defaults={"*": aiohttp_cors.ResourceOptions(allow_credentials=True, expose_headers="*", allow_headers="*")})
    for r in list(app.router.routes()): cors.add(r)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', 8080).start()
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())