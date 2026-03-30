# bot.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from config import BOT_TOKEN
from database.db import init_db
from handlers.user import user_router
from handlers.admin import admin_router

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Инициализация базы данных
    await init_db()
    
    # Настройка бота с ParseMode
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    
    # Регистрация роутеров
    dp.include_router(admin_router)
    dp.include_router(user_router)
    
    # Запуск поллинга
    await bot.delete_webhook(drop_pending_updates=True)
    print("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")