"""
Google Sheets интеграция для Nova Chaloklum Health Massage Telegram Bot
"""
import os
import logging
from datetime import datetime, date, timedelta
from typing import List, Tuple, Dict, Optional
import gspread
from google.oauth2.service_account import Credentials

from config import SHEETS_ENABLED, SHEETS_SPREADSHEET_ID, SHEETS_SHEET_NAME, GOOGLE_CREDENTIALS_FILE, TZINFO, REMINDER_LEAD_MIN

logger = logging.getLogger(__name__)

# Кэш для бронирований из Google Sheets
_sheets_cache: Dict[str, List[Tuple[datetime, datetime]]] = {}
_last_cache_update: Optional[datetime] = None
_cache_ttl_minutes = 5  # Время жизни кэша в минутах

def init_sheets() -> Optional[gspread.Worksheet]:
    """
    Инициализирует подключение к Google Sheets
    
    Returns:
        Worksheet объект или None если подключение невозможно
    """
    if not SHEETS_ENABLED:
        logger.info("Google Sheets интеграция отключена")
        return None
        
    if not SHEETS_SPREADSHEET_ID:
        logger.warning("SHEETS_SPREADSHEET_ID не настроен")
        return None
        
    if not os.path.exists(GOOGLE_CREDENTIALS_FILE):
        logger.warning(f"Файл с учетными данными {GOOGLE_CREDENTIALS_FILE} не найден")
        return None
    
    try:
        # Загружаем учетные данные
        creds = Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_FILE,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        # Подключаемся к Google Sheets
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(SHEETS_SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(SHEETS_SHEET_NAME)
        
        logger.info(f"Успешно подключились к Google Sheets: {SHEETS_SHEET_NAME}")
        return worksheet
        
    except Exception as e:
        logger.error(f"Ошибка подключения к Google Sheets: {e}")
        return None

def parse_sheets_datetime(date_str: str, time_str: str) -> Optional[datetime]:
    """
    Парсит дату и время из Google Sheets в datetime объект
    
    Args:
        date_str: Строка даты в различных форматах
        time_str: Строка времени в различных форматах
        
    Returns:
        datetime объект или None если парсинг неудачен
    """
    try:
        # Попробуем различные форматы дат
        date_formats = ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%m/%d/%Y']
        date_obj = None
        
        for fmt in date_formats:
            try:
                date_obj = datetime.strptime(date_str.strip(), fmt).date()
                break
            except ValueError:
                continue
        
        if not date_obj:
            logger.warning(f"Не удалось распарсить дату: {date_str}")
            return None
        
        # Попробуем различные форматы времени
        time_formats = ['%H:%M', '%H:%M:%S', '%I:%M %p', '%I:%M:%S %p']
        time_obj = None
        
        time_str_clean = time_str.strip()
        for fmt in time_formats:
            try:
                time_obj = datetime.strptime(time_str_clean, fmt).time()
                break
            except ValueError:
                continue
        
        # Если не удалось распарсить время, попробуем простой формат "13"
        if not time_obj and time_str_clean.isdigit():
            try:
                hour = int(time_str_clean)
                if 0 <= hour <= 23:
                    time_obj = datetime.min.time().replace(hour=hour)
            except ValueError:
                pass
        
        if not time_obj:
            logger.warning(f"Не удалось распарсить время: {time_str}")
            return None
        
        return datetime.combine(date_obj, time_obj)
        
    except Exception as e:
        logger.error(f"Ошибка парсинга даты/времени '{date_str}' / '{time_str}': {e}")
        return None

def fetch_bookings_for_date(target_date: date) -> List[Tuple[datetime, datetime]]:
    """
    Получает все бронирования для указанной даты из Google Sheets
    
    Args:
        target_date: Дата для получения бронирований
        
    Returns:
        Список кортежей (start_datetime, end_datetime)
    """
    global _sheets_cache, _last_cache_update
    
    date_key = target_date.strftime("%Y-%m-%d")
    now = datetime.now()
    
    # Проверяем кэш
    if (_last_cache_update and 
        (now - _last_cache_update).total_seconds() < _cache_ttl_minutes * 60 and
        date_key in _sheets_cache):
        logger.debug(f"Используем кэшированные данные для {date_key}")
        return _sheets_cache[date_key]
    
    # Инициализируем подключение к Sheets
    worksheet = init_sheets()
    if not worksheet:
        logger.warning("Google Sheets недоступен, возвращаем пустой список")
        return []
    
    try:
        # Получаем все записи из таблицы
        all_records = worksheet.get_all_records()
        bookings = []
        
        for record in all_records:
            try:
                # Ищем колонки с датой и временем (гибкие названия)
                date_value = None
                start_time_value = None
                duration_value = None
                
                # Попробуем найти дату в различных колонках
                for key in record.keys():
                    key_lower = key.lower().strip()
                    value = str(record[key]).strip()
                    
                    # Пропускаем пустые значения и колонки с таймзонами
                    if not value or value in ['Asia/Bangkok', 'UTC']:
                        continue
                        
                    if 'date' in key_lower or 'дата' in key_lower:
                        date_value = value
                    elif ('time' in key_lower and 'start' in key_lower) or ('время' in key_lower and ('начал' in key_lower or 'старт' in key_lower)):
                        start_time_value = value
                    elif 'time' in key_lower or 'время' in key_lower:
                        if not start_time_value and ':' in value:  # Проверяем что это время
                            start_time_value = value
                    elif 'duration' in key_lower or 'длительность' in key_lower or 'продолж' in key_lower:
                        duration_value = value
                
                if not all([date_value, start_time_value]):
                    continue
                
                # Парсим дату и время начала
                start_dt = parse_sheets_datetime(date_value, start_time_value)
                if not start_dt:
                    continue
                
                # Проверяем, что дата совпадает с целевой
                if start_dt.date() != target_date:
                    continue
                
                # Определяем длительность
                duration_minutes = 60  # По умолчанию 60 минут
                if duration_value:
                    try:
                        # Пытаемся извлечь число минут
                        if duration_value.isdigit():
                            duration_minutes = int(duration_value)
                        elif 'мин' in duration_value.lower() or 'min' in duration_value.lower():
                            # Извлекаем число из строки "90 мин" или "90 minutes"
                            import re
                            match = re.search(r'\d+', duration_value)
                            if match:
                                duration_minutes = int(match.group())
                    except (ValueError, AttributeError):
                        logger.warning(f"Не удалось распарсить длительность: {duration_value}")
                
                # Вычисляем время окончания
                end_dt = start_dt + timedelta(minutes=duration_minutes)
                
                bookings.append((start_dt, end_dt))
                logger.debug(f"Найдено бронирование: {start_dt} - {end_dt}")
                
            except Exception as e:
                logger.warning(f"Ошибка обработки записи из Sheets: {record}, ошибка: {e}")
                continue
        
        # Обновляем кэш
        _sheets_cache[date_key] = bookings
        _last_cache_update = now
        
        logger.info(f"Загружено {len(bookings)} бронирований для {date_key} из Google Sheets")
        return bookings
        
    except Exception as e:
        logger.error(f"Ошибка получения данных из Google Sheets для {date_key}: {e}")
        return []

def invalidate_cache():
    """Очищает кэш бронирований"""
    global _sheets_cache, _last_cache_update
    _sheets_cache.clear()
    _last_cache_update = None
    logger.info("Кэш Google Sheets очищен")

def get_sheets_reservations_for_date(target_date: date) -> List[Tuple[datetime, datetime]]:
    """
    Публичная функция для получения резерваций из Google Sheets для календарных утилит
    
    Args:
        target_date: Дата для получения резерваций
        
    Returns:
        Список кортежей (start_datetime, end_datetime) в локальном времени
    """
    if not SHEETS_ENABLED:
        return []
    
    bookings = fetch_bookings_for_date(target_date)
    
    # Убеждаемся, что все datetime объекты в локальном времени
    local_bookings = []
    for start_dt, end_dt in bookings:
        if start_dt.tzinfo is None:
            # Если timezone не указан, считаем что это местное время
            start_dt = start_dt.replace(tzinfo=None)
            end_dt = end_dt.replace(tzinfo=None)
        else:
            # Конвертируем в местное время
            start_dt = start_dt.astimezone(TZINFO).replace(tzinfo=None)
            end_dt = end_dt.astimezone(TZINFO).replace(tzinfo=None)
        
        local_bookings.append((start_dt, end_dt))
    
    return local_bookings

def ensure_reminder_column(worksheet: gspread.Worksheet) -> None:
    """
    Убеждается, что в таблице есть колонка reminder_2h_sent
    """
    try:
        # Получаем первую строку с заголовками
        headers = worksheet.row_values(1)
        
        # Проверяем, есть ли колонка с напоминаниями
        reminder_col_name = "reminder_2h_sent"
        if reminder_col_name not in headers:
            # Добавляем колонку в конец
            col_index = len(headers) + 1
            worksheet.update_cell(1, col_index, reminder_col_name)
            logger.info(f"Добавлена колонка {reminder_col_name} в позицию {col_index}")
        else:
            logger.debug(f"Колонка {reminder_col_name} уже существует")
            
    except Exception as e:
        logger.error(f"Ошибка при проверке/добавлении колонки напоминаний: {e}")

def fetch_due_reminders(lead_min: int, window_sec: int = 300) -> List[Dict]:
    """
    Получает записи, для которых нужно отправить напоминания
    
    Args:
        lead_min: За сколько минут до записи отправлять напоминание
        window_sec: Окно в секундах для поиска записей (по умолчанию 5 минут)
        
    Returns:
        Список словарей с данными записей: booking_id, tg_user_id, language, 
        service_title, date_str, time, duration_min
    """
    if not SHEETS_ENABLED:
        return []
    
    worksheet = init_sheets()
    if not worksheet:
        return []
    
    try:
        # Убеждаемся что колонка напоминаний существует
        ensure_reminder_column(worksheet)
        
        # Получаем все записи
        all_records = worksheet.get_all_records()
        due_reminders = []
        
        now = datetime.now(TZINFO)
        window_start = now
        window_end = now + timedelta(seconds=window_sec)
        
        for record in all_records:
            try:
                # Проверяем, отправлено ли уже напоминание
                reminder_sent = str(record.get('reminder_2h_sent', '')).strip()
                if reminder_sent and reminder_sent.lower() not in ['', '0', 'false', 'no']:
                    continue  # Напоминание уже отправлено
                
                # Извлекаем данные записи
                booking_id = str(record.get('booking_id', '')).strip()
                date_iso = str(record.get('date_iso', '')).strip()
                date_str = str(record.get('date_str', '')).strip()
                time_str = str(record.get('time', '')).strip()
                service_title = str(record.get('service_title', '')).strip()
                tg_user_id = str(record.get('telegram_id', '')).strip()
                language = str(record.get('language', 'en')).strip()
                duration_min = str(record.get('duration_min', '60')).strip()
                
                if not all([booking_id, tg_user_id, service_title]):
                    continue
                
                # Парсим дату и время записи
                booking_dt = None
                
                if date_iso and time_str:
                    # Пробуем использовать date_iso + time
                    try:
                        if 'T' in date_iso:
                            # Полная дата-время в ISO формате
                            booking_dt = datetime.fromisoformat(date_iso.replace('Z', '+00:00'))
                            if booking_dt.tzinfo:
                                booking_dt = booking_dt.astimezone(TZINFO)
                            else:
                                booking_dt = booking_dt.replace(tzinfo=TZINFO)
                        else:
                            # Только дата в ISO, добавляем время
                            booking_date = datetime.fromisoformat(date_iso).date()
                            booking_time = parse_time_string(time_str)
                            if booking_time:
                                booking_dt = datetime.combine(booking_date, booking_time)
                                booking_dt = booking_dt.replace(tzinfo=TZINFO)
                    except Exception:
                        pass
                
                if not booking_dt and date_str and time_str:
                    # Фолбэк на date_str + time
                    booking_dt = parse_sheets_datetime(date_str, time_str)
                    if booking_dt:
                        # Убеждаемся что время в правильной timezone
                        if booking_dt.tzinfo is None:
                            booking_dt = booking_dt.replace(tzinfo=TZINFO)
                        else:
                            booking_dt = booking_dt.astimezone(TZINFO)
                
                if not booking_dt:
                    logger.warning(f"Не удалось распарсить дату для записи {booking_id}")
                    continue
                
                # Вычисляем время для отправки напоминания
                reminder_time = booking_dt - timedelta(minutes=lead_min)
                
                # Проверяем, попадает ли время напоминания в окно
                if window_start <= reminder_time <= window_end:
                    # Парсим длительность
                    try:
                        duration_minutes = int(duration_min) if duration_min.isdigit() else 60
                    except (ValueError, AttributeError):
                        duration_minutes = 60
                    
                    # Парсим telegram_id
                    try:
                        telegram_user_id = int(tg_user_id)
                    except (ValueError, TypeError):
                        logger.warning(f"Неверный telegram_id: {tg_user_id} для записи {booking_id}")
                        continue
                    
                    due_reminders.append({
                        'booking_id': booking_id,
                        'tg_user_id': telegram_user_id,
                        'language': language,
                        'service_title': service_title,
                        'date_str': date_str,
                        'time': time_str,
                        'duration_min': duration_minutes,
                        'booking_datetime': booking_dt
                    })
                    
                elif reminder_time < window_start:
                    # Время напоминания уже прошло, отправляем сразу
                    try:
                        duration_minutes = int(duration_min) if duration_min.isdigit() else 60
                        telegram_user_id = int(tg_user_id)
                        
                        due_reminders.append({
                            'booking_id': booking_id,
                            'tg_user_id': telegram_user_id,
                            'language': language,
                            'service_title': service_title,
                            'date_str': date_str,
                            'time': time_str,
                            'duration_min': duration_minutes,
                            'booking_datetime': booking_dt,
                            'overdue': True  # Флаг что напоминание просрочено
                        })
                    except (ValueError, TypeError):
                        continue
                        
            except Exception as e:
                logger.warning(f"Ошибка обработки записи для напоминания: {record}, ошибка: {e}")
                continue
        
        logger.info(f"Найдено {len(due_reminders)} записей для отправки напоминаний")
        return due_reminders
        
    except Exception as e:
        logger.error(f"Ошибка получения записей для напоминаний: {e}")
        return []

def parse_time_string(time_str: str) -> Optional[datetime.time]:
    """
    Парсит строку времени в объект time
    """
    if not time_str:
        return None
        
    try:
        time_formats = ['%H:%M', '%H:%M:%S', '%I:%M %p', '%I:%M:%S %p']
        
        for fmt in time_formats:
            try:
                return datetime.strptime(time_str.strip(), fmt).time()
            except ValueError:
                continue
        
        # Пробуем простой формат "13"
        if time_str.strip().isdigit():
            hour = int(time_str.strip())
            if 0 <= hour <= 23:
                return datetime.min.time().replace(hour=hour)
                
    except Exception as e:
        logger.warning(f"Ошибка парсинга времени '{time_str}': {e}")
    
    return None

def mark_reminder_sent(booking_id: str) -> None:
    """
    Помечает запись как "напоминание отправлено"
    
    Args:
        booking_id: ID записи для пометки
    """
    if not SHEETS_ENABLED:
        return
    
    worksheet = init_sheets()
    if not worksheet:
        return
    
    try:
        # Получаем все записи
        all_records = worksheet.get_all_records()
        
        # Ищем строку с нужным booking_id
        for i, record in enumerate(all_records, start=2):  # Начинаем с 2, так как 1 - заголовки
            if str(record.get('booking_id', '')).strip() == booking_id:
                # Находим колонку reminder_2h_sent
                headers = worksheet.row_values(1)
                try:
                    reminder_col_index = headers.index('reminder_2h_sent') + 1
                except ValueError:
                    # Колонки нет, добавляем
                    ensure_reminder_column(worksheet)
                    headers = worksheet.row_values(1)
                    reminder_col_index = headers.index('reminder_2h_sent') + 1
                
                # Ставим метку отправки
                timestamp = datetime.now(TZINFO).isoformat()
                worksheet.update_cell(i, reminder_col_index, timestamp)
                logger.info(f"Помечена запись {booking_id} как отправленная в {timestamp}")
                return
        
        logger.warning(f"Не найдена запись с booking_id: {booking_id}")
        
    except Exception as e:
        logger.error(f"Ошибка пометки напоминания для {booking_id}: {e}")