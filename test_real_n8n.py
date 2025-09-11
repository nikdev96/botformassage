#!/usr/bin/env python3
"""
Тестирование реальной n8n интеграции с живым webhook
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Добавляем текущую директорию в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_real_n8n():
    """Тестирование реальной n8n интеграции"""
    logger.info("🧪 Тестирование реальной n8n интеграции")
    
    # Проверяем конфигурацию
    from config import ENABLE_N8N, N8N_WEBHOOK_URL
    
    logger.info(f"📋 Конфигурация:")
    logger.info(f"   ENABLE_N8N: {ENABLE_N8N}")
    logger.info(f"   N8N_WEBHOOK_URL: {N8N_WEBHOOK_URL}")
    
    if not ENABLE_N8N:
        logger.error("❌ n8n интеграция отключена (ENABLE_N8N=0)")
        return False
    
    if not N8N_WEBHOOK_URL:
        logger.error("❌ N8N_WEBHOOK_URL не настроен")
        return False
    
    # Импортируем модули
    from utils import reserve_and_notify, user_languages
    
    # Создаем mock объект бота
    class MockBot:
        async def send_message(self, chat_id, text):
            logger.info(f"📤 Mock bot: сообщение в чат {chat_id}")
            logger.info(f"   Текст: {text[:200]}...")
            return True
        
        async def get_chat(self, user_id):
            class MockChat:
                username = "test_user_n8n"
            return MockChat()
    
    # Подготавливаем тестовые данные
    bot = MockBot()
    test_user_id = 111222333
    user_languages[test_user_id] = "ru"
    
    # Тестовые данные для записи
    test_bookings = [
        {
            "service_key": "thai_traditional",
            "duration": 60,
            "date_str": "20.12.2024", 
            "date_iso": "2024-12-20",
            "time_str": "15:00",
            "client_name": "Тест Клиент",
            "client_phone": "+66987654321",
            "source": "manual"
        },
        {
            "service_key": "oil_massage",
            "duration": 90,
            "date_str": "21.12.2024", 
            "date_iso": "2024-12-21",
            "time_str": "16:30",
            "client_name": "AI Test User",
            "client_phone": "+66111222333",
            "source": "ai"
        }
    ]
    
    logger.info("🎯 Запускаем тестовые бронирования...")
    
    success_count = 0
    
    for i, booking in enumerate(test_bookings, 1):
        logger.info(f"\n📋 Тест {i}/{len(test_bookings)}: {booking['source']} booking")
        logger.info(f"   Услуга: {booking['service_key']}")
        logger.info(f"   Дата: {booking['date_str']}")
        logger.info(f"   Время: {booking['time_str']}")
        logger.info(f"   Клиент: {booking['client_name']}")
        
        try:
            source = booking.pop('source')  # Убираем source из данных
            result = await reserve_and_notify(bot, test_user_id, booking, source)
            
            if result:
                logger.info(f"✅ Тест {i} завершен успешно")
                success_count += 1
            else:
                logger.warning(f"⚠️  Тест {i} завершен с предупреждениями")
                
            # Даем время на отправку webhook
            logger.info("⏳ Ждем отправку webhook...")
            await asyncio.sleep(3)
            
        except Exception as e:
            logger.error(f"❌ Ошибка в тесте {i}: {e}")
    
    logger.info(f"\n🎉 Тестирование завершено!")
    logger.info(f"   Успешных тестов: {success_count}/{len(test_bookings)}")
    logger.info(f"   Проверьте логи n8n workflow на предмет получения {success_count} webhook'ов")
    
    return success_count == len(test_bookings)


if __name__ == '__main__':
    success = asyncio.run(test_real_n8n())
    print("\n" + "="*60)
    if success:
        print("🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("📡 Проверьте n8n workflow - должны быть получены webhook'и")
    else:
        print("❌ Некоторые тесты не прошли")
    print("="*60)
    
    sys.exit(0 if success else 1)