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
from config import BOT_TOKEN, REMINDERS_ENABLED, REMINDER_POLL_INTERVAL_SEC, REMINDER_LEAD_MIN
from handlers import router
from utils import run_offline_tests

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Переменная для хранения in-memory напоминаний (фолбэк)
_in_memory_reminders: dict = {}

async def reminder_worker(bot: Bot):
    """
    Фоновый воркер для отправки напоминаний
    """
    logger.info("🔔 Запуск воркера напоминаний...")
    
    try:
        while True:
            await asyncio.sleep(REMINDER_POLL_INTERVAL_SEC)
            
            if not REMINDERS_ENABLED:
                continue
            
            try:
                # Импортируем внутри цикла чтобы избежать циклических импортов
                from google_sheets import fetch_due_reminders, mark_reminder_sent
                from utils import format_reminder_message, safe_text
                
                # Получаем записи для напоминания
                due_reminders = fetch_due_reminders(REMINDER_LEAD_MIN, REMINDER_POLL_INTERVAL_SEC + 60)
                
                for reminder in due_reminders:
                    try:
                        # Форматируем сообщение напоминания
                        message_text = format_reminder_message(
                            reminder['language'],
                            reminder['service_title'], 
                            reminder['date_str'],
                            reminder['time'],
                            reminder['duration_min']
                        )
                        
                        # Отправляем напоминание
                        await bot.send_message(
                            chat_id=reminder['tg_user_id'],
                            text=message_text,
                            parse_mode=ParseMode.MARKDOWN
                        )
                        
                        # Помечаем как отправленное
                        mark_reminder_sent(reminder['booking_id'])
                        
                        overdue_note = " (просроченное)" if reminder.get('overdue') else ""
                        logger.info(f"✅ Отправлено напоминание для записи {reminder['booking_id']}{overdue_note}")
                        
                        # Небольшая задержка между отправками
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        logger.error(f"❌ Ошибка отправки напоминания для {reminder['booking_id']}: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"❌ Ошибка в цикле напоминаний: {e}")
                continue
                
    except asyncio.CancelledError:
        logger.info("🔔 Воркер напоминаний остановлен")
        raise
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в воркере напоминаний: {e}")

async def schedule_in_memory_reminder(bot: Bot, user_id: int, booking_data: dict, run_at_dt):
    """
    Фолбэк: запланировать напоминание in-memory (не переживет рестарт)
    
    Args:
        bot: Экземпляр бота
        user_id: ID пользователя
        booking_data: Данные записи
        run_at_dt: Когда отправить напоминание
    """
    from datetime import datetime
    from config import TZINFO
    from utils import format_reminder_message, get_lang
    
    try:
        now = datetime.now(TZINFO)
        
        # Если время уже прошло, отправляем сразу
        if run_at_dt <= now:
            logger.info(f"📨 Отправка немедленного напоминания для пользователя {user_id}")
            
            lang = get_lang(user_id)
            message_text = format_reminder_message(
                lang,
                booking_data.get('service_title', 'Услуга'),
                booking_data.get('date_str', 'Дата не указана'),
                booking_data.get('time_str', 'Время не указано'),
                booking_data.get('duration', 60)
            )
            
            await bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Вычисляем задержку
        delay_seconds = (run_at_dt - now).total_seconds()
        logger.info(f"📅 Запланировано in-memory напоминание для пользователя {user_id} через {delay_seconds/60:.1f} минут")
        
        # Ждем до времени отправки
        await asyncio.sleep(delay_seconds)
        
        # Отправляем напоминание
        lang = get_lang(user_id)
        message_text = format_reminder_message(
            lang,
            booking_data.get('service_title', 'Услуга'),
            booking_data.get('date_str', 'Дата не указана'),
            booking_data.get('time_str', 'Время не указано'),
            booking_data.get('duration', 60)
        )
        
        await bot.send_message(
            chat_id=user_id,
            text=message_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"✅ Отправлено in-memory напоминание для пользователя {user_id}")
        
    except asyncio.CancelledError:
        logger.info(f"⏹️ In-memory напоминание отменено для пользователя {user_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка in-memory напоминания для пользователя {user_id}: {e}")

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
    
    # Запускаем воркер напоминаний, если они включены
    reminder_task = None
    if REMINDERS_ENABLED:
        reminder_task = asyncio.create_task(reminder_worker(bot))
        logger.info("🔔 Воркер напоминаний запущен")
    else:
        logger.info("🔕 Напоминания отключены")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        # Останавливаем воркер напоминаний
        if reminder_task and not reminder_task.done():
            reminder_task.cancel()
            try:
                await reminder_task
            except asyncio.CancelledError:
                pass
        
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise