from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from aiogram.exceptions import TelegramAPIError

from config import config
from db import models

router = Router()

BOT_USERNAME = "AvtoMerkaBot"


def _main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎨 Начать примерку", callback_data="fit:start"),
                InlineKeyboardButton(text="📋 Как это работает?", callback_data="help:how"),
            ],
            [
                InlineKeyboardButton(text="💰 Мой баланс", callback_data="balance:show"),
                InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="topup:soon"),
            ],
            [
                InlineKeyboardButton(text="👥 Пригласить друга", callback_data="ref:info"),
            ],
        ]
    )


async def _safe_edit(callback: CallbackQuery, text: str, **kwargs) -> None:
    try:
        await callback.answer()
    except TelegramAPIError:
        pass
    try:
        await callback.message.edit_text(text, **kwargs)
    except TelegramAPIError:
        await callback.message.answer(text, **kwargs)


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandStart) -> None:
    user = message.from_user
    await models.get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )

    args = command.args
    if args and args.startswith("ref_"):
        try:
            inviter_id = int(args.removeprefix("ref_"))
            processed = await models.process_referral(inviter_id, user.id)
            if processed:
                await message.answer(
                    f"🎉 Ты был приглашён другом! Оба получили "
                    f"<b>+{models.BONUS_PER_REFERRAL}</b> бесплатную генерацию!",
                    parse_mode="HTML",
                )
        except (ValueError, Exception):
            pass

    await message.answer(
        f"🚗 Привет, {user.first_name}!\n\n"
        "Я — <b>AvtoMerkaBot</b>, AI-помощник для примерки аксессуаров на твою машину.\n\n"
        "🎯 <b>Что я умею:</b>\n"
        "• Примерять диски, спойлеры, обвесы\n"
        "• Менять цвет кузова\n"
        "• И многое другое!\n\n"
        f"🎁 <b>Первые {config.free_generations} генерации — бесплатно!</b>\n"
        f"💰 Стоимость генерации: <b>{config.gen_cost // 100}₽</b>",
        reply_markup=_main_menu(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "help:how")
async def cb_help_how(callback: CallbackQuery) -> None:
    await _safe_edit(
        callback,
        "📋 <b>Как пользоваться:</b>\n\n"
        "1️⃣ Нажми «Начать примерку»\n"
        "2️⃣ Отправь фото своей машины\n"
        "3️⃣ Выбери: сменить цвет, примерить деталь или описать текстом\n"
        "4️⃣ Получи результат!\n\n"
        f"💰 Стоимость: <b>{config.gen_cost // 100}₽</b> за генерацию\n"
        f"🎁 Первые <b>{config.free_generations}</b> — бесплатно",
        reply_markup=_main_menu(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "ref:info")
async def cb_ref_info(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    ref_count = await models.get_referral_count(user_id)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
    await _safe_edit(
        callback,
        "👥 <b>Пригласи друга — получи бонус!</b>\n\n"
        f"Твоя реферальная ссылка:\n<code>{ref_link}</code>\n\n"
        f"Приглашено друзей: <b>{ref_count}</b>\n\n"
        "🎁 За каждого приглашённого друга:\n"
        f"• Ты получаешь <b>+{models.BONUS_PER_REFERRAL}</b> бесплатную генерацию\n"
        f"• Друг тоже получает <b>+{models.BONUS_PER_REFERRAL}</b> бесплатную генерацию",
        reply_markup=_main_menu(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "balance:show")
async def cb_balance_show(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
    except TelegramAPIError:
        pass
    stats = await models.get_user_stats(callback.from_user.id)
    paid_gens = await models.get_paid_gen_count(callback.from_user.id)
    ref_count = await models.get_referral_count(callback.from_user.id)
    text = (
        f"💰 <b>Мой баланс</b>\n\n"
        f"Баланс: <b>{stats.get('balance', 0) // 100}₽</b>\n"
        f"Бесплатных примерок: <b>{stats.get('free_gen_left', 0)}</b>\n"
        f"Платных примерок: <b>{paid_gens}</b>\n"
        f"Приглашено друзей: <b>{ref_count}</b>"
    )
    try:
        await callback.message.edit_text(text, reply_markup=_main_menu(), parse_mode="HTML")
    except TelegramAPIError:
        await callback.message.answer(text, reply_markup=_main_menu(), parse_mode="HTML")


@router.message(Command("balance"))
async def cmd_balance(message: Message) -> None:
    stats = await models.get_user_stats(message.from_user.id)
    paid_gens = await models.get_paid_gen_count(message.from_user.id)
    ref_count = await models.get_referral_count(message.from_user.id)
    await message.answer(
        f"💰 <b>Мой баланс</b>\n\n"
        f"Баланс: <b>{stats.get('balance', 0) // 100}₽</b>\n"
        f"Бесплатных примерок: <b>{stats.get('free_gen_left', 0)}</b>\n"
        f"Платных примерок: <b>{paid_gens}</b>\n"
        f"Приглашено друзей: <b>{ref_count}</b>",
        reply_markup=_main_menu(),
        parse_mode="HTML",
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message) -> None:
    await message.answer("Действие отменено.", reply_markup=_main_menu())


@router.callback_query(F.data == "topup:soon")
async def cb_topup_soon(callback: CallbackQuery) -> None:
    await _safe_edit(
        callback,
        "💳 <b>Пополнение баланса</b>\n\n"
        "Скоро здесь можно будет пополнить баланс прямо в Telegram!\n"
        "Следи за обновлениями.",
        reply_markup=_main_menu(),
        parse_mode="HTML",
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    stats = await models.get_global_stats()
    await message.answer(
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Пользователей: <b>{stats['total_users']}</b>\n"
        f"🆕 Сегодня: <b>{stats['new_today']}</b>\n"
        f"🎨 Генераций: <b>{stats['total_gens']}</b>\n"
        f"📈 Сегодня: <b>{stats['gens_today']}</b>\n"
        f"💰 Выручка: <b>{stats['total_revenue'] // 100}₽</b>\n"
        f"💸 Расход на API: <b>{stats['total_cost'] // 100}₽</b>",
        parse_mode="HTML",
    )
