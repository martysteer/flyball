# Flyball — Makefile for local dev + Pi deployment

.PHONY: help setup setup-pi setup-dev venv conductor controller test clean install

VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

help:
	@echo "Flyball — make targets:"
	@echo ""
	@echo "  make setup-pi     One-time Pi hardware setup (Pimoroni drivers — needs reboot)"
	@echo "  make setup        Create venv + install runtime deps"
	@echo "  make setup-dev    Create venv + install runtime + dev/test deps"
	@echo "  make conductor    Run Conductor (Slate authority)"
	@echo "  make controller   Run Controller (Spark client)"
	@echo "  make test         Run test suite"
	@echo "  make clean        Remove venv + pycache"
	@echo "  make install      Install systemd services (Pi deployment)"
	@echo ""

# One-time Pi hardware setup — run once per Pi, then reboot
# Clones and runs official Pimoroni installers for Inky + Unicorn HAT Mini.
# Handles: SPI, I2C, config.txt overlays, system GPIO packages, Python drivers.
setup-pi:
	@if [ "$$(uname -s)" != "Linux" ]; then \
		echo "setup-pi is for Raspberry Pi only. Skipping on $$(uname -s)."; \
		exit 0; \
	fi
	@echo "=== Installing Pimoroni Inky (Slate display) ==="
	@echo ""
	@if [ ! -d "$$HOME/inky" ]; then \
		git clone --depth 1 https://github.com/pimoroni/inky $$HOME/inky; \
	else \
		echo "$$HOME/inky already exists, skipping clone"; \
	fi
	cd $$HOME/inky && sudo ./install.sh
	@echo ""
	@echo "=== Installing Pimoroni Unicorn HAT Mini (Spark display) ==="
	@echo ""
	@if [ ! -d "$$HOME/unicornhatmini-python" ]; then \
		git clone --depth 1 https://github.com/pimoroni/unicornhatmini-python $$HOME/unicornhatmini-python; \
	else \
		echo "$$HOME/unicornhatmini-python already exists, skipping clone"; \
	fi
	cd $$HOME/unicornhatmini-python && sudo ./install.sh
	@echo ""
	@echo "✓ Pimoroni drivers installed."
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
	@echo "  (Hardware lib build failures on Mac are expected — hardware detection handles fallback)"

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
