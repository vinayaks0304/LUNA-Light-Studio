#!/usr/bin/env bash
# Install a completed PyInstaller onedir bundle without requiring root.
set -Eeuo pipefail
if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /path/to/PyInstaller/dist/LUNA" >&2
  exit 2
fi
BUNDLE="$(cd -- "$1" && pwd)"
if [[ ! -x "$BUNDLE/LUNA" ]]; then
  echo "Missing executable: $BUNDLE/LUNA" >&2
  exit 1
fi
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
APP_PARENT="${HOME}/.local/opt"
DEST="$APP_PARENT/luna"
PREVIOUS="$APP_PARENT/luna-previous"
ICON_DIR="${HOME}/.local/share/icons/hicolor"
DESKTOP_DIR="${HOME}/.local/share/applications"
BIN_DIR="${HOME}/.local/bin"
mkdir -p "$APP_PARENT" "$DESKTOP_DIR" "$BIN_DIR" \
  "$ICON_DIR/256x256/apps" "$ICON_DIR/512x512/apps"

STAGE="$(mktemp -d "$APP_PARENT/.luna-staging.XXXXXXXX")"
backup_moved=0
rollback() {
  if [[ -n "$STAGE" && -d "$STAGE" ]]; then rm -rf -- "$STAGE"; fi
  if [[ "$backup_moved" == 1 && ! -e "$DEST" && -d "$PREVIOUS" ]]; then
    mv -- "$PREVIOUS" "$DEST"
  fi
}
trap rollback EXIT
cp -a -- "$BUNDLE/." "$STAGE/"
chmod +x "$STAGE/LUNA"
# Retain one previous binary installation for easy rollback. User data is elsewhere.
if [[ -e "$DEST" ]]; then
  if [[ -e "$PREVIOUS" ]]; then rm -rf -- "$PREVIOUS"; fi
  mv -- "$DEST" "$PREVIOUS"
  backup_moved=1
fi
mv -- "$STAGE" "$DEST"
STAGE=""

cp -- "$ROOT/assets/luna-256.png" "$ICON_DIR/256x256/apps/io.luna.LightStudio.png"
cp -- "$ROOT/assets/luna-512.png" "$ICON_DIR/512x512/apps/io.luna.LightStudio.png"

# Freedesktop desktop entries do not expand ~ or $HOME in Exec paths.
cat > "$DESKTOP_DIR/io.luna.LightStudio.desktop" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=LUNA Light Studio
GenericName=Bluetooth LED Controller
Comment=Control your Bluetooth LED strip
Exec="$DEST/LUNA"
TryExec=$DEST/LUNA
Icon=io.luna.LightStudio
Terminal=false
StartupNotify=true
StartupWMClass=LUNA
Categories=Utility;AudioVideo;
Keywords=LED;Light;Bluetooth;Colour;Color;RGB;
EOF
chmod 644 "$DESKTOP_DIR/io.luna.LightStudio.desktop"

cat > "$BIN_DIR/luna" <<'EOF'
#!/usr/bin/env bash
exec "$HOME/.local/opt/luna/LUNA" "$@"
EOF
chmod +x "$BIN_DIR/luna"

if [[ "${LUNA_SKIP_DESKTOP_REFRESH:-0}" != 1 ]]; then
  if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" || true
  fi
  if command -v kbuildsycoca6 >/dev/null 2>&1; then
    kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
  fi
fi
trap - EXIT
printf 'Installed executable: %s\nKDE launcher: %s\n' \
  "$DEST/LUNA" "$DESKTOP_DIR/io.luna.LightStudio.desktop"
