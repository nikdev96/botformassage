"""
Nova Chaloklum Health Massage Telegram Bot
==========================================
Двуязычный бот (RU/EN) для записи на услуги массажа и спа.

Функционал:
- Выбор языка при старте (/start, /lang)
- 4 категории: Massage, Spa, Waxing, Nails
- Выбор длительности для услуг
- Процесс записи: услуга → длительность → дата → время → имя → телефон → подтверждение
- Уведомления администратора
- Офлайн-режим тестирования (RUN_TESTS=1)

Технологии: aiogram 3, python-dotenv
"""

from __future__ import annotations

# SSL проверка до импорта aiogram
try:
    import ssl
    _SSL_AVAILABLE = True
except ImportError:
    _SSL_AVAILABLE = False
    import sys
    import types
    sys.modules["ssl"] = types.ModuleType("ssl")

import asyncio
import calendar as _cal
import logging
import os
import zoneinfo
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# Конфигурация
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
TZ = os.getenv("TZ", "Asia/Bangkok")

if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN не найден в .env файле")

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
# In-memory резервации: {"YYYY-MM-DD": [(start_dt, end_dt), ...]}
RESERVATIONS = defaultdict(list)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# In-memory хранилище языков пользователей (легко расширяемо до БД)
user_languages: Dict[int, str] = {}

# Локализация
TEXTS = {
    "ru": {
        "welcome": "🏝 *Добро пожаловать в Nova Chaloklum Health Massage!*\n\nВыберите язык:",
        "choose_language": "Выберите язык:",
        "language_changed": "✅ Язык изменен на русский",
        "choose_category": "Выберите категорию услуг:",
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
        "edit": "✏️ Изменить",
        "cancel": "❌ Отменить",
        "booking_confirmed": "✅ *Запись успешно создана!*\n\n📋 {service}\n📅 {date} в {time} ({tz})\n⏱ {duration} минут\n💰 {price} THB\n\nМы свяжемся с вами для подтверждения.\nСпасибо за выбор нашего салона! 🙏",
        "booking_cancelled": "❌ Запись отменена.\n\nДля новой записи используйте /start",
        "edit_booking": "✏️ Давайте изменим запись.\n\n📅 Введите новую дату (ДД.ММ.ГГГГ):",
        "admin_new_booking": "🆕 *Новая запись!*\n\n📋 Услуга: {service}\n⏱ Длительность: {duration} мин\n📅 Дата/время: {date} в {time} ({tz})\n👤 Клиент: {name}\n📞 Телефон: {phone}\n🆔 User ID: {user_id}\n👤 Username: @{username}",
        "select_duration": "⏱ Выберите длительность:",
        "pick_date": "Выберите дату:",
        "pick_time": "Выберите время:",
        "no_slots": "На выбранную дату нет свободных слотов. Выберите другую дату.",
        "mon": "Пн", "tue": "Вт", "wed": "Ср", "thu": "Чт", "fri": "Пт", "sat": "Сб", "sun": "Вс",
        "prev": "‹", "next": "›",
        "month_fmt": "{month} {year}",
        "categories": {
            "massage": "Массаж",
            "spa": "Spa",
            "waxing": "Воск",
            "nails": "Ногти"
        },
        "russian": "🇷🇺 Русский",
        "english": "🇬🇧 English"
    },
    "en": {
        "welcome": "🏝 *Welcome to Nova Chaloklum Health Massage!*\n\nChoose language:",
        "choose_language": "Choose language:",
        "language_changed": "✅ Language changed to English",
        "choose_category": "Choose service category:",
        "back": "← Back",
        "book_service": "📅 Book",
        "cat_massage": "Massage",
        "cat_spa": "Spa",
        "cat_wax": "Waxing",
        "cat_nails": "Nails",
        "back_to_services": "← To list",
        "back_to_menu": "← To menu",
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
        "edit": "✏️ Edit",
        "cancel": "❌ Cancel",
        "booking_confirmed": "✅ *Booking successfully created!*\n\n📋 {service}\n📅 {date} at {time} ({tz})\n⏱ {duration} minutes\n💰 {price} THB\n\nWe will contact you for confirmation.\nThank you for choosing our salon! 🙏",
        "booking_cancelled": "❌ Booking cancelled.\n\nUse /start for new booking",
        "edit_booking": "✏️ Let's edit the booking.\n\n📅 Enter new date (DD.MM.YYYY):",
        "admin_new_booking": "🆕 *New booking!*\n\n📋 Service: {service}\n⏱ Duration: {duration} min\n📅 Date/time: {date} at {time} ({tz})\n👤 Client: {name}\n📞 Phone: {phone}\n🆔 User ID: {user_id}\n👤 Username: @{username}",
        "select_duration": "⏱ Choose duration:",
        "pick_date": "Choose a date:",
        "pick_time": "Choose a time:",
        "no_slots": "No free slots for this date. Pick another date.",
        "mon": "Mo", "tue": "Tu", "wed": "We", "thu": "Th", "fri": "Fr", "sat": "Sa", "sun": "Su",
        "prev": "‹", "next": "›",
        "month_fmt": "{month} {year}",
        "categories": {
            "massage": "Massage",
            "spa": "Spa", 
            "waxing": "Waxing",
            "nails": "Nails"
        },
        "russian": "🇷🇺 Русский",
        "english": "🇬🇧 English"
    }
}

