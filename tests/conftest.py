import io
import os
import sys

import pytest
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agriscope import create_app  # noqa: E402
from agriscope.config import Config  # noqa: E402
from agriscope.detector import InferenceError, ModelUnavailable, summarize  # noqa: E402
from agriscope.knowledge import describe_class  # noqa: E402


class FakeDetector:
    """Stands in for the real model so API tests run fast and without torch."""

    def __init__(self, ready=True, raises=None):
        self.ready, self._raises = ready, raises
        self.error = None if ready else "Model weights were not found. See the README for where to place them."
        self.calls = []

    def info(self):
        return {"ready": self.ready, "error": self.error, "task": "detect", "num_classes": 15, "input_size": 800}

    def ensure_loaded(self):
        if not self.ready:
            raise ModelUnavailable(self.error)

    def predict(self, image, confidence):
        self.ensure_loaded()
        if self._raises:
            raise self._raises
        self.calls.append((image.size, confidence))
        meta = describe_class("late_blight")
        dets = [{"id": 0, "class_id": 11, "raw_label": "late_blight", "label": meta["label"], "group": meta["group"],
                 "healthy": False, "confidence": 0.9, "box": {"x1": 1.0, "y1": 2.0, "x2": 30.0, "y2": 40.0}}]
        return {"image": {"width": image.size[0], "height": image.size[1]}, "threshold": confidence,
                "inference_ms": 5, "detections": dets, "findings": summarize(dets)}


def make_image_bytes(fmt="JPEG", size=(128, 96), mode="RGB", **kw):
    buf = io.BytesIO()
    Image.new(mode, size, (30, 120, 40) if mode == "RGB" else None).save(buf, fmt, **kw)
    return buf.getvalue()


@pytest.fixture
def fake():
    return FakeDetector()


@pytest.fixture
def client(fake):
    app = create_app(Config(preload_model=False, max_upload_mb=1.0), detector=fake)
    app.testing = True
    return app.test_client()


@pytest.fixture
def post_file(client):
    def _post(data, name="leaf.jpg", **form):
        return client.post("/api/detect", data={"file": (io.BytesIO(data), name), **form}, content_type="multipart/form-data")
    return _post
