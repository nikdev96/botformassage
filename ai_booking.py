"""
AI Booking Assistant для Nova Chaloklum Health Massage Bot
Обрабатывает естественный язык и оформляет записи через OpenAI API
"""
import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any

from config import (
    OPENAI_API_KEY, FEATURE_AI_BOOKING, TZINFO, MAX_DAYS_AHEAD,
    user_languages
)
from models import SERVICE_CATALOG, SERVICE_CATEGORIES
from text_formatter import get_text, safe_text
from validators import validate_date_format, validate_time_format, is_valid_phone
from utils import get_service_by_key, get_service_variant
from calendar_utils import generate_slots

logger = logging.getLogger(__name__)

def get_services_catalog_for_ai(lang: str = "en") -> Dict[str, Any]:
    """
    Возвращает сокращенный каталог услуг для передачи в AI
    
    Args:
        lang: Язык для названий услуг
        
    Returns:
        Словарь с услугами: {category: {service_key: {title, durations}}}
    """
    catalog = {}
    
    for category, service_keys in SERVICE_CATEGORIES.items():
        catalog[category] = {}
        for service_key in service_keys:
            service = get_service_by_key(service_key)
            if service:
                title = service.get_title(lang)
                durations = [variant.duration_min for variant in service.variants]
                catalog[category][service_key] = {
                    "title": title,
                    "durations": durations
                }
    
    return catalog

async def ai_extract_booking(user_id: int, user_lang: str, user_text: str, context: Dict = None) -> Dict[str, Any]:
    """
    Извлекает данные бронирования из естественного языка через OpenAI
    
    Args:
        user_id: ID пользователя
        user_lang: Язык пользователя (ru/en)
        user_text: Текст пользователя
        context: Контекст предыдущего диалога (опционально)
        
    Returns:
        Словарь с извлеченными данными и статусом
    """
    if not FEATURE_AI_BOOKING or not OPENAI_API_KEY:
        return {"error": get_text(user_id, "ai_unavailable")}
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Получаем каталог услуг для AI
        services = get_services_catalog_for_ai(user_lang)
        
        # Текущая дата для расчетов
        today = datetime.now(TZINFO).date()
        max_date = today + timedelta(days=MAX_DAYS_AHEAD)
        
        # Системный промпт на языке пользователя
        system_prompt = {
            "en": f"""You are a booking assistant for Nova Chaloklum Health Massage spa. 
Today is {today.strftime('%Y-%m-%d')} (%A). Maximum booking ahead: {MAX_DAYS_AHEAD} days (until {max_date.strftime('%Y-%m-%d')}).
Working hours: Mon-Sat 10:00-22:00, Sun 10:00-20:00.

Available services: {json.dumps(services, ensure_ascii=False)}

Extract booking information from user request. Return ONLY valid JSON without any markdown or explanations:
{{"category": "massage|spa|waxing|nails", "service_key": "exact_key_from_catalog", "duration_min": number, "date_iso": "YYYY-MM-DD", "time_str": "HH:MM", "client_name": "string", "client_phone": "string", "language": "{user_lang}", "missing": ["field1", "field2"], "message": "clarification_needed_or_ready_to_confirm"}}

Rules:
- Only return fields you are confident about
- For relative dates: "today"={today}, "tomorrow"={today + timedelta(days=1)}, etc.
- If time not specified but date is, suggest available slots
- Add fields to "missing" array if not provided or unclear
- Set "message" to explanation of what's missing or confirmation request""",
            "ru": f"""Вы помощник по записи в спа-салон Nova Chaloklum Health Massage.
Сегодня {today.strftime('%Y-%m-%d')} ({today.strftime('%A')}). Максимум записи вперед: {MAX_DAYS_AHEAD} дней (до {max_date.strftime('%Y-%m-%d')}).
Рабочие часы: Пн-Сб 10:00-22:00, Вс 10:00-20:00.

Доступные услуги: {json.dumps(services, ensure_ascii=False)}

Извлеките информацию о записи из запроса пользователя. Верните ТОЛЬКО валидный JSON без markdown или пояснений:
{{"category": "massage|spa|waxing|nails", "service_key": "точный_ключ_из_каталога", "duration_min": число, "date_iso": "YYYY-MM-DD", "time_str": "HH:MM", "client_name": "строка", "client_phone": "строка", "language": "{user_lang}", "missing": ["поле1", "поле2"], "message": "что_нужно_уточнить_или_готово_к_подтверждению"}}

Правила:
- Возвращайте только поля, в которых уверены
- Для относительных дат: "сегодня"={today}, "завтра"={today + timedelta(days=1)}, и т.д.
- Если время не указано, но дата есть - предложите доступные слоты
- Добавьте поля в массив "missing", если не предоставлены или неясны
- В "message" укажите что нужно уточнить или запрос подтверждения"""
        }[user_lang]
        
        # Добавляем контекст если есть
        messages = [{"role": "system", "content": system_prompt}]
        if context:
            messages.append({"role": "assistant", "content": f"Previous context: {json.dumps(context)}"})
        messages.append({"role": "user", "content": user_text})
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2,
            max_tokens=800
        )
        
        if not response.choices or not response.choices[0].message:
            return {"error": get_text(user_id, "ai_unavailable")}
        
        # Парсим JSON ответ
        ai_response = response.choices[0].message.content.strip()
        
        # Убираем markdown форматирование если есть
        if ai_response.startswith("```json"):
            ai_response = ai_response[7:-3].strip()
        elif ai_response.startswith("```"):
            ai_response = ai_response[3:-3].strip()
        
        try:
            result = json.loads(ai_response)
            result["raw_ai_response"] = ai_response
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI JSON response: {ai_response}, error: {e}")
            return {"error": get_text(user_id, "ai_unavailable")}
        
    except Exception as e:
        logger.error(f"Error in AI booking extraction: {e}")
        return {"error": get_text(user_id, "ai_unavailable")}

