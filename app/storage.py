from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import (
    BASE_DIR,
    DATA_DIR,
    DEFAULT_DISPLAY_HEIGHT,
    DEFAULT_DISPLAY_WIDTH,
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
        "settings": {
            "rotation_seconds": DEFAULT_ROTATION_SECONDS,
            "display_width": DEFAULT_DISPLAY_WIDTH,
            "display_height": DEFAULT_DISPLAY_HEIGHT,
        },
        "images": [],
        "scheduler": {"last_index": -1},
    }


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def _normalize_state(state: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    changed = False

    if "settings" not in state:
        state["settings"] = {
            "rotation_seconds": DEFAULT_ROTATION_SECONDS,
            "display_width": DEFAULT_DISPLAY_WIDTH,
            "display_height": DEFAULT_DISPLAY_HEIGHT,
        }
        changed = True
    else:
        settings = state["settings"]
        if "rotation_seconds" not in settings:
            settings["rotation_seconds"] = DEFAULT_ROTATION_SECONDS
            changed = True
        if "display_width" not in settings:
            settings["display_width"] = DEFAULT_DISPLAY_WIDTH
            changed = True
        if "display_height" not in settings:
            settings["display_height"] = DEFAULT_DISPLAY_HEIGHT
            changed = True

    if "images" not in state or not isinstance(state["images"], list):
        state["images"] = []
        changed = True

    if "scheduler" not in state:
        state["scheduler"] = {"last_index": -1}
        changed = True

    if "last_index" not in state["scheduler"]:
        state["scheduler"]["last_index"] = -1
        changed = True

    for image in state["images"]:
        if "processed_path" not in image:
            image["processed_path"] = None
            changed = True

        if "status" not in image or image["status"] not in {"pending", "ready"}:
            image["status"] = "ready" if image.get("processed_path") else "pending"
            changed = True

        if "mode" not in image:
            image["mode"] = "manual" if image["status"] == "ready" else None
            changed = True

        if image["status"] == "pending" and image.get("order") is not None:
            image["order"] = None
            changed = True

    ready_images = [img for img in state["images"] if img.get("status") == "ready"]
    ready_images_sorted = sorted(ready_images, key=lambda img: int(img.get("order") or 0))
    for idx, image in enumerate(ready_images_sorted):
        if image.get("order") != idx:
            image["order"] = idx
            changed = True

    ready_count = len(ready_images_sorted)
    if int(state["scheduler"].get("last_index", -1)) >= ready_count:
        state["scheduler"]["last_index"] = -1
        changed = True

    return state, changed


def load_state() -> dict[str, Any]:
    _ensure_dirs()
    if not STATE_FILE.exists():
        state = _default_state()
        save_state(state)
        return state

    with _lock, STATE_FILE.open("r", encoding="utf-8") as f:
        state = json.load(f)

    state, changed = _normalize_state(state)
    if changed:
        save_state(state)
    return state


def save_state(state: dict[str, Any]) -> None:
    _ensure_dirs()
    with _lock, STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def get_images_sorted() -> list[dict[str, Any]]:
    state = load_state()
    ready = [img for img in state["images"] if img.get("status") == "ready"]
    return sorted(ready, key=lambda img: img["order"])


def get_pending_images() -> list[dict[str, Any]]:
    state = load_state()
    pending = [img for img in state["images"] if img.get("status") == "pending"]
    return sorted(pending, key=lambda img: img.get("created_at", ""))


def get_image(image_id: str) -> dict[str, Any] | None:
    state = load_state()
    return next((img for img in state["images"] if img["id"] == image_id), None)


def get_next_pending_image(current_image_id: str | None = None) -> dict[str, Any] | None:
    pending = get_pending_images()
    if not pending:
        return None

    if current_image_id is None:
        return pending[0]

    ids = [img["id"] for img in pending]
    if current_image_id not in ids:
        return pending[0]

    idx = ids.index(current_image_id)
    if idx + 1 < len(pending):
        return pending[idx + 1]
    return None


def add_pending_image(image: dict[str, Any]) -> None:
    state = load_state()
    image["created_at"] = datetime.now(timezone.utc).isoformat()
    image["status"] = "pending"
    image["order"] = None
    image["processed_path"] = None
    image["mode"] = None
    state["images"].append(image)
    save_state(state)


def mark_image_ready(image_id: str, processed_path: str, mode: str) -> bool:
    state = load_state()
    target = next((img for img in state["images"] if img["id"] == image_id), None)
    if target is None:
        return False

    ready = [img for img in state["images"] if img.get("status") == "ready" and img["id"] != image_id]
    target["status"] = "ready"
    target["processed_path"] = processed_path
    target["mode"] = mode
    target["order"] = len(sorted(ready, key=lambda img: img["order"]))
    save_state(state)
    return True


def delete_image(image_id: str) -> bool:
    state = load_state()
    images = state["images"]
    target = next((img for img in images if img["id"] == image_id), None)
    if target is None:
        return False

    for key in ("original_path", "processed_path"):
        path_value = target.get(key)
        if not path_value:
            continue
        file_path = _resolve_path(path_value)
        if file_path.exists():
            file_path.unlink()

    state["images"] = [img for img in images if img["id"] != image_id]

    ready_sorted = sorted(
        [img for img in state["images"] if img.get("status") == "ready"],
        key=lambda i: i["order"],
    )
    for idx, image in enumerate(ready_sorted):
        image["order"] = idx

    if state["scheduler"]["last_index"] >= len(ready_sorted):
        state["scheduler"]["last_index"] = -1

    save_state(state)
    return True


def reorder_images(ordered_ids: list[str]) -> bool:
    state = load_state()
    ready = [img for img in state["images"] if img.get("status") == "ready"]
    if set(ordered_ids) != {img["id"] for img in ready}:
        return False

    image_map = {img["id"]: img for img in ready}
    for idx, image_id in enumerate(ordered_ids):
        image_map[image_id]["order"] = idx

    save_state(state)
    return True


def get_rotation_seconds() -> int:
    state = load_state()
    return int(state["settings"].get("rotation_seconds", DEFAULT_ROTATION_SECONDS))


def set_rotation_seconds(seconds: int) -> None:
    state = load_state()
    state["settings"]["rotation_seconds"] = max(10, int(seconds))
    save_state(state)


def get_display_size() -> tuple[int, int]:
    state = load_state()
    width = int(state["settings"].get("display_width", DEFAULT_DISPLAY_WIDTH))
    height = int(state["settings"].get("display_height", DEFAULT_DISPLAY_HEIGHT))
    return max(100, width), max(100, height)


def set_display_size(width: int, height: int) -> None:
    state = load_state()
    state["settings"]["display_width"] = max(100, int(width))
    state["settings"]["display_height"] = max(100, int(height))
    save_state(state)


def get_and_advance_next_image() -> dict[str, Any] | None:
    state = load_state()
    images = sorted(
        [img for img in state["images"] if img.get("status") == "ready"],
        key=lambda img: img["order"],
    )
    if not images:
        state["scheduler"]["last_index"] = -1
        save_state(state)
        return None

    next_index = (int(state["scheduler"].get("last_index", -1)) + 1) % len(images)
    state["scheduler"]["last_index"] = next_index
    save_state(state)
    return images[next_index]
