# Flyball Setup Guide

## Local Development (macOS)

### First Time Setup

```bash
# Clone repo (if needed)
cd flyball

# Create venv + install dev dependencies
make setup-dev

# Run tests to verify
make test
```

### Running

**Two terminals:**

Terminal 1 (Conductor/Slate):
```bash
make conductor
```

Terminal 2 (Controller/Spark):
```bash
make controller
```

**Press keys:**
- Conductor terminal: `a/b/c/d` to switch channels
- Controller terminal: `a/b/x/y` to cycle/commit options
- Either terminal: `q` to quit

### Development

```bash
# Run tests
make test

# Clean up venv
make clean

# Rebuild from scratch
make clean && make setup-dev
```

## Pi Zero Deployment

### Option A: Manual Install (Simple)

On each Pi Zero:

```bash
# Copy files to Pi
scp -r flyball/ pi@slate.local:~/

# SSH to Pi
ssh pi@slate.local

# Install
cd flyball
make setup

# Run conductor (on Slate Pi)
make conductor

# Or run controller (on Spark Pi)
make controller
```

### Option B: System Install (Production)

On each Pi:

```bash
cd flyball
make install
```

This installs to `/opt/flyball` system-wide.

Then set up systemd services (M5):
```bash
sudo cp deploy/slate-conductor.service /etc/systemd/system/
sudo systemctl enable slate-conductor
sudo systemctl start slate-conductor
```

## Dependencies

### Runtime (both Pis)
- Python 3.11+
- websockets 12.0
- pydantic 2.5.0
- pillow 10.1.0

### Dev/Test (macOS only)
- pytest 7.4.3
- pytest-asyncio 0.21.1

## Troubleshooting

**"command not found: make"**
- macOS: Install Xcode Command Line Tools: `xcode-select --install`
- Pi: Should be pre-installed on Raspberry Pi OS

**PIL image doesn't open**
- macOS: Pillow uses default image viewer
- Verify Pillow installed: `venv/bin/python -c "from PIL import Image"`

**Import errors**
- Make sure venv is activated or use `make` targets (auto-activates)
- Verify: `which python` should show `flyball/venv/bin/python`

**Port 8765 in use**
- Kill existing process: `lsof -ti:8765 | xargs kill`
- Or change port in `shared/config.py` + env var `FLYBALL_CONDUCTOR_PORT`