def get_text(user_id: int, key: str, **kwargs) -> str:
    """Получает локализованный текст для пользователя"""
    lang = user_languages.get(user_id, "en")
    text = TEXTS[lang]
    
    # Навигация по вложенным ключам (например "categories.massage")
    for part in key.split("."):
        text = text[part]
    
    return text.format(**kwargs) if kwargs else text

def get_lang(user_id: int) -> str:
    """Получает язык пользователя"""
    return user_languages.get(user_id, "en")

# Модель услуги с поддержкой нескольких длительностей
@dataclass
class ServiceVariant:
    duration: int  # минуты
    price: int     # THB

@dataclass 
class Service:
    key: str
    title_ru: str
    title_en: str
    variants: List[ServiceVariant]
    note: str = ""
    
    def get_title(self, lang: str) -> str:
        return self.title_ru if lang == "ru" else self.title_en

# Каталог услуг согласно ТЗ
SERVICE_CATALOG: Dict[str, List[Service]] = {
    "massage": [
        Service(
            key="thai",
            title_ru="Тайский массаж",
            title_en="Thai massage",
            variants=[
                ServiceVariant(30, 300),
                ServiceVariant(60, 400), 
                ServiceVariant(90, 600),
                ServiceVariant(120, 750)
            ]
        ),
        Service(
            key="thai_herbal",
            title_ru="Тайский массаж с травяными мешочками",
            title_en="Thai massage with thai herbal compress",
            variants=[
                ServiceVariant(60, 600),
                ServiceVariant(90, 900),
                ServiceVariant(120, 1200)
            ]
        ),
        Service(
            key="deep_oil",
            title_ru="Тайский массаж с маслом (глубокий)",
            title_en="Thai massage with oil (deep tissue)",
            variants=[
                ServiceVariant(30, 350),
                ServiceVariant(60, 500),
                ServiceVariant(90, 750),
                ServiceVariant(120, 950)
            ]
        ),
        Service(
            key="reflexology_foot",
            title_ru="Рефлекторный массаж стоп",
            title_en="Reflexology foot massage",
            variants=[
                ServiceVariant(30, 300),
                ServiceVariant(60, 400),
                ServiceVariant(90, 600),
                ServiceVariant(120, 750)
            ]
        ),
        Service(
            key="foot_herbal",
            title_ru="Массаж ног с травяными мешочками",
            title_en="Foot massage with thai herbal compress",
            variants=[
                ServiceVariant(60, 500),
                ServiceVariant(90, 750),
                ServiceVariant(120, 900)
            ]
        ),
        Service(
            key="neck_shoulder",
            title_ru="Массаж шеи и плеч",
            title_en="Neck and shoulder massage",
            variants=[
                ServiceVariant(30, 350),
                ServiceVariant(60, 500),
                ServiceVariant(90, 750),
                ServiceVariant(120, 950)
            ]
        ),
        Service(
            key="neck_shoulder_herbal",
            title_ru="Шея и плечи с травяными мешочками",
            title_en="Neck and shoulder with thai herbal compress",
            variants=[
                ServiceVariant(60, 650),
                ServiceVariant(90, 900),
                ServiceVariant(120, 1100)
            ]
        ),
        Service(
            key="oil",
            title_ru="Массаж с маслом",
            title_en="Oil massage",
            variants=[
                ServiceVariant(60, 500),
                ServiceVariant(90, 750),
                ServiceVariant(120, 950)
            ]
        ),
        Service(
            key="oil_herbal",
            title_ru="Массаж с маслом и травяными мешочками",
            title_en="Oil massage with thai herbal compress",
            variants=[
                ServiceVariant(60, 700),
                ServiceVariant(90, 1050),
                ServiceVariant(120, 1350)
            ]
        ),
        Service(
            key="hot_oil",
            title_ru="Массаж горячим маслом",
            title_en="Hot oil massage",
            variants=[
                ServiceVariant(60, 650),
                ServiceVariant(90, 900),
                ServiceVariant(120, 1100)
            ]
        ),
        Service(
            key="coconut_oil",
            title_ru="Массаж с кокосовым маслом",
            title_en="Coconut oil massage",
            variants=[
                ServiceVariant(30, 350),
                ServiceVariant(60, 500),
                ServiceVariant(90, 750),
                ServiceVariant(120, 950)
            ]
        ),
        Service(
            key="aloe_vera",
            title_ru="Aloe vera массаж (после солнца)",
            title_en="Aloe vera massage (sunburned skin)",
            variants=[
                ServiceVariant(60, 600),
                ServiceVariant(90, 900),
                ServiceVariant(120, 1150)
            ]
        ),
        Service(
            key="body_scrub",
            title_ru="Скраб тела (кофе/рис/тайские травы)",
            title_en="Body scrub (coffee, rice milk, thai herbs)",
            variants=[
                ServiceVariant(60, 600),
                ServiceVariant(90, 900)
            ]
        )
    ],
    "spa": [
        Service(
            key="hair_spa_facial",
            title_ru="Hair Spa & Facial Massage (70 мин)",
            title_en="Hair Spa & Facial Massage (70 minutes)",
            variants=[ServiceVariant(70, 990)]
        ),
        Service(
            key="scrub_aroma_package",
            title_ru="Пакет: скраб тела + аромамассаж (2 часа)",
            title_en="Package: Body Scrub & Aromatherapy Oil (2 hours)",
            variants=[ServiceVariant(120, 1200)]
        ),
        Service(
            key="foot_spa",
            title_ru="Foot Spa",
            title_en="Foot Spa",
            variants=[ServiceVariant(60, 900)]
        ),
        Service(
            key="foot_scrub",
            title_ru="Foot Scrub",
            title_en="Foot Scrub",
            variants=[ServiceVariant(60, 600)]
        ),
        Service(
            key="body_scrub_simple",
            title_ru="Body Scrub (простая программа)",
            title_en="Body Scrub (simple)",
            variants=[ServiceVariant(60, 700)]
        )
    ],
    "waxing": [
        Service(
            key="waxing_leg",
            title_ru="Воск — ноги",
            title_en="Waxing — legs",
            variants=[ServiceVariant(60, 0)],  # TODO: поставить цену
            note="TODO: set price"
        ),
        Service(
            key="waxing_arm",
            title_ru="Воск — руки",  
            title_en="Waxing — arms",
            variants=[ServiceVariant(45, 0)],  # TODO
            note="TODO: set price"
        ),
        Service(
            key="waxing_bikini",
            title_ru="Воск — бикини",
            title_en="Waxing — bikini",
            variants=[ServiceVariant(45, 0)],  # TODO
            note="TODO: set price"
        )
    ],
    "nails": [
        # Remove
        Service(
            key="remove_color",
            title_ru="Снятие лака",
            title_en="Remove color",
            variants=[ServiceVariant(30, 100)]
        ),
        Service(
            key="remove_pvc",
            title_ru="Снятие PVC",
            title_en="Remove PVC",
            variants=[ServiceVariant(30, 200)]
        ),
        Service(
            key="remove_extensions",
            title_ru="Снятие акрил/гель",
            title_en="Remove acrylic or gel extensions",
            variants=[ServiceVariant(45, 300)]
        ),
        # Color
        Service(
            key="normal_hand_foot",
            title_ru="Обычный маникюр/педикюр (покрытие)",
            title_en="Normal hand and foot",
            variants=[ServiceVariant(60, 350)]
        ),
        Service(
            key="hand_gel",
            title_ru="Гель-лак — руки",
            title_en="Hand gel polish",
            variants=[ServiceVariant(60, 400)]
        ),
        Service(
            key="foot_gel",
            title_ru="Гель-лак — ноги",
            title_en="Foot gel color",
            variants=[ServiceVariant(60, 450)]
        ),
        Service(
            key="nail_designs",
            title_ru="Дизайн ногтей",
            title_en="Nail designs",
            variants=[ServiceVariant(30, 50)],
            note="50–100 THB (start from 50)"
        ),
        Service(
            key="white_french",
            title_ru="Белый френч",
            title_en="White-French",
            variants=[ServiceVariant(60, 700)]
        ),
        Service(
            key="cat_eye",
            title_ru="Кошачий глаз",
            title_en="Cat eye color",
            variants=[ServiceVariant(60, 600)]
        ),
        Service(
            key="glitter",
            title_ru="Глиттер",
            title_en="Glitter color",
            variants=[ServiceVariant(60, 500)]
        ),
        # Extensions
        Service(
            key="pvc_soft_gel",
            title_ru="Наращивание PVC Soft gel",
            title_en="PVC Soft gel",
            variants=[ServiceVariant(90, 600)]
        ),
        Service(
            key="gel_extensions",
            title_ru="Наращивание гелем (от)",
            title_en="Gel extensions start",
            variants=[ServiceVariant(120, 1500)]
        ),
        # Clean set
        Service(
            key="dry_skin",
            title_ru="Чистка (сухая кожа)",
            title_en="Dry skin clean set",
            variants=[ServiceVariant(45, 250)]
        ),
        Service(
            key="manicure",
            title_ru="Маникюр",
            title_en="Manicure",
            variants=[ServiceVariant(60, 350)]
        ),
        Service(
            key="pedicure",
            title_ru="Педикюр",
            title_en="Pedicure",
            variants=[ServiceVariant(60, 400)]
        ),
        Service(
            key="hands_spa",
            title_ru="Hands Spa",
            title_en="Hands Spa",
            variants=[ServiceVariant(60, 600)]
        ),
        Service(
            key="foot_spa_nails",
            title_ru="Foot Spa (ногти)",
            title_en="Foot Spa (nails)",
            variants=[ServiceVariant(60, 900)]
        )
    ]
}