def normalize_and_validate(data: Dict[str, Any], user_id: int) -> Tuple[Dict[str, Any], List[str]]:
    """
    Нормализует и валидирует данные бронирования
    
    Args:
        data: Данные от AI
        user_id: ID пользователя для локализации
        
    Returns:
        Tuple[нормализованные_данные, список_ошибок]
    """
    normalized = {}
    errors = []
    
    # Валидация категории
    if "category" in data and data["category"] in SERVICE_CATEGORIES:
        normalized["category"] = data["category"]
    elif "category" in data:
        errors.append("Invalid category")
    
    # Валидация услуги
    if "service_key" in data:
        service = get_service_by_key(data["service_key"])
        if service:
            normalized["service_key"] = data["service_key"]
            
            # Определяем категорию услуги для фиксированных длительностей
            service_category = None
            for category, services in SERVICE_CATEGORIES.items():
                if data["service_key"] in services:
                    service_category = category
                    break
            
            # Валидация длительности с учетом фиксированных категорий
            if service_category == "nails":
                # Nails: фиксированная длительность 90 минут
                normalized["duration"] = 90
            elif service_category == "waxing":
                # Waxing: первый доступный вариант или 60 минут
                if service.variants:
                    normalized["duration"] = service.variants[0].duration_min
                else:
                    normalized["duration"] = 60
            elif "duration_min" in data:
                # Massage/Spa: валидируем предложенную длительность
                variant = get_service_variant(data["service_key"], data["duration_min"])
                if variant:
                    normalized["duration"] = data["duration_min"]
                else:
                    errors.append("Invalid duration for this service")
            else:
                # Если длительность не указана для massage/spa, берем первый доступный
                if service.variants:
                    normalized["duration"] = service.variants[0].duration_min
                else:
                    errors.append("No duration available for this service")
        else:
            errors.append("Invalid service")
    
    # Валидация даты
    if "date_iso" in data:
        try:
            date_obj = datetime.fromisoformat(data["date_iso"]).date()
            today = datetime.now(TZINFO).date()
            max_date = today + timedelta(days=MAX_DAYS_AHEAD)
            
            if date_obj < today:
                errors.append("Date is in the past")
            elif date_obj > max_date:
                errors.append(f"Date too far in future (max {MAX_DAYS_AHEAD} days)")
            else:
                normalized["date_iso"] = data["date_iso"]
                normalized["date_str"] = date_obj.strftime("%d.%m.%Y")
        except ValueError:
            errors.append("Invalid date format")
    
    # Валидация времени
    if "time_str" in data:
        if validate_time_format(data["time_str"]):
            normalized["time_str"] = data["time_str"]
        else:
            errors.append("Invalid time format")
    
    # Валидация имени
    if "client_name" in data and data["client_name"] and len(data["client_name"].strip()) >= 2:
        normalized["client_name"] = data["client_name"].strip()
    
    # Валидация телефона
    if "client_phone" in data and is_valid_phone(data["client_phone"]):
        normalized["client_phone"] = data["client_phone"].strip()
    
    # Проверка доступности слота
    if all(key in normalized for key in ["date_iso", "time_str", "duration"]):
        try:
            date_obj = datetime.fromisoformat(normalized["date_iso"]).date()
            slots = generate_slots(date_obj, normalized["duration"])
            
            # Проверяем, есть ли запрашиваемое время среди доступных слотов
            requested_time = normalized["time_str"]
            
            # Слоты могут быть строками или datetime объектами
            available_times = []
            for slot in slots:
                if hasattr(slot, 'strftime'):
                    available_times.append(slot.strftime("%H:%M"))
                else:
                    # Если slot уже строка
                    available_times.append(str(slot))
            
            if requested_time not in available_times:
                errors.append(f"Time slot unavailable. Available: {', '.join(available_times[:5])}")
                
        except Exception as e:
            logger.error(f"Error checking slot availability: {e}")
            errors.append("Error checking slot availability")
    
    return normalized, errors

