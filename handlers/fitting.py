import base64
import logging
import tempfile

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.exceptions import TelegramAPIError

from handlers.common import _main_menu
from states import FittingStates
from services import image_gen
from config import config
from db import models

router = Router()

logger = logging.getLogger(__name__)


COLORS = [
    ("⚫ Чёрный", "чёрный"),
    ("⚪ Белый", "белый"),
    ("🔴 Красный", "красный"),
    ("🔵 Синий", "синий"),
    ("🩶 Серый", "серый"),
    ("🪙 Серебристый", "серебристый"),
    ("🟤 Коричневый", "коричневый"),
]

RETOUCH_TYPES = [
    ("🚗 Экстерьер (убрать грязь/царапины)", "retouch:exterior"),
    ("🛋️ Интерьер (убрать пыль/загрязнения)", "retouch:interior"),
    ("✨ Полная ретушь (подготовка к продаже)", "retouch:full"),
]


async def _safe_edit(callback: CallbackQuery, text: str, **kwargs) -> None:
    try:
        await callback.answer()
    except TelegramAPIError:
        pass
    try:
        await callback.message.edit_text(text, **kwargs)
    except TelegramAPIError:
        await callback.message.answer(text, **kwargs)


def _nav_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Начать заново", callback_data="fit:start"),
                InlineKeyboardButton(text="🏠 Главное меню", callback_data="back:menu"),
            ],
        ]
    )


def _action_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔧 Примерить деталь/аксессуар", callback_data="action:detail")],
            [InlineKeyboardButton(text="🖌️ Поменять цвет", callback_data="action:color")],
            [InlineKeyboardButton(text="✍️ Описать изменение текстом", callback_data="action:text")],
            [InlineKeyboardButton(text="✨ Ретушь / подготовка к продаже", callback_data="action:retouch")],
            [InlineKeyboardButton(text="🏷️ Наклейка / изображение на кузов", callback_data="action:sticker")],
            [InlineKeyboardButton(text="🔢 Убрать номера", callback_data="action:plates")],
            [
                InlineKeyboardButton(text="🔄 Начать заново", callback_data="fit:start"),
                InlineKeyboardButton(text="🏠 Главное меню", callback_data="back:menu"),
            ],
        ]
    )