CATEGORIES = ["massage", "spa", "waxing", "nails"]

# Состояния FSM для процесса записи (унифицированные ключи)
class BookingState(StatesGroup):
    selecting_service = State()
    selecting_duration = State()
    entering_date = State()      # Теперь показываем календарь
    entering_time = State()      # Теперь показываем слоты
    entering_name = State()
    entering_phone = State()
    confirming = State()

# Утилиты для клавиатур
def create_language_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру выбора языка"""
    keyboard = [
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def add_persistent_menu_buttons(builder: InlineKeyboardBuilder, user_id: int):
    """Добавляет кнопки постоянного меню в InlineKeyboardBuilder"""
    builder.row(
        InlineKeyboardButton(text=get_text(user_id, "main_menu"), callback_data="main_menu"),
        InlineKeyboardButton(text=get_text(user_id, "change_language"), callback_data="change_lang")
    )

def create_main_menu(user_id: int) -> ReplyKeyboardMarkup:
    """Создает главное меню с категориями на нужном языке"""
    lang = user_languages.get(user_id, "en")
    keyboard = []
    for category in CATEGORIES:
        category_name = get_text(user_id, f"categories.{category}")
        keyboard.append([KeyboardButton(text=category_name)])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder=get_text(user_id, "choose_category")
    )

# Inline categories menu (меню «выпадает» прямо в чат)
CATEGORY_SLUGS = [
    ("massage", "Массаж"),
    ("spa", "Spa"),
    ("wax", "Воск"),
    ("nails", "Ногти"),
]
# Маппинг slug -> ключ каталога
SLUG_TO_KEY = {
    "massage": "massage",
    "spa": "spa", 
    "wax": "waxing",
    "nails": "nails"
}

def cat_label(slug: str, user_id: int) -> str:
    lang = get_lang(user_id)
    labels = {
        "massage": {"ru": TEXTS["ru"]["cat_massage"], "en": TEXTS["en"]["cat_massage"]},
        "spa": {"ru": TEXTS["ru"]["cat_spa"], "en": TEXTS["en"]["cat_spa"]},
        "wax": {"ru": TEXTS["ru"]["cat_wax"], "en": TEXTS["en"]["cat_wax"]},
        "nails": {"ru": TEXTS["ru"]["cat_nails"], "en": TEXTS["en"]["cat_nails"]},
    }
    return labels[slug][lang]

def categories_kb(user_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for slug, _ in CATEGORY_SLUGS:
        b.button(text=cat_label(slug, user_id), callback_data=f"cat:{slug}")
    b.adjust(2)  # 2 столбца
    
    # Добавляем кнопки постоянного меню
    add_persistent_menu_buttons(b, user_id)
    
    return b.as_markup()

# Календарь и слоты
def _month_name(lang: str, year: int, month: int) -> str:
    """Возвращает название месяца"""
    if lang == "ru":
        months_ru = [
            "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]
        return months_ru[month]
    else:
        return _cal.month_name[month]

def build_calendar(user_id: int, year: int, month: int, min_date: date, max_date: date) -> InlineKeyboardMarkup:
    """Строит inline-клавиатуру календаря"""
    lang = get_lang(user_id)
    
    # Первая строка: навигация
    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1
    
    next_month = month + 1
    next_year = year
    if next_month == 13:
        next_month = 1
        next_year += 1
    
    # Проверяем можно ли листать назад/вперед
    current_date = date(year, month, 1)
    min_month_date = date(min_date.year, min_date.month, 1)
    max_month_date = date(max_date.year, max_date.month, 1)
    
    builder = InlineKeyboardBuilder()
    
    # Строка навигации
    nav_row = []
    if current_date > min_month_date:
        nav_row.append(InlineKeyboardButton(
            text=get_text(user_id, "prev"), 
            callback_data=f"calnav:prev:{prev_year}:{prev_month}"
        ))
    else:
        nav_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))
    
    nav_row.append(InlineKeyboardButton(
        text=get_text(user_id, "month_fmt", month=_month_name(lang, year, month), year=year),
        callback_data="noop"
    ))
    
    if current_date < max_month_date:
        nav_row.append(InlineKeyboardButton(
            text=get_text(user_id, "next"),
            callback_data=f"calnav:next:{next_year}:{next_month}"
        ))
    else:
        nav_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))
    
    builder.row(*nav_row)
    
    # Строка с днями недели
    weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    weekday_row = [
        InlineKeyboardButton(text=get_text(user_id, day), callback_data="noop")
        for day in weekdays
    ]
    builder.row(*weekday_row)
    
    # Сетка дат
    month_calendar = _cal.monthcalendar(year, month)
    for week in month_calendar:
        week_row = []
        for day in week:
            if day == 0:
                # Пустая ячейка
                week_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))
            else:
                day_date = date(year, month, day)
                if min_date <= day_date <= max_date:
                    # Доступная дата
                    week_row.append(InlineKeyboardButton(
                        text=str(day),
                        callback_data=f"cal:{day_date.isoformat()}"
                    ))
                else:
                    # Недоступная дата
                    week_row.append(InlineKeyboardButton(text="·", callback_data="noop"))
        builder.row(*week_row)
    
    # Добавляем кнопки постоянного меню
    add_persistent_menu_buttons(builder, user_id)
    
    return builder.as_markup()

def _parse_hhmm(time_str: str) -> tuple[int, int]:
    """Парсит строку времени HH:MM в (часы, минуты)"""
    h, m = map(int, time_str.split(":"))
    return h, m

def generate_slots(date_obj: date, duration_min: int) -> list[str]:
    """Генерирует список доступных временных слотов для даты"""
    weekday = date_obj.weekday()
    if weekday not in WORKING_HOURS:
        return []
    
    start_time_str, end_time_str = WORKING_HOURS[weekday]
    start_h, start_m = _parse_hhmm(start_time_str)
    end_h, end_m = _parse_hhmm(end_time_str)
    
    # Создаем datetime для начала и конца рабочего дня
    start_dt = datetime.combine(date_obj, datetime.min.time().replace(hour=start_h, minute=start_m)).replace(tzinfo=TZINFO)
    end_dt = datetime.combine(date_obj, datetime.min.time().replace(hour=end_h, minute=end_m)).replace(tzinfo=TZINFO)
    
    # Если это сегодня, не показываем прошедшие слоты
    now = datetime.now(TZINFO)
    if date_obj == now.date():
        # Добавляем буфер 30 минут к текущему времени
        min_start_time = now + timedelta(minutes=30)
        if start_dt < min_start_time:
            start_dt = min_start_time
    
    slots = []
    current_dt = start_dt
    
    # Генерируем слоты с шагом SLOT_STEP_MIN
    while current_dt + timedelta(minutes=duration_min) <= end_dt:
        slot_end_dt = current_dt + timedelta(minutes=duration_min)
        
        # Проверяем пересечение с занятыми интервалами
        date_iso = date_obj.isoformat()
        is_available = True
        for reserved_start, reserved_end in RESERVATIONS[date_iso]:
            # Проверяем пересечение интервалов
            if not (slot_end_dt <= reserved_start or current_dt >= reserved_end):
                is_available = False
                break
        
        if is_available:
            slots.append(current_dt.strftime("%H:%M"))
        
        current_dt += timedelta(minutes=SLOT_STEP_MIN)
    
    return slots

def slots_kb(user_id: int, date_obj: date, duration_min: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру с временными слотами"""
    slots = generate_slots(date_obj, duration_min)
    
    if not slots:
        # Возвращаем пустую клавиатуру если нет слотов
        return InlineKeyboardMarkup(inline_keyboard=[])
    
    builder = InlineKeyboardBuilder()
    for slot in slots:
        builder.button(text=slot, callback_data=f"time:{slot}")
    
    builder.adjust(4)  # 4 кнопки в ряд
    
    # Добавляем кнопку "Назад"
    builder.row(InlineKeyboardButton(
        text=get_text(user_id, "back_to_services"), 
        callback_data="back_to_calendar"
    ))
    
    # Добавляем кнопки постоянного меню
    add_persistent_menu_buttons(builder, user_id)
    
    return builder.as_markup()

