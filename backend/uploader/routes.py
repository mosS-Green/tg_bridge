import time
import requests
import asyncio
from urllib.parse import quote, unquote
from mimetypes import guess_type
from quart import (
    Blueprint,
    request,
    jsonify,
    Response,
    stream_with_context,
)
from pyrogram.errors import FloodWait

# Import the shared pyrogram client instance
from .. import app_config, pyrogram_client

# Create a Blueprint for the backend API
backend_bp = Blueprint(
    'backend_bp',
    __name__,
    url_prefix='/api'
)

# --- UPLOAD ROUTE ---
@backend_bp.route("/upload", methods=["POST"])
async def upload():
    """Handles file uploads to Telegram."""
    form_data = await request.form
    token = form_data.get("token", "").strip() or app_config.BOT_TOKEN
    chat_id = form_data.get("chatid", "").strip() or app_config.CHAT_ID

    if not token or not chat_id:
        return jsonify({"ok": False, "message": "❌ Missing Bot Token or Chat ID."}), 400

    files = await request.files
    file = files.get("file")
    if not file:
        return jsonify({"ok": False, "message": "❌ No file was provided."}), 400

    api_method = 'sendPhoto' if file.mimetype.lower().startswith('image/') else 'sendDocument'
    file_type_key = 'photo' if api_method == 'sendPhoto' else 'document'
    telegram_api_url = f"https://api.telegram.org/bot{token}"

    try:
        # Using requests for upload as it handles multipart/form-data well
        resp = requests.post(
            f"{telegram_api_url}/{api_method}",
            data={"chat_id": chat_id, "caption": form_data.get("caption", "").strip()},
            files={file_type_key: (file.filename, file, file.mimetype)},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("ok"):
            return jsonify({"ok": True, "message": "✅ Upload successful!"})
        else:
            return jsonify({"ok": False, "message": f"❌ API Error: {data.get('description', 'Unknown')}"}), 400
    except requests.exceptions.RequestException as e:
        return jsonify({"ok": False, "message": f"❌ Network Error: {e}"}), 500


# --- FILE LISTING ROUTE ---
@backend_bp.route("/get_recent_files", methods=["GET"])
async def get_recent_files():
    """Fetches messages from the last 30 minutes and returns a list of files."""
    if not app_config.CHAT_ID:
        return jsonify({"ok": False, "message": "❌ Server CHAT_ID not configured."}), 500

    files = []
    thirty_mins_ago = int(time.time()) - (30 * 60)

    try:
        # Use Pyrogram to fetch history
        async for message in pyrogram_client.get_chat_history(chat_id=int(app_config.CHAT_ID), limit=100):
            if message.date < thirty_mins_ago:
                break  # Stop when we go past 30 minutes

            media = message.document or message.photo
            if media:
                files.append({
                    "name": getattr(media, 'file_name', f"photo_{message.id}.jpg"),
                    "file_id": media.file_id,
                    "size": media.file_size,
                    "mime": getattr(media, 'mime_type', 'image/jpeg')
                })
        
        return jsonify({"ok": True, "files": files})
    except Exception as e:
        return jsonify({"ok": False, "message": f"❌ Error fetching history: {e}"}), 500


# --- FILE STREAMING ROUTE ---
@backend_bp.route("/stream", methods=["GET"])
async def stream():
    """Streams a file from Telegram using file_id."""
    file_id = request.args.get("file_id")
    file_name = request.args.get("name", "download")
    file_size = int(request.args.get("size", 0))
    mime_type = unquote(request.args.get("mime", "application/octet-stream"))

    if not file_id:
        return Response("Missing file_id", status=400)

    range_header = request.headers.get("Range", "")
    start = 0
    end = file_size - 1

    if range_header:
        # Partial content request
        byte1, byte2 = range_header.replace("bytes=", "").split("-")
        start = int(byte1)
        if byte2:
            end = int(byte2)

    chunk_size = 16 * 1024  # 16 KB
    length = (end - start) + 1

    async def generate_chunks():
        # Using an async generator for streaming
        try:
            streamer = pyrogram_client.stream_media(file_id, offset=start, limit=length)
            async for chunk in streamer:
                yield chunk
        except FloodWait as e:
            # Tell the client to wait and retry
            print(f"FloodWait: sleeping for {e.value} seconds")
            await asyncio.sleep(e.value)
            # Re-yield or handle error
            yield b"Error: FloodWait received, please try again shortly."
        except Exception as e:
            print(f"Error during streaming: {e}")
            yield b"Error: Could not stream the file."
    
    headers = {
        "Content-Type": mime_type,
        "Content-Length": str(length),
        "Content-Disposition": f'attachment; filename="{file_name}"',
        "Accept-Ranges": "bytes",
        "Content-Range": f"bytes {start}-{end}/{file_size}",
    }
    
    # Use stream_with_context for efficient streaming
    return Response(stream_with_context(generate_chunks()), status=206, headers=headers)
