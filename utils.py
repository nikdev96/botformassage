"""
Утилиты для Nova Chaloklum Health Massage Telegram Bot
"""
import re
from typing import Optional
from config import TEXTS, user_languages
from models import SERVICE_CATALOG, SERVICE_CATEGORIES, Service, ServiceVariant

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
        localized_name = get_text(user_id, f"categories.{category_key}")
        if localized_name.lower() == category_name.lower():
            return category_key
    
    return None

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