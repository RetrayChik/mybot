from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.enums import ChatAction

from config import CHANNEL_ID, CHANNEL_LINK, OLLAMA_MODEL
from database.db import (
    add_user, get_user_chats, create_chat, 
    get_bot_status, delete_chat, get_sub_status
)
from keyboards.kb import (
    check_sub_keyboard, main_menu_keyboard, 
    chat_actions_keyboard, delete_confirm_keyboard,
    model_selection_keyboard
)
from states.fsm import ChatState
from services.ai import generate_response

user_router = Router()
MAX_MESSAGE_LENGTH = 4090

MODEL_MAP = {
    "minimax": "minimax-m2.7:cloud",
    "qwen35": "qwen3.5:397b-cloud",
    "gptoss": "gpt-oss:120b-cloud",
    "gemini": "gemini-3-flash-preview:cloud",
    "kimi": "kimi-k2-thinking:cloud",
    "glm": "glm-5:cloud",
}

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