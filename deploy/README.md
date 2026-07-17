# Flyball Pi Deployment Guide

Deploy Flyball to two Raspberry Pi Zero 2 W boards: one Slate (Inky Impression), one Spark (Unicorn HAT Mini).

## Prerequisites

**Two Pi Zero 2 W boards:**
- Slate: Inky Impression 4" (640×400, 7-colour e-paper)
- Spark: Unicorn HAT Mini (17×7 RGB LED matrix)

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
```

**On Spark Pi:**
```bash
sudo hostnamectl set-hostname flyball-spark
```

Reboot both Pis. Verify discovery:
```bash
# From Spark, ping Slate
ping -c 3 flyball-slate.local

# From Slate, ping Spark
ping -c 3 flyball-spark.local
```

## Step 1.5: Enable I2C and Verify Hardware

**On both Pis:**

1. **Enable I2C interface:**
```bash
sudo raspi-config
```
Navigate to: `Interface Options → I2C → Enable`

Reboot after enabling.

2. **Verify HAT is properly seated:**
   - Power off the Pi
   - Ensure HAT is firmly seated on all 40 GPIO pins
   - No gaps between HAT and Pi header
   - Power on

3. **Check I2C devices detected:**

**On Slate Pi (Inky Impression):**
```bash
sudo i2cdetect -y 1
```

Expected output should show device at `0x50` (EEPROM):
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50: 50 -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- --
```

**On Spark Pi (Unicorn HAT Mini):**
```bash
sudo i2cdetect -y 1
```

Expected output should show device at `0x77` (IS31FL3731 LED driver):
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- 77
```

**If devices not detected:**
- Reseat HAT firmly on GPIO header
- Check for bent pins
- Verify I2C is enabled in raspi-config
- Try a different power supply (low voltage can cause I2C issues)

**Fallback behavior:**
If hardware detection fails, both apps fall back to pygame mock windows. This allows testing the WebSocket bus and state machine without physical displays. Hardware detection happens at startup in `SlateDisplay` and `SparkDisplay` classes.

## Step 2: Clone Repository

**On both Pis:**
```bash
cd ~
git clone https://github.com/YOUR_USERNAME/flyball.git
cd flyball
```

## Step 3: Install Dependencies

**On both Pis:**
```bash
make setup
```

This creates a venv and installs:
- WebSocket client/server (`websockets`)
- Image compositing (`pillow`)
- Display mocks for debugging (`pygame`)
- Hardware drivers (`unicornhatmini`, `inky[rpi]`, `gpiozero`)

Hardware driver build failures on non-Pi platforms are expected — hardware detection falls back to mocks. On real Pis, drivers should compile successfully.

## Step 4: Install systemd Services

**On Slate Pi:**
```bash
cd ~/flyball
make install
sudo systemctl enable flyball-slate
sudo systemctl start flyball-slate
```

**On Spark Pi:**
```bash
cd ~/flyball
make install
sudo systemctl enable flyball-spark
sudo systemctl start flyball-spark
```

Services start automatically on boot with `Restart=always`.

## Step 5: Verify Running

**Check service status:**
```bash
# On Slate
sudo systemctl status flyball-slate

# On Spark
sudo systemctl status flyball-spark
```

**View logs:**
```bash
# On Slate
sudo journalctl -u flyball-slate -f

