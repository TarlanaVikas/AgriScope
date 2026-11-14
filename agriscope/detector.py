"""Model loading and inference. The model is loaded once and reused; inference is serialised
with a lock because Ultralytics predictors are not guaranteed to be thread-safe."""
from __future__ import annotations

import logging
import os
import threading
import time

from PIL import Image

from .knowledge import describe_class, guidance_for

# Never let Ultralytics pip-install packages at runtime from inside a web server process.
os.environ.setdefault("YOLO_AUTOINSTALL", "False")

log = logging.getLogger("agriscope.detector")
RETRY_AFTER_FAILURE_S = 15.0


class ModelUnavailable(Exception):
    """Weights are missing, unreadable or incompatible."""


class InferenceError(Exception):
    """The model loaded but failed on this image."""


class Detector:
    def __init__(self, model_path: str, device: str | None = None, imgsz: int | None = None, max_det: int = 100):
        self.model_path, self.device, self.imgsz, self.max_det = model_path, device, imgsz, max_det
        self._model = None
        self._lock = threading.Lock()
        self._error: str | None = None
        self._failed_at = 0.0

    # ---- status -------------------------------------------------------------------------
    @property
    def ready(self) -> bool:
        return self._model is not None

    @property
    def error(self) -> str | None:
        return None if self.ready else self._error

    def class_names(self) -> dict[int, str]:
        return dict(self._model.names) if self._model is not None else {}

    def info(self) -> dict:
        info = {"ready": self.ready, "error": self.error}
        if self._model is not None:
            info.update(
                task=self._model.task,
                num_classes=len(self._model.names),
                input_size=self.imgsz or (self._model.overrides or {}).get("imgsz"),
            )
        return info

    # ---- loading ------------------------------------------------------------------------
    def ensure_loaded(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            if self._error and time.monotonic() - self._failed_at < RETRY_AFTER_FAILURE_S:
                raise ModelUnavailable(self._error)
            try:
                if not os.path.isfile(self.model_path):
                    raise FileNotFoundError("model weights file not found")
                from ultralytics import YOLO  # imported lazily so the web app can start without it

                model = YOLO(self.model_path)
                if getattr(model, "task", None) != "detect":
                    raise ValueError(f"expected an object-detection model, got task={getattr(model, 'task', None)!r}")
                self._model, self._error = model, None
                log.info("Model loaded: %d classes", len(model.names))
            except Exception as exc:  # noqa: BLE001 - reported to the caller in sanitised form
                log.error("Model load failed (%s): %s", type(exc).__name__, exc)
                if isinstance(exc, FileNotFoundError):
                    self._error = "Model weights were not found. See the README for where to place them."
                elif isinstance(exc, ImportError):
                    self._error = "The detection libraries (ultralytics / torch) are not installed."
                else:
                    self._error = "The model weights could not be loaded; the file may be corrupted or incompatible."
                self._failed_at = time.monotonic()
                raise ModelUnavailable(self._error) from exc

    # ---- inference ----------------------------------------------------------------------
    def predict(self, image: Image.Image, confidence: float) -> dict:
        self.ensure_loaded()
        kwargs = {"conf": confidence, "max_det": self.max_det, "verbose": False}
        if self.device:
            kwargs["device"] = self.device
        if self.imgsz:
            kwargs["imgsz"] = self.imgsz
        started = time.perf_counter()
        try:
            with self._lock:
                # A PIL image is treated as RGB by Ultralytics (NumPy arrays would be assumed BGR).
                result = self._model.predict(source=image, **kwargs)[0]
            xyxy = result.boxes.xyxy.cpu().numpy()
            scores = result.boxes.conf.cpu().numpy()
            classes = result.boxes.cls.cpu().numpy().astype(int)
        except Exception as exc:  # noqa: BLE001
            log.exception("Inference failed")
            raise InferenceError("The model couldn't analyze this image. Try a different photo.") from exc
        elapsed_ms = round((time.perf_counter() - started) * 1000)

        width, height = image.size
        names = self._model.names
        detections = []
        for (x1, y1, x2, y2), score, cid in sorted(zip(xyxy, scores, classes), key=lambda t: -t[1]):
            x1, x2 = max(0.0, min(float(x1), width)), max(0.0, min(float(x2), width))
            y1, y2 = max(0.0, min(float(y1), height)), max(0.0, min(float(y2), height))
            raw = str(names[int(cid)])
            meta = describe_class(raw)
            detections.append(
                {
                    "id": len(detections),
                    "class_id": int(cid),
                    "raw_label": raw,
                    "label": meta["label"],
                    "group": meta["group"],
                    "healthy": meta["healthy"],
                    "confidence": round(float(score), 4),
                    "box": {"x1": round(x1, 1), "y1": round(y1, 1), "x2": round(x2, 1), "y2": round(y2, 1)},
                }
            )
        return {
            "image": {"width": width, "height": height},
            "threshold": confidence,
            "inference_ms": elapsed_ms,
            "detections": detections,
            "findings": summarize(detections),
        }


def summarize(detections: list[dict]) -> list[dict]:
    """Group detections by class. Disease findings come first (by top confidence), healthy last."""
    groups: dict[int, dict] = {}
    for d in detections:
        g = groups.setdefault(
            d["class_id"],
            {"class_id": d["class_id"], "label": d["label"], "raw_label": d["raw_label"], "group": d["group"],
             "healthy": d["healthy"], "count": 0, "top_confidence": 0.0, "detection_ids": []},
        )
        g["count"] += 1
        g["top_confidence"] = max(g["top_confidence"], d["confidence"])
        g["detection_ids"].append(d["id"])
    findings = sorted(groups.values(), key=lambda g: (g["healthy"], -g["top_confidence"]))
    for f in findings:
        f["guidance"] = guidance_for(f["raw_label"])
    return findings
