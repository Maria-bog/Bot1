import asyncio
import asyncpg
import ssl
import os
from dotenv import load_dotenv

load_dotenv()

async def init_database():
    try:
        # SSL контекст для Neon
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Подключаемся с SSL
        conn = await asyncpg.connect(
            os.getenv('DATABASE_URL'),
            ssl=ssl_context
        )
        
        print("🗂️ Создаем таблицы...")
        
        # Создаем таблицы
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                interest_area TEXT,
                expertise_area TEXT,
                contact_tag VARCHAR(100),
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS likes (
                id SERIAL PRIMARY KEY,
                from_user_id INTEGER REFERENCES users(id),
                to_user_id INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(from_user_id, to_user_id)
            );

            CREATE TABLE IF NOT EXISTS skips (
                id SERIAL PRIMARY KEY,
                from_user_id INTEGER REFERENCES users(id),
                to_user_id INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(from_user_id, to_user_id)
            );
        """)
        
        print("✅ Таблицы созданы!")
        
        # Проверим
        tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        print("📊 Таблицы в базе:")
        for table in tables:
            print(f"   - {table['table_name']}")
        
        await conn.close()
        print("🎉 База готова к использованию!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(init_database())