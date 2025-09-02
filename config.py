import os
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists
load_dotenv()

class Config:
    """Application configuration settings."""

    # --- Pyrogram Client Settings ---
    API_ID = os.environ.get("API_ID")
    API_HASH = os.environ.get("API_HASH")
    # This bot token is used for both Pyrogram and the uploader/fetcher
    BOT_TOKEN = os.environ.get("BOT_TOKEN")

    # --- Flask App Settings ---
    CHAT_ID = os.environ.get("CHAT_ID")
    # The full URL where your Render app will be live (e.g., https://my-app.onrender.com)
    # This is crucial for generating correct download links.
    APP_BASE_URL = os.environ.get("APP_BASE_URL")
