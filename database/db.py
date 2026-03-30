import aiosqlite
import os

DB_NAME = "bot_database.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица пользователей
        await db.execute('''CREATE TABLE IF NOT EXISTS users 
                          (user_id INTEGER PRIMARY KEY, username TEXT)''')
        
        # Таблица чатов
        await db.execute('''CREATE TABLE IF NOT EXISTS chats 
                          (chat_id INTEGER PRIMARY KEY AUTOINCREMENT, 
                           user_id INTEGER, 
                           title TEXT, 
                           model_name TEXT)''')
        
        # Таблица настроек
        await db.execute('''CREATE TABLE IF NOT EXISTS settings 
                          (id INTEGER PRIMARY KEY, bot_active INTEGER DEFAULT 1, sub_check_active INTEGER DEFAULT 1)''')
        
        # Миграции для старых баз данных
        try:
            await db.execute("ALTER TABLE settings ADD COLUMN bot_active INTEGER DEFAULT 1")
        except:
            pass

        try:
            await db.execute("ALTER TABLE settings ADD COLUMN sub_check_active INTEGER DEFAULT 1")
        except:
            pass
            
        try:
            await db.execute("ALTER TABLE chats ADD COLUMN model_name TEXT DEFAULT 'gpt-oss:120b-cloud'")
        except:
            pass

        # Гарантируем наличие записи с ID 1
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