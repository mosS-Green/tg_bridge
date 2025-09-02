# This file can be empty, but it's where we initialize shared resources.
from pyrogram import Client
from config import Config

# Load configuration
app_config = Config()

# Initialize the Pyrogram client instance.
# We use the BOT_TOKEN for client authentication.
pyrogram_client = Client(
    "telegram_bot_session",
    api_id=int(app_config.API_ID),
    api_hash=app_config.API_HASH,
    bot_token=app_config.BOT_TOKEN
)