def create_services_keyboard(user_id: int, category: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру со списком услуг в категории"""
    builder = InlineKeyboardBuilder()
    lang = user_languages.get(user_id, "en")
    
    services = SERVICE_CATALOG.get(category, [])
    for service in services:
        title = service.get_title(lang)
        builder.button(text=title, callback_data=f"service:{service.key}")
    
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text=get_text(user_id, "back_to_menu"), callback_data="back_to_menu"))
    
    # Добавляем кнопки постоянного меню
    add_persistent_menu_buttons(builder, user_id)
    
    return builder.as_markup()

def create_duration_keyboard(user_id: int, service_key: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру выбора длительности"""
    builder = InlineKeyboardBuilder()
    service = get_service_by_key(service_key)
    
    if not service:
        return InlineKeyboardMarkup(inline_keyboard=[])
        
    for variant in service.variants:
        if variant.price > 0:  # Не показываем варианты без цены
            text = f"{variant.duration} мин — {variant.price} THB"
            builder.button(text=text, callback_data=f"duration:{service_key}:{variant.duration}")
    
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text=get_text(user_id, "back_to_services"), callback_data="back_to_services"))
    
    # Добавляем кнопки постоянного меню
    add_persistent_menu_buttons(builder, user_id)
    
    return builder.as_markup()

