"""
Конфигурация Nova Chaloklum Health Massage Telegram Bot
"""
import os
import zoneinfo
from collections import defaultdict
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv(override=True)

# Основные настройки
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
TZ = os.getenv("TZ", "Asia/Bangkok")

# OpenAI настройки
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
FEATURE_CHATGPT = os.getenv("FEATURE_CHATGPT", "0") == "1"
FEATURE_AI_BOOKING = os.getenv("FEATURE_AI_BOOKING", "0") == "1"


# Webhook настройки
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

# Google Sheets настройки для проверки занятости
SHEETS_ENABLED = os.getenv("SHEETS_ENABLED", "0") == "1"
SHEETS_SPREADSHEET_ID = os.getenv("SHEETS_SPREADSHEET_ID", "")
SHEETS_SHEET_NAME = os.getenv("SHEETS_SHEET_NAME", "bookings")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "google_credentials.json")

# Напоминания настройки
REMINDERS_ENABLED = os.getenv("REMINDERS_ENABLED", "0") == "1"
REMINDER_LEAD_MIN = int(os.getenv("REMINDER_LEAD_MIN", "120"))
REMINDER_POLL_INTERVAL_SEC = int(os.getenv("REMINDER_POLL_INTERVAL_SEC", "60"))

# Конфигурация календаря и рабочего времени
try:
    TZINFO = zoneinfo.ZoneInfo(TZ)
except Exception:
    import logging
    logging.getLogger(__name__).warning(f"Invalid timezone '{TZ}', falling back to Asia/Bangkok")
    TZINFO = zoneinfo.ZoneInfo("Asia/Bangkok")
# Бизнес-константы
BOOKING_SLOT_DURATION_MINUTES = 30  # Минимальный шаг слотов
BOOKING_MAX_ADVANCE_DAYS = 14       # Максимум дней для записи вперед  
REMINDER_DEFAULT_LEAD_MINUTES = 120  # За сколько минут напоминать

# Обратная совместимость
SLOT_STEP_MIN = BOOKING_SLOT_DURATION_MINUTES 
MAX_DAYS_AHEAD = BOOKING_MAX_ADVANCE_DAYS
REMINDER_LEAD_MIN = REMINDER_DEFAULT_LEAD_MINUTES

WORKING_HOURS = {
    0: ("10:00", "22:00"),  # Понедельник
    1: ("10:00", "22:00"),  # Вторник
    2: ("10:00", "22:00"),  # Среда
    3: ("10:00", "22:00"),  # Четверг
    4: ("10:00", "22:00"),  # Пятница
    5: ("10:00", "22:00"),  # Суббота
    6: ("10:00", "20:00"),  # Воскресенье
}

# In-memory резервации: {"YYYY-MM-DD": [(start_dt, end_dt), ...]}
RESERVATIONS = defaultdict(list)

# In-memory хранилище языков пользователей (легко расширяемо до БД)
user_languages: dict[int, str] = {}

# Общие элементы локализации
COMMON_SYMBOLS = {
    "confirm": "✅", "cancel": "❌", "back": "← ", "next": "▶️", "prev": "◀️"
}

