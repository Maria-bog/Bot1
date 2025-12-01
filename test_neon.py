import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def test_neon():
    try:
        conn = await asyncpg.connect(os.getenv('DATABASE_URL') + "?sslmode=require")
        print("✅ Успешное подключение к Neon!")
        
        # Проверим таблицы
        tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        print("📊 Таблицы в базе:")
        for table in tables:
            print(f"   - {table['table_name']}")
        
        await conn.close()
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")

asyncio.run(test_neon())