#!/usr/bin/env python3
"""
Отладочный тест для поиска проблемы с get_text
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import get_text, user_languages
from config import TEXTS

# Тест функции get_text
user_id = 123
user_languages[user_id] = "ru"

print("Тестируем get_text...")

# Простой тест
try:
    result = get_text(user_id, "welcome")
    print(f"✅ Простой тест: {result[:50]}...")
except Exception as e:
    print(f"❌ Простой тест: {e}")

# Тест с параметрами
try:
    result = get_text(user_id, "booking_confirmed", 
                      service="Тест", date="12.12.2024", time="14:30",
                      duration=60, price=400, tz="Asia/Bangkok")
    print(f"✅ Тест с параметрами: {result[:50]}...")
except Exception as e:
    print(f"❌ Тест с параметрами: {e}")

# Исправленный тест - как в новом коде
try:
    admin_template = get_text(user_id, "admin_new_booking")
    result = admin_template.format(
        service="Тест услуга",
        duration=60,
        date="12.12.2024",
        time="14:30",
        name="Тест Клиент",
        phone="+66123456789",
        username="test_user",
        user_id=user_id,
        tz="Asia/Bangkok"
    )
    print(f"✅ Исправленный тест: {result[:50]}...")
except Exception as e:
    print(f"❌ Исправленный тест: {e}")
    import traceback
    traceback.print_exc()

print("Тест завершен")