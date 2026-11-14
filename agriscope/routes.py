"""HTTP routes: server-rendered pages plus a small JSON API."""
from __future__ import annotations

import logging

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for

from .detector import InferenceError, ModelUnavailable
from .imaging import ImageError, decode_upload
from .knowledge import grouped_classes, known_classes

bp = Blueprint("main", __name__)
log = logging.getLogger("agriscope.routes")

SAMPLES = [
    {"file": "late_blight.jpg", "alt": "Sample leaf photo 1"},
    {"file": "eb.jpg", "alt": "Sample leaf photo 2"},
    {"file": "molds.jpg", "alt": "Sample leaf photo 3"},
    {"file": "spot.jpg", "alt": "Sample leaf photo 4"},
]


def _detector():
    return current_app.extensions["detector"]


def _error(status: int, code: str, message: str):
    return jsonify(ok=False, error={"code": code, "message": message}), status


# ---- pages --------------------------------------------------------------------------------
@bp.get("/")
def index():
    return render_template("index.html", groups=grouped_classes(), class_count=len(known_classes()))


@bp.get("/detect")
def detect():
    cfg = current_app.config["AGRISCOPE"]
    return render_template(
        "detect.html", model=_detector().info(), samples=SAMPLES,
        default_confidence=cfg.default_confidence, max_mb=cfg.max_upload_mb,
    )


@bp.get("/about")
def about():
    return render_template("about.html", model=_detector().info(), groups=grouped_classes())


@bp.get("/upload")  # legacy address from the previous version of the app
def legacy_upload():
    return redirect(url_for("main.detect"), code=301)


# ---- API ----------------------------------------------------------------------------------
@bp.get("/api/health")
def health():
    info = _detector().info()
    return jsonify(status="ok" if info["ready"] else "degraded", model=info)


@bp.post("/api/detect")
def api_detect():
    cfg = current_app.config["AGRISCOPE"]
    upload = request.files.get("file")
    if upload is None:
        return _error(400, "no_file", "No image was uploaded. Choose a photo and try again.")

    raw = request.form.get("confidence")
    confidence = cfg.default_confidence
    if raw not in (None, ""):
        try:
            confidence = float(raw)
        except ValueError:
            return _error(400, "invalid_confidence", "Confidence must be a number between 0.05 and 0.95.")
        if not 0.05 <= confidence <= 0.95:
            return _error(400, "invalid_confidence", "Confidence must be a number between 0.05 and 0.95.")

    data = upload.stream.read(cfg.max_upload_bytes + 1)
    if len(data) > cfg.max_upload_bytes:
        return _error(413, "file_too_large", f"That file is larger than the {cfg.max_upload_mb:g} MB limit.")

    try:
        image = decode_upload(data, cfg.max_pixels)
    except ImageError as e:
        return _error(e.status, e.code, e.message)

    try:
        result = _detector().predict(image, confidence)
    except ModelUnavailable as e:
        return _error(503, "model_unavailable", str(e))
    except InferenceError as e:
        return _error(500, "inference_failed", str(e))
    return jsonify(ok=True, **result)
