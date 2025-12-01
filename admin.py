import asyncio
import csv
import json
from datetime import datetime, timedelta
from database import Database
import config

db = Database()

class AdminTools:
    @staticmethod
    async def get_user_stats_csv():
        """Выгрузка статистики пользователей в CSV"""
        async with db.pool.acquire() as conn:
            # Получаем расширенную статистику
            rows = await conn.fetch("""
                SELECT 
                    u.id,
                    u.telegram_id,
                    u.name,
                    u.interest_area,
                    u.expertise_area,
                    u.created_at,
                    COUNT(DISTINCT l_sent.id) as likes_sent,
                    COUNT(DISTINCT l_received.id) as likes_received,
                    COUNT(DISTINCT s.id) as skips_sent,
                    (SELECT COUNT(*) FROM likes l2 
                     JOIN users u2 ON l2.from_user_id = u2.id 
                     WHERE l2.to_user_id = u.id 
                     AND EXISTS (
                         SELECT 1 FROM likes l3 
                         WHERE l3.from_user_id = u.id 
                         AND l3.to_user_id = l2.from_user_id
                     )) as mutual_likes,
                    CASE 
                        WHEN (SELECT COUNT(*) FROM likes WHERE from_user_id = u.id) > 0 
                        THEN ROUND(
                            ((SELECT COUNT(*) FROM likes WHERE to_user_id = u.id)::numeric /
                            (SELECT COUNT(*) FROM likes WHERE from_user_id = u.id)::numeric)::numeric, 
                            2
                        )
                        ELSE 0.0 
                    END as like_ratio
                FROM users u
                LEFT JOIN likes l_sent ON l_sent.from_user_id = u.id
                LEFT JOIN likes l_received ON l_received.to_user_id = u.id
                LEFT JOIN skips s ON s.from_user_id = u.id
                GROUP BY u.id
                ORDER BY u.created_at DESC
            """)
            
            # Конвертируем в словари
            dict_rows = [dict(row) for row in rows]
            
            # Сохраняем в CSV
            filename = f"user_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'id', 'telegram_id', 'name', 'interest_area', 'expertise_area',
                    'created_at', 'likes_sent', 'likes_received', 'skips_sent',
                    'mutual_likes', 'like_ratio'
                ])
                writer.writeheader()
                for row in dict_rows:
                    # Преобразуем datetime в строку
                    row_dict = dict(row)
                    if 'created_at' in row_dict and row_dict['created_at']:
                        row_dict['created_at'] = row_dict['created_at'].isoformat()
                    writer.writerow(row_dict)
            
            return filename, len(dict_rows)

    @staticmethod
    async def get_activity_timeline(days=7):
        """Активность по дням"""
        async with db.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(CASE WHEN table_name = 'users' THEN 1 END) as new_users,
                    COUNT(CASE WHEN table_name = 'likes' THEN 1 END) as likes,
                    COUNT(CASE WHEN table_name = 'skips' THEN 1 END) as skips
                FROM (
                    SELECT created_at, 'users' as table_name FROM users
                    UNION ALL
                    SELECT created_at, 'likes' as table_name FROM likes
                    UNION ALL
                    SELECT created_at, 'skips' as table_name FROM skips
                ) all_events
                WHERE created_at >= CURRENT_DATE - ($1 || ' days')::interval
                GROUP BY DATE(created_at)
                ORDER BY date
            """, str(days))
            
            return [dict(row) for row in rows]

    @staticmethod
    async def get_top_interests(limit=10):
        """Самые популярные интересы"""
        async with db.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    interest_area,
                    COUNT(*) as user_count,
                    COALESCE(
                        ROUND(
                            AVG(
                                CASE 
                                    WHEN (SELECT COUNT(*) FROM likes WHERE from_user_id = u.id) > 0 
                                    THEN (SELECT COUNT(*) FROM likes WHERE to_user_id = u.id)::numeric /
                                         (SELECT COUNT(*) FROM likes WHERE from_user_id = u.id)::numeric
                                    ELSE 0.0 
                                END
                            )::numeric,
                            2
                        ),
                        0.0
                    ) as avg_like_ratio
                FROM users u
                WHERE interest_area IS NOT NULL AND interest_area != ''
                GROUP BY interest_area
                ORDER BY user_count DESC
                LIMIT $1
            """, limit)
            
            return [dict(row) for row in rows]

    @staticmethod
    async def get_simple_stats():
        """Простая статистика (без сложных вычислений)"""
        async with db.pool.acquire() as conn:
            # Базовая статистика
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
            total_likes = await conn.fetchval("SELECT COUNT(*) FROM likes")
            total_skips = await conn.fetchval("SELECT COUNT(*) FROM skips")
            
            # Новые пользователи за сегодня
            new_today = await conn.fetchval("""
                SELECT COUNT(*) FROM users 
                WHERE created_at::date = CURRENT_DATE
            """)
            
            # Активность сегодня
            active_today = await conn.fetchval("""
                SELECT COUNT(DISTINCT from_user_id) FROM likes
                WHERE created_at::date = CURRENT_DATE
            """)
            
            # Взаимные лайки (упрощенный запрос)
            mutual = await conn.fetchval("""
                SELECT COUNT(*) FROM (
                    SELECT DISTINCT LEAST(l1.from_user_id, l1.to_user_id) as user1,
                                    GREATEST(l1.from_user_id, l1.to_user_id) as user2
                    FROM likes l1
                    JOIN likes l2 ON l1.from_user_id = l2.to_user_id 
                        AND l1.to_user_id = l2.from_user_id
                ) t
            """)
            
            return {
                'total_users': total_users,
                'total_likes': total_likes,
                'total_skips': total_skips,
                'new_today': new_today,
                'active_today': active_today,
                'mutual_likes': mutual
            }

    @staticmethod
    async def export_full_database():
        """Полная выгрузка базы для бэкапа"""
        async with db.pool.acquire() as conn:
            # Все таблицы
            tables = ['users', 'likes', 'skips']
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            exported_files = []
            
            for table in tables:
                rows = await conn.fetch(f"SELECT * FROM {table}")
                filename = f"{table}_export_{timestamp}.json"
                
                # Конвертируем строки в словари
                data = []
                for row in rows:
                    row_dict = {}
                    for key, value in dict(row).items():
                        # Преобразуем datetime в строку
                        if hasattr(value, 'isoformat'):
                            row_dict[key] = value.isoformat()
                        else:
                            row_dict[key] = value
                    data.append(row_dict)
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                print(f"✅ Экспортировано {len(data)} записей из {table} в {filename}")
                exported_files.append(filename)
            
            return f"Экспорт завершен. Файлы: {', '.join(exported_files)}"

