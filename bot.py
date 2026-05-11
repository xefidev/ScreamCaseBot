import logging
import asyncio
import sqlite3
from datetime import datetime
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
                        (user_id INTEGER PRIMARY KEY, stars INTEGER DEFAULT 0, join_date TEXT, last_daily TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS payments 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, date TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS promocodes 
                        (code TEXT PRIMARY KEY, reward INTEGER, type TEXT, active BOOLEAN DEFAULT 1)''')
        
        # Миграция: добавляем last_daily если его нет
        try:
            conn.execute("ALTER TABLE users ADD COLUMN last_daily TEXT DEFAULT '1970-01-01 00:00:00'")
        except: pass # Уже есть

    print("✅ База данных полностью готова")

def register_or_get(user_id):
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT stars, join_date FROM users WHERE user_id = ?", (user_id,))
        res = cur.fetchone()
        if res:
            return res, False # Юзер уже был
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("INSERT INTO users (user_id, stars, join_date, last_daily) VALUES (?, 0, ?, ?)", (user_id, date, "1970-01-01 00:00:00"))
        conn.commit()
        return (0, date), True # Новый юзер

def update_balance(user_id, amount, mode="add"):
    with sqlite3.connect('database.db') as conn:
        if mode == "add":
            conn.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (amount, user_id))
        else:
            conn.execute("UPDATE users SET stars = ? WHERE user_id = ?", (amount, user_id))
        conn.execute("INSERT INTO payments (user_id, amount, date) VALUES (?, ?, ?)", 
                     (user_id, amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()

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
        text += "• `/history` — Логи пополнений\n"
        text += "• `/broadcast [текст]` — Рассылка\n"
        text += "• `/gen_promo [code] [reward] [type]` — Создать промокод\n"
        text += "• `/clear_cooldown [ID]` — Сбросить ежедневный бонус"
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("gen_promo"))
async def gen_promo_cmd(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        _, code, reward, ptype = message.text.split()
        with sqlite3.connect('database.db') as conn:
            conn.execute("INSERT OR REPLACE INTO promocodes (code, reward, type, active) VALUES (?, ?, ?, 1)", (code, int(reward), ptype))
        await message.answer(f"✅ Промокод `{code}` на `{reward}` ({ptype}) создан!")
    except: await message.answer("Пример: `/gen_promo PREMIUM 100 case` (тип: case или stars)")

@dp.message(Command("clear_cooldown"))
async def clear_cooldown_cmd(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        target_id = int(message.text.split()[1])
        with sqlite3.connect('database.db') as conn:
            conn.execute("UPDATE users SET last_daily = ? WHERE user_id = ?", ("1970-01-01 00:00:00", target_id))
        await message.answer(f"✅ Кулдаун для `{target_id}` сброшен.")
    except: await message.answer("Пример: `/clear_cooldown ID`")

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

@dp.message(Command("user"))
async def admin_user(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        target_id = int(message.text.split()[1])
        with sqlite3.connect('database.db') as conn:
            res = conn.execute("SELECT stars, join_date FROM users WHERE user_id = ?", (target_id,)).fetchone()
        if res:
            await message.answer(f"👤 **Юзер `{target_id}`**\n\n💰 Баланс: `{res[0]}` ⭐\n📅 В базе с: `{res[1]}`", parse_mode="Markdown")
        else: await message.answer("Не найден.")
    except: await message.answer("Пример: `/user ID`")

@dp.message(Command("stats"))
async def admin_stats(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        with sqlite3.connect('database.db') as conn:
            u = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            s = conn.execute('SELECT SUM(stars) FROM users').fetchone()[0] or 0
        await message.answer(f"📊 **Статистика:**\n\n👤 Юзеров: `{u}`\n💰 Всего звёзд: `{s}`", parse_mode="Markdown")

@dp.message(Command("history"))
async def admin_history(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        with sqlite3.connect('database.db') as conn:
            logs = conn.execute('SELECT user_id, amount, date FROM payments ORDER BY id DESC LIMIT 10').fetchall()
        text = "📜 **Последние действия:**\n\n"
        for uid, amt, dt in logs:
            text += f"▫️ `{uid}`: `+{amt}` ⭐ ({dt})\n"
        await message.answer(text, parse_mode="Markdown")

@dp.message(Command("broadcast"))
async def broadcast_cmd(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    text = message.text.replace("/broadcast ", "")
    with sqlite3.connect('database.db') as conn:
        users = conn.execute('SELECT user_id FROM users').fetchall()
    count = 0
    for (uid,) in users:
        try:
            await bot.send_message(uid, f"📢 **ScreamCase:**\n\n{text}", parse_mode="Markdown")
            count += 1
        except: pass
    await message.answer(f"✅ Рассылка на {count} человек.")

# --- API ДЛЯ САЙТА ---
async def api_balance(request):
    uid = request.query.get("user_id")
    if not uid: return web.json_response({"error": "no_id"}, status=400)
    with sqlite3.connect('database.db') as conn:
        res = conn.execute("SELECT stars FROM users WHERE user_id = ?", (int(uid),)).fetchone()
    return web.json_response({"stars": res[0] if res else 0})

async def api_daily_info(request):
    uid = request.query.get("user_id")
    if not uid: return web.json_response({"error": "no_id"}, status=400)
    with sqlite3.connect('database.db') as conn:
        res = conn.execute("SELECT last_daily FROM users WHERE user_id = ?", (int(uid),)).fetchone()
    if not res: return web.json_response({"error": "not_found"}, status=404)
    
    last_daily = datetime.strptime(res[0], "%Y-%m-%d %H:%M:%S")
    diff = (datetime.now() - last_daily).total_seconds()
    if diff < 86400:
        return web.json_response({"status": "cooldown", "remaining": int(86400 - diff)})
    return web.json_response({"status": "ready"})

async def api_claim_daily(request):
    data = await request.json()
    uid = data.get("user_id")
    with sqlite3.connect('database.db') as conn:
        res = conn.execute("SELECT last_daily FROM users WHERE user_id = ?", (int(uid),)).fetchone()
        if not res: return web.json_response({"error": "not_found"}, status=404)
        
        last_daily = datetime.strptime(res[0], "%Y-%m-%d %H:%M:%S")
        if (datetime.now() - last_daily).total_seconds() < 86400:
            return web.json_response({"error": "cooldown"}, status=400)
        
        conn.execute("UPDATE users SET stars = stars + 10, last_daily = ? WHERE user_id = ?", 
                     (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), uid))
        conn.commit()
    return web.json_response({"success": True, "reward": 10})

async def api_claim_promo(request):
    data = await request.json()
    uid = data.get("user_id")
    code = data.get("code")
    if not uid or not code: return web.json_response({"error": "invalid_data"}, status=400)

    with sqlite3.connect('database.db') as conn:
        promo = conn.execute("SELECT reward, type, active FROM promocodes WHERE code = ?", (code,)).fetchone()
        if not promo or not promo[2]:
            return web.json_response({"error": "invalid_promo"}, status=400)
        
        if code == "PREMIUM":
            paid = conn.execute("SELECT SUM(amount) FROM payments WHERE user_id = ?", (uid,)).fetchone()[0] or 0
            if paid < 50:
                return web.json_response({"error": "premium_only", "message": "Нужно пополнить минимум 50 Stars"}, status=400)

        # Здесь логика начисления (может быть как звезды, так и бесплатный кейс)
        if promo[1] == "stars":
            update_balance(uid, promo[0], "add")
        
        # Деактивируем одноразовые или просто логируем (для теста просто удаляем или деактивируем)
        # conn.execute("UPDATE promocodes SET active = 0 WHERE code = ?", (code,))
        # conn.commit()

    return web.json_response({"success": True, "reward": promo[0], "type": promo[1]})

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
    update_balance(int(uid), int(amt), "add")
    await m.answer(f"✅ Оплата принята! +{amt} ⭐")

async def main():
    init_db()
    app = web.Application()
    app.router.add_get('/api/balance', api_balance)
    app.router.add_get('/api/daily_info', api_daily_info)
    app.router.add_post('/api/claim_daily', api_claim_daily)
    app.router.add_post('/api/claim_promo', api_claim_promo)
    app.router.add_post('/api/create_invoice', api_invoice)
    cors = aiohttp_cors.setup(app, defaults={"*": aiohttp_cors.ResourceOptions(allow_credentials=True, expose_headers="*", allow_headers="*")})
    for r in list(app.router.routes()): cors.add(r)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', 8080).start()
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())

if __name__ == "__main__": asyncio.run(main())