# Flyball Pi Deployment Guide

Two Raspberry Pi Zero 2 W boards: **Slate** (Inky Impression 4") and **Spark** (Unicorn HAT Mini).

## Deploy (fresh SD card)

Flash Raspberry Pi OS Lite (Bookworm+), enable SSH + WiFi, boot, then:

```bash
# 1. Set hostname (on each Pi)
sudo hostnamectl set-hostname flyball-slate   # or flyball-spark
sudo reboot

# 2. Clone repo
cd ~ && git clone https://github.com/YOUR_USERNAME/flyball.git && cd flyball

# 3. Install Pimoroni hardware drivers (one-time, device-specific)
# On flyball-slate (Inky Impression):
make setup-inky

# On flyball-spark (Unicorn HAT Mini):
make setup-unicorn
# Detects Trixie/Bookworm and uses venv-based installer automatically
# Older releases use stock installer

# When prompted to install examples, press Y — lets you test hardware separately from Flyball
# Examples install to ~/Pimoroni/inky or ~/Pimoroni/unicornhatmini
sudo reboot

# 4. Install Flyball app dependencies
make setup

# 5. Install and enable systemd service
make install
sudo systemctl enable --now flyball-slate    # or flyball-spark
```

## Verify

```bash
# Check service
sudo systemctl status flyball-slate          # or flyball-spark

# Watch logs
sudo journalctl -u flyball-slate -f          # or flyball-spark

# Check I2C (Slate: 0x50 EEPROM, Spark: 0x77 LED driver)
sudo i2cdetect -y 1
```

## Update Code

```bash
cd ~/flyball
git pull
sudo systemctl restart flyball-slate         # or flyball-spark
```

## Service Details

| Service | Command | Network | Role |
|---------|---------|---------|------|
| `flyball-slate` | `python -m conductor` | Binds `0.0.0.0:8765` | State authority, Inky display |
| `flyball-spark` | `python -m controller` | Connects to `flyball-slate.local:8765` | LED UI, button events |

Override Conductor host on Spark:
```bash
sudo systemctl edit flyball-spark
# Add: Environment="FLYBALL_CONDUCTOR_HOST=192.168.1.42"
```

## Troubleshooting

**Spark can't connect to Slate:**
```bash
ping flyball-slate.local                     # test mDNS
hostname -I                                  # get IP (run on Slate)
export FLYBALL_CONDUCTOR_HOST=<slate-ip>     # override on Spark
```

**GPIO / lgpio errors:** `make setup-pi && sudo reboot && make clean && make setup`

**Service won't start:** `sudo journalctl -u flyball-slate -n 50`

**HAT not detected:** power off, reseat on all 40 GPIO pins, check `sudo i2cdetect -y 1`

**Inky not refreshing:** normal refresh takes ~30-40s. Check logs for render messages.

**Trixie/Bookworm (Debian 12+):** On Trixie, Unicorn HAT Mini install uses `~/.virtualenvs/pimoroni` venv and `dtoverlay=spi0-2cs` instead of `dtparam=spi=on`. See `deploy/unicornhatmini-trixie/GETTING-STARTED-TRIXIE.md` for details. The Makefile detects this automatically.

**Both HATs on same Pi (testing/dev):** If you ran both `make setup-inky` and `make setup-unicorn` on the same Pi, check SPI config:
```bash
grep spi /boot/firmware/config.txt
# Bullseye and earlier: dtparam=spi=on
# Trixie/Bookworm: dtoverlay=spi0-2cs,cs0_pin=27,cs1_pin=22
# Need both /dev/spidev0.0 (Inky) and /dev/spidev0.1 (Unicorn)
sudo reboot  # after editing config.txt
```
