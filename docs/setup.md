# Flyball Setup Guide

## Local Development (macOS)

### First Time Setup

```bash
cd flyball
make setup-dev    # venv + dev dependencies
make test         # 27 tests pass
```

### Running

Two terminals:

```bash
make conductor    # Terminal 1 — Slate pygame window opens
make controller   # Terminal 2 — Spark pygame window opens
```

Both windows stay on top. Click a window and press keys:
- **Spark window:** `a`/`b` prev/next, `x` commit, `y` shift
- **Slate window:** `a`/`b`/`c`/`d` switch channel
- Either window: `q` or close window to quit

Keypress feedback prints to each terminal.

### Development

```bash
make test                     # run all tests
make clean && make setup-dev  # rebuild from scratch
```

## Pi Zero Deployment

### Manual Install

On each Pi:

```bash
scp -r flyball/ pi@slate.local:~/
ssh pi@slate.local
cd flyball
make setup
make conductor    # on Slate Pi
# or
make controller   # on Spark Pi
```

### System Install (M5)

```bash
make install      # installs to /opt/flyball
sudo cp deploy/slate-conductor.service /etc/systemd/system/
sudo systemctl enable slate-conductor
sudo systemctl start slate-conductor
```

## Dependencies

**Runtime:** websockets 12.0, pydantic 2.5.0, pillow 10.1.0

**Dev/Test:** pytest 7.4.3, pytest-asyncio 0.21.1, pygame 2.5.2

## Troubleshooting

**Port 8765 in use** — `lsof -ti:8765 | xargs kill` or set `FLYBALL_CONDUCTOR_PORT`

**Import errors** — Use `make` targets (auto-activates venv)

**No make** — macOS: `xcode-select --install`
