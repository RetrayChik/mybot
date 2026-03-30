from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Красивые названия для отображения в списке чатов
DISPLAY_MODELS = {
    "minimax-m2.7:cloud": "MiniMax",
    "qwen3.5:397b-cloud": "Qwen 3.5",
    "gpt-oss:120b-cloud": "ChatGPT 4",
    "gemini-3-flash-preview:cloud": "Gemini3 Flash",
    "kimi-k2-thinking:cloud": "Kimi k2 Thinking",
    "glm-5:cloud": "Glm5",
}

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
    # Исправлен ключ qwen3.5 на qwen35, чтобы совпадало с MODEL_MAP
    models = {
        "minimax": "🚀 MiniMax",
        "qwen35": "🌌 Qwen 3.5",
        "gptoss": "💡 ChatGPT 4",
        "gemini": "Gemini 3 Flash",
        "kimi": "Kimi k2",
        "glm": "Glm"
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