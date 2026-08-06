import asyncio
import logging
import os
import sqlite3
import random
import string
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
BOT_USERNAME = os.getenv("BOT_USERNAME", "Ever_XXbot")
REFERRAL_REWARD = 1000
MIN_PAYOUT = 2000

COUNTRIES = [
    "🌍 Worldwide",
    "🇳🇬 Nigeria", "🇬🇭 Ghana", "🇿🇦 South Africa", "🇰🇪 Kenya", "🇪🇬 Egypt", "🇪🇹 Ethiopia",
    "🇺🇸 USA", "🇬🇧 UK", "🇨🇦 Canada", "🇦🇺 Australia", "🇩🇪 Germany", "🇫🇷 France",
    "🇮🇳 India", "🇵🇰 Pakistan", "🇧🇩 Bangladesh", "🇵🇭 Philippines", "🇮🇩 Indonesia",
    "🇧🇷 Brazil", "🇲🇽 Mexico", "🇹🇷 Turkey", "🇦🇪 UAE", "🇸🇦 Saudi Arabia", "🇷🇺 Russia",
    "🇺🇦 Ukraine", "🇮🇹 Italy", "🇪🇸 Spain", "🇳🇱 Netherlands", "🇸🇪 Sweden", "🇳🇴 Norway"
]
# ... rest of file is in the download - 464 lines total
