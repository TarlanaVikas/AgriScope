"""Runtime configuration, read from environment variables (optionally a .env file)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:  # optional convenience; real environment variables always win
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:  # pragma: no cover
    pass


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    root: str = str(ROOT)
    model_path: str = str(ROOT / "models" / "best.pt")
    default_confidence: float = 0.25
    max_upload_mb: float = 10.0
    max_pixels: int = 40_000_000
    max_det: int = 100
    device: str | None = None  # None -> let Ultralytics choose (GPU if present, else CPU)
    imgsz: int | None = None  # None -> use the size stored in the weights
    preload_model: bool = True

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)

    @classmethod
    def from_env(cls) -> "Config":
        model_path = os.environ.get("AGRISCOPE_MODEL_PATH", str(ROOT / "models" / "best.pt"))
        if not os.path.isabs(model_path):
            model_path = str(ROOT / model_path)
        device = os.environ.get("AGRISCOPE_DEVICE", "auto").strip()
        imgsz = _int("AGRISCOPE_IMGSZ", 0)
        return cls(
            model_path=model_path,
            default_confidence=min(max(_float("AGRISCOPE_CONF", 0.25), 0.05), 0.95),
            max_upload_mb=max(_float("AGRISCOPE_MAX_UPLOAD_MB", 10.0), 0.1),
            max_pixels=max(_int("AGRISCOPE_MAX_PIXELS", 40_000_000), 1_000),
            max_det=max(_int("AGRISCOPE_MAX_DET", 100), 1),
            device=None if device.lower() in {"", "auto"} else device,
            imgsz=imgsz or None,
            preload_model=_bool("AGRISCOPE_PRELOAD_MODEL", True),
        )
