# M4 Hardware Bring-Up

## Problem

All display and button code runs in pygame simulation only. Real Unicorn HAT Mini and Inky Impression hardware have no driver implementations. No systemd deployment. PIL compositing logic is mixed into InkyMock display class, making it impossible to share layout between mock and real hardware.

## Scope

Wire real hardware (Unicorn HAT Mini, Inky Impression, GPIO buttons) on two Pi Zero 2 W devices. Run M1 functionality (channel switching, word cycling, commit, sentence building) on physical devices. Defer M2 (image generation) and M3 (evolution loop) — this milestone is about hardware, not new features.

## Design

### Hardware Detection Pattern

Each module tries importing its hardware library at load time. If ImportError, a flag is set. Classes check the flag and fall back to mock.

```python
try:
    from unicornhatmini import UnicornHATMini
    HAS_UNICORN = True
except ImportError:
    HAS_UNICORN = False
```

No env vars, no config files. If the lib exists, use it. On Mac or any system without hardware libs → mock. On Pi with libs installed → hardware.

### Architecture Changes

**Current (M1):**
```
Conductor → InkyMock (pygame, PIL compositing baked in)
Controller → SparkMock (pygame, unicorn emulator)
```

**After M4:**
```
Conductor → SlateDisplay (hardware detection)
              ├─ HAS_INKY=True  → real Inky Impression
              └─ HAS_INKY=False → InkyMock (pygame)
            → BasicImageBackend (PIL compositing)
              renders menu strip + main area + status ribbon → PIL Image
              SlateDisplay just shows whatever image it receives

Controller → SparkDisplay (hardware detection)
              ├─ HAS_UNICORN=True  → real Unicorn HAT Mini
              └─ HAS_UNICORN=False → SparkMock (pygame)

Both → GPIOButtonListener (hardware detection)
         ├─ HAS_GPIO=True  → gpiozero.Button
         └─ HAS_GPIO=False → KeyboardListener (existing)
```

### Display Layer: Just Output Devices

**SparkDisplay (`controller/display.py`):**
- Hardware detection: try import `unicornhatmini`
- If `HAS_UNICORN`: create `UnicornHATMini()`, use `set_pixel()` + `show()` directly
- If not: delegate to SparkMock (existing pygame emulator)
- Same rendering logic: color bar row 0, pips row 1, scrolling text rows 2-6
- The real Unicorn HAT Mini has the same `set_pixel(x, y, r, g, b)` / `show()` API as the mock

**SlateDisplay (`conductor/display.py`):**
- Hardware detection: try import `inky`
- Receives a PIL Image from BasicImageBackend and displays it
- If `HAS_INKY`: `inky.set_image(pil_image)` + `inky.show()`
- If not: delegate to InkyMock which blits the PIL Image onto pygame
- No layout logic in the display class — just "show this image"

**InkyMock (`conductor/display.py`):**
- Refactored: receives PIL Image, converts to pygame surface, blits + flips
- Still handles pygame event loop (keyboard, window close)
- No longer does its own PIL compositing — receives image from BasicImageBackend

### BasicImageBackend

**`shared/image_backend.py`** (refactored from stub):

```python
class BasicImageBackend(ImageBackend):
    """Stub image backend: PIL compositing with placeholder main area."""

    def render_frame(self, state: StateSnapshot) -> Image.Image:
        """Render full Slate frame: menu strip + main area + status ribbon."""
        img = Image.new("RGB", (640, 400), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        # Left menu strip (80px)
        # Main area (placeholder for now — solid color or "no image" text)
        # Bottom status ribbon (sentence + engine status)
        return img
```

The PIL compositing logic currently in `InkyMock._draw_menu_strip()`, `_draw_main_area()`, `_draw_status_ribbon()` moves here, translated from pygame draw calls to PIL `ImageDraw`. Both InkyMock (pygame) and SlateDisplay (real Inky) consume the resulting PIL Image.

**For M2:** Replace `BasicImageBackend` with one that calls AI image gen for the main area. Menu + status compositing stays.

### GPIO Button Listener

**`GPIOButtonListener`** (new class, lives alongside `KeyboardListener`):

