import asyncio
import logging
import os
import aiosqlite
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.enums import ChatAction
from ollama import AsyncClient

# ==========================================
# CONFIG
# ==========================================
BOT_TOKEN = "6163740343:AAFy-JIyB1YiFR98gR7onqNSYIyXrjzKLQ8"
ADMIN_IDS = [5279457272] # Твой Telegram ID

CHANNEL_ID = "-1002891583151" # ID твоего канала
CHANNEL_LINK = "https://t.me/retchk"

OLLAMA_MODEL = "gpt-oss:120b-cloud"
DB_NAME = "bot_database.db"
MAX_MESSAGE_LENGTH = 4090

DISPLAY_MODELS = {
    "minimax-m2.7:cloud": "MiniMax",
    "qwen3.5:397b-cloud": "Qwen 3.5",
    "gpt-oss:120b-cloud": "ChatGPT 4"
}

MODEL_MAP = {
    "minimax": "minimax-m2.7:cloud",
    "qwen35": "qwen3.5:397b-cloud",
    "gptoss": "gpt-oss:120b-cloud",
}

# ==========================================
# FSM STATES
# ==========================================
class ChatState(StatesGroup):
    waiting_for_prompt = State()

# ==========================================
# DATABASE
# ==========================================
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS chats 
                          (chat_id INTEGER PRIMARY KEY AUTOINCREMENT, 
                           user_id INTEGER, title TEXT, model_name TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS settings 
                          (id INTEGER PRIMARY KEY, bot_active INTEGER DEFAULT 1, sub_check_active INTEGER DEFAULT 1)''')
        
        # Миграции
        try:
            await db.execute("ALTER TABLE settings ADD COLUMN bot_active INTEGER DEFAULT 1")
        except: pass
        try:
            await db.execute("ALTER TABLE settings ADD COLUMN sub_check_active INTEGER DEFAULT 1")
        except: pass
        try:
            await db.execute("ALTER TABLE chats ADD COLUMN model_name TEXT DEFAULT 'gpt-oss:120b-cloud'")
        except: pass

        async with db.execute("SELECT 1 FROM settings WHERE id = 1") as cursor:
            if not await cursor.fetchone():
                await db.execute("INSERT INTO settings (id, bot_active, sub_check_active) VALUES (1, 1, 1)")
        
        await db.commit()

async def add_user(user_id, username):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        await db.commit()

async def create_chat(user_id, title, model_name):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "INSERT INTO chats (user_id, title, model_name) VALUES (?, ?, ?) RETURNING chat_id", 
            (user_id, title, model_name)
        ) as cursor:
            row = await cursor.fetchone()
            await db.commit()
            return row[0]

async def get_user_chats(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT chat_id, title, model_name FROM chats WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchall()

async def get_bot_status():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT bot_active FROM settings WHERE id = 1") as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else True

async def set_bot_status(status: bool):
    async with aiosqlite.connect(DB_NAME) as db:
        val = 1 if status else 0
        await db.execute("UPDATE settings SET bot_active = ? WHERE id = 1", (val,))
        await db.commit()

async def get_sub_status():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT sub_check_active FROM settings WHERE id = 1") as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else True

async def set_sub_status(status: bool):
    async with aiosqlite.connect(DB_NAME) as db:
        val = 1 if status else 0
        await db.execute("UPDATE settings SET sub_check_active = ? WHERE id = 1", (val,))
        await db.commit()

async def delete_chat(chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM chats WHERE chat_id = ?", (chat_id,))
        await db.commit()

async def get_all_users():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, username FROM users") as cursor:
            return await cursor.fetchall()

# ==========================================
# AI SERVICE
# ==========================================
async def generate_response(prompt: str, model_name: str) -> str:
    try:
        client = AsyncClient()
        response = await client.chat(
            model=model_name, 
            messages=[{'role': 'user', 'content': prompt}]
        )
        return response['message']['content']
    except Exception as e:
        return f"❌ Ошибка при подключении к Ollama: {e}\nУбедитесь, что Ollama запущена."

# ==========================================
# KEYBOARDS
# ==========================================
def check_sub_keyboard(channel_link):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться", url=channel_link)],
        [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_subscription")]
    ])

def main_menu_keyboard(chats):
    keyboard = [[InlineKeyboardButton(text="➕ Создать новый чат", callback_data="new_chat")]]
    for chat_id, title, model in chats:
        pretty_model = DISPLAY_MODELS.get(model, model)
        keyboard.append([InlineKeyboardButton(text=f"📂 [{pretty_model}] {title}", callback_data=f"open_chat_{chat_id}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def model_selection_keyboard():
    models = {
        "minimax": "🚀 MiniMax",
        "qwen35": "🌌 Qwen 3.5",
        "gptoss": "💡 ChatGPT 4",
    }
    keyboard = []
    row = []
    for cmd, name in models.items():
        row.append(InlineKeyboardButton(text=name, callback_data=f"select_model_{cmd}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_list")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def chat_actions_keyboard(chat_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Написать", callback_data=f"write_chat_{chat_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_confirm_{chat_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_list")]
    ])

def delete_confirm_keyboard(chat_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Да, удалить", callback_data=f"delete_yes_{chat_id}")],
        [InlineKeyboardButton(text="↩️ Отмена", callback_data=f"open_chat_{chat_id}")]
    ])

def admin_panel_keyboard(is_active: bool, sub_active: bool):
    status_text = "🔴 Выключить бота" if is_active else "🟢 Включить бота"
    sub_text = "🔴 Выключить подписку" if sub_active else "🟢 Включить подписку"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=status_text, callback_data="admin_toggle_bot")],
        [InlineKeyboardButton(text=sub_text, callback_data="admin_toggle_sub")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_view_users")]
    ])

# ==========================================
# ROUTERS
# ==========================================
admin_router = Router()
user_router = Router()

# ==========================================
# ADMIN HANDLERS
# ==========================================
@admin_router.message(F.text == "/admin")
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return 
    is_active = await get_bot_status()
    sub_active = await get_sub_status()
    await message.answer("🔧 Панель администратора:", reply_markup=admin_panel_keyboard(is_active, sub_active))

@admin_router.callback_query(F.data == "admin_toggle_bot")
async def cb_toggle_bot(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    new_status = not await get_bot_status()
    await set_bot_status(new_status)
    sub_active = await get_sub_status()
    await callback.message.edit_text(
        "🔧 Панель администратора:\n(Статус бота изменен)", 
        reply_markup=admin_panel_keyboard(new_status, sub_active)
    )

@admin_router.callback_query(F.data == "admin_toggle_sub")
async def cb_toggle_sub(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    new_sub_status = not await get_sub_status()
    await set_sub_status(new_sub_status)
    is_active = await get_bot_status()
    await callback.message.edit_text(
        "🔧 Панель администратора:\n(Обязательная подписка изменена)", 
        reply_markup=admin_panel_keyboard(is_active, new_sub_status)
    )

@admin_router.callback_query(F.data == "admin_view_users")
async def cb_view_users(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    users = await get_all_users()
    if not users:
        return await callback.message.answer("База пользователей пуста.")
    text = f"📊 Статистика:\nВсего пользователей: {len(users)}\n\n👥 Список:\n"
    for user_id, username in users:
        text += f"ID: {user_id} | @{username if username else 'Нет юзернейма'}\n"
    if len(text) > 4000:
        await callback.message.answer(text[:4000] + "\n... (список обрезан)") 
    else:
        await callback.message.answer(text)
    await callback.answer()

# ==========================================
# USER HANDLERS
# ==========================================
async def check_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

@user_router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, state: FSMContext):
    await state.clear()
    try:
        if not await get_bot_status():
            return await message.answer("⚠️ Бот временно отключен администратором.")
    except Exception:
        pass 
    await add_user(message.from_user.id, message.from_user.username)
    sub_required = await get_sub_status()
    if sub_required and not await check_subscription(bot, message.from_user.id):
        return await message.answer("Для использования ИИ-моделей подпишитесь на канал!", 
                                    reply_markup=check_sub_keyboard(CHANNEL_LINK))
    chats = await get_user_chats(message.from_user.id)
    await message.answer(f"Привет, {message.from_user.first_name}! Выбери чат или создай новый:", 
                         reply_markup=main_menu_keyboard(chats))

@user_router.callback_query(F.data == "check_subscription")
async def cb_check_sub(callback: CallbackQuery, bot: Bot):
    if not await get_bot_status():
        return await callback.answer("⚠️ Бот временно отключен.", show_alert=True)
    sub_required = await get_sub_status()
    if sub_required and not await check_subscription(bot, callback.from_user.id):
        return await callback.answer("❌ Вы еще не подписались на канал!", show_alert=True)
    await callback.message.delete()
    chats = await get_user_chats(callback.from_user.id)
    await callback.message.answer("✅ Подписка подтверждена! Выбери чат или создай новый:", 
                                  reply_markup=main_menu_keyboard(chats))

@user_router.callback_query(F.data == "new_chat")
async def cb_new_chat(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🤖 Выберите нейросеть для нового диалога:", 
                                    reply_markup=model_selection_keyboard())

@user_router.callback_query(F.data.startswith("select_model_"))
async def cb_model_selected(callback: CallbackQuery, state: FSMContext):
    short_name = callback.data.split("_")[2]
    full_name = MODEL_MAP.get(short_name, OLLAMA_MODEL)
    await state.update_data(chosen_model=full_name, current_chat_id=None)
    await state.set_state(ChatState.waiting_for_prompt)
    await callback.message.edit_text(f"🚀 Выбрана модель: `{full_name}`\nОтправьте ваш первый запрос:")

@user_router.message(ChatState.waiting_for_prompt)
async def process_ai_request(message: Message, state: FSMContext, bot: Bot):
    if message.text and message.text.startswith('/'): return
    if not await get_bot_status():
        return await message.answer("⚠️ Бот временно отключен администратором.")

    data = await state.get_data()
    chat_id = data.get("current_chat_id")
    model_to_use = data.get("chosen_model", OLLAMA_MODEL)

    if chat_id is None:
        title = (message.text[:25] + '...') if len(message.text) > 25 else message.text
        chat_id = await create_chat(message.from_user.id, title, model_to_use)
        await state.update_data(current_chat_id=chat_id)

    status_msg = await message.answer(f"⏳ Генерирую ответ...")
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        response = await generate_response(message.text, model_to_use)
        await status_msg.delete()
        if len(response) <= MAX_MESSAGE_LENGTH:
            await message.answer(response, parse_mode="Markdown")
        else:
            for i in range(0, len(response), MAX_MESSAGE_LENGTH):
                await message.answer(response[i:i+MAX_MESSAGE_LENGTH])
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка при обращении к серверу: {str(e)}")

@user_router.callback_query(F.data.startswith("write_chat_"))
async def cb_write_existing(callback: CallbackQuery, state: FSMContext):
    chat_id = int(callback.data.split("_")[2])
    await state.update_data(current_chat_id=chat_id)
    await state.set_state(ChatState.waiting_for_prompt)
    await callback.message.answer(f"💬 Вы вошли в чат #{chat_id}. Жду ваш запрос.")

@user_router.callback_query(F.data.startswith("open_chat_"))
async def cb_open_chat(callback: CallbackQuery):
    chat_id = int(callback.data.split("_")[2])
    await callback.message.edit_text(f"⚙️ Управление чатом #{chat_id}:", 
                                    reply_markup=chat_actions_keyboard(chat_id))

@user_router.callback_query(F.data == "back_to_list")
async def cb_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    chats = await get_user_chats(callback.from_user.id)
    await callback.message.edit_text("📂 Ваши активные чаты:", reply_markup=main_menu_keyboard(chats))

@user_router.callback_query(F.data.startswith("delete_confirm_"))
async def cb_confirm_del(callback: CallbackQuery):
    chat_id = int(callback.data.split("_")[2])
    await callback.message.edit_text(f"⚠️ Вы уверены, что хотите удалить чат #{chat_id}?", 
                                    reply_markup=delete_confirm_keyboard(chat_id))

@user_router.callback_query(F.data.startswith("delete_yes_"))
async def cb_delete_chat(callback: CallbackQuery, state: FSMContext):
    chat_id = int(callback.data.split("_")[2])
    await delete_chat(chat_id)
    await state.clear()
    chats = await get_user_chats(callback.from_user.id)
    await callback.answer("Чат успешно удален")
    await callback.message.edit_text("📂 Ваши активные чаты:", reply_markup=main_menu_keyboard(chats))

# ==========================================
# MAIN
# ==========================================
async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()
    
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    
    dp.include_router(admin_router)
    dp.include_router(user_router)
    
    await bot.delete_webhook(drop_pending_updates=True)
    print("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")