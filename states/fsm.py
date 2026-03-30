# states/fsm.py
from aiogram.fsm.state import StatesGroup, State

class ChatState(StatesGroup):
    waiting_for_prompt = State()