# handlers/admin.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from config import ADMIN_IDS
from database.db import get_bot_status, set_bot_status, get_all_users, get_sub_status, set_sub_status
from keyboards.kb import admin_panel_keyboard

admin_router = Router()

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
        await callback.message.answer("База пользователей пуста.")
        return
        
    text = f"📊 Статистика:\nВсего пользователей: {len(users)}\n\n👥 Список:\n"
    for user_id, username in users:
        text += f"ID: {user_id} | @{username if username else 'Нет юзернейма'}\n"
        
    if len(text) > 4000:
        await callback.message.answer(text[:4000] + "\n... (список обрезан)") 
    else:
        await callback.message.answer(text)
    await callback.answer()