async def ai_book(user_id: int, text: str, context: Dict = None) -> Tuple[str, Optional[Dict]]:
    """
    Основная функция AI бронирования
    
    Args:
        user_id: ID пользователя
        text: Текст пользователя
        context: Контекст диалога
        
    Returns:
        Tuple[ответ_пользователю, данные_для_бронирования_или_None]
    """
    lang = user_languages.get(user_id, "en")
    
    # Извлекаем данные через AI
    ai_result = await ai_extract_booking(user_id, lang, text, context)
    
    if "error" in ai_result:
        return ai_result["error"], None
    
    # Нормализуем и валидируем
    normalized, errors = normalize_and_validate(ai_result, user_id)
    
    if errors:
        # Если есть ошибки - возвращаем их для уточнения
        lang = user_languages.get(user_id, "en")
        
        # Специальная обработка для "Invalid service" - добавляем уточнение про массаж
        if "Invalid service" in errors and lang == "ru":
            # Для RU пользователей заменяем "Invalid service" на дружелюбное уточнение
            filtered_errors = [e for e in errors if e != "Invalid service"]
            
            if filtered_errors:
                error_msg = ", ".join(filtered_errors)
                clarify_msg = get_text(user_id, 'ai_clarify_missing').format(fields=error_msg)
            else:
                clarify_msg = ""
            
            massage_clarify = get_text(user_id, 'ai_clarify_massage_type')
            
            if clarify_msg:
                return f"{clarify_msg}\n\n{massage_clarify}", None
            else:
                return massage_clarify, None
        else:
            # Стандартная обработка для EN или других ошибок
            error_msg = "\n".join(errors)
            return f"{get_text(user_id, 'ai_clarify_missing').format(fields=error_msg)}\n\n{ai_result.get('message', '')}", None
    
    # Проверяем, все ли обязательные поля есть
    required_fields = ["service_key", "duration", "date_iso", "time_str", "client_name", "client_phone"]
    missing_fields = []
    
    for field in required_fields:
        if field not in normalized:
            missing_fields.append(field)
    
    if missing_fields:
        # Переводим названия полей
        field_translations = {
            "en": {
                "service_key": "service", "duration": "duration", "date_iso": "date", 
                "time_str": "time", "client_name": "name", "client_phone": "phone"
            },
            "ru": {
                "service_key": "услуга", "duration": "длительность", "date_iso": "дата",
                "time_str": "время", "client_name": "имя", "client_phone": "телефон"
            }
        }
        
        translated_missing = [field_translations[lang].get(field, field) for field in missing_fields]
        missing_text = ", ".join(translated_missing)
        
        clarify_msg = get_text(user_id, 'ai_clarify_missing').format(fields=missing_text)
        return f"{clarify_msg}\n\n{ai_result.get('message', '')}", None
    
    # Все данные есть - готовы к подтверждению
    service = get_service_by_key(normalized["service_key"])
    service_title = service.get_title(lang) if service else normalized["service_key"]
    
    confirm_msg = get_text(user_id, 'ai_ready_to_confirm').format(
        service=safe_text(service_title),
        duration=normalized["duration"],
        date=normalized["date_str"],
        time=normalized["time_str"]
    )
    
    # Возвращаем сообщение подтверждения и данные для записи
    return confirm_msg, normalized