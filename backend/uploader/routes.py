import time
import requests
from urllib.parse import unquote
from quart import (
    Blueprint,
    request,
    jsonify,
    Response,
    stream_with_context,
    current_app  # <-- IMPORT current_app
)
from pyrogram.errors import FloodWait
import asyncio

backend_bp = Blueprint(
    'backend_bp',
    __name__,
    url_prefix='/api'
)

@backend_bp.route("/upload", methods=["POST"])
async def upload():
    # Access config from the app context
    app_config = current_app.config['APP_CONFIG']
    form_data = await request.form
    token = form_data.get("token", "").strip() or app_config.BOT_TOKEN
    chat_id = form_data.get("chatid", "").strip() or app_config.CHAT_ID
    # ... (rest of the upload function is the same) ...
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


@backend_bp.route("/get_recent_files", methods=["GET"])
async def get_recent_files():
    # Access config and cache from the app context
    app_config = current_app.config['APP_CONFIG']
    file_cache = current_app.config['FILE_CACHE']

    if not app_config.CHAT_ID:
        return jsonify({"ok": False, "message": "❌ Server CHAT_ID not configured."}), 500

    files = []
    thirty_mins_ago = time.time() - (30 * 60)

    for timestamp, file_details in file_cache:
        if timestamp >= thirty_mins_ago:
            files.append(file_details)
        else:
            break

    return jsonify({"ok": True, "files": files})


@backend_bp.route("/stream", methods=["GET"])
async def stream():
    # Access the pyrogram client from the app context
    pyrogram_client = current_app.config['PYROGRAM_CLIENT']
    file_id = request.args.get("file_id")
    # ... (rest of the stream function is the same) ...
    file_name = request.args.get("name", "download")
    file_size = int(request.args.get("size", 0))
    mime_type = unquote(request.args.get("mime", "application/octet-stream"))

    if not file_id:
        return Response("Missing file_id", status=400)

    range_header = request.headers.get("Range", "")
    start = 0
    end = file_size - 1

    if range_header:
        byte1, byte2 = range_header.replace("bytes=", "").split("-")
        start = int(byte1) if byte1 else 0
        if byte2:
            end = int(byte2)

    length = (end - start) + 1

    async def generate_chunks():
        try:
            streamer = pyrogram_client.stream_media(file_id, offset=start, limit=length)
            async for chunk in streamer:
                yield chunk
        except FloodWait as e:
            print(f"FloodWait: sleeping for {e.value} seconds")
            await asyncio.sleep(e.value)
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

    return Response(stream_with_context(generate_chunks()), status=206, headers=headers)
