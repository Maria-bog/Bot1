import asyncio
import aiohttp
import os
from datetime import datetime
from admin import AdminTools, db
import aiofiles
import json

class DataUploader:
    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url  # URL твоего сервера для загрузки
    
    async def upload_to_server(self, filename, data_type="csv"):
        """Загрузка файла на удаленный сервер"""
        if not self.webhook_url:
            print(f"⚠️ URL сервера не указан, сохраняю локально: {filename}")
            return True  # Возвращаем True, т.к. файл сохранен локально
        
        try:
            async with aiohttp.ClientSession() as session:
                async with aiofiles.open(filename, 'rb') as f:
                    file_data = await f.read()
                    
                    form_data = aiohttp.FormData()
                    form_data.add_field('file', 
                                       file_data, 
                                       filename=filename,
                                       content_type='text/csv' if data_type == 'csv' else 'application/json')
                    form_data.add_field('type', data_type)
                    form_data.add_field('timestamp', datetime.now().isoformat())
                    form_data.add_field('project', 'skillswap_bot')
                    
                    async with session.post(self.webhook_url, data=form_data) as response:
                        if response.status == 200:
                            result = await response.json()
                            print(f"✅ Файл {filename} загружен на сервер: {result}")
                            # Удаляем локальный файл после загрузки
                            os.remove(filename)
                            return True
                        else:
                            error_text = await response.text()
                            print(f"❌ Ошибка загрузки: {response.status} - {error_text}")
                            return False
        except Exception as e:
            print(f"❌ Ошибка при загрузке {filename}: {e}")
            return False
    
    async def upload_json_data(self, data, filename):
        """Загрузка JSON данных"""
        try:
            # Сохраняем локально
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            
            # Загружаем на сервер если есть URL
            if self.webhook_url:
                return await self.upload_to_server(filename, "json")
            return True
        except Exception as e:
            print(f"❌ Ошибка при сохранении JSON: {e}")
            return False
    
    async def daily_export(self):
        """Ежедневная автоматическая выгрузка"""
        try:
            await db.create_pool()
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            print(f"📤 Начинаю ежедневную выгрузку {timestamp}")
            
            # 1. Выгружаем CSV статистику
            csv_file, count = await AdminTools.get_user_stats_csv()
            csv_success = await self.upload_to_server(csv_file, "csv")
            
            # 2. Выгружаем данные об активности
            activity = await AdminTools.get_activity_timeline(30)
            activity_file = f"activity_{datetime.now().strftime('%Y%m%d')}.json"
            activity_success = await self.upload_json_data(activity, activity_file)
            
            # 3. Выгружаем топ интересов
            top_interests = await AdminTools.get_top_interests(20)
            interests_file = f"interests_{datetime.now().strftime('%Y%m%d')}.json"
            interests_success = await self.upload_json_data(top_interests, interests_file)
            
            # 4. Сводный отчет
            summary = {
                "export_date": datetime.now().isoformat(),
                "total_users": count,
                "activity_days": len(activity),
                "top_interests_count": len(top_interests),
                "files_exported": {
                    "csv": csv_success,
                    "activity": activity_success,
                    "interests": interests_success
                }
            }
            
            summary_file = f"summary_{datetime.now().strftime('%Y%m%d')}.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            if self.webhook_url:
                await self.upload_to_server(summary_file, "json")
            
            print(f"✅ Ежедневная выгрузка завершена: пользователей={count}, активность={len(activity)} дней")
            
            return all([csv_success, activity_success, interests_success])
            
        except Exception as e:
            print(f"❌ Ошибка при ежедневной выгрузке: {e}")
            import traceback
            traceback.print_exc()
            return False

# Быстрый тест
async def test_uploader():
    # Для теста используем локальное сохранение (без сервера)
    uploader = DataUploader()  # Без URL - только локальное сохранение
    
    print("🧪 Тестируем загрузчик...")
    success = await uploader.daily_export()
    
    if success:
        print("✅ Тест пройден! Проверь файлы в текущей папке:")
        import glob
        files = glob.glob("*.csv") + glob.glob("*.json")
        for file in files:
            print(f"   📄 {file}")
    else:
        print("❌ Тест не пройден")

if __name__ == "__main__":
    asyncio.run(test_uploader())