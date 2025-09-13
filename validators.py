"""
Валидаторы для Nova Chaloklum Health Massage Telegram Bot
"""
import re
from typing import Dict


class Validator:
    """Класс для централизованной валидации"""
    
    PATTERNS = {
        'date': r'^\d{2}\.\d{2}\.\d{4}$',
        'time': r'^\d{2}:\d{2}$',
        'phone': r'^\+?[\d\s\-\(\)]{10,20}$'
    }
    
    @classmethod
    def validate_format(cls, value: str, format_type: str) -> bool:
        """Универсальный валидатор формата"""
        if format_type not in cls.PATTERNS:
            return False
        return bool(re.match(cls.PATTERNS[format_type], value))
    
    @classmethod
    def validate_date_format(cls, date_str: str) -> bool:
        """Валидирует формат даты ДД.ММ.ГГГГ"""
        return cls.validate_format(date_str, 'date')
    
    @classmethod
    def validate_time_format(cls, time_str: str) -> bool:
        """Валидирует формат времени ЧЧ:ММ"""
        if not cls.validate_format(time_str, 'time'):
            return False
        
        try:
            hours, minutes = map(int, time_str.split(':'))
            return 0 <= hours <= 23 and 0 <= minutes <= 59
        except ValueError:
            return False
    
    @classmethod
    def is_valid_phone(cls, phone: str) -> bool:
        """Улучшенная валидация телефонного номера"""
        if not phone:
            return False
        
        if not cls.validate_format(phone, 'phone'):
            return False
        
        # Проверяем количество цифр
        digits_only = re.sub(r'[^\d]', '', phone)
        return 10 <= len(digits_only) <= 15


# Функции-обертки для обратной совместимости
def validate_date_format(date_str: str) -> bool:
    return Validator.validate_date_format(date_str)


def validate_time_format(time_str: str) -> bool:
    return Validator.validate_time_format(time_str)


def is_valid_phone(phone: str) -> bool:
    return Validator.is_valid_phone(phone)