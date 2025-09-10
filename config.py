"""
Конфигурация Nova Chaloklum Health Massage Telegram Bot
"""
import os
import zoneinfo
from collections import defaultdict
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Основные настройки
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
TZ = os.getenv("TZ", "Asia/Bangkok")

# OpenAI настройки
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
FEATURE_CHATGPT = os.getenv("FEATURE_CHATGPT", "0") == "1"
FEATURE_AI_BOOKING = os.getenv("FEATURE_AI_BOOKING", "0") == "1"

# Конфигурация календаря и рабочего времени
TZINFO = zoneinfo.ZoneInfo(TZ)
WORKING_HOURS = {
    0: ("10:00", "22:00"),  # Понедельник
    1: ("10:00", "22:00"),  # Вторник
    2: ("10:00", "22:00"),  # Среда
    3: ("10:00", "22:00"),  # Четверг
    4: ("10:00", "22:00"),  # Пятница
    5: ("10:00", "22:00"),  # Суббота
    6: ("10:00", "20:00"),  # Воскресенье
}
SLOT_STEP_MIN = 30
MAX_MONTHS_AHEAD = 3
MAX_DAYS_AHEAD = 14

# In-memory резервации: {"YYYY-MM-DD": [(start_dt, end_dt), ...]}
RESERVATIONS = defaultdict(list)

# In-memory хранилище языков пользователей (легко расширяемо до БД)
user_languages: dict[int, str] = {}

