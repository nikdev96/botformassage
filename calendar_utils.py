"""
Календарные утилиты для Nova Chaloklum Health Massage Telegram Bot
"""
import calendar as _cal
from datetime import datetime, date, timedelta
from typing import List
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import TZINFO, WORKING_HOURS, SLOT_STEP_MIN, RESERVATIONS
from text_formatter import get_text
from keyboards import add_persistent_menu_buttons

def build_calendar(user_id: int, year: int, month: int, min_date: date, max_date: date) -> InlineKeyboardMarkup:
    """Строит inline-календарь для выбора даты"""
    builder = InlineKeyboardBuilder()
    
    # Заголовок с месяцем и годом
    month_names_ru = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    month_names_en = [
        "January", "February", "March", "April", "May", "June", 
        "July", "August", "September", "October", "November", "December"
    ]
    
    from config import user_languages
    lang = user_languages.get(user_id, "en")
    month_names = month_names_ru if lang == "ru" else month_names_en
    
    header = f"{month_names[month-1]} {year}"
    builder.row(InlineKeyboardButton(text=header, callback_data="ignore"))
    
    # Кнопки навигации убраны - запись только на 2 недели, не нужна навигация по месяцам
    
    # Дни недели
    weekdays_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    weekdays_en = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    weekdays = weekdays_ru if lang == "ru" else weekdays_en
    
    week_buttons = []
    for day_name in weekdays:
        week_buttons.append(InlineKeyboardButton(text=day_name, callback_data="ignore"))
    builder.row(*week_buttons)
    
    # Календарная сетка
    cal = _cal.monthcalendar(year, month)
    
    for week in cal:
        week_buttons = []
        for day in week:
            if day == 0:
                # Пустой день
                week_buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
            else:
                current_date = date(year, month, day)
                
                # Проверяем, доступен ли день для бронирования
                if min_date <= current_date <= max_date:
                    callback_data = f"cal_date:{year}:{month:02d}:{day:02d}"
                    week_buttons.append(InlineKeyboardButton(
                        text=str(day), 
                        callback_data=callback_data
                    ))
                else:
                    # Недоступный день
                    week_buttons.append(InlineKeyboardButton(text="✖", callback_data="ignore"))
        
        builder.row(*week_buttons)
    
    # Добавляем кнопки меню
    add_persistent_menu_buttons(builder, user_id)
    
    return builder.as_markup()

def generate_slots(date_obj: date, duration_min: int, step_min: int = None) -> List[str]:
    """Генерирует доступные временные слоты на дату"""
    if step_min is None:
        step_min = SLOT_STEP_MIN
    
    weekday = date_obj.weekday()
    
    if weekday not in WORKING_HOURS:
        return []
    
    start_time_str, end_time_str = WORKING_HOURS[weekday]
    start_hour, start_min = map(int, start_time_str.split(":"))
    end_hour, end_min = map(int, end_time_str.split(":"))
    
    # Создаем datetime объекты для начала и конца рабочего дня
    start_dt = datetime.combine(date_obj, datetime.min.time().replace(hour=start_hour, minute=start_min))
    end_dt = datetime.combine(date_obj, datetime.min.time().replace(hour=end_hour, minute=end_min))
    
    # Проверяем таймзону и прошедшее время для сегодняшнего дня
    now = datetime.now(TZINFO)
    now_local = now.replace(tzinfo=None)
    
    if date_obj == now_local.date():
        # Для сегодняшнего дня не показываем слоты, которые уже прошли + буфер 30 минут
        min_start = now_local + timedelta(minutes=30)
        # Округляем до ближайшего шага вперед
        minutes_from_midnight = min_start.hour * 60 + min_start.minute
        rounded_minutes = ((minutes_from_midnight // step_min) + 1) * step_min
        min_start_rounded = datetime.combine(date_obj, datetime.min.time()) + timedelta(minutes=rounded_minutes)
        start_dt = max(start_dt, min_start_rounded)
    
    # Получаем существующие резервации на эту дату (локальные)
    date_key = date_obj.strftime("%Y-%m-%d")
    local_reservations = list(RESERVATIONS.get(date_key, []))
    
    # Получаем резервации из Google Sheets
    sheets_reservations = []
    try:
        from google_sheets import get_sheets_reservations_for_date
        sheets_reservations = get_sheets_reservations_for_date(date_obj)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Ошибка загрузки резерваций из Google Sheets: {e}")
    
    # Объединяем все резервации для проверки занятости
    all_reservations = local_reservations + sheets_reservations
    
    slots = []
    current_dt = start_dt
    
    while current_dt + timedelta(minutes=duration_min) <= end_dt:
        slot_end = current_dt + timedelta(minutes=duration_min)
        
        # Проверяем, не пересекается ли слот с существующими резервациями
        is_available = True
        for res_start, res_end in all_reservations:
            # Проверка пересечения интервалов
            if not (slot_end <= res_start or current_dt >= res_end):
                is_available = False
                break
        
        if is_available:
            slots.append(current_dt.strftime("%H:%M"))
        
        current_dt += timedelta(minutes=step_min)
    
    return slots

def slots_kb(user_id: int, date_obj: date, duration_min: int, step_min: int = None) -> InlineKeyboardMarkup:
    """Создает клавиатуру с доступными временными слотами"""
    builder = InlineKeyboardBuilder()
    
    slots = generate_slots(date_obj, duration_min, step_min)
    
    if not slots:
        # Нет доступных слотов
        builder.row(InlineKeyboardButton(
            text=get_text(user_id, "no_slots"), 
            callback_data="ignore"
        ))
    else:
        # Добавляем кнопки слотов
        for slot_time in slots:
            builder.button(
                text=slot_time, 
                callback_data=f"slot_time:{date_obj.strftime('%Y-%m-%d')}:{slot_time}"
            )
        
        builder.adjust(3)  # 3 кнопки в ряд
    
    # Кнопка "Назад к календарю" 
    builder.row(InlineKeyboardButton(
        text=get_text(user_id, "back"), 
        callback_data="back_to_calendar"
    ))
    
    # Добавляем кнопки меню
    add_persistent_menu_buttons(builder, user_id)
    
    return builder.as_markup()