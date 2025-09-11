"""
Утилиты для Nova Chaloklum Health Massage Telegram Bot
"""
import re
import logging
from datetime import datetime, timedelta
from typing import Optional
from config import TEXTS, user_languages, TZ
from models import SERVICE_CATALOG, SERVICE_CATEGORIES, Service, ServiceVariant

logger = logging.getLogger(__name__)

def escape_md(text: str) -> str:
    """Экранирует спецсимволы Markdown для безопасной подстановки пользовательского ввода"""
    special_chars = "_*[]()~>#+-=|{}.!"
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text

def safe_text(text: str) -> str:
    """Безопасная обработка пользовательского текста для Markdown"""
    if not text:
        return ""
    return escape_md(str(text).strip())

def is_valid_phone(phone: str) -> bool:
    """Улучшенная валидация телефонного номера с поддержкой различных форматов"""
    if not phone:
        return False
    
    # Поддержка: +, цифры, пробелы, скобки, тире
    # Минимум 10 цифр, максимум 15
    pattern = r'^\+?[\d\s\-\(\)]{10,20}$'
    
    if not re.match(pattern, phone):
        return False
    
    # Проверяем, что есть достаточно цифр (минимум 10)
    digits_only = re.sub(r'[^\d]', '', phone)
    return 10 <= len(digits_only) <= 15

def get_text(user_id: int, key: str, **kwargs) -> str:
    """Получает локализованный текст по ключу"""
    lang = get_lang(user_id)
    
    # Навигация по вложенным ключам (например, "categories.massage")
    keys = key.split(".")
    text = TEXTS[lang]
    for k in keys:
        if isinstance(text, dict) and k in text:
            text = text[k]
        else:
            # Fallback на английский, если ключ не найден
            text = TEXTS["en"]
            for k in keys:
                if isinstance(text, dict) and k in text:
                    text = text[k]
                else:
                    return f"❌ Text not found: {key}"
            break
    
    # Форматирование с параметрами
    if isinstance(text, str) and kwargs:
        try:
            return text.format(**kwargs)
        except KeyError as e:
            return f"❌ Missing parameter {e} for key: {key}"
    
    return str(text)

def get_lang(user_id: int) -> str:
    """Получает язык пользователя (по умолчанию английский)"""
    return user_languages.get(user_id, "en")

def validate_date_format(date_str: str) -> bool:
    """Валидирует формат даты ДД.ММ.ГГГГ"""
    pattern = r'^\d{2}\.\d{2}\.\d{4}$'
    return bool(re.match(pattern, date_str))

def validate_time_format(time_str: str) -> bool:
    """Валидирует формат времени ЧЧ:ММ"""
    pattern = r'^\d{2}:\d{2}$'
    if not re.match(pattern, time_str):
        return False
    
    # Дополнительная валидация значений
    try:
        hours, minutes = map(int, time_str.split(':'))
        return 0 <= hours <= 23 and 0 <= minutes <= 59
    except ValueError:
        return False

def get_service_by_key(service_key: str) -> Optional[Service]:
    """Находит услугу по ключу"""
    for service in SERVICE_CATALOG:
        if service.key == service_key:
            return service
    return None

def get_service_variant(service_key: str, duration: int) -> Optional[ServiceVariant]:
    """Находит вариант услуги по ключу и длительности"""
    service = get_service_by_key(service_key)
    if service:
        for variant in service.variants:
            if variant.duration_min == duration:
                return variant
    return None

def get_category_by_local_name(user_id: int, category_name: str) -> Optional[str]:
    """Находит категорию по локализованному имени"""
    lang = get_lang(user_id)
    
    for category_key in SERVICE_CATEGORIES.keys():
        # Маппинг для корректной локализации (waxing -> wax)
        text_key = "wax" if category_key == "waxing" else category_key
        localized_name = get_text(user_id, f"categories.{text_key}")
        if localized_name.lower() == category_name.lower():
            return category_key
    
    return None

