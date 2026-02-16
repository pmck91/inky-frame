# eInk Photo Frame (Inky Impression 5.7)

FastAPI-based photo frame manager for Raspberry Pi Zero 2 W.

## Features

- Drag-and-drop multi-image upload
- Queue-based edit workflow:
  - uploads go to a pending crop list
  - browser editor supports crop-to-fill (`cover`) and resize-to-fit (`contain`)
  - pan + zoom controls (including mouse wheel + pinch)
  - rotate left/right and horizontal/vertical flip tools
  - fixed safe-area guide overlay in the editor
  - only saved/processed images become display-ready
- Delete images
- Drag-to-reorder display sequence
- Settings page for rotation interval and configurable display resolution
- Background scheduler calling `display(image)` placeholder

## Run

```bash
uv sync
python main.py
```

Open `http://<pi-ip>:8000`.

## Raspberry Pi Setup

### 1. Install system dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip libjpeg-dev zlib1g-dev
```

### 2. Install `uv` and project dependencies

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# restart shell, then:
cd /home/[Update with your user]/inky-frame
uv sync
```

### 3. Run manually (test)

```bash
cd /home/[Update with your user]/inky-frame
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. Enable Raspberry Pi interfaces (I2C/SPI)

```bash
# Enable I2C
sudo raspi-config nonint do_i2c 0

# Enable SPI
sudo raspi-config nonint do_spi 0
```

Reboot after enabling:

```bash
sudo reboot
```

## systemd Service (Port 80)

Copy the bundled service file:

```bash
sudo cp deploy/systemd/eink-frame.service /etc/systemd/system/eink-frame.service
```

Service contents (`deploy/systemd/eink-frame.service`):

```ini
[Unit]
Description=eInk Photo Frame Web App
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/[Update with your user]/inky-frame
Environment=PYTHONUNBUFFERED=1
ExecStart=//home/[Update with your user]/inky-frame/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 80
Restart=always
RestartSec=3

# Allow non-root bind to privileged port 80
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE

# Basic hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=false

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable eink-frame.service
sudo systemctl start eink-frame.service
sudo systemctl status eink-frame.service
```

Logs:

```bash
journalctl -u eink-frame.service -f
```

Note: Port `80` is privileged; this service uses `CAP_NET_BIND_SERVICE` so it can run as `pi`.

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
