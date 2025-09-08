"""
Nova Chaloklum Health Massage Telegram Bot
==========================================
Двуязычный бот (RU/EN) для записи на услуги массажа и спа.

Функционал:
- Выбор языка при старте (/start, /lang)
- 4 категории: Massage, Spa, Waxing, Nails
- Выбор длительности для услуг
- Процесс записи: услуга → длительность → дата → время → имя → телефон → подтверждение
- Уведомления администратора
- Офлайн-режим тестирования (RUN_TESTS=1)

Технологии: aiogram 3, python-dotenv
"""

from __future__ import annotations

# SSL проверка до импорта aiogram
try:
    import ssl
    _SSL_AVAILABLE = True
except ImportError:
    _SSL_AVAILABLE = False
    import sys
    import types
    sys.modules["ssl"] = types.ModuleType("ssl")

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# Импорты локальных модулей
from config import BOT_TOKEN
from handlers import router
from utils import run_offline_tests

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    """Главная функция запуска бота"""
    if os.getenv("RUN_TESTS") == "1":
        run_offline_tests()
        return
    
    if not BOT_TOKEN:
        raise SystemExit("❌ BOT_TOKEN не найден в .env файле")
    
    if not _SSL_AVAILABLE:
        logger.warning("Python собран без SSL - подключение к Telegram невозможно")
        return
    
    logger.info("🚀 Запуск Nova Chaloklum Health Massage Bot...")
    
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    dp = Dispatcher()
    dp.include_router(router)
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise