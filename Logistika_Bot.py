import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, LabeledPrice

# --- TOKEnLARNI SOZLASH ---
# Telegram Bot Tokenini bu yerga yozing
TOKEN = "8840225514:AAFxpX0uTkVRoQRk7KXaLwKyCpcEGTc-hKQ"

# BotFather'dan olingan CLICK Terminal Test tokeni
PAYMENT_PROVIDER_TOKEN = "398062629:TEST:999999999_F91D8F69C042267444B74CC0B3C747757EB0E065" 

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ----- BAZANI TO'G'RI SOZLASH -----
def db_init():
    conn = sqlite3.connect("logistika.db")
    cursor = conn.cursor()
    # Yuklar jadvali
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
    # Haydovchilar jadvali (obuna holati bilan)
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
# ---------------------------------

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

# /start buyrug'i
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

# 🚚 Haydovchi tugmasi (Obunani tekshirish bilan)
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

    # Agar obunasi bo'lmasa to'lov hisobini (Invoice) yuboramiz
    ism, is_subscribed = haydovchi
    if is_subscribed == 0:
        await send_subscription_invoice(callback.message, user_id)
        return

    # Obunasi bo'lsa yuklarni ko'rsatamiz
    await show_all_yuklar(callback.message)

# 💳 CLICK To'lov hisobini yuborish funksiyasi
async def send_subscription_invoice(message: types.Message, user_id: int):
    # Obuna narxi: 40 000 so'm (oxiriga ikkita nol tiyinlar uchun)
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

# To'lovdan oldingi majburiy tekshiruv (Telegram talabi)
@dp.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# To'lov muvaffaqiyatli amalga oshganda obunani faollashtirish
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
        INSERT OR REPLACE INTO haydovchilar (user_id, ism, mashina_turi, telefon, is_subscribed)
        VALUES (?, ?, ?, ?, 0)
    """, (message.from_user.id, data['ism'], data['mashina_turi'], user_phone))
    conn.commit()
    conn.close()
    
    await message.answer(f"🎉 Rahmat, {data['ism']}! Ro'yxatdan muvaffaqiyatli o'tdingiz.", reply_markup=ReplyKeyboardRemove())
    await state.clear()
    
    # Ro'yxatdan o'tishi bilan unga CLICK to'lov hisobini chiqaramiz
    await send_subscription_invoice(message, message.from_user.id)

# 📋 YUKLARNI XATOSIZ CHIQARISH FUNKSIYASI
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
            f"📞 **Telefon:** `{tel}`\n"
            f"{lichka_matni}\n"
            f"—" * 20
        )
        await message.answer(yuk_matni, parse_mode="Markdown")

# 📦 Yuk egasi bo'limi
@dp.callback_query(F.data == "role_owner")
async def start_yuk_elon(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.answer("1️⃣ **Yukingiz turi nima?**\n(Masalan: Meva, Mebel)", parse_mode="Markdown")
    await state.set_state(YukElon.yuk_turi)

@dp.message(YukElon.yuk_turi)
async def get_yuk_turi(message: types.Message, state: FSMContext):
    await state.update_data(yuk_turi=message.text)
    await message.answer("2️⃣ **Yuk qayerdan olinadi?**", parse_mode="Markdown")
    await state.set_state(YukElon.qayerdan)

@dp.message(YukElon.qayerdan)
async def get_qayerdan(message: types.Message, state: FSMContext):
    await state.update_data(qayerdan=message.text)
    await message.answer("3️⃣ **Yuk qayerga yetkazilishi kerak?**", parse_mode="Markdown")
    await state.set_state(YukElon.qayerga)

@dp.message(YukElon.qayerga)
async def get_qayerga(message: types.Message, state: FSMContext):
    await state.update_data(qayerga=message.text)
    await message.answer("4️⃣ **Xizmat haqi (Kira) qancha berasiz?**", parse_mode="Markdown")
    await state.set_state(YukElon.narxi)

@dp.message(YukElon.narxi)
async def get_narxi(message: types.Message, state: FSMContext):
    await state.update_data(narxi=message.text)
    phone_kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]
    ], resize_keyboard=True, one_time_keyboard=True)
    await message.answer("5️⃣ **Siz bilan bog'lanish uchun telefon raqamingiz?**", reply_markup=phone_kb, parse_mode="Markdown")
    await state.set_state(YukElon.telefon)

@dp.message(YukElon.telefon)
async def get_telefon(message: types.Message, state: FSMContext):
    user_phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(telefon=user_phone)
    data = await state.get_data()
    
    await message.answer("Rahmat! Ma'lumotlar tayyorlandi.", reply_markup=ReplyKeyboardRemove())
    
    elon_text = (
        "📦 **YANGI YUK E'LONI!**\n\n"
        f"📦 **Yuk turi:** {data['yuk_turi']}\n"
        f"📍 **Qayerdan:** {data['qayerdan']}\n"
        f"🏁 **Qayerga:** {data['qayerga']}\n"
        f"💰 **Yo'l haqi:** {data['narxi']}\n"
        f"📞 **Aloqa:** {user_phone}\n\n"
        "Ma'lumotlar to'g'rimi? Tasdiqlaysizmi?"
    )
    tasdiq_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_yes"),
        InlineKeyboardButton(text="❌ Bekor quilting", callback_data="confirm_no")
    ]])
    await message.answer(elon_text, reply_markup=tasdiq_kb, parse_mode="Markdown")

# ✅ Tasdiqlash
@dp.callback_query(F.data == "confirm_yes")
async def confirm_yes_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data:
        await callback.answer("Xatolik: Ma'lumot topilmadi.", show_alert=True)
        return

    user_id = callback.from_user.id
    username = callback.from_user.username
    
    conn = sqlite3.connect("logistika.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO yuklar (user_id, username, yuk_turi, qayerdan, qayerga, narxi, telefon)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, str(username), data['yuk_turi'], data['qayerdan'], data['qayerga'], data['narxi'], data['telefon']))
    conn.commit()
    conn.close()
    
    await callback.answer("E'lon bazaga saqlandi!", show_alert=True)
    await callback.message.edit_text(text=callback.message.text + "\n\n🟢 **BU E'LON BAZAGA MUVAFFAQIYATLI QO'SHILDI!**", parse_mode="Markdown")
    await state.clear()

# ❌ Bekor qilish
@dp.callback_query(F.data == "confirm_no")
async def confirm_no_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("E'lon bekor qilindi", show_alert=True)
    await callback.message.edit_text(text=callback.message.text + "\n\n🔴 **BU E'LON BEKOR QILINDI!**", parse_mode="Markdown")
    await state.clear()

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Bot yangi modellar bilan muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot to'xtatildi!")
