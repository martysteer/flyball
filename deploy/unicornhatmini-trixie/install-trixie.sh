#!/bin/bash
# install-trixie.sh
#
# Unicorn HAT Mini installer for Raspberry Pi OS based on Debian 12 (Bookworm)
# and Debian 13 (Trixie). Drop this into the root of unicornhatmini-python and
# run it as your normal user (NOT with sudo):
#
#     ./install-trixie.sh
#
# The stock install.sh predates PEP 668 ("externally-managed-environment") and
# the removal of Python 2, so it can no longer work on Bookworm or Trixie.
# This script instead:
#
#   1. Installs system dependencies with apt
#   2. Creates a Python virtual environment at ~/.virtualenvs/pimoroni
#      (with --system-site-packages so it can see apt's spidev and the
#      RPi.GPIO -> lgpio compatibility shim)
#   3. Installs the unicornhatmini library into that venv from PyPI/piwheels
#   4. Enables SPI with the `spi0-2cs` overlay, relocating the kernel's
#      chip-select pins to spare GPIOs
#   5. Optionally copies the examples to ~/Pimoroni/unicornhatmini
#
# Why `dtoverlay=spi0-2cs,cs0_pin=27,cs1_pin=22` instead of `dtparam=spi=on`?
#   The library needs three things at once:
#     a) /dev/spidev0.0  (left LED driver chip)
#     b) /dev/spidev0.1  (right LED driver chip)
#     c) BCM 8 (CE0) and BCM 7 (CE1) free, because it drives the chip-select
#        lines itself via RPi.GPIO (it opens both spidev devices with
#        no_cs=True and bit-bangs CS around each transfer)
#   On Bookworm/Trixie, RPi.GPIO is really the rpi-lgpio shim, which requests
#   pins from the kernel instead of poking registers -- and the kernel will
#   not hand over pins it has already claimed:
#     - Plain `dtparam=spi=on` claims BCM 7/8 as the kernel's chip selects,
#       so (c) fails with `lgpio.error: 'GPIO busy'`.
#     - `dtoverlay=spi0-0cs` frees the pins but only creates /dev/spidev0.0,
#       so (b) fails with `FileNotFoundError` when opening SpiDev(0, 1).
#   Moving the kernel's chip selects to unused pins (27 and 22 by default)
#   satisfies all three: both spidev nodes exist, and BCM 7/8 are untouched.
#   The kernel never actually toggles 27/22 because the library sets no_cs,
#   but they are claimed at boot - change the pins below if you need them.

VENV_DIR="$HOME/.virtualenvs/pimoroni"
RESOURCES_DIR="$HOME/Pimoroni/unicornhatmini"
CONFIG_FILE="/boot/firmware/config.txt"
[ -f "$CONFIG_FILE" ] || CONFIG_FILE="/boot/config.txt"

# Kernel chip-select lines get parked on these spare pins. Avoid the pins the
# HAT actually uses: 10 (MOSI), 11 (SCLK), 8/7 (real CS) and the buttons on
# 5, 6, 16 and 24.
OVERLAY="dtoverlay=spi0-2cs,cs0_pin=27,cs1_pin=22"

APT_PACKAGES=(python3-full python3-venv python3-pip python3-spidev python3-pil python3-numpy)

REBOOT_REQUIRED=false
FORCE=false
[ "$1" = "-y" ] && FORCE=true

success() { echo -e "$(tput setaf 2)$1$(tput sgr0)"; }
inform()  { echo -e "$(tput setaf 6)$1$(tput sgr0)"; }
warning() { echo -e "$(tput setaf 1)$1$(tput sgr0)"; }
die()     { warning "$1"; exit 1; }

confirm() {
    $FORCE && return 0
    read -r -p "$1 [y/N] " response < /dev/tty
    [[ $response =~ ^(yes|y|Y)$ ]]
}

# --- sanity checks ----------------------------------------------------------

if [ "$(id -u)" -eq 0 ]; then
    warning "Do not run this script with sudo - the virtual environment must"
    warning "belong to your normal user. Run it as:  ./install-trixie.sh"
    warning "(it will call sudo itself for apt and config.txt changes)"
    exit 1
fi

command -v sudo >/dev/null || die "sudo is required."

if [ -f /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
fi
case "${VERSION_CODENAME:-unknown}" in
    trixie|bookworm)
        inform "Detected OS release: ${VERSION_CODENAME}" ;;
    bullseye|buster)
        die "This installer is for Bookworm/Trixie. On ${VERSION_CODENAME}, use the original install.sh instead." ;;
    *)
        warning "Unrecognised release '${VERSION_CODENAME:-unknown}' - continuing anyway; this should work on any Debian 12+ based Pi OS." ;;
