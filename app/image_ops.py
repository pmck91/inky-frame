from __future__ import annotations

import uuid
from io import BytesIO
from pathlib import Path
from typing import Literal

from fastapi import UploadFile
from PIL import Image, ImageOps

from .config import DISPLAY_HEIGHT, DISPLAY_WIDTH, ORIGINALS_DIR, PROCESSED_DIR

ProcessMode = Literal["crop", "fit", "fit_crop"]


def _center_crop_to_target(image: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_w, src_h = image.size
    src_ratio = src_w / src_h
    target_ratio = target_w / target_h

    if src_ratio > target_ratio:
        new_h = src_h
        new_w = int(src_h * target_ratio)
    else:
        new_w = src_w
        new_h = int(src_w / target_ratio)

    left = (src_w - new_w) // 2
    top = (src_h - new_h) // 2
    right = left + new_w
    bottom = top + new_h
    cropped = image.crop((left, top, right, bottom))
    return cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)


def _fit_in_target(image: Image.Image, target_w: int, target_h: int) -> Image.Image:
    # Letterbox onto white background to preserve full photo.
    fitted = ImageOps.contain(image, (target_w, target_h), Image.Resampling.LANCZOS)
    out = Image.new("RGB", (target_w, target_h), "white")
    x = (target_w - fitted.width) // 2
    y = (target_h - fitted.height) // 2
    out.paste(fitted, (x, y))
    return out


def _fit_crop(image: Image.Image, target_w: int, target_h: int) -> Image.Image:
    # Scale first, then crop overflow to fill target without distortion.
    return ImageOps.fit(image, (target_w, target_h), Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def process_upload(upload: UploadFile, mode: ProcessMode) -> dict[str, str]:
    image_id = str(uuid.uuid4())
    suffix = Path(upload.filename or "image").suffix.lower() or ".jpg"

    original_path = ORIGINALS_DIR / f"{image_id}{suffix}"
    processed_path = PROCESSED_DIR / f"{image_id}.png"

    payload = upload.file.read()
    original_path.write_bytes(payload)

    image = Image.open(BytesIO(payload)).convert("RGB")

    if mode == "crop":
        processed = _center_crop_to_target(image, DISPLAY_WIDTH, DISPLAY_HEIGHT)
    elif mode == "fit":
        processed = _fit_in_target(image, DISPLAY_WIDTH, DISPLAY_HEIGHT)
    else:
        processed = _fit_crop(image, DISPLAY_WIDTH, DISPLAY_HEIGHT)

    processed.save(processed_path, format="PNG")

    return {
        "id": image_id,
        "name": upload.filename or f"image-{image_id}",
        "mode": mode,
        "original_path": f"data/images/originals/{image_id}{suffix}",
        "processed_path": f"data/images/processed/{image_id}.png",
    }