async def show_calendar_for_booking(user_id: int, message_or_callback, state: 'FSMContext') -> None:
    """
    Helper функция для показа календаря и установки состояния selecting_date
    
    Args:
        user_id: ID пользователя
        message_or_callback: Message или CallbackQuery объект для отправки/редактирования
        state: FSM состояние
    """
    logger.info(f"📅 Показываю календарь для пользователя {user_id}")
    from datetime import datetime, timedelta
    from config import TZINFO, MAX_DAYS_AHEAD
    from models import BookingState
    
    today = datetime.now(TZINFO).date()
    max_date = today + timedelta(days=MAX_DAYS_AHEAD)
    
    # Импорт внутри функции чтобы избежать циклический импорт
    from calendar_utils import build_calendar
    
    calendar_markup = build_calendar(user_id, today.year, today.month, today, max_date)
    pick_date_text = get_text(user_id, "pick_date")
    
    await state.set_state(BookingState.selecting_date)
    
    # Проверяем тип объекта и вызываем соответствующий метод
    try:
        # Проверяем если это CallbackQuery
        if hasattr(message_or_callback, 'message'):
            # CallbackQuery - редактируем сообщение
            logger.info(f"📅 Редактирую сообщение с календарем для {user_id} (CallbackQuery)")
            await message_or_callback.message.edit_text(pick_date_text, reply_markup=calendar_markup)
            await message_or_callback.answer()  # Отвечаем на callback
        else:
            # Message - отправляем новое сообщение
            logger.info(f"📅 Отправляю новое сообщение с календарем для {user_id} (Message)")
            await message_or_callback.answer(pick_date_text, reply_markup=calendar_markup)
        logger.info(f"✅ Календарь успешно отправлен пользователю {user_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке календаря пользователю {user_id}: {e}")


async def show_time_slots(user_id: int, callback: 'CallbackQuery', state: 'FSMContext', selected_date: 'date', duration: int, step_min: Optional[int] = None) -> None:
    """
    Helper функция для показа временных слотов и установки состояния selecting_time
    
    Args:
        user_id: ID пользователя
        callback: CallbackQuery объект
        state: FSM состояние
        selected_date: Выбранная дата
        duration: Длительность услуги в минутах
        step_min: Шаг слотов в минутах (опционально)
    """
    from models import BookingState
    
    # Импорт внутри функции чтобы избежать циклический импорт
    from calendar_utils import slots_kb
    
    pick_time_text = get_text(user_id, "pick_time")
    time_slots_markup = slots_kb(user_id, selected_date, duration, step_min)
    
    await callback.message.edit_text(pick_time_text, reply_markup=time_slots_markup)
    await state.set_state(BookingState.selecting_time)


async def handle_fsm_back_navigation(user_id: int, message: 'Message', state: 'FSMContext', current_state: str) -> None:
    """
    Helper функция для обработки навигации "Назад" в FSM состояниях
    
    Args:
        user_id: ID пользователя
        message: Message объект
        state: FSM состояние
        current_state: Текущее состояние FSM
    """
    from models import BookingState
    from keyboards import create_back_keyboard, create_main_menu
    
    if current_state == BookingState.entering_phone.state:
        # Возвращаемся к вводу имени
        await state.set_state(BookingState.entering_name)
        await message.answer(
            get_text(user_id, "step_name"),
            reply_markup=create_back_keyboard(user_id)
        )
    elif current_state == BookingState.entering_name.state:
        # Возвращаемся к вводу времени
        await state.set_state(BookingState.entering_time)
        await message.answer(
            get_text(user_id, "step_time"),
            reply_markup=create_back_keyboard(user_id)
        )
    elif current_state == BookingState.entering_time.state:
        # Возвращаемся к выбору даты - показываем календарь
        await show_calendar_for_booking(user_id, message, state)
    else:
        # Во всех остальных состояниях возвращаем в главное меню
        await state.clear()
        await message.answer(
            get_text(user_id, "choose_category"),
            reply_markup=create_main_menu(user_id)
        )


