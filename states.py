import logging

from aiogram.fsm.state import StatesGroup, State

logging.basicConfig(level=logging.INFO)


class FittingStates(StatesGroup):
    waiting_car_photo = State()
    waiting_action_choice = State()
    waiting_part_photo = State()
    waiting_instruction = State()
    waiting_color_choice = State()
    waiting_custom_color = State()
    waiting_retouch_choice = State()
    waiting_sticker_photo = State()
    waiting_sticker_instruction = State()