# Быстрая проверка (упрощенная)
async def test_admin_tools():
    await db.create_pool()
    
    print("📊 Тестируем админ-инструменты...")
    
    try:
        # 1. Простая статистика
        print("\n📈 Простая статистика:")
        stats = await AdminTools.get_simple_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        # 2. CSV выгрузка (упрощенная)
        print("\n📤 Тестируем CSV выгрузку...")
        filename, count = await AdminTools.get_user_stats_csv()
        print(f"✅ Выгружено {count} пользователей в {filename}")
        
        # 3. Активность
        print("\n📊 Активность за 7 дней:")
        activity = await AdminTools.get_activity_timeline(7)
        print(f"   Всего дней с активностью: {len(activity)}")
        if activity:
            for day in activity[:3]:  # Показать первые 3 дня
                date_str = day['date'].strftime('%d.%m') if hasattr(day['date'], 'strftime') else str(day['date'])
                print(f"   {date_str}: +{day['new_users']} пользователей, {day['likes']} лайков")
        
        # 4. Топ интересов
        print("\n🎯 Топ интересов:")
        top = await AdminTools.get_top_interests(5)
        for i, item in enumerate(top, 1):
            print(f"   {i}. {item['interest_area']}: {item['user_count']} пользователей")
        
        print("\n🎉 Все админ-инструменты работают корректно!")
        
        # Покажем содержимое CSV
        print(f"\n📄 Первые 3 строки из {filename}:")
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for i, line in enumerate(lines[:4]):  # Заголовок + 3 строки
                    print(f"   {line.strip()}")
        except:
            pass
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_admin_tools())