from quart import Blueprint, render_template
from config import Config

# Create a Blueprint for the frontend.
# It knows where to find templates and static files.
frontend_bp = Blueprint(
    'frontend_bp',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/static' # URL path for static files
)

@frontend_bp.route("/")
async def index():
    """Renders the main single-page application."""
    app_config = Config()
    return await render_template(
        'index.html',
        app_base_url=app_config.APP_BASE_URL
    )
