from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import (
    BASE_DIR,
    DATA_DIR,
    DEFAULT_ROTATION_SECONDS,
    ORIGINALS_DIR,
    PROCESSED_DIR,
    STATE_FILE,
)

_lock = threading.Lock()


def _resolve_path(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else (BASE_DIR / p)


def _default_state() -> dict[str, Any]:
    return {
        "settings": {"rotation_seconds": DEFAULT_ROTATION_SECONDS},
        "images": [],
        "scheduler": {"last_index": -1},
    }


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def load_state() -> dict[str, Any]:
    _ensure_dirs()
    if not STATE_FILE.exists():
        state = _default_state()
        save_state(state)
        return state

    with _lock, STATE_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict[str, Any]) -> None:
    _ensure_dirs()
    with _lock, STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def get_images_sorted() -> list[dict[str, Any]]:
    state = load_state()
    return sorted(state["images"], key=lambda img: img["order"])


def add_image(image: dict[str, Any]) -> None:
    state = load_state()
    image["created_at"] = datetime.now(timezone.utc).isoformat()
    image["order"] = len(state["images"])
    state["images"].append(image)
    save_state(state)


def delete_image(image_id: str) -> bool:
    state = load_state()
    images = state["images"]
    target = next((img for img in images if img["id"] == image_id), None)
    if target is None:
        return False

    for key in ("original_path", "processed_path"):
        file_path = _resolve_path(target[key])
        if file_path.exists():
            file_path.unlink()

    state["images"] = [img for img in images if img["id"] != image_id]
    for idx, image in enumerate(sorted(state["images"], key=lambda i: i["order"])):
        image["order"] = idx

    if state["scheduler"]["last_index"] >= len(state["images"]):
        state["scheduler"]["last_index"] = -1

    save_state(state)
    return True


def reorder_images(ordered_ids: list[str]) -> bool:
    state = load_state()
    images = state["images"]
    if set(ordered_ids) != {img["id"] for img in images}:
        return False

    image_map = {img["id"]: img for img in images}
    state["images"] = [image_map[img_id] for img_id in ordered_ids]
    for idx, image in enumerate(state["images"]):
        image["order"] = idx

    save_state(state)
    return True


def get_rotation_seconds() -> int:
    state = load_state()
    return int(state["settings"].get("rotation_seconds", DEFAULT_ROTATION_SECONDS))


def set_rotation_seconds(seconds: int) -> None:
    state = load_state()
    state["settings"]["rotation_seconds"] = max(10, int(seconds))
    save_state(state)


def get_and_advance_next_image() -> dict[str, Any] | None:
    state = load_state()
    images = sorted(state["images"], key=lambda img: img["order"])
    if not images:
        state["scheduler"]["last_index"] = -1
        save_state(state)
        return None

    next_index = (int(state["scheduler"].get("last_index", -1)) + 1) % len(images)
    state["scheduler"]["last_index"] = next_index
    save_state(state)
    return images[next_index]
