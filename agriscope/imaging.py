"""Upload validation and decoding. Uploads are handled in memory only: nothing is written
to disk and the client-supplied filename is never used."""
from __future__ import annotations

import io

from PIL import Image, ImageOps, UnidentifiedImageError

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MIN_SIDE = 32


def _sniff(data: bytes) -> str | None:
    """Identify the container from magic bytes so arbitrary data never reaches an image decoder.
    (Ultralytics patches PIL.Image.open globally; keeping unknown data away from it is safer.)"""
    if data.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WEBP"
    return None


class ImageError(Exception):
    def __init__(self, code: str, message: str, status: int):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def decode_upload(data: bytes, max_pixels: int) -> Image.Image:
    """Validate raw bytes and return an upright RGB PIL image, or raise ImageError."""
    if not data:
        raise ImageError("empty_file", "The uploaded file is empty.", 400)
    if _sniff(data) is None:
        raise ImageError("unsupported_type", "That file isn't a supported image. Use a JPG, PNG or WebP photo.", 415)
    try:
        img = Image.open(io.BytesIO(data))
        fmt = img.format
    except Image.DecompressionBombError:
        raise ImageError("image_too_large", "That image has too many pixels to process safely.", 422)
    except (UnidentifiedImageError, OSError, ValueError, ImportError):
        raise ImageError("corrupt_image", "That image appears to be damaged and couldn't be read.", 422)
    if fmt not in ALLOWED_FORMATS:
        raise ImageError("unsupported_type", "Unsupported image format. Use a JPG, PNG or WebP photo.", 415)

    width, height = img.size
    if width * height > max_pixels:
        raise ImageError("image_too_large", f"That image is larger than {max_pixels / 1e6:.0f} megapixels. Please downscale it.", 422)
    if min(width, height) < MIN_SIDE:
        raise ImageError("image_too_small", f"That image is too small (minimum {MIN_SIDE} px per side).", 422)

    try:
        img.load()
        img = ImageOps.exif_transpose(img)  # match the orientation the browser shows
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            rgba = img.convert("RGBA")
            background = Image.new("RGB", rgba.size, (255, 255, 255))
            background.paste(rgba, mask=rgba.getchannel("A"))
            return background
        return img.convert("RGB")
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        raise ImageError("corrupt_image", "That image appears to be damaged and couldn't be read.", 422)
