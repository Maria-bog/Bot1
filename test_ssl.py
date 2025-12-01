import asyncio
import asyncpg
import ssl
import os
from dotenv import load_dotenv

load_dotenv()

async def test_ssl_connection():
    try:
        # Создаем SSL контекст
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Подключаемся с SSL
        conn = await asyncpg.connect(
            os.getenv('DATABASE_URL'),
            ssl=ssl_context
        )
        
        print("✅ SSL подключение успешно!")
        
        # Проверим таблицы
        tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        print("📊 Таблицы в базе:")
        for table in tables:
            print(f"   - {table['table_name']}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка SSL подключения: {e}")

asyncio.run(test_ssl_connection())