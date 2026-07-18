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
#   4. Enables SPI using the `spi0-0cs` device tree overlay
#   5. Optionally copies the examples to ~/Pimoroni/unicornhatmini
#
# Why `dtoverlay=spi0-0cs` instead of plain `dtparam=spi=on`?
#   The Unicorn HAT Mini has two LED driver chips sharing SPI0, and the Python
#   library toggles their chip-select lines (BCM 8 / CE0 and BCM 7 / CE1)
#   itself via RPi.GPIO. On Bookworm/Trixie, RPi.GPIO is really the rpi-lgpio
#   shim, which requests pins from the kernel instead of poking registers --
#   and the kernel will not hand over pins the SPI driver has already claimed
#   as its chip selects. That is the `lgpio.error: 'GPIO busy'` crash.
#   The spi0-0cs overlay enables SPI0 *without* claiming any chip-select
#   pins, leaving BCM 7/8 free for the library to drive.

VENV_DIR="$HOME/.virtualenvs/pimoroni"
RESOURCES_DIR="$HOME/Pimoroni/unicornhatmini"
CONFIG_FILE="/boot/firmware/config.txt"
[ -f "$CONFIG_FILE" ] || CONFIG_FILE="/boot/config.txt"

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

if grep -Eq "^[[:space:]]*dtoverlay=spi0-0cs" "$CONFIG_FILE"; then
    inform "spi0-0cs overlay already enabled - nothing to do."
else
    BACKUP="$(dirname "$CONFIG_FILE")/config.preinstall-unicornhatmini-$(date +%Y-%m-%d-%H-%M-%S).txt"
    inform "Backing up $CONFIG_FILE to $BACKUP"
    sudo cp "$CONFIG_FILE" "$BACKUP"

    # Plain `dtparam=spi=on` makes the kernel claim BCM 7/8 as chip selects,
    # which breaks this library (see header). Comment it out if present.
    if grep -Eq "^[[:space:]]*dtparam=spi=on" "$CONFIG_FILE"; then
        inform "Commenting out dtparam=spi=on (replaced by spi0-0cs)"
        sudo sed -i -E 's|^[[:space:]]*(dtparam=spi=on.*)|#\1|' "$CONFIG_FILE"
    fi

    inform "Adding dtoverlay=spi0-0cs"
    printf '\n[all]\n# Unicorn HAT Mini: enable SPI with no kernel-claimed chip-select pins\ndtoverlay=spi0-0cs\n' \
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
