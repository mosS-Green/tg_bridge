import asyncio
from quart import Quart
from hypercorn.asyncio import serve
from hypercorn.config import Config as HypercornConfig

# Import Blueprints and the Pyrogram client
from frontend.uploader import frontend_bp
from backend.uploader.routes import backend_bp
from backend import pyrogram_client, app_config

# We use Quart instead of Flask because it's ASGI-native
app = Quart(__name__)

# Register the blueprints
app.register_blueprint(frontend_bp)
app.register_blueprint(backend_bp)

# --- App Lifecycle: Start and Stop Pyrogram Client ---
@app.before_serving
async def startup():
    """Connects the Pyrogram client before the app starts serving requests."""
    print("Starting Pyrogram client...")
    await pyrogram_client.start()
    print("Pyrogram client started.")

@app.after_serving
async def shutdown():
    """Disconnects the Pyrogram client after the app stops."""
    print("Stopping Pyrogram client...")
    await pyrogram_client.stop()
    print("Pyrogram client stopped.")


async def main():
    """Main function to configure and run the ASGI server."""
    # Configure Hypercorn for Render deployment
    # Render provides the PORT environment variable.
    port = int(app_config.PORT) if hasattr(app_config, 'PORT') else 8080
    hypercorn_config = HypercornConfig()
    hypercorn_config.bind = [f"0.0.0.0:{port}"]
    
    # Run the Quart app with Hypercorn
    await serve(app, hypercorn_config)

if __name__ == "__main__":
    # To run locally: python app.py
    # For production (Render): hypercorn app:app
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down...")