def _retouch_kb() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=label, callback_data=data)] for label, data in RETOUCH_TYPES]
    rows.append([
        InlineKeyboardButton(text="🔄 Начать заново", callback_data="fit:start"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="back:menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _color_kb() -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(COLORS), 2):
        row = [
            InlineKeyboardButton(text=label, callback_data=f"color:{code}")
            for label, code in COLORS[i:i + 2]
        ]
        rows.append(row)
    rows.append([
        InlineKeyboardButton(text="🎨 Другой цвет", callback_data="color:custom"),
    ])
    rows.append([
        InlineKeyboardButton(text="🔄 Начать заново", callback_data="fit:start"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="back:menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _result_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Начать заново", callback_data="fit:start"),
                InlineKeyboardButton(text="🏠 Главное меню", callback_data="back:menu"),
            ],
        ]
    )


@router.message(Command("fit"))
async def cmd_fit(message: Message, state: FSMContext) -> None:
    await state.set_state(FittingStates.waiting_car_photo)
    await message.answer("📸 Отправь фото своей машины, чтобы я понял, что примерять.", reply_markup=_nav_kb())


@router.callback_query(F.data == "fit:start")
async def cb_fit_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FittingStates.waiting_car_photo)
    await _safe_edit(callback, "📸 Отправь фото своей машины, чтобы я понял, что примерять.", reply_markup=_nav_kb())


@router.callback_query(F.data == "back:menu")
async def cb_back_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _safe_edit(callback, "Выбери действие:", reply_markup=_main_menu())


@router.message(FittingStates.waiting_car_photo, F.photo)
async def get_car_photo(message: Message, state: FSMContext) -> None:
    photo = message.photo[-1]
    await state.update_data(car_photo_file_id=photo.file_id)
    await state.set_state(FittingStates.waiting_action_choice)
    await message.answer(
        "✅ Получил фото машины!\n\nЧто нужно сделать?",
        reply_markup=_action_kb(),
    )


@router.message(FittingStates.waiting_car_photo)
async def ask_car_photo_again(message: Message) -> None:
    await message.answer("Мне нужно именно фото машины. Отправь изображение 🚘", reply_markup=_nav_kb())


@router.callback_query(FittingStates.waiting_action_choice, F.data == "action:detail")
async def cb_action_detail(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FittingStates.waiting_part_photo)
    await _safe_edit(
        callback,
        "📸 Отправь фото детали/аксессуара, которую нужно примерить.",
        reply_markup=_nav_kb(),
    )


@router.callback_query(FittingStates.waiting_action_choice, F.data == "action:color")
async def cb_action_color(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FittingStates.waiting_color_choice)
    await _safe_edit(
        callback,
        "🎨 Выбери цвет кузова или напиши свой:",
        reply_markup=_color_kb(),
    )


@router.callback_query(FittingStates.waiting_action_choice, F.data == "action:text")
async def cb_action_text(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FittingStates.waiting_instruction)
    await _safe_edit(
        callback,
        "✍️ Напиши текстом, что нужно сделать с машиной.\n\n"
        "Например:\n"
        "• «Добавь спойлер на багажник»\n"
        "• «Поставь пороги и обвес»\n"
        "• «Сделай тюнинг фар»\n"
        "• «Добавь аэродинамический обвес»\n\n"
        "Нейросеть постарается предложить лучший вариант.",
        reply_markup=_nav_kb(),
    )


@router.callback_query(FittingStates.waiting_action_choice, F.data == "action:retouch")
async def cb_action_retouch(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FittingStates.waiting_retouch_choice)
    await _safe_edit(
        callback,
        "✨ <b>Ретушь / подготовка к продаже</b>\n\n"
        "Выбери тип обработки:",
        reply_markup=_retouch_kb(),
        parse_mode="HTML",
    )


@router.callback_query(FittingStates.waiting_action_choice, F.data == "action:sticker")
async def cb_action_sticker(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FittingStates.waiting_sticker_photo)
    await _safe_edit(
        callback,
        "🏷️ <b>Наклейка / изображение на кузов</b>\n\n"
        "📸 Отправь изображение наклейки или рисунка, "
        "который хочешь нанести на машину.",
        reply_markup=_nav_kb(),
        parse_mode="HTML",
    )


PLATE_REMOVAL_PROMPT = (
    "Remove or blur the license plates from this car photo. "
    "Replace the license plate area with a clean, blank plate or smooth surface "
    "that matches the surrounding area naturally. "
    "Keep the car's EXACT original model, color, angle, lighting, background, "
    "and all other details unchanged. Only modify the license plate area."
)


@router.callback_query(FittingStates.waiting_action_choice, F.data == "action:plates")
async def cb_action_plates(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    await _generate_and_send(
        callback.message, state, data,
        instruction=PLATE_REMOVAL_PROMPT,
        user_id=callback.from_user.id,
        action_type_override="plate_removal",
    )


RETOUCH_PROMPTS = {
    "retouch:exterior": (
        "Perform professional car exterior retouching on this photo. "
        "Remove all dirt, dust, mud, minor scratches, and scuff marks. "
        "Restore the paint to a clean, polished condition. "
        "Fix faded or oxidized areas. "
        "Keep the car's original appearance, color, and details exactly as they are. "
        "Do NOT change the car model, color, angle, background, or any modifications. "
        "Only clean and restore the existing surface."
    ),
    "retouch:interior": (
        "Perform professional car interior retouching on this photo. "
        "Remove all dust, stains, and visible wear from seats, dashboard, and surfaces. "
        "Clean up the interior to look fresh and well-maintained. "
        "Keep all original materials, colors, and textures. "
        "Do NOT change any components or add new elements."
    ),
    "retouch:full": (
        "Perform full professional car retouching for sale preparation on this photo. "
        "Remove ALL dirt, dust, mud, rust spots, scratches, scuff marks, and stains. "
        "Restore paint to showroom condition — polished, glossy, clean. "
        "Fix any faded, oxidized, or chipped paint areas. "
        "Clean all surfaces inside and out. "
        "The car must look like it just came from a professional detailer. "
        "Keep the car's EXACT original model, color, angle, lighting, and background. "
        "Do NOT generate a new car or change anything about it — only restore the existing surfaces."
    ),
}


@router.callback_query(FittingStates.waiting_retouch_choice, F.data.startswith("retouch:"))
async def cb_retouch_pick(callback: CallbackQuery, state: FSMContext) -> None:
    retouch_type = callback.data
    data = await state.get_data()
    await state.clear()
    prompt = RETOUCH_PROMPTS.get(retouch_type, RETOUCH_PROMPTS["retouch:full"])
    await _generate_and_send(
        callback.message, state, data,
        instruction=prompt,
        user_id=callback.from_user.id,
        action_type_override="retouch",
    )


@router.message(FittingStates.waiting_part_photo, F.photo)
async def get_part_photo(message: Message, state: FSMContext) -> None:
    photo = message.photo[-1]
    await state.update_data(part_photo_file_id=photo.file_id)
    await state.set_state(FittingStates.waiting_instruction)
    await message.answer(
        "👍 Отлично! Теперь напиши текстом, что именно сделать "
        "(например: «поставь эти диски на передние колёса»).",
        reply_markup=_nav_kb(),
    )


@router.message(FittingStates.waiting_part_photo)
async def ask_part_photo_again(message: Message) -> None:
    await message.answer("Мне нужно фото детали. Отправь изображение 🔧", reply_markup=_nav_kb())


@router.message(FittingStates.waiting_instruction, F.text)
async def get_instruction(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    await _generate_and_send(message, state, data, instruction=message.text)


@router.callback_query(FittingStates.waiting_color_choice, F.data.startswith("color:"))
async def cb_color_pick(callback: CallbackQuery, state: FSMContext) -> None:
    color_code = callback.data.removeprefix("color:")

    if color_code == "custom":
        await state.set_state(FittingStates.waiting_custom_color)
        await _safe_edit(
            callback,
            "✍️ Напиши нужный цвет (например: «металлик бордо», «матовый зелёный»).",
            reply_markup=_nav_kb(),
        )
        return

    try:
        await callback.answer()
    except TelegramAPIError:
        pass
    data = await state.get_data()
    await state.clear()
    await _generate_and_send(callback.message, state, data, instruction=f"Покрась кузов в {color_code} цвет", user_id=callback.from_user.id)


@router.message(FittingStates.waiting_custom_color, F.text)
async def get_custom_color(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    color = message.text.strip()
    await _generate_and_send(message, state, data, instruction=f"Покрась кузов в цвет «{color}»")


@router.message(FittingStates.waiting_sticker_photo, F.photo)
async def get_sticker_photo(message: Message, state: FSMContext) -> None:
    photo = message.photo[-1]
    await state.update_data(part_photo_file_id=photo.file_id)
    await state.set_state(FittingStates.waiting_sticker_instruction)
    await message.answer(
        "👍 Получил изображение!\n\n"
        "Напиши, куда нанести наклейку "
        "(например: «на капот по центру», «на дверь водителя», «на багажник»).\n\n"
        "Или отправь «без изменений» — нейросеть сама решит лучшее расположение.",
        reply_markup=_nav_kb(),
    )


@router.message(FittingStates.waiting_sticker_photo)
async def ask_sticker_photo_again(message: Message) -> None:
    await message.answer("Мне нужно фото наклейки. Отправь изображение 🏷️", reply_markup=_nav_kb())


@router.message(FittingStates.waiting_sticker_instruction, F.text)
async def get_sticker_instruction(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    placement = message.text.strip()
    if placement.lower() in ("без изменений", "пропустить", "нет"):
        placement = "Apply the sticker/image to the car in the most visually appealing position."
    else:
        placement = f"Place the sticker/image on: {placement}"
    await state.clear()
    instruction = (
        "Take the SECOND image (the sticker/decals/raster image) and apply it onto "
        "the car from the FIRST image. "
        "The sticker/image should look realistic — match the car's surface curvature, "
        "lighting, shadows, and perspective. "
        f"Placement: {placement} "
        "Keep the car's EXACT original model, color, angle, lighting, and background. "
        "Only add the sticker/image, nothing else."
    )
    await _generate_and_send(message, state, data, instruction=instruction, action_type_override="sticker")


async def _generate_and_send(
    message: Message,
    state: FSMContext,
    data: dict,
    instruction: str,
    user_id: int | None = None,
    action_type_override: str | None = None,
) -> None:
    if user_id is None:
        user_id = message.from_user.id

    used_free = await models.use_free_gen(user_id)
    if not used_free:
        balance = await models.get_balance(user_id)
        if balance < config.gen_cost:
            needed = (config.gen_cost - balance) // 100
            await message.answer(
                f"😔 Недостаточно средств.\n"
                f"Баланс: <b>{balance // 100}₽</b>, нужно: <b>{config.gen_cost // 100}₽</b>\n"
                f"Пополни баланс на <b>{needed}₽</b> или больше.",
                reply_markup=_result_kb(),
                parse_mode="HTML",
            )
            return
        await models.deduct_balance(user_id, config.gen_cost, instruction)

    await message.answer("⏳ Генерирую результат, подожди немного…")

    action_type = action_type_override or (
        "color_change" if "цвет" in instruction.lower() or "color" in instruction.lower() or "paint" in instruction.lower()
        else "retouch" if "retouch" in instruction.lower() or "clean" in instruction.lower()
        else "sticker" if "sticker" in instruction.lower() or "apply" in instruction.lower()
        else "part_fitting"
    )
    result_ok = False

    try:
        car_bytes = await _download(message.bot, data["car_photo_file_id"])
        part_bytes = None
        if data.get("part_photo_file_id"):
            part_bytes = await _download(message.bot, data["part_photo_file_id"])

        result_url = await image_gen.generate_fitting(
            car_image=car_bytes,
            part_image=part_bytes,
            part_description=data.get("part_desc", ""),
            instruction=instruction,
        )
        result_ok = result_url is not None
    except Exception as exc:  # noqa: BLE001
        logger.exception("Generation failed")
        if not used_free:
            await models.add_balance(user_id, config.gen_cost, "refund-failed")
        await message.answer(
            f"😕 Не удалось сгенерировать результат: {exc}\nПопробуй ещё раз позже.",
            reply_markup=_result_kb(),
        )
        return
    finally:
        cost = 0 if used_free else config.gen_cost
        await models.record_generation(user_id, action_type, image_gen.MODEL, cost, result_ok)

    if not result_url:
        if not used_free:
            await models.add_balance(user_id, config.gen_cost, "refund-empty")
        await message.answer(
            "😕 Не удалось получить изображение. Попробуй ещё раз.",
            reply_markup=_result_kb(),
        )
        return

    if result_url.startswith("data:image"):
        try:
            header, b64 = result_url.split(",", 1)
            raw = base64.b64decode(b64)
            suffix = ".png" if "png" in header else ".jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(raw)
                tmp_path = tmp.name
            await message.answer_photo(
                photo=FSInputFile(tmp_path),
                caption="🎉 Готово! Вот твоя примерка.",
                reply_markup=_result_kb(),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to send generated image")
            await message.answer(
                f"😕 Получил изображение, но не смог отправить: {exc}",
                reply_markup=_result_kb(),
            )
    else:
        await message.answer_photo(
            photo=result_url,
            caption="🎉 Готово! Вот твоя примерка.",
            reply_markup=_result_kb(),
        )


async def _download(bot, file_id: str) -> bytes:
    file = await bot.get_file(file_id)
    buf = await bot.download_file(file.file_path)
    return buf.read()
