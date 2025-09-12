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

from config import ADMIN_CHAT_ID, TZ, TZINFO, MAX_DAYS_AHEAD, RESERVATIONS, user_languages, TEXTS, FEATURE_AI_BOOKING, OPENAI_API_KEY
from models import BookingState, SERVICE_CATEGORIES
from aiogram.fsm.state import State, StatesGroup
from utils import (
    get_text, get_lang, validate_date_format, validate_time_format, 
    is_valid_phone, safe_text, get_service_by_key, get_service_variant,
    get_category_by_local_name, reserve_and_notify, show_calendar_for_booking,
    show_time_slots, handle_fsm_back_navigation
)
from keyboards import (
    create_language_keyboard, create_main_menu, categories_kb,
    create_services_keyboard, create_duration_keyboard, create_confirm_keyboard,
    create_back_keyboard
)
from calendar_utils import build_calendar, slots_kb
from chatgpt import ask_chatgpt

# Состояния для AI чата
class ChatState(StatesGroup):
    asking = State()

class AIState(StatesGroup):
    asking = State()

# Настройка логирования
logger = logging.getLogger(__name__)

# Создаем router для handlers
router = Router()

# === КОМАНДЫ И СТАРТОВЫЕ ХЭНДЛЕРЫ ===

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """
    Команда /start - приветствие и выбор языка
    
    Args:
        message: Входящее сообщение от пользователя
        state: FSM контекст для управления состояниями
    """
    await state.clear()
    user_id = message.from_user.id
    
    if user_id in user_languages:
        # Пользователь уже выбрал язык ранее
        await message.answer(
            get_text(user_id, "choose_category"),
            reply_markup=create_main_menu(user_id)
        )
    else:
        await message.answer(
            TEXTS["en"]["welcome"],
            reply_markup=create_language_keyboard()
        )

@router.message(Command("lang"))
async def cmd_lang(message: Message, state: FSMContext) -> None:
    """
    Команда смены языка
    
    Args:
        message: Входящее сообщение от пользователя
        state: FSM контекст для управления состояниями
    """
    await state.clear()
    user_id = message.from_user.id
    
    await message.answer(
        get_text(user_id, "choose_language"),
        reply_markup=create_language_keyboard()
    )

@router.message(Command("ai"))
async def cmd_ai(message: Message, state: FSMContext):
    """Команда запуска AI ассистента"""
    await state.clear()
    user_id = message.from_user.id
    
    from config import FEATURE_CHATGPT, OPENAI_API_KEY
    
    # Проверяем, доступен ли AI
    if not FEATURE_CHATGPT or not OPENAI_API_KEY:
        await message.answer(get_text(user_id, "ai_unavailable"))
        return
    
    # Переводим в режим ожидания вопроса
    await state.set_state(ChatState.asking)
    await message.answer(get_text(user_id, "enter_ai_question"))

@router.message(Command("ai_book"))
async def cmd_ai_book(message: Message, state: FSMContext):
    """Команда запуска AI booking ассистента"""
    await state.clear()
    user_id = message.from_user.id
    
    # Проверяем, доступен ли AI booking
    if not FEATURE_AI_BOOKING or not OPENAI_API_KEY:
        await message.answer(get_text(user_id, "ai_unavailable"))
        return
    
    # Переводим в режим AI бронирования
    await state.set_state(AIState.asking)
    await message.answer(get_text(user_id, "ai_start"))

# === ВЫБОР ЯЗЫКА ===

