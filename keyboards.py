"""
Клавиатуры для Nova Chaloklum Health Massage Telegram Bot
"""
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List

from config import user_languages
from models import SERVICE_CATEGORIES, SERVICE_CATALOG
from utils import get_text, get_service_by_key

def create_language_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру выбора языка"""
    keyboard = [
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def add_persistent_menu_buttons(builder: InlineKeyboardBuilder, user_id: int) -> None:
    """Добавляет кнопки постоянного меню в InlineKeyboardBuilder"""
    builder.row(
        InlineKeyboardButton(text=get_text(user_id, "main_menu"), callback_data="main_menu"),
        InlineKeyboardButton(text=get_text(user_id, "change_language"), callback_data="change_lang")
    )

def create_main_menu(user_id: int) -> ReplyKeyboardMarkup:
    """Создает основное меню с категориями услуг"""
    lang = user_languages.get(user_id, "en")
    
    buttons = []
    categories = [
        ("massage", "🌿"),
        ("spa", "🧖‍♀️"), 
        ("waxing", "✨"),
        ("nails", "💅")
    ]
    
    row1 = []
    row2 = []
    
    for i, (category, emoji) in enumerate(categories):
        # Маппинг для корректной локализации
        category_key = "cat_wax" if category == "waxing" else f"cat_{category}"
        text = f"{emoji} {get_text(user_id, category_key)}"
        button = KeyboardButton(text=text)
        
        if i < 2:
            row1.append(button)
        else:
            row2.append(button)
    
    buttons = [row1, row2]
    
    # Добавляем кнопку смены языка
    lang_button = KeyboardButton(text=get_text(user_id, "change_language"))
    buttons.append([lang_button])
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def cat_label(slug: str, user_id: int) -> str:
    """Возвращает локализованное название категории"""
    labels = {
        "massage": get_text(user_id, "cat_massage"),
        "spa": get_text(user_id, "cat_spa"), 
        "waxing": get_text(user_id, "cat_wax"),
        "nails": get_text(user_id, "cat_nails")
    }
    return labels.get(slug, slug)

def categories_kb(user_id: int) -> InlineKeyboardMarkup:
    """Создает inline-клавиатуру с категориями услуг"""
    builder = InlineKeyboardBuilder()
    
    categories = [
        ("massage", "🌿"),
        ("spa", "🧖‍♀️"),
        ("waxing", "✨"), 
        ("nails", "💅")
    ]
    
    for category, emoji in categories:
        text = f"{emoji} {cat_label(category, user_id)}"
        builder.button(text=text, callback_data=f"cat:{category}")
    
    builder.adjust(2)  # 2 кнопки в ряд
    
    # Добавляем кнопки меню
    add_persistent_menu_buttons(builder, user_id)
    
    return builder.as_markup()

def create_services_keyboard(user_id: int, category: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру с услугами определенной категории"""
    builder = InlineKeyboardBuilder()
    
    if category not in SERVICE_CATEGORIES:
        return InlineKeyboardMarkup(inline_keyboard=[])
    
    service_keys = SERVICE_CATEGORIES[category]
    lang = user_languages.get(user_id, "en")
    
    for service_key in service_keys:
        service = get_service_by_key(service_key)
        if service:
            title = service.get_title(lang)
            builder.button(text=title, callback_data=f"service:{service_key}")
    
    builder.adjust(1)  # По одной кнопке в ряд
    
    # Кнопка "Назад к категориям"
    builder.row(InlineKeyboardButton(
        text=get_text(user_id, "back"), 
        callback_data="back_to_categories"
    ))
    
    # Добавляем кнопки меню
    add_persistent_menu_buttons(builder, user_id)
    
    return builder.as_markup()

def create_duration_keyboard(user_id: int, service_key: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру выбора длительности для услуги"""
    builder = InlineKeyboardBuilder()
    
    service = get_service_by_key(service_key)
    if not service:
        return InlineKeyboardMarkup(inline_keyboard=[])
    
    for variant in service.variants:
        text = f"{variant.duration_min} мин - {variant.price_thb} THB"
        callback_data = f"duration:{service_key}:{variant.duration_min}"
        builder.button(text=text, callback_data=callback_data)
    
    builder.adjust(1)  # По одной кнопке в ряд
    
    # Кнопка "Назад к услугам"
    category = None
    for cat, services in SERVICE_CATEGORIES.items():
        if service_key in services:
            category = cat
            break
    
    if category:
        builder.row(InlineKeyboardButton(
            text=get_text(user_id, "back_to_services"), 
            callback_data=f"back_to_services:{category}"
        ))
    
    # Добавляем кнопки меню
    add_persistent_menu_buttons(builder, user_id)
    
    return builder.as_markup()

def create_confirm_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру подтверждения записи"""
    keyboard = [
        [
            InlineKeyboardButton(
                text=get_text(user_id, "confirm"), 
                callback_data="confirm:yes"
            ),
            InlineKeyboardButton(
                text=get_text(user_id, "cancel"), 
                callback_data="confirm:no"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)