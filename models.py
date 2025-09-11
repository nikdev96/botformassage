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

# Каталог услуг
SERVICE_CATALOG = [
    # Массаж
    Service(
        key="thai_traditional",
        title_ru="Традиционный тайский массаж",
        title_en="Traditional Thai Massage",
        variants=[
            ServiceVariant(60, 400),
            ServiceVariant(90, 600),
            ServiceVariant(120, 800)
        ]
    ),
    Service(
        key="oil_massage",
        title_ru="Масляный массаж",
        title_en="Oil Massage",
        variants=[
            ServiceVariant(60, 450),
            ServiceVariant(90, 650),
            ServiceVariant(120, 850)
        ]
    ),
    Service(
        key="deep_tissue",
        title_ru="Глубокий массаж тканей",
        title_en="Deep Tissue Massage",
        variants=[
            ServiceVariant(60, 500),
            ServiceVariant(90, 700),
            ServiceVariant(120, 900)
        ]
    ),
    Service(
        key="hot_stone",
        title_ru="Массаж горячими камнями",
        title_en="Hot Stone Massage",
        variants=[
            ServiceVariant(90, 800),
            ServiceVariant(120, 1000)
        ]
    ),
    Service(
        key="foot_massage",
        title_ru="Массаж стоп",
        title_en="Foot Massage",
        variants=[
            ServiceVariant(45, 300),
            ServiceVariant(60, 400)
        ]
    ),
    Service(
        key="head_shoulders",
        title_ru="Массаж головы и плеч",
        title_en="Head & Shoulders Massage", 
        variants=[
            ServiceVariant(30, 250),
            ServiceVariant(45, 350)
        ]
    ),
    
    # Spa услуги
    Service(
        key="aromatherapy",
        title_ru="Ароматерапия",
        title_en="Aromatherapy",
        variants=[
            ServiceVariant(60, 550),
            ServiceVariant(90, 750)
        ]
    ),
    Service(
        key="body_scrub",
        title_ru="Скраб для тела",
        title_en="Body Scrub",
        variants=[
            ServiceVariant(45, 400),
            ServiceVariant(60, 500)
        ]
    ),
    Service(
        key="body_wrap",
        title_ru="Обертывание тела",
        title_en="Body Wrap",
        variants=[
            ServiceVariant(60, 600),
            ServiceVariant(90, 800)
        ]
    ),
    Service(
        key="facial_basic",
        title_ru="Базовый уход за лицом",
        title_en="Basic Facial",
        variants=[
            ServiceVariant(60, 450),
            ServiceVariant(90, 650)
        ]
    ),
    Service(
        key="facial_premium",
        title_ru="Премиум уход за лицом",
        title_en="Premium Facial",
        variants=[
            ServiceVariant(90, 800),
            ServiceVariant(120, 1000)
        ]
    ),
    
    # Воск (эпиляция)
    Service(
        key="wax_legs",
        title_ru="Эпиляция ног воском",
        title_en="Leg Waxing",
        variants=[
            ServiceVariant(45, 350),
            ServiceVariant(60, 450)
        ]
    ),
    Service(
        key="wax_arms",
        title_ru="Эпиляция рук воском", 
        title_en="Arm Waxing",
        variants=[
            ServiceVariant(30, 250),
            ServiceVariant(45, 350)
        ]
    ),
    Service(
        key="wax_bikini",
        title_ru="Эпиляция бикини воском",
        title_en="Bikini Waxing", 
        variants=[
            ServiceVariant(30, 300),
            ServiceVariant(45, 400)
        ]
    ),
    Service(
        key="wax_eyebrows",
        title_ru="Коррекция бровей воском",
        title_en="Eyebrow Waxing",
        variants=[
            ServiceVariant(15, 150),
            ServiceVariant(20, 200)
        ]
    ),
    
    # Ногтевой сервис
    Service(
        key="manicure_basic",
        title_ru="Базовый маникюр",
        title_en="Basic Manicure",
        variants=[
            ServiceVariant(90, 800)
        ]
    ),
    Service(
        key="manicure_gel",
        title_ru="Гель-лак маникюр",
        title_en="Gel Polish Manicure",
        variants=[
            ServiceVariant(90, 800)
        ]
    ),
    Service(
        key="pedicure_basic",
        title_ru="Базовый педикюр",
        title_en="Basic Pedicure",
        variants=[
            ServiceVariant(90, 800)
        ]
    ),
    Service(
        key="pedicure_gel",
        title_ru="Гель-лак педикюр",
        title_en="Gel Polish Pedicure",
        variants=[
            ServiceVariant(90, 800)
        ]
    ),
    Service(
        key="nail_art",
        title_ru="Дизайн ногтей",
        title_en="Nail Art",
        variants=[
            ServiceVariant(90, 800)
        ]
    )
]

# Категории услуг
SERVICE_CATEGORIES = {
    "massage": ["thai_traditional", "oil_massage", "deep_tissue", "hot_stone", "foot_massage", "head_shoulders"],
    "spa": ["aromatherapy", "body_scrub", "body_wrap", "facial_basic", "facial_premium"],
    "waxing": ["wax_legs", "wax_arms", "wax_bikini", "wax_eyebrows"],
    "nails": ["manicure_basic", "manicure_gel", "pedicure_basic", "pedicure_gel", "nail_art"]
}