esac

# --- system packages --------------------------------------------------------

inform "\nInstalling system packages with apt..."
sudo apt update || die "apt update failed."
sudo apt install -y "${APT_PACKAGES[@]}" || die "apt install failed."

# RPi.GPIO must be provided by the lgpio-backed shim on modern kernels.
# Raspberry Pi OS Trixie ships it by default; install it if missing.
if ! sudo apt install -y python3-rpi-lgpio 2>/dev/null; then
    sudo apt install -y python3-rpi.gpio \
        || warning "Could not install an RPi.GPIO provider. If 'import RPi.GPIO' fails later, install python3-rpi-lgpio manually."
fi

# --- virtual environment ----------------------------------------------------

if [ ! -f "$VENV_DIR/bin/activate" ]; then
    inform "\nCreating virtual environment: $VENV_DIR"
    mkdir -p "$(dirname "$VENV_DIR")"
    python3 -m venv --system-site-packages "$VENV_DIR" || die "Failed to create virtual environment."
else
    inform "\nUsing existing virtual environment: $VENV_DIR"
fi

# shellcheck disable=SC1091
. "$VENV_DIR/bin/activate"

inform "Installing unicornhatmini into the virtual environment..."
pip install --upgrade unicornhatmini || die "pip install unicornhatmini failed."

# --- SPI configuration ------------------------------------------------------

inform "\nConfiguring SPI in $CONFIG_FILE..."

if grep -Eq "^[[:space:]]*dtoverlay=spi0-2cs" "$CONFIG_FILE"; then
    inform "spi0-2cs overlay already enabled - nothing to do."
else
    BACKUP="$(dirname "$CONFIG_FILE")/config.preinstall-unicornhatmini-$(date +%Y-%m-%d-%H-%M-%S).txt"
    inform "Backing up $CONFIG_FILE to $BACKUP"
    sudo cp "$CONFIG_FILE" "$BACKUP"

    # `dtparam=spi=on` makes the kernel claim BCM 7/8 as chip selects,
    # which breaks this library (see header). Comment it out if present.
    if grep -Eq "^[[:space:]]*dtparam=spi=on" "$CONFIG_FILE"; then
        inform "Commenting out dtparam=spi=on (kernel would claim BCM 7/8)"
        sudo sed -i -E 's|^[[:space:]]*(dtparam=spi=on.*)|#\1|' "$CONFIG_FILE"
    fi

    # spi0-0cs (a workaround that works for single-device SPI boards) frees
    # the pins but removes /dev/spidev0.1, which this library also needs.
    if grep -Eq "^[[:space:]]*dtoverlay=spi0-0cs" "$CONFIG_FILE"; then
        inform "Commenting out dtoverlay=spi0-0cs (it does not provide /dev/spidev0.1)"
        sudo sed -i -E 's|^[[:space:]]*(dtoverlay=spi0-0cs.*)|#\1|' "$CONFIG_FILE"
    fi

    inform "Adding $OVERLAY"
    printf '\n[all]\n# Unicorn HAT Mini: SPI with both spidev nodes; kernel chip-selects parked\n# on spare pins so the library can drive BCM 7/8 itself\n%s\n' "$OVERLAY" \
        | sudo tee -a "$CONFIG_FILE" > /dev/null
    REBOOT_REQUIRED=true
fi

# --- examples ---------------------------------------------------------------

if [ -d "examples" ]; then
    if confirm "Would you like to copy examples to $RESOURCES_DIR?"; then
        mkdir -p "$RESOURCES_DIR"
        cp -r examples "$RESOURCES_DIR/"
        inform "Examples copied to $RESOURCES_DIR/examples"
    fi
fi

# --- done -------------------------------------------------------------------

success "\nAll done!"
echo
echo "To use the Unicorn HAT Mini (no sudo needed - and sudo would bypass the venv):"
echo
echo "    source $VENV_DIR/bin/activate"
echo "    python examples/demo.py"
echo
echo "In scripts, cron jobs or systemd services, call the venv's interpreter"
echo "directly: $VENV_DIR/bin/python your_script.py"
if [ "$REBOOT_REQUIRED" = true ]; then
    echo
    warning "SPI configuration changed - reboot before first use:  sudo reboot"
fi