def run_offline_tests() -> None:
    """Запускает офлайн-тесты согласно ТЗ"""
    print("🧪 Запуск офлайн-тестов...")
    
    # Имитируем пользователя с русским языком
    test_user_id = 12345
    user_languages[test_user_id] = "ru"
    
    # Тест 1: Проверяем локализацию
    welcome_ru = get_text(test_user_id, "welcome")
    assert "Добро пожаловать" in welcome_ru, f"Ошибка русской локализации: {welcome_ru}"
    
    # Переключаемся на английский
    user_languages[test_user_id] = "en"
    welcome_en = get_text(test_user_id, "welcome")
    assert "Welcome" in welcome_en, f"Ошибка английской локализации: {welcome_en}"
    
    # Тест 2: Проверяем каталог услуг
    assert len(SERVICE_CATALOG) > 0, "Каталог услуг пуст"
    
    # Проверяем наличие ключевых услуг
    service_keys = [s.key for s in SERVICE_CATALOG]
    required_services = ["thai_traditional", "oil_massage", "manicure_basic", "facial_basic"]
    for req_service in required_services:
        assert req_service in service_keys, f"Отсутствует услуга: {req_service}"
    
    # Тест 3: Проверяем категории
    assert len(SERVICE_CATEGORIES) == 4, f"Должно быть 4 категории, найдено: {len(SERVICE_CATEGORIES)}"
    expected_categories = ["massage", "spa", "waxing", "nails"]
    for cat in expected_categories:
        assert cat in SERVICE_CATEGORIES, f"Отсутствует категория: {cat}"
    
    # Тест 4: Проверяем валидацию
    assert validate_date_format("15.12.2024"), "Валидация даты работает неправильно"
    assert not validate_date_format("2024-12-15"), "Валидация даты пропускает неверный формат"
    assert validate_time_format("14:30"), "Валидация времени работает неправильно"
    assert not validate_time_format("25:99"), "Валидация времени пропускает неверный формат"
    
    # Тест 5: Проверяем валидацию телефона
    assert is_valid_phone("+66123456789"), "Валидация телефона отклоняет правильный номер"
    assert is_valid_phone("+7 916 123 45 67"), "Валидация телефона не поддерживает пробелы"
    assert not is_valid_phone("123"), "Валидация телефона пропускает короткий номер"
    assert not is_valid_phone("abc123def456"), "Валидация телефона пропускает буквы"
    
    # Тест 6: Проверяем экранирование
    test_text = "Тест_с*спец[]символами"
    escaped = escape_md(test_text)
    assert "\\_" in escaped and "\\*" in escaped and "\\[" in escaped, "Экранирование не работает"
    
    # Тест 7: Проверяем поиск услуг
    thai_service = get_service_by_key("thai_traditional")
    assert thai_service is not None, "Не найдена услуга thai_traditional"
    assert thai_service.title_ru == "Традиционный тайский массаж", "Неверное название услуги"
    
    variant = get_service_variant("thai_traditional", 60)
    assert variant is not None, "Не найден вариант услуги"
    assert variant.price_thb > 0, "Цена должна быть больше нуля"
    
    # Тест 8: Проверяем константы
    from config import WORKING_HOURS, SLOT_STEP_MIN, RESERVATIONS, MAX_DAYS_AHEAD
    assert len(WORKING_HOURS) == 7, "WORKING_HOURS должен содержать 7 дней"
    assert SLOT_STEP_MIN > 0, "SLOT_STEP_MIN должен быть больше нуля"
    assert isinstance(RESERVATIONS, dict), "RESERVATIONS должен быть словарем"
    assert MAX_DAYS_AHEAD == 14, "MAX_DAYS_AHEAD должен быть 14"
    
    # Тест 9: Проверяем ограничение 14 дней
    from datetime import datetime, date, timedelta
    from config import TZINFO
    
    today = datetime.now(TZINFO).date()
    max_date = today + timedelta(days=MAX_DAYS_AHEAD)
    
    # Проверяем, что максимальная дата не превышает 14 дней от сегодня
    days_diff = (max_date - today).days
    assert days_diff == 14, f"Максимальная дата должна быть через 14 дней, получено: {days_diff}"
    
    # Тест 10: Проверяем генерацию слотов для сегодняшнего дня
    from calendar_utils import generate_slots
    
    # Для сегодняшнего дня проверяем, что не показываются прошедшие слоты
    today_slots = generate_slots(today, 60)
    if today_slots:
        # Первый слот должен быть не раньше текущего времени + 30 минут
        from datetime import datetime
        now = datetime.now(TZINFO)
        now_local = now.replace(tzinfo=None)
        min_time = now_local + timedelta(minutes=30)
        
        first_slot_time = datetime.strptime(today_slots[0], "%H:%M").time()
        first_slot_dt = datetime.combine(today, first_slot_time)
        
        # Проверяем, что первый слот не в прошлом (с учетом округления)
        if first_slot_dt < min_time:
            # Разрешаем небольшое отклонение из-за округления до шага
            time_diff = (min_time - first_slot_dt).total_seconds() / 60
            assert time_diff < SLOT_STEP_MIN, f"Первый слот {today_slots[0]} слишком рано. Разница: {time_diff} минут"
    
    print("✅ ALL TESTS PASSED (включая календарные функции и ограничение 14 дней)")

