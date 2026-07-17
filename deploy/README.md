# Flyball Pi Deployment Guide

Deploy Flyball to two Raspberry Pi Zero 2 W boards: one Slate (Inky Impression), one Spark (Unicorn HAT Mini).

## Prerequisites

**Two Pi Zero 2 W boards:**
- Slate: Inky Impression 4" (640x400, 7-colour e-paper)
- Spark: Unicorn HAT Mini (17x7 RGB LED matrix)

**Both Pis:**
- Raspberry Pi OS Lite (Bookworm or later)
- Same router/LAN, WiFi configured
- SSH enabled
- Python 3.11+

## Step 1: Configure Hostnames

Set hostnames so devices discover each other via mDNS.

**On Slate Pi:**
```bash
sudo hostnamectl set-hostname flyball-slate
sudo reboot
```

**On Spark Pi:**
```bash
sudo hostnamectl set-hostname flyball-spark
sudo reboot
```

Verify discovery:
```bash
# From Spark, ping Slate
ping -c 3 flyball-slate.local
```

## Step 2: Hardware Setup (one-time)

Power off each Pi, seat HAT firmly on all 40 GPIO pins, power on. Then:

**On both Pis:**
```bash
cd ~/flyball
make setup-pi
```

This runs the Pimoroni-equivalent hardware setup:
- Enables **SPI** (required by both Unicorn HAT Mini and Inky Impression)
- Enables **I2C** (required by Inky Impression EEPROM and Unicorn HAT Mini LED driver)
- Adds `/boot/firmware/config.txt` overlays for Inky: `dtoverlay=spi0-0cs`, `dtoverlay=i2c1`
- Installs **python3-lgpio** system package (GPIO pin factory for gpiozero)

**Reboot required after `setup-pi`:**
```bash
sudo reboot
```

### Verify hardware after reboot

**On Slate Pi (Inky Impression):**
```bash
sudo i2cdetect -y 1
```

Expected: device at `0x50` (EEPROM):
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
50: 50 -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
```

**On Spark Pi (Unicorn HAT Mini):**
```bash
sudo i2cdetect -y 1
```

Expected: device at `0x77` (IS31FL3731 LED driver):
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
70: -- -- -- -- -- -- -- 77
```

**If devices not detected:**
- Power off, reseat HAT on GPIO header, check for bent pins
- Verify SPI/I2C enabled: `sudo raspi-config` > Interface Options
- Try a different power supply (low voltage causes I2C issues)

## Step 3: Install Dependencies

**On both Pis:**
```bash
cd ~/flyball
make setup
```

Creates a venv (with `--system-site-packages` for GPIO access) and installs:
- `websockets` — WebSocket client/server
- `pillow` — image compositing
- `pygame` — display mocks (dev/debug)
- `unicornhatmini` — LED matrix driver
- `inky` — e-paper driver
- `gpiozero` — button GPIO (uses system `lgpio` as pin factory)

If setup ends with `lgpio not found`, run `make setup-pi` first.

## Step 4: Install systemd Services

**On both Pis:**
```bash
make install
```

**On Slate Pi:**
```bash
sudo systemctl enable --now flyball-slate
```

**On Spark Pi:**
```bash
sudo systemctl enable --now flyball-spark
```

Services start automatically on boot with `Restart=always`.

## Step 5: Verify Running

```bash
# On Slate
sudo systemctl status flyball-slate
sudo journalctl -u flyball-slate -f

# On Spark
sudo systemctl status flyball-spark
sudo journalctl -u flyball-spark -f
```

Slate should log:
```
INFO: Starting Conductor server...
INFO: WebSocket server listening on ws://localhost:8765
```

Spark should log:
```
INFO: Connected to Conductor at ws://flyball-slate.local:8765
```

## Service Files

### flyball-slate.service
- Runs: `python -m conductor`
- Binds: `0.0.0.0:8765` (WebSocket server on all interfaces)
- Role: State authority, image generation, Inky display driver

### flyball-spark.service
- Runs: `python -m controller`
- Connects to: `flyball-slate.local:8765`
- Role: LED UI, button events, WebSocket client

Override Conductor host:
```bash
sudo systemctl edit flyball-spark
```
```ini
[Service]
Environment="FLYBALL_CONDUCTOR_HOST=192.168.1.42"
```

## Hardware Detection

On Pi hardware, apps exit with a clear error if hardware isn't detected.
On Mac/Linux (simulation mode), apps fall back to pygame mock windows.

**Slate:** `from inky.auto import auto` > real Inky, or exit on Pi
**Spark:** `from unicornhatmini import UnicornHATMini` > real LED matrix, or exit on Pi
**Buttons:** `gpiozero.Button` with `lgpio` pin factory, or exit on Pi

## Button Mapping

**Slate (Inky Impression, 4 buttons down left edge):**
- A > Subject channel
- B > Context channel
- C > Style channel
- D > Engine channel

**Spark (Unicorn HAT Mini, 4 buttons at corners):**
- A (top-left) > Previous option
- B (bottom-left) > Next option
- X (top-right) > Commit option to sentence
- Y (bottom-right) > Shift mode

See `docs/02-interaction-model.md` for full button semantics.

## Managing Services

```bash
# Stop
sudo systemctl stop flyball-slate   # or flyball-spark

# Disable auto-start
sudo systemctl disable flyball-slate

# Re-deploy code changes
cd ~/flyball
git pull
sudo systemctl restart flyball-slate  # or flyball-spark
```

## Troubleshooting

### Spark can't connect to Slate

```bash
ping flyball-slate.local
```

If fails, override with IP:
```bash
# Find Slate IP (run on Slate)
hostname -I

# On Spark
export FLYBALL_CONDUCTOR_HOST=192.168.1.42
venv/bin/python -m controller
```

Slate must allow TCP 8765: `sudo ufw allow 8765/tcp`

### lgpio not found / GPIO errors

```bash
make setup-pi   # installs python3-lgpio, enables SPI/I2C
sudo reboot
make clean
make setup
```

### Service won't start

```bash
sudo journalctl -u flyball-slate -n 50
```

Common issues:
- Missing `word_blocks.json` > ensure `shared/data/word_blocks.json` exists
- GPIO permission denied > service runs as `pi` user, add to `gpio` group if needed
- lgpio not found > run `make setup-pi` and reboot

### Display not updating

**Slate:** Inky refresh takes ~30-40s. Check logs for render messages.
**Spark:** Check HAT is seated. Verify I2C: `sudo i2cdetect -y 1`

## Network Architecture

```
+------------------+         WebSocket          +------------------+
|  Spark (client)  |  ________________________> |  Slate (server)  |
|                  |                             |                  |
| Unicorn HAT Mini | <_________________________ | Inky Impression  |
| 17x7 RGB + 4 btn |     JSON state messages    | 640x400 + 4 btn  |
|                  |                             |                  |
| flyball-spark    |                             | flyball-slate    |
|   .local         |                             |   .local:8765    |
+------------------+                             +------------------+
        |                                                 |
        +---------------------- LAN ----------------------+
```

- Slate binds `:8765` and serves WebSocket
- Spark resolves `flyball-slate.local` via mDNS (avahi) and connects
- All state authority on Slate; Spark is a thin LED+button UI
