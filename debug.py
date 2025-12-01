import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def debug_database():
    try:
        conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
        
        # Проверим пользователей в базе
        users = await conn.fetch("SELECT * FROM users")
        print(f"📊 Всего пользователей в базе: {len(users)}")
        
        for user in users:
            print(f"👤 ID: {user['id']}, TG: {user['telegram_id']}, Имя: {user['name']}")
        
        # Проверим лайки
        likes = await conn.fetch("SELECT * FROM likes")
        print(f"❤️ Всего лайков: {len(likes)}")
        
        # Проверим функцию get_unseen_profiles
        if users:
            test_user_id = users[0]['telegram_id']
            unseen = await conn.fetch("""
                SELECT u.id, u.telegram_id, u.name
                FROM users u
                WHERE u.id != $1
                  AND u.id NOT IN (
                    SELECT to_user_id FROM likes WHERE from_user_id = $1
                  )
                  AND u.id NOT IN (
                    SELECT to_user_id FROM skips WHERE from_user_id = $1
                  )
                LIMIT 5
            """, users[0]['id'])
            
            print(f"🎯 Непросмотренных анкет для {users[0]['name']}: {len(unseen)}")
            for profile in unseen:
                print(f"   - {profile['name']} (ID: {profile['id']})")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

asyncio.run(debug_database())