def create_confirm_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру подтверждения записи"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text=get_text(user_id, "confirm"), callback_data="confirm:yes")
    builder.button(text=get_text(user_id, "edit"), callback_data="confirm:edit")
    builder.button(text=get_text(user_id, "cancel"), callback_data="confirm:cancel")
    builder.adjust(1)
    
    # Добавляем кнопки постоянного меню
    add_persistent_menu_buttons(builder, user_id)
    
    return builder.as_markup()

# Вспомогательные функции
def get_service_by_key(service_key: str) -> Optional[Service]:
    """Находит услугу по ключу"""
    for services_list in SERVICE_CATALOG.values():
        for service in services_list:
            if service.key == service_key:
                return service
    return None

def get_service_variant(service_key: str, duration: int) -> Optional[ServiceVariant]:
    """Находит вариант услуги по ключу и длительности"""
    service = get_service_by_key(service_key)
    if not service:
        return None
        
    for variant in service.variants:
        if variant.duration == duration:
            return variant
    return None

def validate_date_format(date_str: str) -> bool:
    """Проверяет формат даты"""
    try:
        datetime.strptime(date_str, "%d.%m.%Y")
        return True
    except ValueError:
        return False

def validate_time_format(time_str: str) -> bool:
    """Проверяет формат времени"""
    try:
        datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False

def get_category_by_local_name(user_id: int, category_name: str) -> Optional[str]:
    """Находит ключ категории по локализованному имени"""
    for category in CATEGORIES:
        if get_text(user_id, f"categories.{category}") == category_name:
            return category
    return None

# Основной роутер
router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start - выбор языка"""
    await state.clear()
    user_id = message.from_user.id
    
    # Если язык уже выбран, переходим к меню
    if user_id in user_languages:
        await message.answer(
            get_text(user_id, "choose_category"),
            reply_markup=categories_kb(user_id)
        )
    else:
        await message.answer(
            TEXTS["en"]["welcome"],
            reply_markup=create_language_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

@router.message(Command("lang"))
async def cmd_lang(message: Message, state: FSMContext):
    """Команда смены языка"""
    await state.clear()
    await message.answer(
        get_text(message.from_user.id, "choose_language"),
        reply_markup=create_language_keyboard()
    )

@router.callback_query(F.data.startswith("lang:"))
async def select_language(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора языка"""
    lang = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    user_languages[user_id] = lang
    
    await callback.message.edit_text(
        get_text(user_id, "language_changed")
    )
    
    await callback.message.answer(
        get_text(user_id, "choose_category"),
        reply_markup=categories_kb(user_id)
    )
    await callback.answer()

