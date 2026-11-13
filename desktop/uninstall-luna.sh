#!/usr/bin/env bash
# Remove the application and launcher, but keep the user's saved colours/settings.
set -Eeuo pipefail
APP="$HOME/.local/opt/luna"
PREV="$HOME/.local/opt/luna-previous"
DESKTOP="$HOME/.local/share/applications/io.luna.LightStudio.desktop"
CLI="$HOME/.local/bin/luna"
rm -rf -- "$APP" "$PREV"
rm -f -- "$DESKTOP" "$CLI" \
  "$HOME/.local/share/icons/hicolor/256x256/apps/io.luna.LightStudio.png" \
  "$HOME/.local/share/icons/hicolor/512x512/apps/io.luna.LightStudio.png"
if command -v kbuildsycoca6 >/dev/null 2>&1; then
  kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
fi
echo 'LUNA was uninstalled. Your saved colours and preferences were preserved.'