# === УТИЛИТЫ ДЛЯ ПОВТОРНОГО ИСПОЛЬЗОВАНИЯ ===

async def reserve_and_notify(bot: 'Bot', user_id: int, data: dict, booking_source: str = "manual") -> str:
    """
    Общая функция для резервации слота и отправки уведомлений
    
    Args:
        bot: Экземпляр бота для отправки сообщений
        user_id: ID пользователя 
        data: Данные бронирования (service_key, duration, date_str, time_str, client_name, client_phone, date_iso)
        booking_source: Источник бронирования ('manual', 'ai')
    """
    from config import ADMIN_CHAT_ID, TZ, TZINFO, RESERVATIONS
    
    # Получаем данные об услуге
    service = get_service_by_key(data["service_key"])
    variant = get_service_variant(data["service_key"], data["duration"])
    
    if not service or not variant:
        logger.error(f"Service or variant not found: {data['service_key']}, {data['duration']}")
        return
    
    lang = get_lang(user_id)
    service_title = service.get_title(lang)
    
    # Сообщение админу
    # Пытаемся получить username пользователя (если возможно)
    username_value = None
    try:
        # aiogram Bot не всегда знает username пользователя, пробуем получить чат
        chat = await bot.get_chat(user_id)
        username_value = getattr(chat, "username", None)
    except Exception:
        pass

    # Получаем шаблон сообщения для админа
    admin_template = get_text(user_id, "admin_new_booking")
    
    # Форматируем сообщение с подстановкой переменных
    try:
        admin_message = admin_template.format(
            service=service_title,
            duration=data["duration"],
            date=data["date_str"],
            time=data["time_str"],
            name=safe_text(data["client_name"]),
            phone=safe_text(data["client_phone"]),
            username=safe_text(username_value or "не указан"),
            user_id=user_id,
            tz=TZ
        )
    except KeyError as e:
        logger.error(f"Ошибка форматирования админского сообщения: {e}")
        admin_message = f"Новая запись: {service_title}, {data['date_str']} {data['time_str']}, клиент: {data['client_name']}"
    
    # Отправляем уведомление админу
    try:
        await bot.send_message(ADMIN_CHAT_ID, admin_message)
    except Exception as e:
        logger.error(f"Failed to send admin notification: {e}")
    
    # Сообщение пользователю
    success_key = "ai_booking_success" if booking_source == "ai" else "booking_confirmed"
    
    if booking_source == "ai":
        confirmation_message = get_text(user_id, success_key)
    else:
        confirmation_message = get_text(
            user_id, success_key,
            service=service_title,
            date=data["date_str"],
            time=data["time_str"],
            duration=data["duration"],
            price=variant.price_thb,
            tz=TZ
        )
    
    # Финальная проверка доступности и фиксация слота в резервациях
    date_iso = data.get("date_iso")
    if date_iso and data.get("time_str"):
        try:
            # Парсим дату и время
            if date_iso:
                booking_date = datetime.fromisoformat(date_iso).date()
            else:
                # Парсим из date_str если date_iso отсутствует  
                booking_date = datetime.strptime(data["date_str"], "%d.%m.%Y").date()
            
            # Обрабатываем разные форматы времени
            time_str = data["time_str"]
            try:
                if ":" in time_str:
                    booking_time = datetime.strptime(time_str, "%H:%M").time()
                else:
                    # Если пришло только число часов, добавляем :00
                    booking_time = datetime.strptime(f"{time_str}:00", "%H:%M").time()
            except ValueError as e:
                logger.error(f"Неверный формат времени: {time_str}, ошибка: {e}")
                return confirmation_message
            
            start_dt = datetime.combine(booking_date, booking_time)
            end_dt = start_dt + timedelta(minutes=data["duration"])
            
            # Финальная проверка доступности с учетом Google Sheets
            from calendar_utils import generate_slots
            available_slots = generate_slots(booking_date, data["duration"])
            
            if time_str not in available_slots:
                # Время недоступно, предлагаем альтернативы
                if available_slots:
                    alternatives = ", ".join(available_slots[:5])  # Показываем до 5 вариантов
                    error_message = get_text(user_id, "ai_time_unavailable", slots=alternatives)
                else:
                    error_message = get_text(user_id, "slots_unavailable_try_again")
                
                # Отправляем сообщение пользователю об ошибке
                await bot.send_message(user_id, error_message)
                return error_message
            
            # Добавляем резервацию
            date_key = booking_date.strftime("%Y-%m-%d")
            RESERVATIONS[date_key].append((start_dt, end_dt))
            
            logger.info(f"Slot reserved: {start_dt} - {end_dt} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при фиксации резервации: {e}")
    
    # Отправляем webhook на локальный сервер для Google Sheets
    await send_webhook_to_sheets(user_id, data, service, variant, booking_source, username_value)
    
    # Фолбэк: если Sheets отключены, планируем in-memory напоминание
    from config import SHEETS_ENABLED, REMINDERS_ENABLED
    if not SHEETS_ENABLED and REMINDERS_ENABLED:
        try:
            from datetime import datetime, timedelta
            from config import REMINDER_LEAD_MIN, TZINFO
            
            # Вычисляем время напоминания
            if date_iso and data.get("time_str"):
                booking_date = datetime.fromisoformat(date_iso).date() if date_iso else datetime.strptime(data["date_str"], "%d.%m.%Y").date()
                time_str = data["time_str"]
                
                if ":" in time_str:
                    booking_time = datetime.strptime(time_str, "%H:%M").time()
                else:
                    booking_time = datetime.strptime(f"{time_str}:00", "%H:%M").time()
                
                booking_dt = datetime.combine(booking_date, booking_time).replace(tzinfo=TZINFO)
                reminder_dt = booking_dt - timedelta(minutes=REMINDER_LEAD_MIN)
                
                # Планируем напоминание
                from main import schedule_in_memory_reminder
                
                # Подготавливаем данные для напоминания
                reminder_data = {
                    'service_title': service.get_title(get_lang(user_id)),
                    'date_str': data["date_str"],
                    'time_str': data["time_str"],
                    'duration': data["duration"]
                }
                
                # Создаем задачу напоминания
                import asyncio
                asyncio.create_task(schedule_in_memory_reminder(bot, user_id, reminder_data, reminder_dt))
                logger.info(f"📅 Запланировано in-memory напоминание для пользователя {user_id} на {reminder_dt}")
                
        except Exception as e:
            logger.error(f"Ошибка планирования in-memory напоминания: {e}")
    
    return confirmation_message


