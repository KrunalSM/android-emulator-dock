.PHONY: help build install uninstall clean dev test

PREFIX ?= ~/.local

help:
	@echo "Android Emulator Dock (AED) Makefile"
	@echo ""
	@echo "Usage:"
	@echo "  make install    - Install AED for the current user (binaries, desktop entry, icon)"
	@echo "  make uninstall  - Remove AED and its desktop integration"
	@echo "  make build      - Build the Python wheel package into dist/"
	@echo "  make dev        - Setup a local development virtual environment"
	@echo "  make test       - Run the test suite"
	@echo "  make clean      - Clean build artifacts and caches"

build:
	python3 -m pip wheel . -w dist/

install:
	@echo "Installing Python package..."
	python3 -m pip install --user .
	@echo "Installing desktop entry and icon..."
	mkdir -p $(PREFIX)/share/icons/hicolor/512x512/apps/ $(PREFIX)/share/applications/
	cp assets/logo.png $(PREFIX)/share/icons/hicolor/512x512/apps/android-emulator-dock.png
	cp android-emulator-dock.desktop $(PREFIX)/share/applications/
	gtk-update-icon-cache -f -t $(PREFIX)/share/icons/hicolor || true
	update-desktop-database $(PREFIX)/share/applications/ || true
	@echo "Installation complete! You can now launch 'android-emulator-dock' from your app menu or terminal."

uninstall:
	@echo "Uninstalling Python package..."
	python3 -m pip uninstall -y android-emulator-dock
	@echo "Removing desktop entry and icon..."
	rm -f $(PREFIX)/share/applications/android-emulator-dock.desktop
	rm -f $(PREFIX)/share/icons/hicolor/512x512/apps/android-emulator-dock.png
	gtk-update-icon-cache -f -t $(PREFIX)/share/icons/hicolor || true
	update-desktop-database $(PREFIX)/share/applications/ || true
	@echo "Uninstallation complete."

dev:
	python3 -m venv .venv
	.venv/bin/pip install -e .
	@echo "Development environment ready. Run 'source .venv/bin/activate'."

test:
	PYTHONPATH=src:proto python3 -m unittest discover -s tests

clean:
	rm -rf dist/ build/ *.egg-info/ .venv/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
