import os
import asyncio
import logging
import sqlite3
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, LabeledPrice

# --- LOGGING SOZLASH ---
logging.basicConfig(level=logging.INFO)

# --- TOKENLARNI SOZLASH ---
TOKEN = "8840225514:AAFxpX0uTkVRoQRk7KXaLwKyCpcEGTc-hKQ"
PAYMENT_PROVIDER_TOKEN = "398062629:TEST:999999999_F91D8F69C042267444B74CC0B3C747757EB0E065" 

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ----- RENDER UCHUN VEB-SERVER FUNKSIYASI -----
async def handle(request):
    return web.Response(text="Bot 24/7 rejimida muvaffaqiyatli ishlamoqda!")

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
            telefon TEXT,
            is_subscribed INTEGER DEFAULT 0 
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
        text=f"Assalomu alaykum, {message.from_user.full_name}!\nLogistika botiga xush kelibsiz.\nRolingizni tanlang:",
        reply_markup=kb
    )

@dp.callback_query(F.data == "role_driver")
async def role_driver_clicked(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    
    conn = sqlite3.connect("logistika.db")
    cursor = conn.cursor()
    cursor.execute("SELECT ism, is_subscribed FROM haydovchilar WHERE user_id = ?", (user_id,))
    haydovchi = cursor.fetchone()
    conn.close()
    
    if not haydovchi:
        await callback.message.answer(
            "🚚 Siz hali haydovchi sifatida ro'yxatdan o'tmabsiz.\nKeling, profil yaratamiz!\n\n1️⃣ **Ism va familiyangizni kiriting:**"
        )
        await state.set_state(HaydovchiRegistratsiya.ism)
        return

    ism, is_subscribed = haydovchi
    if is_subscribed == 0:
        await send_subscription_invoice(callback.message, user_id)
        return

    await show_all_yuklar(callback.message)

async def send_subscription_invoice(message: types.Message, user_id: int):
    prices = [LabeledPrice(label="1 oylik obuna tarif", amount=4000000)] 
    
    await bot.send_invoice(
        chat_id=user_id,
        title="Botga 1 oylik obuna",
        description="Mavjud barcha yuk e'lonlarini 1 oy davomida cheksiz va xatosiz ko'rish imkoniyati.",
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="UZS",
        prices=prices,
        start_parameter="subscription_payment",
        payload="month_subscription"
    )

@dp.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment_handler(message: types.Message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect("logistika.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE haydovchilar SET is_subscribed = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    await message.answer(
        "🎉 To'lovingiz muvaffaqiyatli qabul qilindi!\n"
        "Sizning 1 oylik obunangiz faollashdi. Endi yuklarni bemalol ko'rishingiz mumkin.\n\n"
        "Qaytadan /start bosing va yuklarni ko'rishga o'ting!"
    )

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
        INSERT OR REPLACE INTO haydovchilar (user_id, ism, mashina_turi, telefon, is_subscribed)
        VALUES (?, ?, ?, ?, 0)
    """, (message.from_user.id, data['ism'], data['mashina_turi'], user_phone))
    conn.commit()
    conn.close()
    
    await message.answer(f"🎉 Rahmat, {data['ism']}! Ro'yxatdan muvaffaqiyatli o'tdingiz.", reply_markup=ReplyKeyboardRemove())
    await state.clear()
    await send_subscription_invoice(message, message.from_user.id)

async def show_all_yuklar(message: types.Message):
    conn = sqlite3.connect("logistika.db")
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute("SELECT username, yuk_turi, qayerdan, qayerga, narxi, telefon FROM yuklar")
    yuklar = cursor.fetchall()
    conn.close()
    
    if not yuklar:
        await message.answer("😔 Hozircha tizimda faol yuk e'lonlari mavjud emas.")
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
    # ---- Render port xatosini tuzatish (Veb-serverni ishga tushirish) ----
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    # ------------------------------------------------------------------

    # Botni polling rejimida ishga tushirish
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

