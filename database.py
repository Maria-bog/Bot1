import asyncpg
import config
import ssl
from datetime import datetime

class Database:
    def __init__(self):
        self.pool = None

    async def create_pool(self):
        try:
            # SSL контекст для Neon
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Подключаемся с SSL
            self.pool = await asyncpg.create_pool(
                config.DATABASE_URL,
                ssl=ssl_context,
                min_size=1,
                max_size=10
            )
            
            # Принудительно создаем таблицы при каждом подключении
            await self.create_tables()
            print("✅ Подключение к базе установлено с SSL")
            
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            raise

    async def create_tables(self):
        async with self.pool.acquire() as conn:
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
            print("✅ Таблицы созданы/проверены")

    # Остальные методы остаются без изменений...
    async def get_user_by_tg(self, tg_id):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, telegram_id, name, interest_area, expertise_area, contact_tag FROM users WHERE telegram_id = $1",
                tg_id
            )
            return dict(row) if row else None

    async def save_user(self, tg_id, name, interest, expertise, contact):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO users (telegram_id, name, interest_area, expertise_area, contact_tag)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (telegram_id) 
                DO UPDATE SET 
                    name = EXCLUDED.name,
                    interest_area = EXCLUDED.interest_area,
                    expertise_area = EXCLUDED.expertise_area,
                    contact_tag = EXCLUDED.contact_tag
                RETURNING id, telegram_id, name, interest_area, expertise_area, contact_tag
            """, tg_id, name, interest, expertise, contact)
            return dict(row)

    async def update_user(self, tg_id, **kwargs):
        """Обновляет данные пользователя"""
        async with self.pool.acquire() as conn:
            set_parts = []
            values = []
            i = 1
            
            for field, value in kwargs.items():
                if value is not None:
                    set_parts.append(f"{field} = ${i}")
                    values.append(value)
                    i += 1
            
            if not set_parts:
                return await self.get_user_by_tg(tg_id)
            
            values.append(tg_id)
            query = f"""
                UPDATE users 
                SET {', '.join(set_parts)}
                WHERE telegram_id = ${i}
                RETURNING id, telegram_id, name, interest_area, expertise_area, contact_tag
            """
            
            row = await conn.fetchrow(query, *values)
            return dict(row) if row else None

    async def get_unseen_profiles(self, for_tg_id, limit=1):
        async with self.pool.acquire() as conn:
            my_user = await self.get_user_by_tg(for_tg_id)
            if not my_user:
                return []

            rows = await conn.fetch("""
                SELECT u.id, u.telegram_id, u.name, u.interest_area, u.expertise_area
                FROM users u
                WHERE u.id != $1
                  AND u.id NOT IN (
                    SELECT to_user_id FROM likes WHERE from_user_id = $1
                  )
                  AND u.id NOT IN (
                    SELECT to_user_id FROM skips WHERE from_user_id = $1
                  )
                ORDER BY RANDOM()
                LIMIT $2
            """, my_user['id'], limit)
            
            return [dict(row) for row in rows]

    async def save_like(self, from_tg_id, to_user_id):
        async with self.pool.acquire() as conn:
            from_user = await self.get_user_by_tg(from_tg_id)
            if not from_user:
                return False, "not_registered"

            try:
                await conn.execute(
                    "INSERT INTO likes (from_user_id, to_user_id) VALUES ($1, $2)",
                    from_user['id'], to_user_id
                )
                return True, from_user['id']
            except asyncpg.UniqueViolationError:
                return False, "already_liked"

    async def save_skip(self, from_tg_id, to_user_id):
        async with self.pool.acquire() as conn:
            from_user = await self.get_user_by_tg(from_tg_id)
            if not from_user:
                return False

            try:
                await conn.execute("""
                    INSERT INTO skips (from_user_id, to_user_id) 
                    VALUES ($1, $2) 
                    ON CONFLICT DO NOTHING
                """, from_user['id'], to_user_id)
                return True
            except Exception as e:
                print(f"❌ Ошибка при сохранении пропуска: {e}")
                return False

    async def get_user_by_id(self, user_id):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, telegram_id, name, interest_area, expertise_area, contact_tag FROM users WHERE id = $1",
                user_id
            )
            return dict(row) if row else None

    async def get_likes_for_user(self, tg_id):
        async with self.pool.acquire() as conn:
            user = await self.get_user_by_tg(tg_id)
            if not user:
                return []

            rows = await conn.fetch("""
                SELECT u.id, u.telegram_id, u.name, u.contact_tag, l.created_at
                FROM likes l
                JOIN users u ON l.from_user_id = u.id
                WHERE l.to_user_id = $1
                ORDER BY l.created_at DESC
            """, user['id'])
            
            return [dict(row) for row in rows]

    async def get_mutual_likes(self, tg_id):
        async with self.pool.acquire() as conn:
            user = await self.get_user_by_tg(tg_id)
            if not user:
                return []

            rows = await conn.fetch("""
                SELECT DISTINCT u.id, u.telegram_id, u.name, u.contact_tag
                FROM likes l1
                JOIN likes l2 ON l1.from_user_id = l2.to_user_id AND l1.to_user_id = l2.from_user_id
                JOIN users u ON l2.from_user_id = u.id
                WHERE l1.from_user_id = $1
            """, user['id'])
            
            return [dict(row) for row in rows]

    async def get_user_stats(self, tg_id):
        async with self.pool.acquire() as conn:
            user = await self.get_user_by_tg(tg_id)
            if not user:
                return None

            likes_received = await conn.fetchval(
                "SELECT COUNT(*) FROM likes WHERE to_user_id = $1",
                user['id']
            )

            likes_sent = await conn.fetchval(
                "SELECT COUNT(*) FROM likes WHERE from_user_id = $1",
                user['id']
            )

            mutual_likes = await conn.fetchval("""
                SELECT COUNT(*) FROM likes l1
                JOIN likes l2 ON l1.from_user_id = l2.to_user_id AND l1.to_user_id = l2.from_user_id
                WHERE l1.from_user_id = $1
            """, user['id'])

            return {
                'likes_received': likes_received,
                'likes_sent': likes_sent,
                'mutual_likes': mutual_likes
            }