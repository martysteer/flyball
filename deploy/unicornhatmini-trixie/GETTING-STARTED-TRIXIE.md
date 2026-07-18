# Unicorn HAT Mini on Raspberry Pi OS Trixie (Debian 13)

These instructions replace the official [Getting Started guide](https://learn.pimoroni.com/article/getting-started-with-unicorn-hat-mini)
and the repo's `install.sh` for Raspberry Pi OS **Bookworm (Debian 12)** and
**Trixie (Debian 13)**. Tested target: Pi Zero 2 W, Trixie, Python 3.13.

Two things have changed since the official instructions were written:

1. **System-wide `pip` is blocked (PEP 668).** `sudo pip3 install unicornhatmini`
   now fails with `externally-managed-environment`. The library must be
   installed into a Python virtual environment instead.
2. **`RPi.GPIO` is now the `rpi-lgpio` shim.** It requests pins from the kernel
   rather than writing to hardware registers, and the kernel only lets one
   owner claim a pin. The Unicorn HAT Mini library drives the two SPI
   chip-select lines (BCM 8 / CE0 and BCM 7 / CE1) itself, but the ordinary
   `dtparam=spi=on` setting makes the kernel's SPI driver claim those pins
   first — so the library crashes with `lgpio.error: 'GPIO busy'`.
   The fix is to enable SPI with the `spi0-0cs` overlay ("SPI0, zero chip
   selects"), which provides `/dev/spidev0.0` but leaves BCM 7/8 free.

## Quick install

```bash
git clone https://github.com/pimoroni/unicornhatmini-python
cd unicornhatmini-python
# copy install-trixie.sh into this directory, then:
chmod +x install-trixie.sh
./install-trixie.sh        # run as your normal user, NOT sudo
sudo reboot
```

After rebooting:

```bash
source ~/.virtualenvs/pimoroni/bin/activate
python ~/unicornhatmini-python/examples/demo.py
```

## Manual install

If you would rather do it by hand, these are the steps the script performs.

### 1. System packages

```bash
sudo apt update
sudo apt install python3-full python3-spidev python3-pil python3-numpy python3-rpi-lgpio
```

(`python3-rpi-lgpio` is preinstalled on Raspberry Pi OS Trixie; installing it
again is harmless.)

### 2. Virtual environment + library

```bash
python3 -m venv --system-site-packages ~/.virtualenvs/pimoroni
source ~/.virtualenvs/pimoroni/bin/activate
pip install unicornhatmini
```

`--system-site-packages` matters: it lets the venv see apt's `spidev` and the
`RPi.GPIO` shim. The package is `unicornhatmini` — `unicornhathd` is a
different product (Unicorn HAT HD) and will not drive this board.

### 3. Enable SPI via the spi0-0cs overlay

Do **not** use `sudo raspi-config nonint do_spi 0` on its own — that writes
`dtparam=spi=on`, which causes the `'GPIO busy'` error described above.
Instead edit `/boot/firmware/config.txt`:

```bash
sudo sed -i 's/^dtparam=spi=on/#dtparam=spi=on/' /boot/firmware/config.txt
printf '\n[all]\ndtoverlay=spi0-0cs\n' | sudo tee -a /boot/firmware/config.txt
sudo reboot
```

### 4. Run an example

```bash
source ~/.virtualenvs/pimoroni/bin/activate
cd ~/unicornhatmini-python/examples
python demo.py
```

No `sudo` — your user is already in the `spi` and `gpio` groups, and `sudo`
would run the system Python instead of the venv. Remember to activate the venv
in every new shell, or call the interpreter directly:

```bash
~/.virtualenvs/pimoroni/bin/python demo.py
```

### Running at boot (systemd)

```ini
[Unit]
Description=Unicorn HAT Mini display
After=multi-user.target

[Service]
User=pi
ExecStart=/home/pi/.virtualenvs/pimoroni/bin/python /home/pi/my_display.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Troubleshooting

**`error: externally-managed-environment`** — you ran `pip`/`pip3` outside the
virtual environment (or with `sudo`). Activate the venv first.

**`ModuleNotFoundError: No module named 'unicornhatmini'`** — either the venv
isn't activated in this shell, or you installed `unicornhathd` (wrong board)
instead of `unicornhatmini`.

**`lgpio.error: 'GPIO busy'`** — the kernel SPI driver still owns the
chip-select pins. Check `/boot/firmware/config.txt`: `dtparam=spi=on` must be
commented out, `dtoverlay=spi0-0cs` must be present, and you must reboot after
changing it. You can verify with `sudo apt install gpiod` and
`gpioinfo | grep -E 'GPIO[78]"'` — the pins should show as `unused`, not
`"spi0 CS0"` / `"spi0 CS1"`.

**`FileNotFoundError: /dev/spidev0.0`** — SPI isn't enabled at all. Make sure
`dtoverlay=spi0-0cs` is in `/boot/firmware/config.txt` and reboot;
`ls /dev/spidev*` should then list `/dev/spidev0.0`.

**Display works but buttons don't** — the four buttons are on BCM 5, 6, 16
and 24 and use the same `RPi.GPIO` shim; make sure nothing else has claimed
those pins (`gpioinfo`), and run the `buttons.py` example from the venv.

**Old installers** — `install.sh` (tries Python 2 and system pip) and
`install-bullseye.sh` in this repo are for older OS releases and will not work
on Bookworm/Trixie.