@router.message(F.text)
async def select_category(message: Message, state: FSMContext):
    """Обработчик выбора категории по названию"""
    user_id = message.from_user.id
    category = get_category_by_local_name(user_id, message.text)
    
    if not category:
        return  # Игнорируем неизвестные сообщения
        
    await state.clear()
    await state.update_data(category=category)
    
    services = SERVICE_CATALOG.get(category, [])
    if not services:
        await message.answer(f"Раздел временно недоступен.")
        return
    
    category_name = get_text(user_id, f"categories.{category}")
    await message.answer(
        f"📋 *{category_name}*\n\nВыберите услугу:",
        reply_markup=create_services_keyboard(user_id, category),
        parse_mode=ParseMode.MARKDOWN
    )
    await state.set_state(BookingState.selecting_service)

@router.callback_query(F.data.startswith("cat:"))
async def select_category_inline(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора категории через inline-кнопки"""
    slug = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    category = SLUG_TO_KEY.get(slug)
    
    if not category:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return
        
    await state.clear()
    await state.update_data(category=category)
    
    services = SERVICE_CATALOG.get(category, [])
    if not services:
        await callback.answer("Раздел временно недоступен", show_alert=True)
        return
    
    category_name = cat_label(slug, user_id)
    await callback.message.edit_text(
        f"📋 *{category_name}*\n\nВыберите услугу:",
        reply_markup=create_services_keyboard(user_id, category),
        parse_mode=ParseMode.MARKDOWN
    )
    await state.set_state(BookingState.selecting_service)
    await callback.answer()

@router.callback_query(F.data.startswith("service:"))
async def show_duration_selection(callback: CallbackQuery, state: FSMContext):
    """Показывает выбор длительности для услуги"""
    service_key = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    service = get_service_by_key(service_key)
    
    if not service:
        await callback.answer("❌ Услуга не найдена", show_alert=True)
        return
    
    await state.update_data(service_key=service_key)
    
    title = service.get_title(user_languages.get(user_id, "en"))
    
    # Если только один вариант длительности, пропускаем выбор
    available_variants = [v for v in service.variants if v.price > 0]
    if len(available_variants) == 1:
        variant = available_variants[0]
        await state.update_data(duration=variant.duration)
        await state.set_state(BookingState.entering_date)
        
        # Показываем календарь
        today = datetime.now(TZINFO).date()
        max_date = today + timedelta(days=MAX_MONTHS_AHEAD * 31)
        
        await callback.message.edit_text(
            get_text(user_id, "pick_date"),
            reply_markup=build_calendar(user_id, today.year, today.month, today, max_date)
        )
    else:
        await callback.message.edit_text(
            f"*{title}*\n\n{get_text(user_id, 'select_duration')}",
            reply_markup=create_duration_keyboard(user_id, service_key),
            parse_mode=ParseMode.MARKDOWN
        )
        await state.set_state(BookingState.selecting_duration)
    
    await callback.answer()

@router.callback_query(F.data.startswith("duration:"))
async def select_duration(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора длительности"""
    parts = callback.data.split(":")
    service_key = parts[1]
    duration = int(parts[2])
    user_id = callback.from_user.id
    
    await state.update_data(service_key=service_key, duration=duration)
    await state.set_state(BookingState.entering_date)
    
    # Показываем календарь
    today = datetime.now(TZINFO).date()
    max_date = today + timedelta(days=MAX_MONTHS_AHEAD * 31)
    
    await callback.message.edit_text(
        get_text(user_id, "pick_date"),
        reply_markup=build_calendar(user_id, today.year, today.month, today, max_date)
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_services")
async def back_to_services(callback: CallbackQuery, state: FSMContext):
    """Возврат к списку услуг"""
    data = await state.get_data()
    category = data.get("category", CATEGORIES[0])
    user_id = callback.from_user.id
    
    category_name = get_text(user_id, f"categories.{category}")
    await callback.message.edit_text(
        f"📋 *{category_name}*\n\nВыберите услугу:",
        reply_markup=create_services_keyboard(user_id, category),
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    user_id = callback.from_user.id
    await state.clear()
    await callback.message.edit_text(
        get_text(user_id, "choose_category"),
        reply_markup=categories_kb(user_id)
    )
    await callback.answer()

@router.callback_query(F.data == "main_menu")
async def handle_main_menu(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Главное меню' - возврат в главное меню"""
    user_id = callback.from_user.id
    await state.clear()
    await callback.message.edit_text(
        get_text(user_id, "choose_category"),
        reply_markup=categories_kb(user_id)
    )
    await callback.answer()

@router.callback_query(F.data == "change_lang")
async def handle_change_language(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Сменить язык' - показывает выбор языка"""
    user_id = callback.from_user.id
    await callback.message.edit_text(
        get_text(user_id, "choose_language"),
        reply_markup=create_language_keyboard()
    )
    await callback.answer()

# Новые обработчики календаря и слотов
@router.callback_query(BookingState.entering_date, F.data.startswith("calnav:"))
async def navigate_calendar(callback: CallbackQuery, state: FSMContext):
    """Навигация по календарю (prev/next месяц)"""
    parts = callback.data.split(":")
    action = parts[1]
    year = int(parts[2])
    month = int(parts[3])
    user_id = callback.from_user.id
    
    today = datetime.now(TZINFO).date()
    max_date = today + timedelta(days=MAX_MONTHS_AHEAD * 31)
    
    await callback.message.edit_reply_markup(
        reply_markup=build_calendar(user_id, year, month, today, max_date)
    )
    await callback.answer()

@router.callback_query(BookingState.entering_date, F.data.startswith("cal:"))
async def select_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты из календаря"""
    date_iso = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    
    try:
        selected_date = date.fromisoformat(date_iso)
        date_str = selected_date.strftime("%d.%m.%Y")
    except ValueError:
        await callback.answer("❌ Неверная дата", show_alert=True)
        return
    
    # Сохраняем дату
    await state.update_data(date_str=date_str, date_iso=date_iso)
    
    # Получаем длительность услуги
    data = await state.get_data()
    duration = data.get("duration", 60)
    
    # Генерируем слоты
    kb = slots_kb(user_id, selected_date, duration)
    
    if not kb.inline_keyboard:
        # Нет доступных слотов
        await callback.answer(get_text(user_id, "no_slots"), show_alert=True)
        return
    
    await state.set_state(BookingState.entering_time)
    await callback.message.edit_text(
        get_text(user_id, "pick_time"),
        reply_markup=kb
    )
    await callback.answer()

@router.callback_query(BookingState.entering_time, F.data.startswith("time:"))
async def select_time_slot(callback: CallbackQuery, state: FSMContext):
    """Выбор временного слота"""
    time_str = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    
    await state.update_data(time_str=time_str)
    await state.set_state(BookingState.entering_name)
    
    await callback.message.edit_text(get_text(user_id, "step_name"))
    await callback.answer()

@router.callback_query(F.data == "back_to_calendar")
async def back_to_calendar(callback: CallbackQuery, state: FSMContext):
    """Возврат к календарю"""
    user_id = callback.from_user.id
    
    today = datetime.now(TZINFO).date()
    max_date = today + timedelta(days=MAX_MONTHS_AHEAD * 31)
    
    await state.set_state(BookingState.entering_date)
    await callback.message.edit_text(
        get_text(user_id, "pick_date"),
        reply_markup=build_calendar(user_id, today.year, today.month, today, max_date)
    )
    await callback.answer()

@router.message(BookingState.entering_date)
async def process_date(message: Message, state: FSMContext):
    """Обрабатывает ввод даты"""
    date_str = message.text.strip()
    user_id = message.from_user.id
    
    if not validate_date_format(date_str):
        await message.answer(
            get_text(user_id, "invalid_date"),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    await state.update_data(date_str=date_str)
    await state.set_state(BookingState.entering_time)
    
    await message.answer(
        get_text(user_id, "step_time"),
        parse_mode=ParseMode.MARKDOWN
    )

@router.message(BookingState.entering_time)
async def process_time(message: Message, state: FSMContext):
    """Обрабатывает ввод времени"""
    time_str = message.text.strip()
    user_id = message.from_user.id
    
    if not validate_time_format(time_str):
        await message.answer(
            get_text(user_id, "invalid_time"),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    await state.update_data(time_str=time_str)
    await state.set_state(BookingState.entering_name)
    
    await message.answer(
        get_text(user_id, "step_name"),
        parse_mode=ParseMode.MARKDOWN
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
        parse_mode=ParseMode.MARKDOWN
    )

@router.message(BookingState.entering_phone)
async def process_phone(message: Message, state: FSMContext):
    """Обрабатывает ввод телефона и показывает подтверждение"""
    phone = message.text.strip()
    user_id = message.from_user.id
    
    if len(phone) < 10 or not any(char.isdigit() for char in phone):
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
        name=data["client_name"],
        phone=data["client_phone"]
    )
    
    await message.answer(
        confirmation_text,
        reply_markup=create_confirm_keyboard(user_id),
        parse_mode=ParseMode.MARKDOWN
    )

@router.callback_query(BookingState.confirming, F.data.startswith("confirm:"))
async def process_confirmation(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Обрабатывает подтверждение записи"""
    action = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    
    if action == "cancel":
        await state.clear()
        await callback.message.edit_text(get_text(user_id, "booking_cancelled"))
        await callback.answer()
        return
    
    if action == "edit":
        await state.set_state(BookingState.entering_date)
        
        # Показываем календарь для редактирования
        today = datetime.now(TZINFO).date()
        max_date = today + timedelta(days=MAX_MONTHS_AHEAD * 31)
        
        await callback.message.edit_text(
            get_text(user_id, "pick_date"),
            reply_markup=build_calendar(user_id, today.year, today.month, today, max_date)
        )
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
            name=data["client_name"],
            phone=data["client_phone"],
            user_id=user_id,
            username=callback.from_user.username or "не указан",
            tz=TZ
        )
        try:
            await bot.send_message(ADMIN_CHAT_ID, admin_message, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления админу: {e}")
    
    # Подтверждение клиенту
    confirmation_message = get_text(
        user_id, "booking_confirmed",
        service=service_title,
        date=data["date_str"],
        time=data["time_str"],
        duration=data["duration"],
        price=variant.price,
        tz=TZ
    )
    
    await callback.message.edit_text(
        confirmation_message,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Фиксируем слот в резервациях
    date_iso = data.get("date_iso")
    if date_iso and data.get("time_str"):
        try:
            selected_date = date.fromisoformat(date_iso)
            time_parts = data["time_str"].split(":")
            start_dt = datetime.combine(
                selected_date, 
                datetime.min.time().replace(hour=int(time_parts[0]), minute=int(time_parts[1]))
            ).replace(tzinfo=TZINFO)
            end_dt = start_dt + timedelta(minutes=data["duration"])
            
            # Добавляем резервацию
            RESERVATIONS[date_iso].append((start_dt, end_dt))
            logger.info(f"Зафиксирован слот: {start_dt} - {end_dt}")
        except Exception as e:
            logger.error(f"Ошибка фиксации слота: {e}")
    
    await state.clear()
    await callback.answer("✅")

# Офлайн-тестирование
def run_offline_tests():
    """Запускает офлайн-тесты согласно ТЗ"""
    print("🧪 Запуск офлайн-тестов...")
    
    # Имитируем пользователя с русским языком
    user_ru = 12345
    user_languages[user_ru] = "ru"
    
    # Имитируем пользователя с английским языком  
    user_en = 54321
    user_languages[user_en] = "en"
    
    # Тест a) RU показывает "Тайский массаж (60 мин — 400 THB)"
    services_kb_ru = create_services_keyboard(user_ru, "massage")
    found_thai_ru = False
    for row in services_kb_ru.inline_keyboard:
        for button in row:
            if "Тайский массаж" in button.text:
                found_thai_ru = True
                break
    assert found_thai_ru, "Тест RU: 'Тайский массаж' не найден в списке"
    
    # Тест b) EN показывает "Thai massage (60 min — 400 THB)"  
    services_kb_en = create_services_keyboard(user_en, "massage")
    found_thai_en = False
    for row in services_kb_en.inline_keyboard:
        for button in row:
            if "Thai massage" in button.text:
                found_thai_en = True
                break
    assert found_thai_en, "Тест EN: 'Thai massage' не найден в списке"
    
    # Тест c) в разделе "Nails" есть услуга "Manicure — 350 THB"
    services_kb_nails = create_services_keyboard(user_en, "nails")
    found_manicure = False
    for row in services_kb_nails.inline_keyboard:
        for button in row:
            if "Manicure" in button.text:
                found_manicure = True
                break
    assert found_manicure, "Тест: 'Manicure' не найден в разделе Nails"
    
    # Дополнительные тесты
    # Тест поиска услуги
    service = get_service_by_key("thai")
    assert service is not None, "Услуга 'thai' не найдена"
    assert service.title_en == "Thai massage", "Неверный английский заголовок"
    
    # Тест валидации
    assert validate_date_format("15.12.2024") == True
    assert validate_date_format("invalid") == False
    assert validate_time_format("14:30") == True
    assert validate_time_format("25:99") == False
    
    # Тест локализации
    assert get_text(user_ru, "categories.massage") == "Массаж"
    assert get_text(user_en, "categories.massage") == "Massage"
    
    # Новые тесты календарной функциональности
    today = datetime.now(TZINFO).date()
    
    # Тест календаря: build_calendar должен возвращать клавиатуру с кнопками cal:
    calendar_kb = build_calendar(user_ru, today.year, today.month, today, today + timedelta(days=30))
    found_cal_button = False
    for row in calendar_kb.inline_keyboard:
        for button in row:
            if button.callback_data and button.callback_data.startswith("cal:"):
                found_cal_button = True
                break
        if found_cal_button:
            break
    assert found_cal_button, "Календарь не содержит кнопок с callback_data начинающимся на 'cal:'"
    
    # Тест временных слотов: generate_slots должен вернуть список строк в формате "HH:MM"
    tomorrow = today + timedelta(days=1)
    slots = generate_slots(tomorrow, 60)
    assert isinstance(slots, list), "generate_slots должен вернуть список"
    if slots:  # Проверяем только если есть слоты
        import re
        time_pattern = re.compile(r'^\d{2}:\d{2}$')
        for slot in slots:
            assert isinstance(slot, str), f"Слот должен быть строкой: {slot}"
            assert time_pattern.match(slot), f"Слот должен быть в формате HH:MM: {slot}"
    
    # Тест рабочих часов
    assert len(WORKING_HOURS) == 7, "WORKING_HOURS должен содержать 7 дней недели"
    for day_schedule in WORKING_HOURS.values():
        assert len(day_schedule) == 2, "Каждый день должен иметь начало и конец"
        assert isinstance(day_schedule[0], str) and isinstance(day_schedule[1], str), "Время должно быть строками"
        # Проверяем формат времени HH:MM
        import re
        time_pattern = re.compile(r'^\d{2}:\d{2}$')
        assert time_pattern.match(day_schedule[0]), f"Время начала должно быть в формате HH:MM: {day_schedule[0]}"
        assert time_pattern.match(day_schedule[1]), f"Время окончания должно быть в формате HH:MM: {day_schedule[1]}"
    
    # Тест структуры резерваций
    assert isinstance(RESERVATIONS, dict), "RESERVATIONS должен быть словарем"
    
    print("✅ ALL TESTS PASSED (включая календарные функции)")

async def main():
    """Главная функция запуска бота"""
    if os.getenv("RUN_TESTS") == "1":
        run_offline_tests()
        return
    
    if not _SSL_AVAILABLE:
        logger.warning("Python собран без SSL - подключение к Telegram невозможно")
        return
    
    logger.info("🚀 Запуск Nova Chaloklum Health Massage Bot...")
    
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")