# On Spark
sudo journalctl -u flyball-spark -f
```

Spark should log:
```
INFO: Connected to Conductor at ws://flyball-slate.local:8765
```

Slate should log:
```
INFO: Controller connected
```

## Service Files

### flyball-slate.service
- Runs: `python -m conductor`
- Binds: `0.0.0.0:8765` (listens on all interfaces)
- Role: State authority, WebSocket server, image generation, Inky display driver

### flyball-spark.service
- Runs: `python -m controller`
- Connects to: `flyball-slate.local:8765`
- Role: LED UI, button events, WebSocket client

Override Conductor host via environment:
```bash
sudo systemctl edit flyball-spark
```
Add:
```ini
[Service]
Environment="FLYBALL_CONDUCTOR_HOST=192.168.1.42"
```

## Hardware Detection

Both apps detect hardware at startup:

**Slate:**
- Tries `from inky.auto import auto` → real Inky Impression
- Falls back to `InkyMock` (pygame window) if import fails

**Spark:**
- Tries `from unicornhatmini import UnicornHATMini` → real LED matrix
- Falls back to `SparkMock` (pygame window) if import fails

**Buttons (both):**
- Tries `gpiozero` for BCM 5/6/16/24 GPIO listeners
- Falls back to `KeyboardListener` (pygame key events) if GPIO unavailable

Run on a Mac or Linux dev machine → mocks render in pygame windows. Run on a Pi with HATs attached → hardware drivers activate.

## Button Mapping

**Slate (Inky Impression 4 buttons, left edge, top to bottom):**
- A → Subject channel
- B → Context channel
- C → Style channel
- D → Engine channel (loop settings)

**Spark (Unicorn HAT Mini 4 buttons, corners):**
- A (top-left) → Previous option
- B (bottom-left) → Next option
- X (top-right) → Commit option to sentence
- Y (bottom-right) → Shift mode (reserved for future)

See `docs/02-interaction-model.md` for full button semantics.

## Stopping Services

```bash
# On Slate
sudo systemctl stop flyball-slate

# On Spark
sudo systemctl stop flyball-spark
```

## Disabling Auto-Start

```bash
# On Slate
sudo systemctl disable flyball-slate

# On Spark
sudo systemctl disable flyball-spark
```

## Troubleshooting

### Spark can't connect to Slate

**Check mDNS resolution:**
```bash
# On Spark
ping flyball-slate.local
```

If fails, try IP directly:
```bash
# Find Slate IP
hostname -I  # run on Slate

# Override on Spark
export FLYBALL_CONDUCTOR_HOST=192.168.1.42
venv/bin/python -m controller
```

**Check firewall:**
Slate must allow incoming TCP 8765:
```bash
# On Slate
sudo ufw allow 8765/tcp
```

### Service won't start

**Check logs:**
```bash
sudo journalctl -u flyball-slate -n 50
```

Common issues:
- Missing `word_blocks.json` → ensure `shared/data/word_blocks.json` exists
- Python import errors → re-run `make setup`
- GPIO permission denied → service runs as `pi` user, should have GPIO access by default

### Display not updating

**Slate (Inky):**
- Inky refresh takes ~30–40s, check logs for "Rendering frame" messages
- Verify Inky HAT seated correctly on GPIO header

**Spark (Unicorn HAT Mini):**
- Check logs for "Updating Spark display" messages
- Verify HAT seated correctly and I2C enabled:
```bash
sudo raspi-config
# Interface Options → I2C → Enable
```

### Re-deploying Code Changes

```bash
cd ~/flyball
git pull
sudo systemctl restart flyball-slate  # or flyball-spark
```

Services run from `~/flyball` — no separate install step needed after initial `make install`.

## Network Architecture

```
┌──────────────────┐         WebSocket          ┌──────────────────┐
│  Spark (client)  │  ─────────────────────────>│  Slate (server)  │
│                  │                             │                  │
│ Unicorn HAT Mini │<────────────────────────────│ Inky Impression  │
│ 17×7 RGB + 4 btn │     JSON state messages    │ 640×400 + 4 btn  │
│                  │                             │                  │
│ flyball-spark    │                             │ flyball-slate    │
│   .local:*       │                             │   .local:8765    │
└──────────────────┘                             └──────────────────┘
        │                                                 │
        └─────────────────── LAN ──────────────────────┘
```

- Slate binds `:8765` and serves WebSocket
- Spark resolves `flyball-slate.local` via mDNS (avahi) and connects
- All state authority on Slate; Spark is a thin LED+button UI

## Next Steps

- Configure image generation API key (M2): see `docs/04-prompt-engine.md`
- Enable evolution loop (M3): ENGINE channel → Loop=ON
- Add boot resilience (M5): state persistence across reboots

See `docs/05-roadmap.md` for milestone progress.