async def send_webhook_to_sheets(user_id: int, data: dict, service: 'Service', variant: 'ServiceVariant', booking_source: str, username_value: Optional[str]) -> None:
    """
    Отправляет webhook на локальный сервер для записи в Google Sheets
    """
    import aiohttp
    import asyncio
    import uuid
    from datetime import datetime
    from config import WEBHOOK_URL, TZINFO, TZ
    
    # Если WEBHOOK_URL не настроен, пропускаем отправку
    if not WEBHOOK_URL.strip():
        logger.info("WEBHOOK_URL не настроен, пропускаем отправку webhook")
        return
    
    # Генерируем уникальный booking_id
    booking_id = str(uuid.uuid4())
    
    # Подготавливаем payload
    lang = get_lang(user_id)
    service_title = service.get_title(lang)
    
    webhook_payload = {
        "event": "booking.created",
        "payload": {
            "booking_id": booking_id,
            "source": booking_source,
            "created_at": datetime.now(TZINFO).isoformat(),
            "timezone": TZ,
            "language": lang,
            "user": {
                "telegram_id": user_id,
                "username": username_value or "не указан"
            },
            "service": {
                "key": data["service_key"],
                "title": service_title,
                "duration_min": data["duration"],
                "price_thb": variant.price_thb
            },
            "booking": {
                "date_iso": data.get("date_iso", ""),
                "date_str": data["date_str"],
                "time": data["time_str"],
                "client_name": data["client_name"],
                "client_phone": data["client_phone"]
            }
        }
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(WEBHOOK_URL, json=webhook_payload) as response:
                if response.status == 200:
                    logger.info(f"✅ Webhook отправлен успешно для booking_id: {booking_id}")
                    response_text = await response.text()
                    logger.debug(f"Webhook response: {response_text}")
                else:
                    logger.error(f"❌ Ошибка webhook: HTTP {response.status}")
                    try:
                        error_text = await response.text()
                        logger.error(f"Webhook error response: {error_text}")
                    except Exception:
                        logger.error("Не удалось прочитать ответ webhook")
                        
    except aiohttp.ClientError as e:
        logger.error(f"❌ Сетевая ошибка при отправке webhook: {e}")
    except asyncio.TimeoutError:
        logger.error("❌ Таймаут при отправке webhook")
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка при отправке webhook: {e}")

def format_reminder_message(lang: str, service_title: str, date_str: str, time_str: str, duration_min: int) -> str:
    """
    Форматирует сообщение напоминания
    
    Args:
        lang: Язык пользователя ('ru' или 'en')
        service_title: Название услуги
        date_str: Дата в формате DD.MM.YYYY
        time_str: Время в формате HH:MM
        duration_min: Длительность в минутах
        
    Returns:
        Отформатированное сообщение напоминания
    """
    from config import TEXTS
    
    # Получаем шаблон сообщения
    template = TEXTS.get(lang, TEXTS['en']).get('reminder_2h', 'Reminder: your appointment is in 2 hours.')
    
    # Безопасно форматируем все переменные
    try:
        formatted_message = template.format(
            service=safe_text(service_title),
            date=safe_text(date_str),
            time=safe_text(time_str),
            duration=duration_min
        )
        return formatted_message
    except Exception as e:
        logger.error(f"Ошибка форматирования напоминания: {e}")
        # Фолбэк сообщение
        return f"⏰ Напоминание о записи через 2 часа: {service_title}, {date_str} в {time_str}"
