from quart import Blueprint, render_template
from config import Config

# Create a Blueprint for the frontend.
# The key is to define a unique static_url_path for this blueprint's static files.
frontend_bp = Blueprint(
    'frontend_bp',
    __name__,
    template_folder='templates',
    static_folder='static',
    # This line tells Quart: "Serve the files from the 'static_folder' (./static/)
    # at the URL path '/frontend/static'".
    static_url_path='/frontend/static'
)

@frontend_bp.route("/")
async def index():
    """Renders the main single-page application."""
    app_config = Config()
    return await render_template(
        'index.html',
        app_base_url=app_config.APP_BASE_URL
    )
