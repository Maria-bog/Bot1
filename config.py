import os
from dotenv import load_dotenv

load_dotenv()

# Для Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен")

# Автоматически создаем таблицы при первом запуске
if not DATABASE_URL:
    print("⚠️ DATABASE_URL не установлен, проверь переменные окружения")
    # Для Railway можно использовать встроенную базу
    # Railway автоматически создает DATABASE_URL при добавлении PostgreSQL