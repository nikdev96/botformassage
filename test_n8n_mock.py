#!/usr/bin/env python3
"""
Тестовый скрипт для проверки n8n интеграции с локальным mock webhook сервером

Использование:
1. Запустите mock сервер: python test_n8n_mock.py --server --port 8899
2. В другом терминале: python test_n8n_mock.py --test --port 8899

Или все в одном процессе:
python test_n8n_mock.py --all --port 8899
"""

import argparse
import asyncio
import json
import logging
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from multiprocessing import Process
import os
import sys
import time
from typing import Dict, Any
import urllib.request

# Добавляем текущую директорию в PYTHONPATH для импорта модулей бота
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WebhookHandler(BaseHTTPRequestHandler):
    """HTTP Handler для приема webhook от бота"""
    
    def do_GET(self):
        """Обработка GET запроса (для проверки доступности)"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {'status': 'ok', 'message': 'Mock n8n webhook server is running', 'timestamp': datetime.now().isoformat()}
        self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        """Обработка POST запроса"""
        try:
            # Получаем длину содержимого
            content_length = int(self.headers.get('Content-Length', 0))
            
            # Читаем тело запроса
            post_data = self.rfile.read(content_length)
            webhook_data = json.loads(post_data.decode('utf-8'))
            
            # Логируем полученные данные
            logger.info("📥 Получен webhook от бота:")
            logger.info(f"   Method: {self.command}")
            logger.info(f"   Path: {self.path}")
            logger.info(f"   Headers: {dict(self.headers)}")
            logger.info(f"   Data: {json.dumps(webhook_data, indent=2, ensure_ascii=False)}")
            
            # Проверяем структуру данных
            self._validate_webhook_data(webhook_data)
            
            # Отправляем успешный ответ
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok', 'received_at': datetime.now().isoformat()}).encode())
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки webhook: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def _validate_webhook_data(self, data: Dict[str, Any]):
        """Валидация структуры webhook данных"""
        required_fields = ['event', 'payload']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Отсутствует обязательное поле: {field}")
        
        if data['event'] != 'booking.created':
            logger.warning(f"⚠️  Неожиданный тип события: {data['event']}")
        
        payload = data['payload']
        required_payload_fields = [
            'booking_id', 'source', 'created_at', 'timezone', 'language',
            'user', 'service', 'booking'
        ]
        
        for field in required_payload_fields:
            if field not in payload:
                raise ValueError(f"Отсутствует поле в payload: {field}")
        
        # Проверяем подполя
        if 'telegram_id' not in payload['user']:
            raise ValueError("Отсутствует user.telegram_id")
        
        service_fields = ['key', 'title', 'duration_min', 'price_thb']
        for field in service_fields:
            if field not in payload['service']:
                raise ValueError(f"Отсутствует service.{field}")
        
        booking_fields = ['date_iso', 'date_str', 'time', 'client_name', 'client_phone']
        for field in booking_fields:
            if field not in payload['booking']:
                raise ValueError(f"Отсутствует booking.{field}")
        
        logger.info("✅ Структура webhook данных корректна")

    def log_message(self, format, *args):
        """Отключаем стандартные HTTP логи"""
        pass


def run_mock_server(port: int = 8899):
    """Запуск mock HTTP сервера"""
    logger.info(f"🚀 Запуск mock n8n webhook сервера на порту {port}")
    logger.info(f"📡 URL: http://127.0.0.1:{port}/webhook/test")
    
    server = HTTPServer(('127.0.0.1', port), WebhookHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("🛑 Сервер остановлен")
        server.shutdown()


async def test_n8n_integration(port: int = 8899):
    """Тестирование n8n интеграции"""
    logger.info("🧪 Тестирование n8n интеграции")
    
    # Настраиваем переменные окружения для теста
    webhook_url = f"http://127.0.0.1:{port}/webhook/test"
    os.environ['ENABLE_N8N'] = '1'
    os.environ['N8N_WEBHOOK_URL'] = webhook_url
    
    logger.info(f"📡 Webhook URL: {webhook_url}")
    
    # Импортируем модули после настройки окружения
    from utils import reserve_and_notify, get_lang
    from config import user_languages
    from datetime import datetime, timezone
    
    # Создаем mock объект бота
    class MockBot:
        async def send_message(self, chat_id, text):
            logger.info(f"📤 Mock bot отправляет сообщение в {chat_id}: {text[:100]}...")
            return True
        
        async def get_chat(self, user_id):
            class MockChat:
                username = "test_user"
            return MockChat()
    
    # Подготавливаем тестовые данные
    bot = MockBot()
    test_user_id = 987654321
    user_languages[test_user_id] = "ru"
    
    test_data = {
        "service_key": "thai_traditional",
        "duration": 60,
        "date_str": "15.12.2024", 
        "date_iso": "2024-12-15",
        "time_str": "14:30",
        "client_name": "Тест Пользователь",
        "client_phone": "+66123456789"
    }
    
    logger.info("📋 Тестовые данные подготовлены:")
    logger.info(f"   Пользователь: {test_user_id}")
    logger.info(f"   Услуга: {test_data['service_key']}")
    logger.info(f"   Дата: {test_data['date_str']} ({test_data['date_iso']})")
    logger.info(f"   Время: {test_data['time_str']}")
    logger.info(f"   Клиент: {test_data['client_name']} ({test_data['client_phone']})")
    
    # Проверяем, что mock сервер доступен
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2):
            pass
    except Exception as e:
        logger.error(f"❌ Mock сервер недоступен на порту {port}: {e}")
        logger.error("   Убедитесь, что сервер запущен: python test_n8n_mock.py --server")
        return False
    
    # Выполняем тестовое бронирование
    logger.info("🎯 Запускаем тестовое бронирование...")
    
    try:
        # Тест для manual booking
        result = await reserve_and_notify(bot, test_user_id, test_data, "manual")
        logger.info(f"✅ Manual booking завершено: {result is not None}")
        
        # Даем время на отправку webhook
        await asyncio.sleep(2)
        
        # Тест для AI booking
        result = await reserve_and_notify(bot, test_user_id, test_data, "ai")
        logger.info(f"✅ AI booking завершено: {result is not None}")
        
        # Даем время на отправку webhook
        await asyncio.sleep(2)
        
        logger.info("🎉 Тестирование завершено успешно!")
        logger.info("   Проверьте логи mock сервера на предмет получения webhook'ов")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при тестировании: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Тестирование n8n интеграции')
    parser.add_argument('--server', action='store_true', help='Запуск mock webhook сервера')
    parser.add_argument('--test', action='store_true', help='Запуск теста интеграции')
    parser.add_argument('--all', action='store_true', help='Запуск сервера и теста одновременно')
    parser.add_argument('--port', type=int, default=8899, help='Порт для mock сервера')
    
    args = parser.parse_args()
    
    if args.all:
        # Запускаем сервер в отдельном процессе
        server_process = Process(target=run_mock_server, args=(args.port,))
        server_process.start()
        
        # Даем серверу время на запуск
        time.sleep(2)
        
        # Запускаем тест
        success = asyncio.run(test_n8n_integration(args.port))
        
        # Останавливаем сервер
        server_process.terminate()
        server_process.join()
        
        sys.exit(0 if success else 1)
        
    elif args.server:
        run_mock_server(args.port)
        
    elif args.test:
        success = asyncio.run(test_n8n_integration(args.port))
        sys.exit(0 if success else 1)
        
    else:
        parser.print_help()


if __name__ == '__main__':
    main()