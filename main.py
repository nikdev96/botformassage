"""
Aiogram Booking Bot — минимальный MVP для массажного салона
-----------------------------------------------------------
Функции:
- Главное меню: категории → список услуг → описание → «Записаться»
- Запись: дата/время → имя → телефон → подтверждение
- Уведомление администратора/мастера (ADMIN_CHAT_ID)
- Каталог услуг в коде (SERVICE_CATALOG)

Особенности:
- .env для BOT_TOKEN, ADMIN_CHAT_ID, TZ
- Офлайн-тесты (RUN_TESTS=1 python main.py)
- Заглушка ssl (если Python собран без OpenSSL)

"""

from __future__ import annotations

# SSL shim (чтобы не падало при отсутствии модуля ssl)
_SSL_AVAILABLE = True
try:
    import ssl  # noqa: F401
except Exception:
    _SSL_AVAILABLE = False
    import sys, types
    sys.modules["ssl"] = types.ModuleType("ssl")

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# -----------------------------
# Конфигурация
# -----------------------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
TZ = os.getenv("TZ", "Asia/Bangkok")

if not BOT_TOKEN:
    raise SystemExit("[ENV] BOT_TOKEN is empty. Add it to .env")

logging.basicConfig(level=logging.INFO)

# -----------------------------
# Модель услуги и каталог
# -----------------------------
@dataclass
class Service:
    key: str
    title: str
    duration_min: int
    price: int
    currency: str
    description: str


SERVICE_CATALOG: Dict[str, List[Service]] = {
    "Массаж": [
        Service(
            key="thai_basic",
            title="Тайский массаж (1 ч)",
            duration_min=60,
            price=700,
            currency="THB",
            description=(
                "Техника тайского массажа — элементы пассивной йоги, работа по точкам.\n"
                "Растяжка, выкручивания, локти и стопы.\n\n"
                "Стоимость: 700 THB / 60 мин."
            ),
        ),
        Service(
            key="anti_cellulite",
            title="Антицеллюлитный массаж (1 ч)",
            duration_min=60,
            price=900,
            currency="THB",
            description="Интенсивная проработка проблемных зон.\n\nСтоимость: 900 THB / 60 мин.",
        ),
        Service(
            key="stones",
            title="Массаж горячими камнями (1 ч)",
            duration_min=60,
            price=1000,
            currency="THB",
            description="Глубокое расслабление и прогрев мышц.\n\nСтоимость: 1000 THB / 60 мин.",
        ),
    ],
    "Косметология": [],
    "Маникюр/Педикюр": [],
    "Акции": [],
}

CATEGORIES = list(SERVICE_CATALOG.keys())

# -----------------------------
# Состояния записи
# -----------------------------
class Booking(StatesGroup):
    choosing_service = State()
    ask_date = State()
    ask_time = State()
    ask_name = State()
    ask_phone = State()
    confirm = State()


# -----------------------------
# Клавиатуры и утилиты
# -----------------------------
main_menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=c)] for c in CATEGORIES],
    resize_keyboard=True,
    input_field_placeholder="Выберите раздел",
)


