# Flyball — Makefile for local dev + Pi deployment

.PHONY: help setup setup-inky setup-unicorn setup-dev venv conductor controller test clean install

VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

help:
	@echo "Flyball — make targets:"
	@echo ""
	@echo "  make setup-inky      One-time Slate Pi setup (Inky Impression drivers)"
	@echo "  make setup-unicorn   One-time Spark Pi setup (Unicorn HAT Mini drivers)"
	@echo "  make setup           Create venv + install runtime deps"
	@echo "  make setup-dev       Create venv + install runtime + dev/test deps"
	@echo "  make conductor       Run Conductor (Slate authority)"
	@echo "  make controller      Run Controller (Spark client)"
	@echo "  make test            Run test suite"
	@echo "  make clean           Remove venv + pycache"
	@echo "  make install         Install systemd services (Pi deployment)"
	@echo ""

# One-time Slate Pi setup — Inky Impression drivers
# Run on flyball-slate Pi only. Handles: SPI, I2C, config.txt, GPIO, Python drivers.
setup-inky:
	@if [ "$$(uname -s)" != "Linux" ]; then \
		echo "setup-inky is for Raspberry Pi only. Skipping on $$(uname -s)."; \
		exit 0; \
	fi
	@echo "Caching sudo credentials..."
	@sudo -v
	@echo ""
	@echo "=== Installing Pimoroni Inky (Slate display) ==="
	@echo ""
	@rm -rf /tmp/pimoroni-inky
	git clone --depth 1 https://github.com/pimoroni/inky /tmp/pimoroni-inky
	cd /tmp/pimoroni-inky && ./install.sh
	@echo ""
	@echo "✓ Inky drivers installed."
	@echo "  REBOOT REQUIRED: sudo reboot"
	@echo "  Then run: make setup"

# One-time Spark Pi setup — Unicorn HAT Mini drivers
# Run on flyball-spark Pi only. Handles: SPI, I2C, config.txt, GPIO, Python drivers.
# Detects Trixie/Bookworm and uses install-trixie.sh; older releases use stock installer.
setup-unicorn:
	@if [ "$$(uname -s)" != "Linux" ]; then \
		echo "setup-unicorn is for Raspberry Pi only. Skipping on $$(uname -s)."; \
		exit 0; \
	fi
	@echo "Caching sudo credentials..."
	@sudo -v
	@echo ""
	@echo "=== Installing Pimoroni Unicorn HAT Mini (Spark display) ==="
	@echo ""
	@rm -rf /tmp/pimoroni-unicorn
	git clone --depth 1 https://github.com/pimoroni/unicornhatmini-python /tmp/pimoroni-unicorn
	@if [ -f /etc/os-release ]; then \
		. /etc/os-release; \
		case "$${VERSION_CODENAME:-unknown}" in \
			trixie|bookworm) \
				echo "Detected $${VERSION_CODENAME} — using Trixie-compatible installer"; \
				cp deploy/unicornhatmini-trixie/install-trixie.sh /tmp/pimoroni-unicorn/; \
				chmod +x /tmp/pimoroni-unicorn/install-trixie.sh; \
				cd /tmp/pimoroni-unicorn && ./install-trixie.sh; \
				;; \
			*) \
				echo "Using stock installer"; \
				cd /tmp/pimoroni-unicorn && sudo ./install.sh; \
				;; \
		esac; \
	else \
		echo "Cannot detect OS release — using stock installer"; \
		cd /tmp/pimoroni-unicorn && sudo ./install.sh; \
	fi
	@echo ""
	@echo "✓ Unicorn HAT Mini drivers installed."
	@echo "  REBOOT REQUIRED: sudo reboot"
	@echo "  Then run: make setup"

venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating venv..."; \
		if [ "$$(uname -s)" = "Linux" ]; then \
			python3 -m venv --system-site-packages $(VENV); \
		else \
			python3 -m venv $(VENV); \
		fi; \
	fi

setup: venv
	@echo "Installing runtime dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "✓ Setup complete. Run 'make conductor' or 'make controller'"

setup-dev: venv
	@echo "Installing dev dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt
	@echo "✓ Dev setup complete. Run 'make test' to verify"

conductor: setup
	@echo "Starting Conductor (Slate authority)..."
	$(PYTHON) -m conductor

controller: setup
	@echo "Starting Controller (Spark client)..."
	$(PYTHON) -m controller

test: setup-dev
	@echo "Running tests..."
	$(PYTHON) -m pytest tests/ -v

clean:
	@echo "Cleaning up..."
	rm -rf $(VENV)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✓ Clean"

# Pi deployment: install systemd services (code stays in ~/flyball via git)
install:
	@echo "Installing systemd services..."
	sudo cp deploy/flyball-slate.service /etc/systemd/system/ 2>/dev/null || true
	sudo cp deploy/flyball-spark.service /etc/systemd/system/ 2>/dev/null || true
	sudo systemctl daemon-reload
	@echo ""
	@echo "Services installed. Enable the appropriate one:"
	@echo "  sudo systemctl enable --now flyball-slate   # on Slate Pi"
	@echo "  sudo systemctl enable --now flyball-spark   # on Spark Pi"
