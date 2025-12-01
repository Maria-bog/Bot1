import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

# Список тестовых пользователей
TEST_USERS = [
    {"name": "Анна Программист", "interest": "Data Science", "expertise": "Python, ML", "contact": "@anna_python"},
    {"name": "Максим Дизайнер", "interest": "UI/UX", "expertise": "Figma, Adobe XD", "contact": "@max_design"},
    {"name": "Елена Маркетолог", "interest": "SMM", "expertise": "Таргет, контент", "contact": "@lena_marketing"},
    {"name": "Дмитрий Разработчик", "interest": "Backend", "expertise": "Java, Spring", "contact": "@dima_java"},
    {"name": "Ольга Аналитик", "interest": "Product Management", "expertise": "SQL, аналитика", "contact": "@olga_analytics"},
    {"name": "Иван Фронтенд", "interest": "React", "expertise": "JavaScript, Vue", "contact": "@ivan_frontend"},
    {"name": "София Тестировщик", "interest": "Автотесты", "expertise": "Selenium, pytest", "contact": "@sofia_qa"},
    {"name": "Алексей DevOps", "interest": "Kubernetes", "expertise": "Docker, AWS", "contact": "@alex_devops"},
    {"name": "Мария Копирайтер", "interest": "SEO", "expertise": "Тексты, LSI", "contact": "@maria_text"},
    {"name": "Сергей Менеджер", "interest": "Управление", "expertise": "Agile, Scrum", "contact": "@sergey_pm"},
    {"name": "Татьяна iOS", "interest": "SwiftUI", "expertise": "Swift, UIKit", "contact": "@tanya_ios"},
    {"name": "Павел Android", "interest": "Kotlin", "expertise": "Android SDK", "contact": "@pavel_android"},
    {"name": "Юлия Data Engineer", "interest": "Big Data", "expertise": "Spark, Hadoop", "contact": "@yulia_data"},
    {"name": "Артем Бэкенд", "interest": "Node.js", "expertise": "Express, MongoDB", "contact": "@artem_node"},
    {"name": "Кристина Дизайнер", "interest": "Графика", "expertise": "Illustrator, Photoshop", "contact": "@kristina_design"}
]

async def add_test_users():
    try:
        # Подключаемся к базе
        conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
        
        print("🗂️ Начинаем добавление тестовых пользователей...")
        
        # Начинаем с telegram_id 1000 чтобы не пересекаться с реальными пользователями
        telegram_id = 1000
        
        for user_data in TEST_USERS:
            try:
                # Добавляем пользователя
                await conn.execute("""
                    INSERT INTO users (telegram_id, name, interest_area, expertise_area, contact_tag)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (telegram_id) DO NOTHING
                """, telegram_id, user_data["name"], user_data["interest"], user_data["expertise"], user_data["contact"])
                
                print(f"✅ Добавлен: {user_data['name']} (ID: {telegram_id})")
                telegram_id += 1
                
            except Exception as e:
                print(f"❌ Ошибка при добавлении {user_data['name']}: {e}")
        
        # Проверим сколько пользователей теперь в базе
        count = await conn.fetchval("SELECT COUNT(*) FROM users")
        print(f"\n🎉 Готово! Всего пользователей в базе: {count}")
        
        # Покажем добавленных пользователей
        print("\n📋 Добавленные пользователи:")
        users = await conn.fetch("SELECT name, interest_area, expertise_area, contact_tag FROM users ORDER BY id")
        for user in users:
            print(f"👤 {user['name']} | 🎯 {user['interest_area']} | 💼 {user['expertise_area']} | 📱 {user['contact_tag']}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка подключения к базе: {e}")

if __name__ == "__main__":
    asyncio.run(add_test_users())