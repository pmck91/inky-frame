from __future__ import annotations

import asyncio
from pathlib import Path

from .config import BASE_DIR
from .storage import get_and_advance_next_image, get_rotation_seconds


class RotationScheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._running = False

    def start(self) -> None:
        if self._task is None:
            self._running = True
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        while self._running:
            image = get_and_advance_next_image()
            if image is not None:
                display(BASE_DIR / Path(image["processed_path"]))
            interval = max(10, get_rotation_seconds())
            await asyncio.sleep(interval)


def display(image_path: Path) -> None:
    """Placeholder for actual Inky display rendering implementation."""
    print(f"Display placeholder: {image_path}")
