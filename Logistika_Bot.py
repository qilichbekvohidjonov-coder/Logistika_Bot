import os
import asyncio
import logging
import sqlite3
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# --- LOGGING SOZLASH ---
logging.basicConfig(level=logging.INFO)

# --- TOKENNI SOZLASH ---
TOKEN = "8840225514:AAFxpX0uTkVRoQRk7KXaLwKyCpcEGTc-hKQ"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ----- RENDER UCHUN VEB-SERVER FUNKSIYASI -----
async def handle(request):
    return web.Response(text="Bot 24/7 rejimida va mutlaqo BEPUL ishlamoqda!")

# ----- BAZANI TO'G'RI SOZLASH -----
def db_init():
    conn = sqlite3.connect("logistika.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS yuklar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            yuk_turi TEXT,
            qayerdan TEXT,
            qayerga TEXT,
            narxi TEXT,
            telefon TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS haydovchilar (
            user_id INTEGER PRIMARY KEY,
            ism TEXT,
            mashina_turi TEXT,
            telefon TEXT
        )
    """)
    conn.commit()
    conn.close()

db_init()

class YukElon(StatesGroup):
    yuk_turi = State()
    qayerdan = State()
    qayerga = State()
    narxi = State()
    telefon = State()

class HaydovchiRegistratsiya(StatesGroup):
    ism = State()
    mashina_turi = State()
    telefon = State()

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚚 Men Haydovchiman", callback_data="role_driver"),
            InlineKeyboardButton(text="📦 Men Yuk Egasiman", callback_data="role_owner")
        ]
    ])
    await message.answer(
        text=f"Assalomu alaykum, {message.from_user.full_name}!\nLogistika botiga xush kelibsiz.\nBot hozircha hamma uchun mutlaqo BEPUL!\n\nRolingizni tanlang:",
        reply_markup=kb
    )

# 🚚 Haydovchi tugmasi bosilganda (TO'LOV OLIB TASHLANDI)
@dp.callback_query(F.data == "role_driver")
async def role_driver_clicked(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    
    conn = sqlite3.connect("logistika.db")
    cursor = conn.cursor()
    cursor.execute("SELECT ism FROM haydovchilar WHERE user_id = ?", (user_id,))
    haydovchi = cursor.fetchone()
    conn.close()
    
    if not haydovchi:
        await callback.message.answer(
            "🚚 Siz hali haydovchi sifatida ro'yxatdan o'tmabsiz.\nKeling, profil yaratamiz!\n\n1️⃣ **Ism va familiyangizni kiriting:**"
        )
        await state.set_state(HaydovchiRegistratsiya.ism)
        return

    # Ro'yxatdan o'tgan bo'lsa, to'lovsiz to'g'ridan-to'g'ri yuklarni ko'rsatadi
    await show_all_yuklar(callback.message)

# 📦 Yuk egasi tugmasi bosilganda
@dp.callback_query(F.data == "role_owner")
async def role_owner_clicked(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "📦 Yangi yuk e'loni berishni boshlaymiz!\n\n1️⃣ **Yukingiz turini kiriting (masalan: Mebel, Mevalar, Qurilish mollari):**"
    )
    await state.set_state(YukElon.yuk_turi)

# Yuk egasi ma'lumotlarini yig'ish
@dp.message(YukElon.yuk_turi)
async def get_yuk_turi(message: types.Message, state: FSMContext):
    await state.update_data(yuk_turi=message.text)
    await message.answer("2️⃣ **Yuk qayerdan olinadi? (Viloyat, shahar yoki tumanni yozing):**")
    await state.set_state(YukElon.qayerdan)

@dp.message(YukElon.qayerdan)
async def get_qayerdan(message: types.Message, state: FSMContext):
    await state.update_data(qayerdan=message.text)
    await message.answer("3️⃣ **Yuk qayerga olib boriladi? (Viloyat, shahar yoki tumanni yozing):**")
    await state.set_state(YukElon.qayerga)

@dp.message(YukElon.qayerga)
async def get_qayerga(message: types.Message, state: FSMContext):
    await state.update_data(qayerga=message.text)
    await message.answer("4️⃣ **Yo'l haqi (Xizmat narxi qancha? Masalan: 500 000 so'm yoki kelishiladi):**")
    await state.set_state(YukElon.narxi)

@dp.message(YukElon.narxi)
async def get_narxi(message: types.Message, state: FSMContext):
    await state.update_data(narxi=message.text)
    phone_kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]
    ], resize_keyboard=True, one_time_keyboard=True)
    await message.answer("5️⃣ **Haydovchilar bog'lanishi uchun telefon raqamingizni yuboring:**", reply_markup=phone_kb)
    await state.set_state(YukElon.telefon)

@dp.message(YukElon.telefon)
async def get_yuk_phone(message: types.Message, state: FSMContext):
    user_phone = message.contact.phone_number if message.contact else message.text
    data = await state.get_data()
    username = message.from_user.username or "Mavjud emas"
    
    conn = sqlite3.connect("logistika.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO yuklar (user_id, username, yuk_turi, qayerdan, qayerga, narxi, telefon)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (message.from_user.id, username, data['yuk_turi'], data['qayerdan'], data['qayerga'], data['narxi'], user_phone))
    conn.commit()
    conn.close()
    
    await message.answer(
        "🎉 Tabriklaymiz! Yuk e'loningiz muvaffaqiyatli saqlandi va haydovchilarga ko'rinadigan bo'ldi.", 
        reply_markup=ReplyKeyboardRemove()
    )
    await state.clear()

# Haydovchi ro'yxatdan o'tish bosqichlari
@dp.message(HaydovchiRegistratsiya.ism)
async def get_driver_name(message: types.Message, state: FSMContext):
    await state.update_data(ism=message.text)
    mashina_kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Labo"), KeyboardButton(text="Gazel")],
        [KeyboardButton(text="Isuzu"), KeyboardButton(text="Fura / Kamaz")]
    ], resize_keyboard=True, one_time_keyboard=True)
    await message.answer("2️⃣ **Yuk mashinangiz turini tanlang yoki yozing:**", reply_markup=mashina_kb)
    await state.set_state(HaydovchiRegistratsiya.mashina_turi)

@dp.message(HaydovchiRegistratsiya.mashina_turi)
async def get_driver_car(message: types.Message, state: FSMContext):
    await state.update_data(mashina_turi=message.text)
    phone_kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]
    ], resize_keyboard=True, one_time_keyboard=True)
    await message.answer("3️⃣ **Telefon raqamingizni yuboring:**", reply_markup=phone_kb)
    await state.set_state(HaydovchiRegistratsiya.telefon)

@dp.message(HaydovchiRegistratsiya.telefon)
async def get_driver_phone(message: types.Message, state: FSMContext):
    user_phone = message.contact.phone_number if message.contact else message.text
    data = await state.get_data()
    
    conn = sqlite3.connect("logistika.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO haydovchilar (user_id, ism, mashina_turi, telefon)
        VALUES (?, ?, ?, ?)
    """, (message.from_user.id, data['ism'], data['mashina_turi'], user_phone))
    conn.commit()
    conn.close()
    
    await message.answer(f"🎉 Rahmat, {data['ism']}! Ro'yxatdan muvaffaqiyatli o'tdingiz. Endi yuklarni ko'rishingiz mumkin.", reply_markup=ReplyKeyboardRemove())
    await state.clear()
    await show_all_yuklar(message)

