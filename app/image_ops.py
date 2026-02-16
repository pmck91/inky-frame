from __future__ import annotations

import uuid
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from PIL import Image

from .config import ORIGINALS_DIR, PROCESSED_DIR


async def save_original_upload(upload: UploadFile) -> dict[str, str]:
    image_id = str(uuid.uuid4())
    suffix = Path(upload.filename or "image").suffix.lower() or ".jpg"

    ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)
    original_path = ORIGINALS_DIR / f"{image_id}{suffix}"
    payload = await upload.read()
    original_path.write_bytes(payload)

    return {
        "id": image_id,
        "name": upload.filename or f"image-{image_id}",
        "original_path": f"data/images/originals/{image_id}{suffix}",
    }


def save_processed_canvas_png(image_id: str, payload: bytes, target_width: int, target_height: int) -> str:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    image = Image.open(BytesIO(payload)).convert("RGB")

    if image.size != (target_width, target_height):
        image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)

    processed_path = PROCESSED_DIR / f"{image_id}.png"
    image.save(processed_path, format="PNG")

    return f"data/images/processed/{image_id}.png"
