#!/bin/bash
# install_shortcut.sh — one-shot installer for the Hip Wear Tester desktop
# shortcut and autostart entry on Raspberry Pi OS.
#
# Run this ONCE on the Pi after cloning the project:
#   bash ~/hip-wear-tester/scripts/install_shortcut.sh
#
# What it does:
#   1. Makes launch.sh executable.
#   2. Substitutes the absolute path to launch.sh into a copy of
#      hip-wear-tester.desktop.
#   3. Installs the .desktop file to:
#        - ~/Desktop/                (double-click icon)
#        - ~/.config/autostart/      (auto-launch on boot)
#   4. Marks both copies as trusted so the Pi desktop runs them without
#      prompting "Are you sure?" each time.
#
# After this, the GUI launches automatically next time you reboot the Pi.
# To re-run the app manually, double-click the desktop icon.

set -e

# Resolve project root (parent of the scripts/ directory).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LAUNCH_SH="$SCRIPT_DIR/launch.sh"
TEMPLATE="$SCRIPT_DIR/hip-wear-tester.desktop"

echo "Installing Hip Wear Tester shortcut..."
echo "  Project dir: $PROJECT_DIR"
echo "  Launcher:    $LAUNCH_SH"
echo ""

# 1. Make launch.sh executable.
chmod +x "$LAUNCH_SH"

# 2. Build the .desktop content with the absolute launcher path baked in.
DESKTOP_CONTENT="$(sed "s|__LAUNCH_SH__|$LAUNCH_SH|g" "$TEMPLATE")"

# 3a. Install to Desktop (for the double-click icon).
DESKTOP_DIR="$HOME/Desktop"
if [ -d "$DESKTOP_DIR" ]; then
    DESKTOP_TARGET="$DESKTOP_DIR/hip-wear-tester.desktop"
    echo "$DESKTOP_CONTENT" > "$DESKTOP_TARGET"
    chmod +x "$DESKTOP_TARGET"
    # On Raspberry Pi OS / LXDE the file manager marks .desktop files as
    # "trusted" via gio. This avoids the "do you trust this?" prompt.
    if command -v gio >/dev/null 2>&1; then
        gio set "$DESKTOP_TARGET" metadata::trusted true || true
    fi
    echo "Installed desktop icon: $DESKTOP_TARGET"
else
    echo "Note: ~/Desktop not found, skipping desktop icon install."
fi

# 3b. Install to ~/.config/autostart (for auto-launch on boot).
AUTOSTART_DIR="$HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"
AUTOSTART_TARGET="$AUTOSTART_DIR/hip-wear-tester.desktop"
echo "$DESKTOP_CONTENT" > "$AUTOSTART_TARGET"
chmod +x "$AUTOSTART_TARGET"
echo "Installed autostart entry: $AUTOSTART_TARGET"

echo ""
echo "Done. To verify:"
echo "  - Look for the 'Hip Wear Tester' icon on your desktop."
echo "  - Reboot the Pi; the dashboard should launch automatically."
echo ""
echo "Logs are written to: ~/.hip-wear-tester/app.log"
echo ""
echo "To uninstall:"
echo "  rm \"$DESKTOP_TARGET\""
echo "  rm \"$AUTOSTART_TARGET\""
