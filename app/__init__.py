import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask


def create_app():
    """
    Application factory.
    Creates the Flask app, configures logging, loads blueprints,
    and prepares required directories.
    """

    app = Flask(__name__)

    # ---------------------------------------------------------
    # Basic config
    # ---------------------------------------------------------
    secret = os.environ.get("LOGSENSE_SECRET_KEY", "dev-only-change-before-deploying")
    app.config["SECRET_KEY"] = secret

    import os as _os
    _is_reloader = _os.environ.get('WERKZEUG_RUN_MAIN') == 'true'

    if not _is_reloader:
        YELLOW = '\033[33m'
        CYAN   = '\033[36m'
        BOLD   = '\033[1m'
        RESET  = '\033[0m'

        if secret == "dev-only-change-before-deploying":
            print(f"\n{YELLOW}{BOLD}  !! Running with the default SECRET_KEY.{RESET}", file=sys.stderr)
            print(f"{YELLOW}     This key is public. Set LOGSENSE_SECRET_KEY to a random string before sharing access.{RESET}\n", file=sys.stderr)

        print(f"{CYAN}{BOLD}  >> LogSense AI{RESET}{CYAN}  http://127.0.0.1:5000{RESET}\n\n", file=sys.stderr)
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024
    app.config["MAX_LINES"] = 20000
    from flask_wtf.csrf import CSRFProtect, CSRFError
    csrf = CSRFProtect(app)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        return {"ok": False, "error": "CSRF validation failed."}, 400

    # Directory used for exporting reports
    app.config["EXPORT_FOLDER"] = os.path.join("exports")
    os.makedirs(app.config["EXPORT_FOLDER"], exist_ok=True)

    # Directory used for server-side logs
    log_dir = os.path.join("logs")
    os.makedirs(log_dir, exist_ok=True)

    # ---------------------------------------------------------
    # Server-side logging (Rotating file handler)
    # ---------------------------------------------------------
    handler = RotatingFileHandler(
        os.path.join(log_dir, "server.log"),
        maxBytes=500_000,
        backupCount=3
    )
    handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)

    if not app.logger.handlers:
        app.logger.addHandler(handler)

    app.logger.setLevel(logging.INFO)

    # ---------------------------------------------------------
    # Blueprint registration
    # ---------------------------------------------------------
    from app.routes import routes
    app.register_blueprint(routes)

    return app
