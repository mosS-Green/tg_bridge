import asyncio
from quart import Quart
from hypercorn.asyncio import serve
from hypercorn.config import Config as HypercornConfig
from collections import deque
import time

# --- Import Blueprints ---
from frontend.uploader import frontend_bp
from backend.uploader.routes import backend_bp

# --- Import Config and Pyrogram ---
from config import Config
from pyrogram import Client, filters

# ===================================================================
# CREATE SHARED RESOURCES CENTRALLY
# ===================================================================
app_config = Config()

# 1. Create the in-memory cache
file_cache = deque(maxlen=200)

# 2. Create the Pyrogram client instance
pyrogram_client = Client(
    "telegram_bot_session",
    api_id=int(app_config.API_ID),
    api_hash=app_config.API_HASH,
    bot_token=app_config.BOT_TOKEN
)

# 3. Define the Pyrogram message handler
@pyrogram_client.on_message(
    filters.chat(app_config.CHAT_ID) & (filters.document | filters.photo)
)
async def cache_new_file(client, message):
    """Listens for new files and adds them to our in-memory cache."""
    media = message.document or message.photo
    if media:
        file_details = {
            "name": getattr(media, 'file_name', f"photo_{message.id}.jpg"),
            "file_id": media.file_id,
            "size": media.file_size,
            "mime": getattr(media, 'mime_type', 'image/jpeg')
        }
        file_cache.appendleft((time.time(), file_details))
        print(f"Cached new file: {file_details['name']}")

# ===================================================================

# Create the Quart App
app = Quart(name)

# Register the blueprints
app.register_blueprint(frontend_bp)
app.register_blueprint(backend_bp)

# Pass shared resources to the app context so blueprints can access them
app.config['PYROGRAM_CLIENT'] = pyrogram_client
app.config['FILE_CACHE'] = file_cache
app.config['APP_CONFIG'] = app_config


async def main():
    """Main function to configure and run the ASGI server."""
    print("Starting Pyrogram client...")
    await pyrogram_client.start()
    port = int(os.environ.get("PORT", 8080))
    hypercorn_config = HypercornConfig()
    hypercorn_config.bind = [f"0.0.0.0:{port}"]
    await serve(app, hypercorn_config)
    await pyrogram_client.stop()
    print("Pyrogram client stopped.")

if name == "__main__":
    try:
        import os # Make sure os is imported for port logic
        asyncio.run(main(), loop_factory=lambda _: pyrogram_client.loop)
    except KeyboardInterrupt:
        print("Shutting down...")
