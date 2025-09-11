#!/usr/bin/env python3
"""
Простой тест функций бота без зависимостей от конфигурации
"""
import os
import sys
import json
from datetime import datetime

# Устанавливаем тестовые переменные окружения
os.environ['BOT_TOKEN'] = 'test_token'
os.environ['ADMIN_CHAT_ID'] = '123456789'
os.environ['TZ'] = 'Asia/Bangkok'
os.environ['OPENAI_API_KEY'] = 'test_key'
os.environ['FEATURE_CHATGPT'] = '0'
os.environ['FEATURE_AI_BOOKING'] = '0'
os.environ['WEBHOOK_URL'] = ''
os.environ['SHEETS_ENABLED'] = '0'
os.environ['REMINDERS_ENABLED'] = '0'
os.environ['RUN_TESTS'] = '1'

print("🧪 Запуск простого теста функций бота")
print("=" * 50)

try:
    # Тест импорта основных модулей
    print("📦 Тестирование импортов...")
    
    from config import TEXTS, user_languages
    from models import SERVICE_CATALOG
    print("✅ config.py импортирован успешно")
    
    from utils import get_lang, format_reminder_message
    print("✅ utils.py импортирован успешно")
    
    # Тест функции get_lang
    print("\n🌍 Тест функции get_lang:")
    user_languages[123] = "ru"
    user_languages[456] = "en"
    
    assert get_lang(123) == "ru", "Ошибка: неправильный язык для пользователя 123"
    assert get_lang(456) == "en", "Ошибка: неправильный язык для пользователя 456"
    assert get_lang(999) == "en", "Ошибка: неправильный язык по умолчанию"
    print("✅ Функция get_lang работает корректно")
    
    # Тест структуры SERVICE_CATALOG
    print("\n🛎️  Тест структуры SERVICE_CATALOG:")
    service_keys = [service.key for service in SERVICE_CATALOG]
    assert 'thai_traditional' in service_keys, "Отсутствует традиционный тайский массаж"
    assert 'manicure_basic' in service_keys, "Отсутствует маникюр"
    
    for service in SERVICE_CATALOG:
        assert hasattr(service, 'key'), f"Отсутствует key для сервиса"
        assert hasattr(service, 'title_ru'), f"Отсутствует title_ru для {service.key}"
        assert hasattr(service, 'title_en'), f"Отсутствует title_en для {service.key}"
        assert hasattr(service, 'variants'), f"Отсутствует variants для {service.key}"
        assert len(service.variants) > 0, f"Нет вариантов для {service.key}"
        
        first_variant = service.variants[0]
        print(f"✅ Сервис {service.key}: {service.title_ru} - {first_variant.duration_min}мин - {first_variant.price_thb}THB")
    
    # Тест функции format_reminder_message
    print("\n📝 Тест функции format_reminder_message:")
    
    message_ru = format_reminder_message("ru", "Тайский традиционный массаж", "15.12.2024", "14:30", 60)
    message_en = format_reminder_message("en", "Thai Traditional Massage", "15.12.2024", "14:30", 60)
    
    assert "Тайский традиционный массаж" in message_ru, "Русское название услуги не найдено"
    assert "Thai Traditional Massage" in message_en, "Английское название услуги не найдено"
    assert "14:30" in message_ru and "14:30" in message_en, "Время не найдено в сообщении"
    
    print("✅ Функция format_reminder_message работает на русском")
    print("✅ Функция format_reminder_message работает на английском")
    
    # Тест функций напоминаний (если они есть)
    try:
        from reminder_system import ReminderSystem
        print("\n⏰ Тест системы напоминаний:")
        reminder = ReminderSystem()
        print(f"✅ ReminderSystem создан: {type(reminder)}")
    except ImportError:
        print("ℹ️  Система напоминаний не найдена (это нормально)")
    
    print("\n" + "=" * 50)
    print("🎉 ВСЕ ПРОСТЫЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    
except Exception as e:
    print(f"\n❌ ОШИБКА В ТЕСТАХ: {e}")
    import traceback
    traceback.print_exc()