```python
try:
    from gpiozero import Button
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False

class GPIOButtonListener(ButtonListener):
    def __init__(self, device="spark", on_exit=None):
        if device == "spark":
            pins = {"A": 5, "B": 6, "X": 16, "Y": 24}
        else:  # slate
            pins = {"A": 5, "B": 6, "C": 16, "D": 24}

        if HAS_GPIO:
            self.buttons = {name: Button(pin, pull_up=True, bounce_time=0.1)
                           for name, pin in pins.items()}
        else:
            self.fallback = KeyboardListener(device, on_exit)
```

BCM pins: 5 (A), 6 (B), 16 (X/C), 24 (Y/D). Same pins on both devices, different button names.

Conductor and Controller instantiate `GPIOButtonListener` instead of `KeyboardListener`. Falls back transparently on Mac.

### Systemd Units

Two service files in `deploy/`:

**`deploy/flyball-slate.service`:**
```ini
[Unit]
Description=Flyball Slate Conductor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/flyball
ExecStart=/home/pi/flyball/venv/bin/python -m conductor
Restart=always
RestartSec=10
Environment="FLYBALL_CONDUCTOR_HOST=0.0.0.0"

[Install]
WantedBy=multi-user.target
```

**`deploy/flyball-spark.service`:**
```ini
[Unit]
Description=Flyball Spark Controller
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/flyball
ExecStart=/home/pi/flyball/venv/bin/python -m controller
Restart=always
RestartSec=10
Environment="FLYBALL_CONDUCTOR_HOST=flyball-slate.local"

[Install]
WantedBy=multi-user.target
```

Code stays in `/home/pi/flyball` (git repo). No copying to `/opt`.

### Makefile Install Target (revised)

```makefile
install:
    sudo cp deploy/flyball-slate.service /etc/systemd/system/ 2>/dev/null || true
    sudo cp deploy/flyball-spark.service /etc/systemd/system/ 2>/dev/null || true
    sudo systemctl daemon-reload
```

Prints instructions to enable/start the appropriate service.

### Dependencies

Add to `requirements.txt`:
```
unicornhatmini>=0.0.4
inky[rpi]>=1.5.0
gpiozero>=2.0
```

These install on Mac too (harmless if unused). Hardware detection handles the fallback.

### Remove IS_SIMULATION

Replace all `IS_SIMULATION = platform.system() != "Linux"` checks in display and button modules with hardware detection (`HAS_UNICORN`, `HAS_INKY`, `HAS_GPIO`). Remove `IS_SIMULATION` from display modules. `shared/config.py` `IS_SIMULATION` stays for now (conductor/controller use it for other checks).

### Deployment Workflow

**First time on each Pi:**
```bash
ssh pi@flyball-slate.local
cd ~
git clone <repo> flyball
cd flyball
make setup
sudo make install
sudo systemctl enable --now flyball-slate
```

**Updating code:**
```bash
ssh pi@flyball-slate.local
cd ~/flyball
git pull
sudo systemctl restart flyball-slate
```

### Testing

**Mac:** `make conductor` + `make controller` works as before. Hardware libs install but ImportError on Mac → falls back to mock.

**Pi (manual first):** SSH in, `make conductor` / `make controller` in separate sessions. Verify real LEDs, real e-paper, real buttons.

**Pi (systemd):** After manual test works, enable systemd service + reboot to verify auto-start.

**Unit tests:** Add test verifying hardware detection flags and fallback behavior (mock the imports).

### Files Summary

| Action | Path |
|--------|------|
| Modify | `requirements.txt` (add hardware libs) |
| Modify | `shared/interfaces/image_backend.py` (add render_frame method) |
| Create | `shared/basic_image_backend.py` (PIL compositing from InkyMock) |
| Modify | `conductor/display.py` (SlateDisplay hardware, InkyMock receives PIL Image) |
| Modify | `controller/display.py` (SparkDisplay hardware detection + real Unicorn) |
| Modify | `controller/buttons.py` (add GPIOButtonListener) |
| Modify | `conductor/buttons.py` (add GPIOButtonListener) |
| Modify | `conductor/conductor.py` (use GPIOButtonListener, wire BasicImageBackend) |
| Modify | `controller/controller.py` (use GPIOButtonListener) |
| Create | `deploy/flyball-slate.service` |
| Create | `deploy/flyball-spark.service` |
| Modify | `Makefile` (revise install target) |
