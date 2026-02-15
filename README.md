# eInk Photo Frame (Inky Impression 5.7)

FastAPI-based photo frame manager for Raspberry Pi Zero 2 W.

## Features

- Drag-and-drop multi-image upload
- Image processing modes for 600x448 display:
  - `fit_crop`: fill screen (resize + crop)
  - `fit`: full image with letterboxing
  - `crop`: centered crop to target
- Delete images
- Drag-to-reorder display sequence
- Rotation interval settings page
- Background scheduler calling `display(image)` placeholder

## Run

```bash
uv sync
python main.py
```

Open `http://<pi-ip>:8000`.

## Storage

- Originals: `data/images/originals/`
- Processed display images: `data/images/processed/`
- App state/settings/order: `data/state.json`

## Integrate Real Display Driver

Edit `display()` in `app/scheduler.py`.

```python
def display(image_path: Path) -> None:
    # TODO: call your Inky Impression update code here
    print(f"Display placeholder: {image_path}")
```

The scheduler handles timing and round-robin image selection.
