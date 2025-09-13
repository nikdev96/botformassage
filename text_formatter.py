"""
Форматирование текста для Nova Chaloklum Health Massage Telegram Bot
"""
import logging
from config import TEXTS, user_languages

logger = logging.getLogger(__name__)


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


def get_lang(user_id: int) -> str:
    """Получает язык пользователя (по умолчанию английский)"""
    return user_languages.get(user_id, "en")


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


def format_reminder_message(lang: str, service_title: str, date_str: str, time_str: str, duration_min: int) -> str:
    """
    Форматирует сообщение напоминания
    """
    # Получаем шаблон сообщения
    template = TEXTS.get(lang, TEXTS['en']).get('reminder_2h', 'Reminder: your appointment is in 2 hours.')
    
    # Безопасно форматируем все переменные
    try:
        formatted_message = template.format(
            service=safe_text(service_title),
            date=safe_text(date_str),
            time=safe_text(time_str),
            duration=duration_min
        )
        return formatted_message
    except Exception as e:
        logger.error(f"Ошибка форматирования напоминания: {e}")
        # Фолбэк сообщение
        return f"⏰ Напоминание о записи через 2 часа: {service_title}, {date_str} в {time_str}"