def services_kb(category: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in SERVICE_CATALOG.get(category, []):
        builder.button(text=s.title, callback_data=f"svc:{s.key}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="Назад", callback_data="nav:back"))
    return builder.as_markup()


def service_card_kb(service_key: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Записаться", callback_data=f"book:{service_key}")
    builder.button(text="Назад", callback_data="nav:to_list")
    builder.adjust(1)
    return builder.as_markup()


def get_service_by_key(service_key: str) -> Optional[Service]:
    for lst in SERVICE_CATALOG.values():
        for s in lst:
            if s.key == service_key:
                return s
    return None


def format_confirm_message(svc: Service, data: dict) -> str:
    return (
        "Проверьте, всё ли верно:\n\n"
        f"Услуга: *{svc.title}*\n"
        f"Дата: *{data['date_str']}*\n"
        f"Время: *{data['time_str']}*\n"
        f"Имя: *{data['client_name']}*\n"
        f"Телефон: *{data['client_phone']}*\n\n"
        "Подтвердить запись?"
    )


# -----------------------------
# Роутер бота
# -----------------------------
router = Router()


@router.message(CommandStart())
async def on_start(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(
        "Добро пожаловать в *Massage*! Выберите категорию ниже:",
        reply_markup=main_menu,
        parse_mode=ParseMode.MARKDOWN,
    )


@router.message(F.text.in_(CATEGORIES))
async def on_choose_category(m: Message, state: FSMContext):
    category = m.text
    await state.clear()
    if not SERVICE_CATALOG.get(category):
        await m.answer("Раздел в разработке. Выберите другой.")
        return
    await state.update_data(category=category)
    await m.answer(
        f"Вы выбрали раздел: *{category}*", parse_mode=ParseMode.MARKDOWN
    )
    await m.answer("Список услуг:", reply_markup=services_kb(category))
    await state.set_state(Booking.choosing_service)


@router.callback_query(F.data.startswith("svc:"))
async def on_service_card(c: CallbackQuery, state: FSMContext):
    service_key = c.data.split(":", 1)[1]
    svc = get_service_by_key(service_key)
    if not svc:
        await c.answer("Услуга не найдена", show_alert=True)
        return
    await state.update_data(service_key=service_key)
    text = f"*{svc.title}*\n\n{svc.description}"
    await c.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=service_card_kb(service_key))
    await c.answer()


@router.callback_query(F.data == "nav:to_list")
async def on_back_to_list(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    category = data.get("category", CATEGORIES[0])
    await c.message.edit_text("Выберите услугу:", reply_markup=services_kb(category))
    await c.answer()


@router.callback_query(F.data == "nav:back")
async def on_back(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.answer("Выберите категорию:", reply_markup=main_menu)
    await c.answer()


@router.callback_query(F.data.startswith("book:"))
async def on_book_start(c: CallbackQuery, state: FSMContext):
    service_key = c.data.split(":", 1)[1]
    await state.update_data(service_key=service_key)
    await state.set_state(Booking.ask_date)
    await c.message.answer("Введите дату в формате ДД.ММ.ГГГГ (например, 21.09.2025).")
    await c.answer()


@router.message(Booking.ask_date)
async def on_book_date(m: Message, state: FSMContext):
    try:
        dt = datetime.strptime(m.text.strip(), "%d.%m.%Y")
    except Exception:
        await m.answer("Неверный формат. Введите ДД.ММ.ГГГГ.")
        return
    await state.update_data(date_str=dt.strftime("%d.%m.%Y"))
    await state.set_state(Booking.ask_time)
    await m.answer("Теперь укажите время (например, 15:00)")


@router.message(Booking.ask_time)
async def on_book_time(m: Message, state: FSMContext):
    try:
        datetime.strptime(m.text.strip(), "%H:%M")
    except Exception:
        await m.answer("Неверный формат времени. Введите HH:MM.")
        return
    await state.update_data(time_str=m.text.strip())
    await state.set_state(Booking.ask_name)
    await m.answer("Как вас зовут?")


@router.message(Booking.ask_name)
async def on_book_name(m: Message, state: FSMContext):
    await state.update_data(client_name=m.text.strip())
    await state.set_state(Booking.ask_phone)
    await m.answer("Укажите телефон (+66..., +7...)")


@router.message(Booking.ask_phone)
async def on_book_phone(m: Message, state: FSMContext):
    await state.update_data(client_phone=m.text.strip())
    data = await state.get_data()
    svc = get_service_by_key(data["service_key"])
    await state.set_state(Booking.confirm)
    await m.answer(
        format_confirm_message(svc, data),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm:yes")],
                [InlineKeyboardButton(text="✏️ Изменить", callback_data="confirm:edit")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="confirm:cancel")],
            ]
        ),
    )


@router.callback_query(Booking.confirm, F.data.startswith("confirm:"))
async def on_confirm(c: CallbackQuery, state: FSMContext, bot: Bot):
    action = c.data.split(":", 1)[1]
    if action == "cancel":
        await state.clear()
        await c.message.edit_text("Запись отменена")
        await c.answer()
        return
    if action == "edit":
        await state.set_state(Booking.ask_date)
        await c.message.answer("Введите дату заново (ДД.ММ.ГГГГ)")
        await c.answer()
        return

    data = await state.get_data()
    svc = get_service_by_key(data["service_key"])
    msg_admin = (
        f"🆕 *Новая запись*\n"
        f"Услуга: {svc.title}\n"
        f"Дата/время: {data['date_str']} {data['time_str']} ({TZ})\n"
        f"Клиент: {data['client_name']}\n"
        f"Телефон: {data['client_phone']}\n"
        f"UserID: {c.from_user.id} (@{c.from_user.username or '—'})"
    )
    if ADMIN_CHAT_ID:
        await bot.send_message(ADMIN_CHAT_ID, msg_admin, parse_mode=ParseMode.MARKDOWN)

    await c.message.edit_text(
        f"Готово! Ваша заявка получена.\n\n*{svc.title}* — {svc.price} {svc.currency}\n"
        f"Дата: {data['date_str']}\nВремя: {data['time_str']} ({TZ})",
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.clear()
    await c.answer()


# -----------------------------
# Офлайн-тесты
# -----------------------------
def run_tests():
    kb = services_kb("Массаж")
    assert any(b.text == "Тайский массаж (1 ч)" for row in kb.inline_keyboard for b in row if isinstance(b, InlineKeyboardButton))
    print("ALL TESTS PASSED")


# -----------------------------
# Запуск
# -----------------------------
async def main():
    if os.getenv("RUN_TESTS") == "1":
        run_tests()
        return
    if not _SSL_AVAILABLE:
        print("[WARN] Python без ssl — бот не сможет подключиться к Telegram.")
        return

    bot = Bot(BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped")