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
	@if command -v uv >/dev/null 2>&1; then \
		uv tool install . --force; \
	elif command -v pipx >/dev/null 2>&1; then \
		pipx install . --force; \
	else \
		python3 -m pip install --user . || python3 -m pip install --user --break-system-packages .; \
	fi
	@echo "Installing desktop entry and icon..."
	mkdir -p $(PREFIX)/share/icons/hicolor/512x512/apps/ $(PREFIX)/share/applications/
	cp assets/logo.png $(PREFIX)/share/icons/hicolor/512x512/apps/android-emulator-dock.png
	cp android-emulator-dock.desktop $(PREFIX)/share/applications/
	gtk-update-icon-cache -f -t $(PREFIX)/share/icons/hicolor || true
	update-desktop-database $(PREFIX)/share/applications/ || true
	@echo "Installation complete! You can now launch 'android-emulator-dock' from your app menu or terminal."

uninstall:
	@echo "Uninstalling Python package..."
	@if command -v uv >/dev/null 2>&1 && uv tool list 2>/dev/null | grep -q "android-emulator-dock"; then \
		uv tool uninstall android-emulator-dock; \
	elif command -v pipx >/dev/null 2>&1 && pipx list 2>/dev/null | grep -q "android-emulator-dock"; then \
		pipx uninstall android-emulator-dock; \
	else \
		python3 -m pip uninstall -y android-emulator-dock || true; \
	fi
	@echo "Removing desktop entry and icon..."
	rm -f $(PREFIX)/share/applications/android-emulator-dock.desktop
	rm -f $(PREFIX)/share/icons/hicolor/512x512/apps/android-emulator-dock.png
	gtk-update-icon-cache -f -t $(PREFIX)/share/icons/hicolor || true
	update-desktop-database $(PREFIX)/share/applications/ || true
	@echo "Uninstallation complete."

dev:
	@if command -v uv >/dev/null 2>&1; then \
		uv venv .venv; \
		uv pip install -e .; \
	else \
		python3 -m venv .venv; \
		.venv/bin/pip install -e .; \
	fi
	@echo "Development environment ready. Run 'source .venv/bin/activate'."

test:
	PYTHONPATH=src:proto python3 -m unittest discover -s tests

clean:
	rm -rf dist/ build/ *.egg-info/ .venv/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
