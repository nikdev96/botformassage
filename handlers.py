"""
Обработчики сообщений для Nova Chaloklum Health Massage Telegram Bot
"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional

from aiogram import F, Router, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from config import ADMIN_CHAT_ID, TZ, TZINFO, MAX_DAYS_AHEAD, RESERVATIONS, user_languages, TEXTS
from models import BookingState
from utils import (
    get_text, get_lang, validate_date_format, validate_time_format, 
    is_valid_phone, safe_text, get_service_by_key, get_service_variant,
    get_category_by_local_name
)
from keyboards import (
    create_language_keyboard, create_main_menu, categories_kb,
    create_services_keyboard, create_duration_keyboard, create_confirm_keyboard
)
from calendar_utils import build_calendar, slots_kb

# Настройка логирования
logger = logging.getLogger(__name__)

# Создаем router для handlers
router = Router()

# === КОМАНДЫ И СТАРТОВЫЕ ХЭНДЛЕРЫ ===

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Команда /start - приветствие и выбор языка"""
    await state.clear()
    user_id = message.from_user.id
    
    if user_id in user_languages:
        # Пользователь уже выбрал язык ранее
        await message.answer(
            get_text(user_id, "choose_category"),
            reply_markup=categories_kb(user_id)
        )
    else:
        await message.answer(
            TEXTS["en"]["welcome"],
            reply_markup=create_language_keyboard()
        )

@router.message(Command("lang"))
async def cmd_lang(message: Message, state: FSMContext):
    """Команда смены языка"""
    await state.clear()
    user_id = message.from_user.id
    
    await message.answer(
        get_text(user_id, "choose_language"),
        reply_markup=create_language_keyboard()
    )

# === ВЫБОР ЯЗЫКА ===

