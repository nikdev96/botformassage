"""
Модели данных для Nova Chaloklum Health Massage Telegram Bot
"""
from dataclasses import dataclass
from typing import Optional, List
from aiogram.fsm.state import State, StatesGroup

@dataclass
class ServiceVariant:
    """Вариант услуги с определенной длительностью и ценой"""
    duration_min: int
    price_thb: int

@dataclass
class Service:
    """Услуга массажа/спа"""
    key: str
    title_ru: str
    title_en: str
    variants: List[ServiceVariant]
    note: str = ""
    
    def get_title(self, lang: str) -> str:
        """Возвращает название услуги на нужном языке"""
        return self.title_ru if lang == "ru" else self.title_en

class BookingState(StatesGroup):
    """Состояния FSM для процесса бронирования"""
    selecting_service = State() 
    selecting_duration = State()
    selecting_date = State()
    selecting_time = State()
    entering_date = State()
    entering_time = State()
    entering_name = State()
    entering_phone = State()
    confirming = State()

# Компактные данные услуг (data-driven)
SERVICES_DATA = {
    # Массаж
    "thai_traditional": ("Традиционный тайский массаж", "Traditional Thai Massage", [(60,400), (90,600), (120,800)]),
    "oil_massage": ("Масляный массаж", "Oil Massage", [(60,450), (90,650), (120,850)]),
    "deep_tissue": ("Глубокий массаж тканей", "Deep Tissue Massage", [(60,500), (90,700), (120,900)]),
    "hot_stone": ("Массаж горячими камнями", "Hot Stone Massage", [(90,800), (120,1000)]),
    "foot_massage": ("Массаж стоп", "Foot Massage", [(45,300), (60,400)]),
    "head_shoulders": ("Массаж головы и плеч", "Head & Shoulders Massage", [(30,250), (45,350)]),
    
    # Spa услуги
    "aromatherapy": ("Ароматерапия", "Aromatherapy", [(60,550), (90,750)]),
    "body_scrub": ("Скраб для тела", "Body Scrub", [(45,400), (60,500)]),
    "body_wrap": ("Обертывание тела", "Body Wrap", [(60,600), (90,800)]),
    "facial_basic": ("Базовый уход за лицом", "Basic Facial", [(60,450), (90,650)]),
    "facial_premium": ("Премиум уход за лицом", "Premium Facial", [(90,800), (120,1000)]),
    
    # Воск (эпиляция)
    "wax_legs": ("Эпиляция ног воском", "Leg Waxing", [(45,350), (60,450)]),
    "wax_arms": ("Эпиляция рук воском", "Arm Waxing", [(30,250), (45,350)]),
    "wax_bikini": ("Эпиляция бикини воском", "Bikini Waxing", [(30,300), (45,400)]),
    "wax_eyebrows": ("Коррекция бровей воском", "Eyebrow Waxing", [(15,150), (20,200)]),
    
    # Ногтевой сервис
    "manicure_basic": ("Базовый маникюр", "Basic Manicure", [(90,800)]),
    "manicure_gel": ("Гель-лак маникюр", "Gel Polish Manicure", [(90,800)]),
    "pedicure_basic": ("Базовый педикюр", "Basic Pedicure", [(90,800)]),
    "pedicure_gel": ("Гель-лак педикюр", "Gel Polish Pedicure", [(90,800)]),
    "nail_art": ("Дизайн ногтей", "Nail Art", [(90,800)])
}

# Генерация каталога услуг из компактных данных
SERVICE_CATALOG = [
    Service(
        key=key,
        title_ru=ru_title,
        title_en=en_title,
        variants=[ServiceVariant(duration, price) for duration, price in variants]
    )
    for key, (ru_title, en_title, variants) in SERVICES_DATA.items()
]

# Индекс для быстрого поиска услуг O(1)
SERVICE_INDEX = {service.key: service for service in SERVICE_CATALOG}

# Категории услуг
SERVICE_CATEGORIES = {
    "massage": ["thai_traditional", "oil_massage", "deep_tissue", "hot_stone", "foot_massage", "head_shoulders"],
    "spa": ["aromatherapy", "body_scrub", "body_wrap", "facial_basic", "facial_premium"],
    "waxing": ["wax_legs", "wax_arms", "wax_bikini", "wax_eyebrows"],
    "nails": ["manicure_basic", "manicure_gel", "pedicure_basic", "pedicure_gel", "nail_art"]
}