# Локализация
TEXTS = {
    "ru": {
        "welcome": "🏝 *Добро пожаловать в Nova Chaloklum Health Massage!*\n\nВыберите язык:",
        "choose_language": "Выберите язык:",
        "language_changed": "✅ Язык изменен на русский",
        "choose_category": "Выберите категорию услуг:",
        "select_service": "Выберите услугу:",
        "back": "← Назад",
        "book_service": "📅 Записаться",
        "cat_massage": "Массаж",
        "cat_spa": "Spa",
        "cat_wax": "Воск",
        "cat_nails": "Ногти",
        "back_to_services": "← К списку",
        "back_to_menu": "← В меню",
        "main_menu": "🏠 Главное меню",
        "change_language": "🌐 Сменить язык",
        "step_date": "📅 *Шаг 1 из 4*\n\nВведите желаемую дату в формате *ДД.ММ.ГГГГ*\nНапример: `15.12.2024`",
        "step_time": "🕐 *Шаг 2 из 4*\n\nВведите желаемое время в формате *ЧЧ:ММ*\nНапример: `14:30`",
        "step_name": "👤 *Шаг 3 из 4*\n\nКак вас зовут?",
        "step_phone": "📞 *Шаг 4 из 4*\n\nВведите ваш номер телефона:\nНапример: `+66123456789` или `+79161234567`",
        "invalid_date": "❌ Неверный формат даты!\n\nВведите дату в формате *ДД.ММ.ГГГГ*\nНапример: `15.12.2024`",
        "invalid_time": "❌ Неверный формат времени!\n\nВведите время в формате *ЧЧ:ММ*\nНапример: `14:30`",
        "invalid_phone": "❌ Неверный формат номера!\n\nВведите номер телефона с кодом страны:\nНапример: `+66123456789`",
        "name_too_short": "❌ Имя слишком короткое. Введите ваше имя:",
        "confirm_booking": "📋 *Подтверждение записи*\n\n🔸 Услуга: *{service}*\n🔸 Длительность: *{duration} мин*\n🔸 Дата: *{date}*\n🔸 Время: *{time}*\n🔸 Клиент: *{name}*\n🔸 Телефон: *{phone}*\n\nВсё верно?",
        "confirm": "✅ Подтвердить",
        "cancel": "❌ Отмена",
        "booking_confirmed": "🎉 *Запись подтверждена!*\n\n📋 Детали записи:\n🔸 Услуга: *{service}*\n🔸 Дата: *{date}*\n🔸 Время: *{time}*\n🔸 Длительность: *{duration} мин*\n🔸 Стоимость: *{price} THB*\n\nМы ждём вас!\n⏰ Часовой пояс: {tz}",
        "booking_cancelled": "❌ Запись отменена. Вы можете начать заново в любое время.",
        "admin_new_booking": "🔔 *Новая запись!*\n\n👤 Клиент: *{name}*\n📞 Телефон: *{phone}*\n🔸 Услуга: *{service}*\n🔸 Дата: *{date}*\n🔸 Время: *{time}*\n🔸 Длительность: *{duration} мин*\n\n👨‍💼 Пользователь: @{username} (ID: {user_id})\n⏰ Часовой пояс: {tz}",
        "select_duration": "Выберите длительность:",
        "pick_date": "📅 Выберите дату:",
        "pick_time": "🕐 Выберите время:",
        "prev_month": "◀️",
        "next_month": "▶️",
        "no_slots": "❌ На эту дату нет свободных слотов",
        "ask_ai": "🤖 Задать вопрос ИИ",
        "enter_ai_question": "Напишите вопрос для ассистента:",
        "ai_unavailable": "ИИ временно недоступен",
        "ai_thinking": "Думаю…",
        "ai_booking": "🤖 ИИ-помощник записи",
        "ai_start": "Опишите, что вы хотите забронировать (услуга/дата/время/длительность).",
        "ai_clarify_missing": "Нужно уточнить: {fields}",
        "ai_time_unavailable": "Выбранное время недоступно. Доступно: {slots}",
        "ai_ready_to_confirm": "Проверьте: {service}, {duration} мин, {date} {time}. Подтвердить?",
        "ai_booking_success": "✅ Запись оформлена через ИИ-помощника!",
        "categories": {
            "massage": "Массаж",
            "spa": "Spa",
            "wax": "Воск", 
            "nails": "Ногти"
        }
    },
    "en": {
        "welcome": "🏝 *Welcome to Nova Chaloklum Health Massage!*\n\nChoose your language:",
        "choose_language": "Choose language:",
        "language_changed": "✅ Language changed to English",
        "choose_category": "Choose service category:",
        "select_service": "Choose a service:",
        "back": "← Back",
        "book_service": "📅 Book",
        "cat_massage": "Massage",
        "cat_spa": "Spa",
        "cat_wax": "Waxing",
        "cat_nails": "Nails",
        "back_to_services": "← Back to list",
        "back_to_menu": "← Back to menu",
        "main_menu": "🏠 Main menu",
        "change_language": "🌐 Change language",
        "step_date": "📅 *Step 1 of 4*\n\nEnter desired date in format *DD.MM.YYYY*\nExample: `15.12.2024`",
        "step_time": "🕐 *Step 2 of 4*\n\nEnter desired time in format *HH:MM*\nExample: `14:30`",
        "step_name": "👤 *Step 3 of 4*\n\nWhat's your name?",
        "step_phone": "📞 *Step 4 of 4*\n\nEnter your phone number:\nExample: `+66123456789` or `+79161234567`",
        "invalid_date": "❌ Invalid date format!\n\nEnter date in format *DD.MM.YYYY*\nExample: `15.12.2024`",
        "invalid_time": "❌ Invalid time format!\n\nEnter time in format *HH:MM*\nExample: `14:30`",
        "invalid_phone": "❌ Invalid phone format!\n\nEnter phone number with country code:\nExample: `+66123456789`",
        "name_too_short": "❌ Name too short. Enter your name:",
        "confirm_booking": "📋 *Booking confirmation*\n\n🔸 Service: *{service}*\n🔸 Duration: *{duration} min*\n🔸 Date: *{date}*\n🔸 Time: *{time}*\n🔸 Client: *{name}*\n🔸 Phone: *{phone}*\n\nIs everything correct?",
        "confirm": "✅ Confirm",
        "cancel": "❌ Cancel",
        "booking_confirmed": "🎉 *Booking confirmed!*\n\n📋 Booking details:\n🔸 Service: *{service}*\n🔸 Date: *{date}*\n🔸 Time: *{time}*\n🔸 Duration: *{duration} min*\n🔸 Price: *{price} THB*\n\nWe're waiting for you!\n⏰ Timezone: {tz}",
        "booking_cancelled": "❌ Booking cancelled. You can start over at any time.",
        "admin_new_booking": "🔔 *New booking!*\n\n👤 Client: *{name}*\n📞 Phone: *{phone}*\n🔸 Service: *{service}*\n🔸 Date: *{date}*\n🔸 Time: *{time}*\n🔸 Duration: *{duration} min*\n\n👨‍💼 User: @{username} (ID: {user_id})\n⏰ Timezone: {tz}",
        "select_duration": "Select duration:",
        "pick_date": "📅 Select date:",
        "pick_time": "🕐 Select time:",
        "prev_month": "◀️",
        "next_month": "▶️",
        "no_slots": "❌ No available slots for this date",
        "ask_ai": "🤖 Ask AI assistant",
        "enter_ai_question": "Type your question for the assistant:",
        "ai_unavailable": "AI is currently unavailable",
        "ai_thinking": "Thinking…",
        "ai_booking": "🤖 AI Booking Assistant",
        "ai_start": "Describe what you want to book (service/date/time/duration).",
        "ai_clarify_missing": "Need to clarify: {fields}",
        "ai_time_unavailable": "Chosen time is unavailable. Available: {slots}",
        "ai_ready_to_confirm": "Please confirm: {service}, {duration} min, {date} {time}. Confirm?",
        "ai_booking_success": "✅ Booking completed via AI Assistant!",
        "categories": {
            "massage": "Massage",
            "spa": "Spa", 
            "wax": "Waxing",
            "nails": "Nails"
        }
    }
}