@router.callback_query(F.data.startswith("lang:"))
async def select_language(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора языка"""
    lang = callback.data.split(":")[1]
    user_id = callback.from_user.id
    user_languages[user_id] = lang
    
    await callback.message.edit_text(
        get_text(user_id, "language_changed"),
        reply_markup=categories_kb(user_id)
    )
    await callback.answer()

# === ТЕКСТОВЫЕ СООБЩЕНИЯ (КНОПКИ МЕНЮ) ===

@router.message(F.text)
async def handle_text_menu(message: Message, state: FSMContext):
    """Обрабатывает текстовые сообщения от кнопок меню"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Если пользователь не выбрал язык, предлагаем выбрать
    if user_id not in user_languages:
        await message.answer(
            get_text(user_id, "welcome"),
            reply_markup=create_language_keyboard()
        )
        return
    
    # Проверяем, является ли это командой смены языка
    if text == get_text(user_id, "change_language"):
        await cmd_lang(message, state)
        return
    
    # Пытаемся найти категорию по названию кнопки
    # Убираем emoji из текста кнопки
    clean_text = text
    for emoji in ["🌿", "🧖‍♀️", "✨", "💅"]:
        clean_text = clean_text.replace(emoji, "").strip()
    
    category = get_category_by_local_name(user_id, clean_text)
    
    if category:
        await select_category_text(message, state, category)
    else:
        # Если в FSM состоянии, обрабатываем соответственно
        current_state = await state.get_state()
        
        if current_state == BookingState.entering_date.state:
            await process_date(message, state)
        elif current_state == BookingState.entering_time.state:
            await process_time(message, state)
        elif current_state == BookingState.entering_name.state:
            await process_name(message, state)
        elif current_state == BookingState.entering_phone.state:
            await process_phone(message, state)
        else:
            # Неизвестная команда, показываем меню
            await message.answer(f"Раздел временно недоступен.")

async def select_category_text(message: Message, state: FSMContext, category: str):
    """Показывает услуги выбранной категории"""
    user_id = message.from_user.id
    await state.clear()
    
    if category not in ["massage", "spa", "waxing", "nails"]:
        await message.answer(f"Раздел временно недоступен.")
        return
    
    category_name = get_text(user_id, f"categories.{category}")
    await message.answer(
        f"📋 *{category_name}*\n\nВыберите услугу:",
        reply_markup=create_services_keyboard(user_id, category)
    )
    await state.set_state(BookingState.selecting_service)

# === INLINE CALLBACK HANDLERS ===

@router.callback_query(F.data.startswith("cat:"))
async def select_category_inline(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор категории через inline кнопку"""
    category = callback.data.split(":")[1]
    user_id = callback.from_user.id
    await state.clear()
    
    category_name = get_text(user_id, f"categories.{category}")
    await callback.message.edit_text(
        f"📋 *{category_name}*\n\nВыберите услугу:",
        reply_markup=create_services_keyboard(user_id, category)
    )
    await state.set_state(BookingState.selecting_service)
    await callback.answer()

@router.callback_query(F.data.startswith("service:"))
async def select_service(callback_query: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор услуги"""
    service_key = callback_query.data.split(":")[1]
    user_id = callback_query.from_user.id
    
    service = get_service_by_key(service_key)
    if not service:
        await callback_query.answer("❌ Услуга не найдена")
        return
    
    await state.update_data(service_key=service_key)
    
    lang = get_lang(user_id)
    title = service.get_title(lang)
    
    if len(service.variants) == 1:
        # Если только один вариант, сразу переходим к выбору даты
        variant = service.variants[0]
        await state.update_data(duration=variant.duration_min)
        await state.set_state(BookingState.selecting_date)
        
        today = datetime.now(TZINFO).date()
        max_date = today + timedelta(days=MAX_DAYS_AHEAD)
        
        await callback_query.message.edit_text(
            get_text(user_id, "pick_date"),
            reply_markup=build_calendar(user_id, today.year, today.month, today, max_date)
        )
    else:
        await callback_query.message.edit_text(
            f"*{title}*\n\n{get_text(user_id, 'select_duration')}",
            reply_markup=create_duration_keyboard(user_id, service_key)
        )
        await state.set_state(BookingState.selecting_duration)
    
    await callback_query.answer()

@router.callback_query(F.data.startswith("duration:"))
async def select_duration(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор длительности услуги"""
    parts = callback.data.split(":")
    service_key = parts[1]
    duration = int(parts[2])
    user_id = callback.from_user.id
    
    await state.update_data(service_key=service_key, duration=duration)
    await state.set_state(BookingState.selecting_date)
    
    today = datetime.now(TZINFO).date()
    max_date = today + timedelta(days=MAX_DAYS_AHEAD)
    
    await callback.message.edit_text(
        get_text(user_id, "pick_date"),
        reply_markup=build_calendar(user_id, today.year, today.month, today, max_date)
    )
    await callback.answer()

# === КАЛЕНДАРЬ ===

@router.callback_query(F.data.startswith("cal_month:"))
async def calendar_navigate_month(callback: CallbackQuery, state: FSMContext):
    """Навигация по месяцам в календаре"""
    parts = callback.data.split(":")
    year = int(parts[1])
    month = int(parts[2])
    user_id = callback.from_user.id
    
    today = datetime.now(TZINFO).date()
    max_date = today + timedelta(days=MAX_DAYS_AHEAD)
    
    await callback.message.edit_reply_markup(
        reply_markup=build_calendar(user_id, year, month, today, max_date)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("cal_date:"))
async def select_calendar_date(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор даты из календаря"""
    parts = callback.data.split(":")
    year = int(parts[1])
    month = int(parts[2])
    day = int(parts[3])
    
    selected_date = date(year, month, day)
    user_id = callback.from_user.id
    
    # Сохраняем дату в состоянии
    date_str = selected_date.strftime("%d.%m.%Y")
    date_iso = selected_date.strftime("%Y-%m-%d")
    await state.update_data(date_str=date_str, date_iso=date_iso)
    
    # Получаем длительность из состояния
    data = await state.get_data()
    duration = data.get("duration", 60)
    
    # Показываем доступные временные слоты
    await callback.message.edit_text(
        get_text(user_id, "pick_time"),
        reply_markup=slots_kb(user_id, selected_date, duration)
    )
    await state.set_state(BookingState.selecting_time)
    await callback.answer()

@router.callback_query(F.data.startswith("slot_time:"))
async def select_time_slot(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор временного слота"""
    parts = callback.data.split(":")
    date_iso = parts[1]
    time_str = parts[2]
    user_id = callback.from_user.id
    
    await state.update_data(time_str=time_str)
    await state.set_state(BookingState.entering_name)
    
    await callback.message.edit_text(
        get_text(user_id, "step_name")
    )
    await callback.answer()

# === РУЧНОЙ ВВОД ДАННЫХ ===

@router.message(BookingState.entering_date)
async def process_date(message: Message, state: FSMContext):
    """Обрабатывает ввод даты в текстовом формате"""
    date_str = message.text.strip()
    user_id = message.from_user.id
    
    if not validate_date_format(date_str):
        await message.answer(
            get_text(user_id, "invalid_date")
        )
        return
    
    # Проверяем диапазон дат (не в прошлом и не далее 14 дней)
    try:
        input_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        today = datetime.now(TZINFO).date()
        max_date = today + timedelta(days=MAX_DAYS_AHEAD)
        
        if input_date < today:
            await message.answer(
                get_text(user_id, "invalid_date")
            )
            return
        
        if input_date > max_date:
            await message.answer(
                get_text(user_id, "invalid_date")
            )
            return
    except ValueError:
        await message.answer(
            get_text(user_id, "invalid_date")
        )
        return
    
    await state.update_data(date_str=date_str)
    await state.set_state(BookingState.entering_time)
    
    await message.answer(
        get_text(user_id, "step_time")
    )

@router.message(BookingState.entering_time)
async def process_time(message: Message, state: FSMContext):
    """Обрабатывает ввод времени"""
    time_str = message.text.strip()
    user_id = message.from_user.id
    
    if not validate_time_format(time_str):
        await message.answer(
            get_text(user_id, "invalid_time")
        )
        return
    
    await state.update_data(time_str=time_str)
    await state.set_state(BookingState.entering_name)
    
    await message.answer(
        get_text(user_id, "step_name")
    )

@router.message(BookingState.entering_name)
async def process_name(message: Message, state: FSMContext):
    """Обрабатывает ввод имени"""
    name = message.text.strip()
    user_id = message.from_user.id
    
    if len(name) < 2:
        await message.answer(get_text(user_id, "name_too_short"))
        return
    
    await state.update_data(client_name=name)
    await state.set_state(BookingState.entering_phone)
    
    await message.answer(
        get_text(user_id, "step_phone")
    )

@router.message(BookingState.entering_phone)
async def process_phone(message: Message, state: FSMContext):
    """Обрабатывает ввод телефона и показывает подтверждение"""
    phone = message.text.strip()
    user_id = message.from_user.id
    
    if not is_valid_phone(phone):
        await message.answer(get_text(user_id, "invalid_phone"))
        return
    
    await state.update_data(client_phone=phone)
    await state.set_state(BookingState.confirming)
    
    data = await state.get_data()
    service = get_service_by_key(data["service_key"])
    lang = user_languages.get(user_id, "en")
    service_title = service.get_title(lang)
    
    confirmation_text = get_text(
        user_id, "confirm_booking",
        service=service_title,
        duration=data["duration"],
        date=data["date_str"],
        time=data["time_str"],
        name=safe_text(data["client_name"]),
        phone=safe_text(data["client_phone"])
    )
    
    await message.answer(
        confirmation_text,
        reply_markup=create_confirm_keyboard(user_id)
    )

# === ПОДТВЕРЖДЕНИЕ ЗАПИСИ ===

@router.callback_query(BookingState.confirming, F.data.startswith("confirm:"))
async def process_confirmation(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Обрабатывает подтверждение записи"""
    action = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    if action == "no":
        await callback.message.edit_text(
            get_text(user_id, "booking_cancelled")
        )
        await state.clear()
        await callback.answer()
        return
    
    # Подтверждение записи
    data = await state.get_data()
    service = get_service_by_key(data["service_key"])
    variant = get_service_variant(data["service_key"], data["duration"])
    lang = user_languages.get(user_id, "en")
    service_title = service.get_title(lang)
    
    # Отправляем уведомление администратору
    if ADMIN_CHAT_ID:
        admin_message = get_text(
            user_id, "admin_new_booking",
            service=service_title,
            duration=data["duration"],
            date=data["date_str"],
            time=data["time_str"],
            name=safe_text(data["client_name"]),
            phone=safe_text(data["client_phone"]),
            user_id=user_id,
            username=safe_text(callback.from_user.username or "не указан"),
            tz=TZ
        )
        try:
            await bot.send_message(ADMIN_CHAT_ID, admin_message)
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления админу: {e}")
    
    # Подтверждение клиенту
    confirmation_message = get_text(
        user_id, "booking_confirmed",
        service=service_title,
        date=data["date_str"],
        time=data["time_str"],
        duration=data["duration"],
        price=variant.price_thb,
        tz=TZ
    )
    
    await callback.message.edit_text(
        confirmation_message
    )
    
    # Фиксируем слот в резервациях
    date_iso = data.get("date_iso")
    if date_iso and data.get("time_str"):
        try:
            # Парсим дату и время
            if date_iso:
                booking_date = datetime.fromisoformat(date_iso).date()
            else:
                # Парсим из date_str если date_iso отсутствует
                booking_date = datetime.strptime(data["date_str"], "%d.%m.%Y").date()
            
            booking_time = datetime.strptime(data["time_str"], "%H:%M").time()
            start_dt = datetime.combine(booking_date, booking_time)
            end_dt = start_dt + timedelta(minutes=data["duration"])
            
            # Добавляем резервацию
            date_key = booking_date.strftime("%Y-%m-%d")
            RESERVATIONS[date_key].append((start_dt, end_dt))
            
        except Exception as e:
            logger.error(f"Ошибка при фиксации резервации: {e}")
    
    await state.clear()
    await callback.answer("✅")

# === НАВИГАЦИЯ ===

@router.callback_query(F.data == "back_to_categories")
async def back_to_categories(callback: CallbackQuery, state: FSMContext):
    """Возвращает к выбору категорий"""
    user_id = callback.from_user.id
    await state.clear()
    
    await callback.message.edit_text(
        get_text(user_id, "choose_category"),
        reply_markup=categories_kb(user_id)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("back_to_services:"))
async def back_to_services(callback: CallbackQuery, state: FSMContext):
    """Возвращает к выбору услуг категории"""
    category = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    category_name = get_text(user_id, f"categories.{category}")
    await callback.message.edit_text(
        f"📋 *{category_name}*\n\nВыберите услугу:",
        reply_markup=create_services_keyboard(user_id, category)
    )
    await state.set_state(BookingState.selecting_service)
    await callback.answer()

@router.callback_query(F.data == "back_to_calendar")
async def back_to_calendar(callback: CallbackQuery, state: FSMContext):
    """Возвращает к календарю"""
    user_id = callback.from_user.id
    
    today = datetime.now(TZINFO).date()
    max_date = today + timedelta(days=MAX_DAYS_AHEAD)
    
    await callback.message.edit_text(
        get_text(user_id, "pick_date"),
        reply_markup=build_calendar(user_id, today.year, today.month, today, max_date)
    )
    await state.set_state(BookingState.selecting_date)
    await callback.answer()

@router.callback_query(F.data == "main_menu")
async def handle_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возвращает в главное меню"""
    user_id = callback.from_user.id
    await state.clear()
    
    await callback.message.edit_text(
        get_text(user_id, "choose_category"),
        reply_markup=categories_kb(user_id)
    )
    await callback.answer("✅")

@router.callback_query(F.data == "change_lang")
async def handle_change_lang(callback: CallbackQuery, state: FSMContext):
    """Смена языка через inline кнопку"""
    user_id = callback.from_user.id
    await state.clear()
    
    await callback.message.edit_text(
        get_text(user_id, "choose_language"),
        reply_markup=create_language_keyboard()
    )
    await callback.answer("✅")

# === ИГНОРИРУЕМЫЕ CALLBACK-И ===

@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    """Игнорирует callback от неактивных кнопок"""
    await callback.answer()