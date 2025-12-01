import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.storage.memory import MemoryStorage

from database import Database
import config
from admin import AdminTools

# Список админов (твой Telegram ID)
ADMIN_IDS = [2085406957]  # Замени на свой ID

# Инициализация
bot = Bot(config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
db = Database()

# FSM состояния для регистрации
class Registration(StatesGroup):
    name = State()
    interest = State()
    expertise = State()
    contact = State()

# FSM состояния для редактирования
class EditProfile(StatesGroup):
    waiting_field = State()
    waiting_value = State()

# Основная клавиатура
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👀 Смотреть анкеты"), KeyboardButton(text="❤️ Мои лайки")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="👤 Мой профиль")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )

# Обработчики
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user = await db.get_user_by_tg(message.from_user.id)
    if user:
        await message.answer(
            f"Привет, {user['name']}! 👋\n\n"
            "Используй кнопки ниже для навигации:",
            reply_markup=get_main_keyboard()
        )
        return
    
    await message.answer(
        "🌟 Добро пожаловать в SkillSwap!\n\n"
        "Давай создадим твой профиль. Как тебя зовут?",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(Registration.name)

# Обработка основной клавиатуры
@dp.message(F.text == "👀 Смотреть анкеты")
async def handle_browse_button(message: types.Message):
    await cmd_browse(message)

@dp.message(F.text == "❤️ Мои лайки")
async def handle_likes_button(message: types.Message):
    await cmd_likes(message)

@dp.message(F.text == "📊 Статистика")
async def handle_stats_button(message: types.Message):
    await cmd_stats(message)

@dp.message(F.text == "👤 Мой профиль")
async def handle_profile_button(message: types.Message):
    await cmd_profile(message)

# Регистрация
@dp.message(Registration.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("🎯 Коротко опиши свои интересы (чему хочешь научиться)?")
    await state.set_state(Registration.interest)

@dp.message(Registration.interest)
async def process_interest(message: types.Message, state: FSMContext):
    await state.update_data(interest=message.text.strip())
    await message.answer("💼 В какой сфере ты можешь помогать другим (твоя экспертиза)?")
    await state.set_state(Registration.expertise)

@dp.message(Registration.expertise)
async def process_expertise(message: types.Message, state: FSMContext):
    await state.update_data(expertise=message.text.strip())
    await message.answer(
        "📱 Укажи свой Telegram для связи (например @username):\n\n"
        "⚠️ Этот тег увидят только те, кому ты понравишься!"
    )
    await state.set_state(Registration.contact)

@dp.message(Registration.contact)
async def process_contact(message: types.Message, state: FSMContext):
    contact_tag = message.text.strip()
    if not contact_tag.startswith('@'):
        contact_tag = '@' + contact_tag
    
    user_data = await state.get_data()
    
    # Сохраняем пользователя
    user = await db.save_user(
        tg_id=message.from_user.id,
        name=user_data['name'],
        interest=user_data['interest'],
        expertise=user_data['expertise'],
        contact=contact_tag
    )
    
    await state.clear()
    
    await message.answer(
        f"✅ Отлично, {user['name']}! Профиль создан!\n\n"
        "Теперь используй кнопки для навигации:",
        reply_markup=get_main_keyboard()
    )

# Команда профиля с кнопками редактирования
@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    user = await db.get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйся - /start")
        return
    
    text = (
        f"👤 <b>Твой профиль</b>\n\n"
        f"📝 Имя: {user['name']}\n"
        f"🎯 Интересы: {user['interest_area']}\n"
        f"💼 Экспертиза: {user['expertise_area']}\n"
        f"📱 Контакт: {user['contact_tag']}\n\n"
        f"🆔 ID: {user['id']}"
    )
    
    # Клавиатура для редактирования
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить имя", callback_data="edit_name")],
        [InlineKeyboardButton(text="🎯 Изменить интересы", callback_data="edit_interest")],
        [InlineKeyboardButton(text="💼 Изменить экспертизу", callback_data="edit_expertise")],
        [InlineKeyboardButton(text="📱 Изменить контакт", callback_data="edit_contact")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_edit")]
    ])
    
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

# Обработка кнопок редактирования
@dp.callback_query(F.data.startswith("edit_"))
async def handle_edit_start(callback: types.CallbackQuery, state: FSMContext):
    field_map = {
        "edit_name": ("имя", "name"),
        "edit_interest": ("интересы", "interest_area"),
        "edit_expertise": ("экспертизу", "expertise_area"),
        "edit_contact": ("контакт", "contact_tag")
    }
    
    field_name, db_field = field_map[callback.data]
    
    await state.set_state(EditProfile.waiting_value)
    await state.update_data(editing_field=db_field, field_name=field_name)
    
    await callback.message.answer(f"Введи новое значение для {field_name}:")
    await callback.answer()

@dp.callback_query(F.data == "cancel_edit")
async def handle_cancel_edit(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Редактирование отменено")
    await callback.answer()

# Обработка ввода нового значения
@dp.message(EditProfile.waiting_value)
async def handle_edit_value(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    field = user_data['editing_field']
    field_name = user_data['field_name']
    new_value = message.text.strip()
    
    # Для контакта добавляем @ если нужно
    if field == 'contact_tag' and not new_value.startswith('@'):
        new_value = '@' + new_value
    
    # Обновляем в базе
    updated_user = await db.update_user(message.from_user.id, **{field: new_value})
    
    if updated_user:
        await message.answer(f"✅ {field_name.capitalize()} успешно обновлено!")
        # Показываем обновленный профиль
        await cmd_profile(message)
    else:
        await message.answer("❌ Ошибка при обновлении профиля")
    
    await state.clear()

# Лента анкет
@dp.message(Command("browse"))
async def cmd_browse(message: types.Message):
    user = await db.get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйся - /start")
        return
    
    profiles = await db.get_unseen_profiles(message.from_user.id, limit=1)
    
    if not profiles:
        await message.answer("🎉 Ты просмотрел все анкеты! Загляни позже.")
        return
    
    profile = profiles[0]
    
    text = (
        f"👤 <b>{profile['name']}</b>\n\n"
        f"🎯 Интересы: {profile['interest_area']}\n"
        f"💼 Экспертиза: {profile['expertise_area']}\n\n"
        f"<i>Тег откроется после лайка ❤️</i>"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❤️ Лайк", callback_data=f"like:{profile['id']}"),
            InlineKeyboardButton(text="➡️ Пропустить", callback_data=f"skip:{profile['id']}")
        ],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")]
    ])
    
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

# Обработка кнопки "В главное меню"
@dp.callback_query(F.data == "main_menu")
async def handle_main_menu(callback: types.CallbackQuery):
    await callback.message.answer(
        "Возвращаемся в главное меню:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

# Обработка лайка
@dp.callback_query(F.data.startswith("like:"))
async def cb_like(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    tg_user = callback.from_user
    
    success, info = await db.save_like(tg_user.id, user_id)
    
    if not success:
        if info == "not_registered":
            await callback.message.answer("Сначала зарегистрируйся - /start")
        elif info == "already_liked":
            await callback.answer("Ты уже лайкал эту анкету")
        await callback.answer()
        return
    
    target_user = await db.get_user_by_id(user_id)
    
    if target_user:
        await callback.message.answer(
            f"❤️ Ты лайкнул(а) {target_user['name']}!\n\n"
            f"📱 Telegram: {target_user['contact_tag']}\n\n"
            f"💬 Напиши ему/ей и договорись о менторстве!",
            reply_markup=get_main_keyboard()
        )
        
        await bot.send_message(
            target_user['telegram_id'],
            f"🎉 Твой профиль понравился {tg_user.full_name}!\n\n"
            f"Теперь они могут написать тебе\n\n"
            f"Посмотреть всех, кто тебя лайкнул - нажми '❤️ Мои лайки'"
        )
    
    await callback.answer("Лайк отправлен!")

# Обработка пропуска - ИСПРАВЛЕННАЯ ВЕРСИЯ
@dp.callback_query(F.data.startswith("skip:"))
async def cb_skip(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    
    # Сохраняем пропуск
    success = await db.save_skip(callback.from_user.id, user_id)
    
    if not success:
        await callback.answer("Ошибка: пользователь не найден")
        return
    
    await callback.answer("Пропущено")
    
    # Получаем следующую анкету
    user = await db.get_user_by_tg(callback.from_user.id)
    if not user:
        await callback.message.edit_text("Сначала зарегистрируйся - /start")
        return
    
    profiles = await db.get_unseen_profiles(callback.from_user.id, limit=1)
    
    if not profiles:
        await callback.message.edit_text("🎉 Ты просмотрел все анкеты! Загляни позже.")
        return
    
    profile = profiles[0]
    
    text = (
        f"👤 <b>{profile['name']}</b>\n\n"
        f"🎯 Интересы: {profile['interest_area']}\n"
        f"💼 Экспертиза: {profile['expertise_area']}\n\n"
        f"<i>Тег откроется после лайка ❤️</i>"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❤️ Лайк", callback_data=f"like:{profile['id']}"),
            InlineKeyboardButton(text="➡️ Пропустить", callback_data=f"skip:{profile['id']}")
        ],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

# Лайки
@dp.message(Command("likes"))
async def cmd_likes(message: types.Message):
    user = await db.get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйся - /start")
        return
    
    likers = await db.get_likes_for_user(message.from_user.id)
    
    if not likers:
        await message.answer(
            "😔 Пока никто не лайкнул твой профиль\n\n"
            "Продолжай смотреть анкеты!",
            reply_markup=get_main_keyboard()
        )
        return
    
    text = "❤️ <b>Тебя лайкнули:</b>\n\n"
    for liker in likers:
        text += f"👤 {liker['name']} - {liker['contact_tag']}\n"
    
    text += "\n🎉 Напиши им и начни общение!"
    
    await message.answer(text, parse_mode="HTML")

# Статистика
@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    user = await db.get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйся - /start")
        return
    
    likers = await db.get_likes_for_user(message.from_user.id)
    mutual = await db.get_mutual_likes(message.from_user.id)
    
    text = (
        f"📊 <b>Твоя статистика</b>\n\n"
        f"❤️ Тебя лайкнули: {len(likers)} чел.\n"
        f"💫 Взаимные лайки: {len(mutual)} чел.\n\n"
        f"Продолжай в том же духе! 🚀"
    )
    
    await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard())

async def main():
    await db.create_pool()
    print("Бот запущен с исправленным пропуском! 🚀")
    await dp.start_polling(bot)

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Панель администратора"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещен")
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика пользователей", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📈 Активность", callback_data="admin_activity")],
        [InlineKeyboardButton(text="🎯 Топ интересов", callback_data="admin_top")],
        [InlineKeyboardButton(text="💾 Экспорт базы", callback_data="admin_export")],
        [InlineKeyboardButton(text="📤 Выгрузить CSV", callback_data="admin_csv")]
    ])
    
    await message.answer("🛠️ Панель администратора:", reply_markup=kb)

