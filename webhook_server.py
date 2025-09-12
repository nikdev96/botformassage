#!/usr/bin/env python3
"""
Python Webhook Server для записи бронирований в Google Sheets
=====================================================

Получает webhook'и от Telegram бота и записывает их в Google Sheets
с поддержкой идемпотентности (не создает дубли по booking_id).

Запуск: python webhook_server.py
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

from flask import Flask, request, jsonify
import gspread
from google.auth.exceptions import GoogleAuthError
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv(override=True)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
SPREADSHEET_ID = os.getenv("SHEETS_SPREADSHEET_ID", "")
SHEET_NAME = os.getenv("SHEETS_SHEET_NAME", "bookings")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "google_credentials.json")
PORT = int(os.getenv("WEBHOOK_PORT", "8080"))

# Flask приложение
app = Flask(__name__)

# Глобальные переменные для Google Sheets
gc = None
worksheet = None


def init_google_sheets():
    """Инициализация подключения к Google Sheets"""
    global gc, worksheet
    
    try:
        # Проверяем наличие файла с ключами
        if not os.path.exists(CREDENTIALS_FILE):
            logger.error(f"Файл с credentials не найден: {CREDENTIALS_FILE}")
            logger.error("Убедитесь что JSON файл от Google Cloud находится в корне проекта")
            return False
        
        # Подключаемся к Google Sheets API
        gc = gspread.service_account(filename=CREDENTIALS_FILE)
        
        # Открываем таблицу
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        
        # Пытаемся открыть лист, если не существует - создаем
        try:
            worksheet = spreadsheet.worksheet(SHEET_NAME)
        except gspread.WorksheetNotFound:
            logger.info(f"Лист '{SHEET_NAME}' не найден, создаем новый...")
            worksheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows=1000, cols=18)
            
            # Добавляем заголовки
            headers = [
                'booking_id', 'created_at', 'source', 'timezone', 'language',
                'tg_user_id', 'tg_username', 'service_key', 'service_title',
                'duration_min', 'price_thb', 'date_iso', 'date_str', 'time',
                'client_name', 'client_phone', 'raw_json', 'reminder_2h_sent'
            ]
            worksheet.append_row(headers)
            logger.info(f"✅ Создан лист '{SHEET_NAME}' с заголовками")
        
        logger.info(f"✅ Подключение к Google Sheets успешно: {spreadsheet.title}")
        logger.info(f"   Лист: {SHEET_NAME}")
        logger.info(f"   URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
        
        return True
        
    except FileNotFoundError:
        logger.error(f"Файл credentials не найден: {CREDENTIALS_FILE}")
        return False
    except GoogleAuthError as e:
        logger.error(f"Ошибка аутентификации Google: {e}")
        return False
    except gspread.SpreadsheetNotFound:
        logger.error(f"Таблица не найдена или нет доступа: {SPREADSHEET_ID}")
        return False
    except gspread.WorksheetNotFound:
        logger.error(f"Лист '{SHEET_NAME}' не найден в таблице")
        return False
    except Exception as e:
        logger.error(f"Неожиданная ошибка при подключении к Google Sheets: {e}")
        return False


def find_booking_row(booking_id: str) -> Optional[int]:
    """Ищет строку с указанным booking_id, возвращает номер строки или None"""
    try:
        # Получаем все значения из колонки A (booking_id)
        booking_ids = worksheet.col_values(1)  # Колонка A
        
        # Ищем booking_id (начинаем с индекса 1, т.к. 0 - заголовок)
        for i, cell_value in enumerate(booking_ids[1:], start=2):  # Начинаем со строки 2
            if cell_value == booking_id:
                logger.info(f"Найдена существующая запись с booking_id {booking_id} в строке {i}")
                return i
        
        return None
        
    except Exception as e:
        logger.error(f"Ошибка при поиске booking_id {booking_id}: {e}")
        return None


def write_booking_to_sheets(payload: Dict[str, Any]) -> bool:
    """Записывает/обновляет бронирование в Google Sheets"""
    try:
        # Подготавливаем данные для записи
        booking_id = payload.get('booking_id', '')
        created_at = payload.get('created_at', '')
        source = payload.get('source', '')
        timezone = payload.get('timezone', '')
        language = payload.get('language', '')
        
        user = payload.get('user', {})
        tg_user_id = user.get('telegram_id', '')
        tg_username = user.get('username', '')
        
        service = payload.get('service', {})
        service_key = service.get('key', '')
        service_title = service.get('title', '')
        duration_min = service.get('duration_min', '')
        price_thb = service.get('price_thb', '')
        
        booking = payload.get('booking', {})
        date_iso = booking.get('date_iso', '')
        date_str = booking.get('date_str', '')
        time = booking.get('time', '')
        client_name = booking.get('client_name', '')
        client_phone = booking.get('client_phone', '')
        
        raw_json = json.dumps(payload, ensure_ascii=False)
        
        # Формируем строку для записи
        row_data = [
            booking_id, created_at, source, timezone, language,
            tg_user_id, tg_username, service_key, service_title,
            duration_min, price_thb, date_iso, date_str, time,
            client_name, client_phone, raw_json, ''  # reminder_2h_sent пустая
        ]
        
        # Проверяем, есть ли уже такая запись
        existing_row = find_booking_row(booking_id)
        
        if existing_row:
            # Обновляем существующую строку
            worksheet.update(f'A{existing_row}:R{existing_row}', [row_data])
            logger.info(f"✅ Обновлена запись с booking_id: {booking_id} (строка {existing_row})")
            return True
        else:
            # Добавляем новую строку
            worksheet.append_row(row_data)
            logger.info(f"✅ Добавлена новая запись с booking_id: {booking_id}")
            return True
            
    except Exception as e:
        logger.error(f"Ошибка при записи в Google Sheets: {e}")
        return False


@app.route('/webhook/booking', methods=['POST'])
def handle_booking_webhook():
    """Обработчик webhook'ов для бронирований"""
    try:
        # Получаем JSON данные
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
        
        # Логируем получение webhook'а
        event = data.get('event', 'unknown')
        logger.info(f"📥 Получен webhook: event={event}")
        
        # Обрабатываем только booking.created
        if event != 'booking.created':
            logger.warning(f"Игнорируем событие: {event}")
            return jsonify({'status': 'ignored', 'reason': 'event not booking.created'})
        
        # Извлекаем payload
        payload = data.get('payload')
        if not payload:
            return jsonify({'error': 'No payload in webhook'}), 400
        
        # Проверяем, что есть booking_id
        booking_id = payload.get('booking_id')
        if not booking_id:
            return jsonify({'error': 'No booking_id in payload'}), 400
        
        # Записываем в Google Sheets
        success = write_booking_to_sheets(payload)
        
        if success:
            return jsonify({
                'status': 'success',
                'booking_id': booking_id,
                'message': 'Booking saved to Google Sheets'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to save to Google Sheets'
            }), 500
            
    except Exception as e:
        logger.error(f"Ошибка обработки webhook'а: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Проверка состояния сервера"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'google_sheets': 'connected' if worksheet else 'disconnected'
    })


@app.route('/', methods=['GET'])
def index():
    """Главная страница"""
    return jsonify({
        'service': 'Nova Massage Webhook Server',
        'endpoints': {
            'webhook': '/webhook/booking (POST)',
            'health': '/health (GET)'
        },
        'google_sheets_connected': worksheet is not None
    })


if __name__ == '__main__':
    print("🚀 Запуск Nova Massage Webhook Server...")
    print(f"📊 Google Sheets ID: {SPREADSHEET_ID}")
    print(f"📋 Лист: {SHEET_NAME}")
    print(f"🔑 Credentials: {CREDENTIALS_FILE}")
    print(f"🌐 Порт: {PORT}")
    print("-" * 50)
    
    # Инициализируем Google Sheets
    if not init_google_sheets():
        print("❌ Не удалось подключиться к Google Sheets. Выход.")
        exit(1)
    
    # Запускаем Flask сервер
    print(f"🎉 Webhook сервер запущен:")
    print(f"   • http://localhost:{PORT}")
    print(f"   • http://192.168.10.130:{PORT}")
    print(f"📡 Webhook URL: http://192.168.10.130:{PORT}/webhook/booking")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=PORT, debug=False)