async def show_all_yuklar(message: types.Message):
    conn = sqlite3.connect("logistika.db")
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute("SELECT username, yuk_turi, qayerdan, qayerga, narxi, telefon FROM yuklar")
    yuklar = cursor.fetchall()
    conn.close()
    
    if not yuklar:
        await message.answer("😔 Hozircha tizimda faol yuk e'lonlari ma'lumotlari mavjud emas.")
        return
    
    await message.answer("🚚 **Tizimdagi mavjud faol yuklar ro'yxati:**\n" + "—" * 20)
    
    for row in yuklar:
        o_username = row["username"]
        y_turi = row["yuk_turi"]
        q_dan = row["qayerdan"]
        q_ga = row["qayerga"]
        narx = row["narxi"]
        tel = row["telefon"]
        
        if o_username and o_username != "None" and o_username != "":
            lichka_matni = f"💬 **Telegram:** @{o_username}"
        else:
            lichka_matni = "💬 **Telegram:** _Mavjud emas (faqat telefon)_"
            
        yuk_matni = (
            f"📦 **YANGI YUK E'LONI!**\n\n"
            f"📦 **Yuk turi:** {y_turi}\n"
            f"📍 **Qayerdan:** {q_dan}\n"
            f"🏁 **Qayerga:** {q_ga}\n"
            f"💰 **Yo'l haqi:** {narx}\n"
            f"📞 **Telefon:** {tel}\n"
            f"{lichka_matni}"
        )
        await message.answer(yuk_matni)

# ----- ASOSIY ISHGA TUSHIRISH QISMI -----
async def main():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
