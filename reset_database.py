import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def reset_database():
    try:
        # Подключаемся к базе
        conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
        
        print("🗑️ Начинаем полный сброс базы данных...")
        
        # Удаляем все таблицы (в правильном порядке из-за внешних ключей)
        await conn.execute("DROP TABLE IF EXISTS likes CASCADE")
        await conn.execute("DROP TABLE IF EXISTS skips CASCADE") 
        await conn.execute("DROP TABLE IF EXISTS users CASCADE")
        
        print("✅ Все таблицы удалены")
        
        # Пересоздаем таблицы заново
        await conn.execute("""
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                interest_area TEXT,
                expertise_area TEXT,
                contact_tag VARCHAR(100),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        await conn.execute("""
            CREATE TABLE likes (
                id SERIAL PRIMARY KEY,
                from_user_id INTEGER REFERENCES users(id),
                to_user_id INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(from_user_id, to_user_id)
            )
        """)
        
        await conn.execute("""
            CREATE TABLE skips (
                id SERIAL PRIMARY KEY,
                from_user_id INTEGER REFERENCES users(id),
                to_user_id INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(from_user_id, to_user_id)
            )
        """)
        
        print("✅ Таблицы созданы заново")
        
        # Проверяем, что база пустая
        user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        likes_count = await conn.fetchval("SELECT COUNT(*) FROM likes")
        skips_count = await conn.fetchval("SELECT COUNT(*) FROM skips")
        
        print(f"📊 Проверка: пользователей - {user_count}, лайков - {likes_count}, пропусков - {skips_count}")
        
        await conn.close()
        print("🎉 База данных полностью сброшена и готова к использованию!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(reset_database())