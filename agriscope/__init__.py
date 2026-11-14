"""AgriScope: AI-assisted plant disease detection."""
import logging
import os

from flask import Flask, jsonify, render_template, request

from .config import Config
from .detector import Detector

__version__ = "1.0.0"
log = logging.getLogger("agriscope")


def create_app(config: Config | None = None, detector: Detector | None = None) -> Flask:
    config = config or Config.from_env()
    app = Flask(
        __name__,
        template_folder=os.path.join(config.root, "templates"),
        static_folder=os.path.join(config.root, "static"),
    )
    app.config["MAX_CONTENT_LENGTH"] = config.max_upload_bytes + 256 * 1024  # multipart overhead
    app.config["AGRISCOPE"] = config
    app.json.sort_keys = False

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    app.extensions["detector"] = detector or Detector(
        model_path=config.model_path,
        device=config.device,
        imgsz=config.imgsz,
        max_det=config.max_det,
    )
    if config.preload_model:
        try:
            app.extensions["detector"].ensure_loaded()
        except Exception:  # noqa: BLE001 - failure is recorded on the detector, never fatal at startup
            pass

    from .routes import bp

    app.register_blueprint(bp)

    @app.context_processor
    def inject_globals():
        return {"version": __version__, "cfg": config}

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
        )
        if request.path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    def error_response(status, code, title, message):
        if request.path.startswith("/api/"):
            return jsonify(ok=False, error={"code": code, "message": message}), status
        return render_template("error.html", status=status, title=title, message=message), status

    @app.errorhandler(404)
    def not_found(_e):
        return error_response(404, "not_found", "Page not found", "That path doesn't lead anywhere in the field.")

    @app.errorhandler(405)
    def bad_method(_e):
        return error_response(405, "method_not_allowed", "Method not allowed", "This address doesn't accept that kind of request.")

    @app.errorhandler(413)
    def too_large(_e):
        msg = f"That file is larger than the {config.max_upload_mb:g} MB limit. Try a smaller or compressed photo."
        return error_response(413, "file_too_large", "File too large", msg)

    @app.errorhandler(Exception)
    def unexpected(e):
        from werkzeug.exceptions import HTTPException

        if isinstance(e, HTTPException):
            return error_response(e.code or 500, "http_error", e.name, e.description or "")
        log.exception("Unhandled error")  # details stay in server logs only
        return error_response(500, "internal_error", "Something went wrong", "An unexpected error occurred. Please try again.")

    return app