@dp.callback_query(F.data == "admin_csv")
async def handle_admin_csv(callback: types.CallbackQuery):
    """Выгрузка CSV"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещен")
        return
    
    await callback.message.answer("⏳ Формирую CSV отчет...")
    
    try:
        filename, count = await AdminTools.get_user_stats_csv()
        
        # Отправляем файл
        with open(filename, 'rb') as f:
            await callback.message.answer_document(
                types.BufferedInputFile(f.read(), filename=filename),
                caption=f"📊 Отчет: {count} пользователей"
            )
        
        await callback.answer("✅ Файл отправлен")
        
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка: {e}")
        await callback.answer("Ошибка")

@dp.callback_query(F.data == "admin_stats")
async def handle_admin_stats(callback: types.CallbackQuery):
    """Быстрая статистика"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещен")
        return
    
    async with db.pool.acquire() as conn:
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
        total_likes = await conn.fetchval("SELECT COUNT(*) FROM likes")
        total_skips = await conn.fetchval("SELECT COUNT(*) FROM skips")
        active_today = await conn.fetchval("""
            SELECT COUNT(DISTINCT from_user_id) 
            FROM likes 
            WHERE created_at >= CURRENT_DATE
        """)
    
    text = (
        "📈 **Общая статистика:**\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"❤️ Всего лайков: {total_likes}\n"
        f"➡️ Всего пропусков: {total_skips}\n"
        f"🎯 Активных сегодня: {active_today}\n"
        f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

# Добавь обработчики для других кнопок аналогично

if __name__ == "__main__":
    asyncio.run(main())