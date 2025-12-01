import asyncio
import schedule
import time
from datetime import datetime
from uploader import DataUploader, db

async def daily_export_job():
    """Задача ежедневной выгрузки"""
    print(f"⏰ Запуск ежедневной выгрузки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Здесь укажи URL своего сервера, если есть
    # uploader = DataUploader(webhook_url="https://твой-сервер.ru/api/upload")
    uploader = DataUploader()  # Только локальное сохранение
    
    try:
        success = await uploader.daily_export()
        if success:
            print(f"✅ Выгрузка завершена успешно: {datetime.now().strftime('%H:%M:%S')}")
        else:
            print(f"⚠️ Выгрузка завершена с ошибками: {datetime.now().strftime('%H:%M:%S')}")
    except Exception as e:
        print(f"❌ Критическая ошибка при выгрузке: {e}")

def run_scheduler():
    """Запуск планировщика"""
    
    print("⏰ Планировщик выгрузки данных запущен")
    print("=" * 50)
    
    # Настрой расписание
    # Ежедневно в 3:00 ночи
    schedule.every().day.at("03:00").do(
        lambda: asyncio.run(daily_export_job())
    )
    
    # Каждый день в 12:00 (для теста)
    schedule.every().day.at("12:00").do(
        lambda: asyncio.run(daily_export_job())
    )
    
    # Каждый час выводим статус
    schedule.every().hour.do(
        lambda: print(f"⏱️  Статус: следующая выгрузка через {int(schedule.idle_seconds()/60)} мин.")
    )
    
    # Первая выгрузка сразу при запуске (для теста)
    print("🚀 Запускаю первую выгрузку сейчас...")
    asyncio.run(daily_export_job())
    
    print("\n📅 Расписание выгрузки:")
    print("   - Ежедневно в 03:00")
    print("   - Ежедневно в 12:00")
    print("   - Следующая выгрузка через ~1 час")
    print("=" * 50)
    
    # Бесконечный цикл планировщика
    while True:
        schedule.run_pending()
        time.sleep(60)  # Проверяем каждую минуту

if __name__ == "__main__":
    run_scheduler()