@router.callback_query(F.data.startswith("lang:"))
async def select_language(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора языка"""
    lang = callback.data.split(":")[1]
    user_id = callback.from_user.id
    user_languages[user_id] = lang
    
    await callback.message.edit_text(
        get_text(user_id, "language_changed")
    )
    # Отправляем новое сообщение с reply-клавиатурой
    await callback.message.answer(
        get_text(user_id, "choose_category"),
        reply_markup=create_main_menu(user_id)
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
    
    # Проверяем, является ли это кнопкой главного меню
    if text == get_text(user_id, "main_menu"):
        await state.clear()
        await message.answer(
            get_text(user_id, "choose_category"),
            reply_markup=create_main_menu(user_id)
        )
        return
    
    # Проверяем, является ли это кнопкой "Назад"
    if text == get_text(user_id, "back"):
        await handle_back_button(message, state)
        return
    
    # Проверяем, является ли это командой AI booking
    if text == get_text(user_id, "ai_booking"):
        await cmd_ai_book(message, state)
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
        elif current_state == ChatState.asking.state:
            await process_ai_question(message, state)
        elif current_state == AIState.asking.state:
            await process_ai_booking(message, state)
        else:
            # Проверяем, не запрос ли это на бронирование
            booking_keywords = [
                "записать", "запись", "забронировать", "бронь", "хочу массаж", 
                "можно записаться", "записаться на", "booking", "book", "appointment",
                "massage appointment", "можешь записать", "запиши меня"
            ]
            
            text_lower = text.lower()
            is_booking_request = any(keyword in text_lower for keyword in booking_keywords)
            
            if is_booking_request:
                # Это запрос на бронирование - активируем AI booking
                await cmd_ai_book(message, state)
                return
            
            # Обычная команда - попробуем ответить через ChatGPT
            from config import FEATURE_CHATGPT, OPENAI_API_KEY
            if FEATURE_CHATGPT and OPENAI_API_KEY:
                # Отправляем вопрос в ChatGPT
                thinking_msg = await message.answer("🤖 Думаю...")
                try:
                    response = await ask_chatgpt(text, user_id)
                    await thinking_msg.edit_text(response)
                except Exception as e:
                    logger.error(f"Error in auto ChatGPT: {e}")
                    await thinking_msg.edit_text("Используйте кнопки меню или команду 🤖 для вопросов к AI")
            else:
                # ChatGPT отключен, показываем стандартное сообщение
                await message.answer("Используйте кнопки меню ниже 👇")

async def handle_back_button(message: Message, state: FSMContext):
    """Обрабатывает нажатие кнопки 'Назад'"""
    user_id = message.from_user.id
    current_state = await state.get_state()
    
    await handle_fsm_back_navigation(user_id, message, state, current_state)

async def select_category_text(message: Message, state: FSMContext, category: str):
    """Показывает услуги выбранной категории"""
    user_id = message.from_user.id
    await state.clear()
    
    if category not in ["massage", "spa", "waxing", "nails"]:
        await message.answer(get_text(user_id, "section_unavailable"))
        return
    
    # Маппинг для корректной локализации категорий
    category_key = "wax" if category == "waxing" else category
    category_name = get_text(user_id, f"categories.{category_key}")
    await message.answer(
        f"📋 *{safe_text(category_name)}*\n\n{get_text(user_id, 'select_service')}:",
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
    
    # Маппинг для корректной локализации категорий
    category_key = "wax" if category == "waxing" else category
    category_name = get_text(user_id, f"categories.{category_key}")
    await callback.message.edit_text(
        f"📋 *{safe_text(category_name)}*\n\n{get_text(user_id, 'select_service')}:",
        reply_markup=create_services_keyboard(user_id, category)
    )
    await state.set_state(BookingState.selecting_service)
    await callback.answer()

@router.callback_query(F.data.startswith("service:"))
async def select_service(callback_query: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор услуги"""
    service_key = callback_query.data.split(":")[1]
    user_id = callback_query.from_user.id
    
    logger.info(f"🔧 Выбрана услуга: {service_key} пользователем {user_id}")
    
    service = get_service_by_key(service_key)
    if not service:
        await callback_query.answer("❌ Услуга не найдена")
        return
    
    await state.update_data(service_key=service_key)
    
    lang = get_lang(user_id)
    title = service.get_title(lang)
    
    # Определяем категорию услуги
    service_category = None
    for category, services in SERVICE_CATEGORIES.items():
        if service_key in services:
            service_category = category
            break
    
    # Обработка фиксированных длительностей для категорий
    if service_category == "nails":
        # Nails: фиксированная длительность 90 минут, сразу к календарю
        await state.update_data(duration=90)
        await show_calendar_for_booking(user_id, callback_query, state)
    elif service_category == "waxing":
        # Waxing: первый вариант или 60 минут по умолчанию
        duration = 60  # fallback
        if service.variants:
            duration = service.variants[0].duration_min
        
        await state.update_data(duration=duration)
        await show_calendar_for_booking(user_id, callback_query, state)
    elif len(service.variants) == 1:
        # Massage/Spa с одним вариантом - сразу к календарю
        variant = service.variants[0]
        await state.update_data(duration=variant.duration_min)
        await show_calendar_for_booking(user_id, callback_query, state)
    else:
        # Massage/Spa с несколькими вариантами - показываем выбор длительности
        await callback_query.message.edit_text(
            f"*{safe_text(title)}*\n\n{get_text(user_id, 'select_duration')}",
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
    await show_calendar_for_booking(user_id, callback, state)
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
    
    # Получаем длительность и service_key из состояния
    data = await state.get_data()
    duration = data.get("duration", 60)
    service_key = data.get("service_key", "")
    
    # Определяем категорию для выбора шага слотов
    service_category = None
    for category, services in SERVICE_CATEGORIES.items():
        if service_key in services:
            service_category = category
            break
    
    # Используем стандартный шаг слотов для всех категорий
    step_min = None
    
    # Показываем доступные временные слоты
    await show_time_slots(user_id, callback, state, selected_date, duration, step_min)
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
    
    # Отправляем отдельное сообщение с reply клавиатурой 
    await callback.message.answer(
        get_text(user_id, "enter_name_prompt"),
        reply_markup=create_back_keyboard(user_id)
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
        get_text(user_id, "step_time"),
        reply_markup=create_back_keyboard(user_id)
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
        get_text(user_id, "step_phone"),
        reply_markup=create_back_keyboard(user_id)
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

# === AI АССИСТЕНТ ===

@router.message(ChatState.asking)
async def process_ai_question(message: Message, state: FSMContext):
    """Обрабатывает вопрос к AI ассистенту"""
    question = message.text.strip()
    user_id = message.from_user.id
    
    if not question:
        await message.answer(get_text(user_id, "enter_ai_question"))
        return
    
    # Отправляем временное сообщение "Думаю..."
    thinking_msg = await message.answer(get_text(user_id, "ai_thinking"))
    
    # Получаем ответ от ChatGPT
    response = await ask_chatgpt(question, user_id)
    
    # Редактируем сообщение с ответом
    await thinking_msg.edit_text(response)
    
    # Отправляем reply-клавиатуру для продолжения работы
    await message.answer(
        get_text(user_id, "choose_category"),
        reply_markup=create_main_menu(user_id)
    )
    
    # Очищаем состояние
    await state.clear()

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
        # Отправляем reply-клавиатуру для продолжения работы
        await callback.message.answer(
            get_text(user_id, "choose_category"),
            reply_markup=create_main_menu(user_id)
        )
        await state.clear()
        await callback.answer()
        return
    
    # Подтверждение записи (единая функция: уведомления, резервация, интеграции)
    data = await state.get_data()
    try:
        confirmation_message = await reserve_and_notify(
            bot,
            user_id,
            data,
            booking_source="manual",
        )
    except TypeError:
        # Совместимость со старой сигнатурой (если резервация без доп. параметров)
        confirmation_message = await reserve_and_notify(bot, user_id, data, "manual")

    await callback.message.edit_text(confirmation_message)

    # Отправляем reply-клавиатуру для продолжения работы
    await callback.message.answer(
        get_text(user_id, "choose_category"),
        reply_markup=create_main_menu(user_id)
    )

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
    
    # Маппинг для корректной локализации категорий
    category_key = "wax" if category == "waxing" else category
    category_name = get_text(user_id, f"categories.{category_key}")
    await callback.message.edit_text(
        f"📋 *{safe_text(category_name)}*\n\n{get_text(user_id, 'select_service')}:",
        reply_markup=create_services_keyboard(user_id, category)
    )
    await state.set_state(BookingState.selecting_service)
    await callback.answer()

@router.callback_query(F.data == "back_to_calendar")
async def back_to_calendar(callback: CallbackQuery, state: FSMContext):
    """Возвращает к календарю"""
    user_id = callback.from_user.id
    
    await show_calendar_for_booking(user_id, callback, state)
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

# === AI BOOKING ХЕНДЛЕРЫ ===

async def process_ai_booking(message: Message, state: FSMContext):
    """Обрабатывает диалог AI booking"""
    from ai_booking import ai_book
    
    user_id = message.from_user.id
    text = message.text.strip()
    
    if not text:
        await message.answer(get_text(user_id, "ai_start"))
        return
    
    # Получаем контекст из состояния
    data = await state.get_data()
    context = data.get("ai_context", {})
    
    # Отправляем "думаю..." сообщение
    thinking_msg = await message.answer(get_text(user_id, "ai_thinking"))
    
    try:
        # Обрабатываем через AI
        response, booking_data = await ai_book(user_id, text, context)
        logger.info(f"AI response: {repr(response)}")
        
        # Редактируем сообщение с ответом (с защитой от Markdown ошибок)
        try:
            await thinking_msg.edit_text(response)
        except Exception as edit_error:
            # Если ошибка парсинга Markdown, отправляем без разметки
            logger.warning(f"Failed to edit with Markdown, trying plain text: {edit_error}")
            try:
                await thinking_msg.edit_text(response, parse_mode=None)
            except Exception:
                # Если и это не работает, отправляем новое сообщение
                await message.answer(response, parse_mode=None)
        
        if booking_data:
            # Готово к подтверждению - показываем кнопки (сообщение уже отправлено в edit_text)
            from keyboards import create_confirm_keyboard
            await message.answer(
                "👆 Подтверждаете запись?",
                reply_markup=create_confirm_keyboard(user_id)
            )
            # Сохраняем данные бронирования в состояние
            await state.update_data(ai_booking_data=booking_data)
        else:
            # Нужны уточнения - обновляем контекст
            context.update({
                "last_user_input": text,
                "last_ai_response": response
            })
            await state.update_data(ai_context=context)
            
    except Exception as e:
        logger.error(f"Error in AI booking: {e}")
        await thinking_msg.edit_text(get_text(user_id, "ai_unavailable"))

@router.callback_query(AIState.asking, F.data.startswith("confirm:"))
async def ai_confirm_booking(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Обрабатывает подтверждение AI booking"""
    action = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    if action == "no":
        await callback.message.edit_text(
            get_text(user_id, "booking_cancelled")
        )
        # Отправляем reply-клавиатуру для продолжения работы  
        await callback.message.answer(
            get_text(user_id, "choose_category"),
            reply_markup=create_main_menu(user_id)
        )
        await state.clear()
        await callback.answer()
        return
    
    # Подтверждение записи через AI
    data = await state.get_data()
    booking_data = data.get("ai_booking_data")
    
    if not booking_data:
        await callback.message.edit_text(get_text(user_id, "ai_unavailable"))
        await state.clear()
        await callback.answer()
        return
    
    try:
        # Используем общую функцию резервации
        confirmation_message = await reserve_and_notify(bot, user_id, booking_data, "ai")
        
        # Показываем подтверждение
        await callback.message.edit_text(confirmation_message)
        
        # Отправляем reply-клавиатуру для продолжения работы
        await callback.message.answer(
            get_text(user_id, "choose_category"),
            reply_markup=create_main_menu(user_id)
        )
        
    except Exception as e:
        logger.error(f"Error confirming AI booking: {e}")
        await callback.message.edit_text(get_text(user_id, "ai_unavailable"))
    
    await state.clear()
    await callback.answer("✅")

# === ИГНОРИРУЕМЫЕ CALLBACK-И ===

@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    """Игнорирует callback от неактивных кнопок"""
    await callback.answer()
