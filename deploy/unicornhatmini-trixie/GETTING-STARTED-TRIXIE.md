# Unicorn HAT Mini on Raspberry Pi OS Trixie (Debian 13)

These instructions replace the official [Getting Started guide](https://learn.pimoroni.com/article/getting-started-with-unicorn-hat-mini)
and the repo's `install.sh` for Raspberry Pi OS **Bookworm (Debian 12)** and
**Trixie (Debian 13)**. Tested target: Pi Zero 2 W, Trixie, Python 3.13.

Two things have changed since the official instructions were written:

1. **System-wide `pip` is blocked (PEP 668).** `sudo pip3 install unicornhatmini`
   now fails with `externally-managed-environment`. The library must be
   installed into a Python virtual environment instead.
2. **`RPi.GPIO` is now the `rpi-lgpio` shim**, which requests pins from the
   kernel instead of writing to hardware registers, and the kernel only lets
   one owner claim each pin. This matters because the library needs three
   things at once: `/dev/spidev0.0` (left LED driver), `/dev/spidev0.1`
   (right LED driver), and **free** BCM 8 (CE0) and BCM 7 (CE1), because it
   opens both spidev devices with `no_cs=True` and toggles the chip-select
   lines itself via `RPi.GPIO`.
   - The ordinary `dtparam=spi=on` provides both spidev nodes but the kernel
     claims BCM 7/8 as its chip selects → `lgpio.error: 'GPIO busy'`.
   - The commonly suggested `dtoverlay=spi0-0cs` frees the pins but only
     creates `/dev/spidev0.0` → `FileNotFoundError` opening `SpiDev(0, 1)`.
   - The fix that satisfies all three is `spi0-2cs` with the kernel's
     chip selects **relocated to spare pins**:
     `dtoverlay=spi0-2cs,cs0_pin=27,cs1_pin=22`

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

### 3. Enable SPI with relocated chip selects

Do **not** use `sudo raspi-config nonint do_spi 0` on its own — that writes
`dtparam=spi=on`, which causes the `'GPIO busy'` error described above. And do
**not** use `dtoverlay=spi0-0cs` — that removes `/dev/spidev0.1`, which this
board needs. Instead edit `/boot/firmware/config.txt`:

```bash
sudo sed -i 's/^dtparam=spi=on/#dtparam=spi=on/' /boot/firmware/config.txt
printf '\n[all]\ndtoverlay=spi0-2cs,cs0_pin=27,cs1_pin=22\n' | sudo tee -a /boot/firmware/config.txt
sudo reboot
```

This enables SPI0 with both spidev device nodes, but parks the kernel's two
chip-select lines on GPIO 27 and 22 instead of 8 and 7. The library sets
`no_cs`, so the kernel never actually toggles them — they just need to point
somewhere that isn't BCM 7/8. GPIO 27 and 22 do get *claimed* at boot, though,
so if you need those pins for something else, substitute any other two free
GPIOs (avoid 8/7/9/10/11 and the HAT's buttons on 5, 6, 16 and 24).

After rebooting, verify:

```bash
ls /dev/spidev*        # should list /dev/spidev0.0 AND /dev/spidev0.1
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

**`lgpio.error: 'GPIO busy'`** — the kernel still owns BCM 7/8 (usually because
`dtparam=spi=on` is active, which claims them as `spi0 CS0`/`CS1`). Comment it
out, use the `spi0-2cs` overlay from step 3, and reboot. To inspect ownership:
`sudo apt install gpiod` then `gpioinfo | grep -E 'GPIO[78]"'` — both pins
should show as `unused`.

**`FileNotFoundError` at `spidev.SpiDev(0, 1)`** — `/dev/spidev0.1` doesn't
exist. This is what you get with `dtoverlay=spi0-0cs`, which only creates
`spidev0.0`. Switch to the `spi0-2cs` line from step 3 and reboot.

**`FileNotFoundError` at `spidev.SpiDev(0, 0)`** — SPI isn't enabled at all.
Add the overlay from step 3 and reboot; `ls /dev/spidev*` should then list
both nodes.

**Display works but buttons don't** — the four buttons are on BCM 5, 6, 16
and 24 and use the same `RPi.GPIO` shim; make sure nothing else has claimed
those pins (`gpioinfo`), and run the `buttons.py` example from the venv.

**Old installers** — `install.sh` (tries Python 2 and system pip) and
`install-bullseye.sh` in this repo are for older OS releases and will not work
on Bookworm/Trixie.