# Компактная локализация (data-driven)
LOCALIZATION_DATA = {
    # Основной интерфейс
    "welcome": ("Добро пожаловать в Nova Chaloklum Health Massage!", "Welcome to Nova Chaloklum Health Massage!"),
    "choose_language": ("Выберите язык:", "Choose language:"),
    "language_changed": ("Язык изменен на русский", "Language changed to English"),
    "choose_category": ("Выберите категорию услуг:", "Choose service category:"),
    "select_service": ("Выберите услугу:", "Choose a service:"),
    "main_menu": ("🏠 Главное меню", "🏠 Main menu"),
    "change_language": ("🌐 Сменить язык", "🌐 Change language"),
    
    # Категории
    "cat_massage": ("Массаж", "Massage"),
    "cat_spa": ("Spa", "Spa"), 
    "cat_wax": ("Воск", "Waxing"),
    "cat_nails": ("Ногти", "Nails"),
    
    # Навигация
    "back_to_services": ("К списку", "Back to list"),
    "back_to_menu": ("В меню", "Back to menu"),
    "book_service": ("📅 Записаться", "📅 Book"),
    
    # Процесс бронирования
    "step_date": ("📅 *Шаг 1 из 4*\n\nВведите желаемую дату в формате *ДД.ММ.ГГГГ*\nНапример: `15.12.2024`", "📅 *Step 1 of 4*\n\nEnter desired date in format *DD.MM.YYYY*\nExample: `15.12.2024`"),
    "step_time": ("🕐 *Шаг 2 из 4*\n\nВведите желаемое время в формате *ЧЧ:ММ*\nНапример: `14:30`", "🕐 *Step 2 of 4*\n\nEnter desired time in format *HH:MM*\nExample: `14:30`"),
    "step_name": ("👤 *Шаг 3 из 4*\n\nКак вас зовут?", "👤 *Step 3 of 4*\n\nWhat's your name?"),
    "step_phone": ("📞 *Шаг 4 из 4*\n\nВведите ваш номер телефона:\nНапример: `+66123456789` или `+79161234567`", "📞 *Step 4 of 4*\n\nEnter your phone number:\nExample: `+66123456789` or `+79161234567`"),
    
    # Валидация
    "invalid_date": ("❌ Неверный формат даты!\n\nВведите дату в формате *ДД.ММ.ГГГГ*\nНапример: `15.12.2024`", "❌ Invalid date format!\n\nEnter date in format *DD.MM.YYYY*\nExample: `15.12.2024`"),
    "invalid_time": ("❌ Неверный формат времени!\n\nВведите время в формате *ЧЧ:ММ*\nНапример: `14:30`", "❌ Invalid time format!\n\nEnter time in format *HH:MM*\nExample: `14:30`"),
    "invalid_phone": ("❌ Неверный формат номера!\n\nВведите номер телефона с кодом страны:\nНапример: `+66123456789`", "❌ Invalid phone format!\n\nEnter phone number with country code:\nExample: `+66123456789`"),
    "name_too_short": ("❌ Имя слишком короткое. Введите ваше имя:", "❌ Name too short. Enter your name:"),
    
    # Подтверждение
    "confirm_booking": ("📋 *Подтверждение записи*\n\n🔸 Услуга: *{service}*\n🔸 Длительность: *{duration} мин*\n🔸 Дата: *{date}*\n🔸 Время: *{time}*\n🔸 Клиент: *{name}*\n🔸 Телефон: *{phone}*\n\nВсё верно?", "📋 *Booking confirmation*\n\n🔸 Service: *{service}*\n🔸 Duration: *{duration} min*\n🔸 Date: *{date}*\n🔸 Time: *{time}*\n🔸 Client: *{name}*\n🔸 Phone: *{phone}*\n\nIs everything correct?"),
    "booking_confirmed": ("🎉 *Запись подтверждена!*\n\n📋 Детали записи:\n🔸 Услуга: *{service}*\n🔸 Дата: *{date}*\n🔸 Время: *{time}*\n🔸 Длительность: *{duration} мин*\n🔸 Стоимость: *{price} THB*\n\nМы ждём вас!\n⏰ Часовой пояс: {tz}", "🎉 *Booking confirmed!*\n\n📋 Booking details:\n🔸 Service: *{service}*\n🔸 Date: *{date}*\n🔸 Time: *{time}*\n🔸 Duration: *{duration} min*\n🔸 Price: *{price} THB*\n\nWe're waiting for you!\n⏰ Timezone: {tz}"),
    "booking_cancelled": ("❌ Запись отменена. Вы можете начать заново в любое время.", "❌ Booking cancelled. You can start over at any time."),
    
    # Админ уведомления
    "admin_new_booking": ("🔔 *Новая запись!*\n\n👤 Клиент: *{name}*\n📞 Телефон: *{phone}*\n🔸 Услуга: *{service}*\n🔸 Дата: *{date}*\n🔸 Время: *{time}*\n🔸 Длительность: *{duration} мин*\n\n👨‍💼 Пользователь: @{username} (ID: {user_id})\n⏰ Часовой пояс: {tz}", "🔔 *New booking!*\n\n👤 Client: *{name}*\n📞 Phone: *{phone}*\n🔸 Service: *{service}*\n🔸 Date: *{date}*\n🔸 Time: *{time}*\n🔸 Duration: *{duration} min*\n\n👨‍💼 User: @{username} (ID: {user_id})\n⏰ Timezone: {tz}"),
    
    # Интерфейс выбора
    "select_duration": ("Выберите длительность:", "Select duration:"),
    "pick_date": ("📅 Выберите дату:", "📅 Select date:"),
    "pick_time": ("🕐 Выберите время:", "🕐 Select time:"),
    "no_slots": ("❌ На эту дату нет свободных слотов", "❌ No available slots for this date"),
    
    # AI функции
    "ask_ai": ("🤖 Задать вопрос ИИ", "🤖 Ask AI assistant"),
    "ai_booking": ("🤖 ИИ-помощник записи", "🤖 AI Booking Assistant"),
    "enter_ai_question": ("Напишите вопрос для ассистента:", "Type your question for the assistant:"),
    "ai_unavailable": ("ИИ временно недоступен", "AI is currently unavailable"),
    "ai_thinking": ("Думаю…", "Thinking…"),
    "ai_start": ("Опишите, что вы хотите забронировать (услуга/дата/время/длительность).", "Describe what you want to book (service/date/time/duration)."),
    "ai_clarify_missing": ("Нужно уточнить: {fields}", "Need to clarify: {fields}"),
    "ai_time_unavailable": ("Выбранное время недоступно. Доступно: {slots}", "Chosen time is unavailable. Available: {slots}"),
    "ai_ready_to_confirm": ("Проверьте: {service}, {duration} мин, {date} {time}. Подтвердить?", "Please confirm: {service}, {duration} min, {date} {time}. Confirm?"),
    "ai_booking_success": ("✅ Запись оформлена через ИИ-помощника!", "✅ Booking completed via AI Assistant!"),
    "ai_clarify_massage_type": ("На какой массаж вы хотите — традиционный тайский или что-то поинтереснее? Также укажите длительность, ваше имя и номер телефона.", "Please clarify massage type: Traditional Thai or something more specific?"),
    
    # Системные сообщения
    "section_unavailable": ("Раздел временно недоступен.", "Section temporarily unavailable."),
    "enter_name_prompt": ("👤 Введите ваше имя:", "👤 Enter your name:"),
    "slots_unavailable_try_again": ("❌ Выбранное время недоступно.\n\nПопробуйте другое время или выберите другую дату.", "❌ Selected time is unavailable.\n\nTry another time or select a different date."),
    "sheets_integration_error": ("⚠️ Временная проблема с проверкой доступности. Попробуйте позже или выберите другое время.", "⚠️ Temporary issue checking availability. Please try later or select different time."),
    "reminder_2h": ("⏰ Напоминание: ваша запись через 2 часа.\n\n🔸 Услуга: *{service}*\n🔸 Дата: *{date}*\n🔸 Время: *{time}*\n🔸 Длительность: *{duration} мин*\n\nЕсли нужно перенести — ответьте на это сообщение.", "⏰ Reminder: your appointment is in 2 hours.\n\n🔸 Service: *{service}*\n🔸 Date: *{date}*\n🔸 Time: *{time}*\n🔸 Duration: *{duration} min*\n\nReply here if you need to reschedule."),
}

# Категории услуг (для совместимости)
SERVICE_CATEGORIES_LOCALIZED = {
    "massage": ("Массаж", "Massage"),
    "spa": ("Spa", "Spa"), 
    "wax": ("Воск", "Waxing"),
    "nails": ("Ногти", "Nails")
}

# Генерация TEXTS словаря из компактных данных
def _build_texts():
    texts = {"ru": {}, "en": {}}
    
    # Общие символы
    for key, value in COMMON_SYMBOLS.items():
        texts["ru"][key] = value
        texts["en"][key] = value
    
    # Основная локализация
    for key, (ru_text, en_text) in LOCALIZATION_DATA.items():
        texts["ru"][key] = f"🏝 *{ru_text}*\n\nВыберите язык:" if key == "welcome" else ru_text
        texts["en"][key] = f"🏝 *{en_text}*\n\nChoose your language:" if key == "welcome" else en_text
    
    # Категории
    texts["ru"]["categories"] = {k: v[0] for k, v in SERVICE_CATEGORIES_LOCALIZED.items()}
    texts["en"]["categories"] = {k: v[1] for k, v in SERVICE_CATEGORIES_LOCALIZED.items()}
    
    return texts

TEXTS = _build_texts()
