#!/usr/bin/env python3
"""
Тестирование AI функциональности бота в реальном окружении
"""
import asyncio
import json
from datetime import datetime, date, timedelta
from config import TZINFO, user_languages
from ai_booking import ai_book, ai_extract_booking

# Устанавливаем язык для тестового пользователя
TEST_USER_ID_RU = 99999999  # Русский пользователь  
TEST_USER_ID_EN = 99999998  # Английский пользователь

user_languages[TEST_USER_ID_RU] = "ru"
user_languages[TEST_USER_ID_EN] = "en"

async def test_ai_massage_clarification():
    """Тест дружелюбного уточнения массажа для русских пользователей"""
    print("\n=== ТЕСТ: Дружелюбное уточнение массажа (RU) ===")
    
    # Тест неконкретного запроса массажа на русском
    text = "хочу массаж завтра"
    result, booking_data = await ai_book(TEST_USER_ID_RU, text)
    
    print(f"Запрос пользователя: {text}")
    print(f"Ответ бота: {result}")
    print(f"Данные бронирования: {booking_data}")
    
    # Проверяем, что AI вернул дружелюбное сообщение с уточнением типа массажа
    if "традиционный тайский" in result and "поинтереснее" in result:
        print("✅ ТЕСТ ПРОЙДЕН: Дружелюбное уточнение массажа работает")
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН: Нет дружелюбного уточнения массажа")
    
    return result

async def test_ai_english_error_handling():
    """Тест стандартной обработки ошибок для английских пользователей"""
    print("\n=== ТЕСТ: Стандартная обработка ошибок (EN) ===")
    
    # Тест неконкретного запроса массажа на английском
    text = "I want massage tomorrow"
    result, booking_data = await ai_book(TEST_USER_ID_EN, text)
    
    print(f"User request: {text}")
    print(f"Bot response: {result}")
    print(f"Booking data: {booking_data}")
    
    # Проверяем стандартную обработку ошибок для английских пользователей
    if "service" in result.lower() and booking_data is None:
        print("✅ TEST PASSED: Standard English error handling works")
    else:
        print("❌ TEST FAILED: English error handling not working")
    
    return result

async def test_ai_complete_booking():
    """Тест полной записи через AI"""
    print("\n=== ТЕСТ: Полная запись через AI ===")
    
    tomorrow = (datetime.now(TZINFO).date() + timedelta(days=1)).strftime("%Y-%m-%d")
    text = f"Хочу тайский массаж на {tomorrow} в 14:00, меня зовут Анна, телефон +66123456789, на 60 минут"
    
    result, booking_data = await ai_book(TEST_USER_ID_RU, text)
    
    print(f"Запрос пользователя: {text}")
    print(f"Ответ бота: {result}")
    print(f"Данные бронирования: {booking_data}")
    
    # Проверяем, что AI правильно извлек все данные
    if booking_data and all(key in booking_data for key in ["service_key", "duration", "date_iso", "time_str", "client_name", "client_phone"]):
        print("✅ ТЕСТ ПРОЙДЕН: Полная запись работает")
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН: Полная запись не работает")
    
    return result, booking_data

async def test_ai_nails_service():
    """Тест услуги маникюра с фиксированной длительностью 90 минут"""
    print("\n=== ТЕСТ: Услуга маникюра (Nails) ===")
    
    tomorrow = (datetime.now(TZINFO).date() + timedelta(days=1)).strftime("%Y-%m-%d")
    text = f"Записать на маникюр {tomorrow} в 15:00, Мария, +66987654321"
    
    result, booking_data = await ai_book(TEST_USER_ID_RU, text)
    
    print(f"Запрос пользователя: {text}")
    print(f"Ответ бота: {result}")
    print(f"Данные бронирования: {booking_data}")
    
    # Проверяем, что для nails автоматически установлена длительность 90 минут
    if booking_data and booking_data.get("duration") == 90:
        print("✅ ТЕСТ ПРОЙДЕН: Nails с фиксированной длительностью 90 минут")
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН: Nails длительность некорректна")
    
    return result, booking_data

async def test_ai_missing_fields():
    """Тест обработки неполных данных"""
    print("\n=== ТЕСТ: Неполные данные ===")
    
    text = "хочу тайский массаж завтра"
    result, booking_data = await ai_book(TEST_USER_ID_RU, text)
    
    print(f"Запрос пользователя: {text}")
    print(f"Ответ бота: {result}")
    print(f"Данные бронирования: {booking_data}")
    
    # Проверяем, что бот запрашивает недостающие поля
    if "время" in result or "имя" in result or "телефон" in result:
        print("✅ ТЕСТ ПРОЙДЕН: Запрос недостающих данных работает")
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН: Не запрашивает недостающие данные")
    
    return result

async def main():
    """Запуск всех тестов AI функциональности"""
    print("🤖 ТЕСТИРОВАНИЕ AI ФУНКЦИОНАЛЬНОСТИ БОТА")
    print("=" * 50)
    
    try:
        # Тест 1: Дружелюбное уточнение массажа (RU)
        await test_ai_massage_clarification()
        
        # Тест 2: Стандартная обработка ошибок (EN)  
        await test_ai_english_error_handling()
        
        # Тест 3: Полная запись через AI
        await test_ai_complete_booking()
        
        # Тест 4: Услуга маникюра с фиксированной длительностью
        await test_ai_nails_service()
        
        # Тест 5: Обработка неполных данных
        await test_ai_missing_fields()
        
        print("\n" + "=" * 50)
        print("🏁 ВСЕ ТЕСТЫ AI ФУНКЦИОНАЛЬНОСТИ ЗАВЕРШЕНЫ")
        
    except Exception as e:
        print(f"❌ ОШИБКА ПРИ ТЕСТИРОВАНИИ: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())