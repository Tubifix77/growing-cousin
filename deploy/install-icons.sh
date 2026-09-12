#!/bin/sh
# Render the cousin mark to PNG and install the desktop launcher.
#
# The icon is DRAWN IN CODE (observer.make_icon) rather than committed as a
# binary, so there is exactly one definition of it: the tray, the window and
# the launcher cannot drift apart, and a change is a readable diff instead of
# an opaque blob.
set -e

HERE=$(cd "$(dirname "$0")/.." && pwd)
ICON_DIR="$HOME/.local/share/icons"
APP_DIR="$HOME/.local/share/applications"
mkdir -p "$ICON_DIR" "$APP_DIR"

# Several sizes: panels pick 22-24, the launcher grid wants 128+, and letting
# the toolkit downscale one big PNG is what makes a tray icon look muddy.
QT_QPA_PLATFORM=offscreen python3 - "$ICON_DIR" <<'PY'
import sys
sys.path.insert(0, __import__("os").path.dirname(
    __import__("os").path.dirname(__import__("os").path.abspath(sys.argv[0]))))
sys.path.insert(0, "%s/growing-cousin" % __import__("os").path.expanduser("~"))
from PyQt6.QtWidgets import QApplication
from PyQt6 import QtCore, QtGui
import observer

app = QApplication([])
out = sys.argv[1]
for size in (16, 22, 24, 32, 48, 64, 128, 256):
    icon = observer.make_icon(QtGui, QtCore, size=size)
    pm = icon.pixmap(size, size)
    name = "%s/growing-cousin.png" % out if size == 256 else \
           "%s/growing-cousin-%d.png" % (out, size)
    pm.save(name, "PNG")
print("wrote icons to %s" % out)
PY

sed -e "s|/home/boas|$HOME|g" "$HERE/deploy/growing-cousin.desktop" \
    > "$APP_DIR/growing-cousin.desktop"
chmod +x "$APP_DIR/growing-cousin.desktop"

# A desktop copy too, if the desktop directory exists under any locale name.
for d in "$HOME/Desktop" "$HOME/Skrivebord" "$HOME/Skrivbord"; do
    [ -d "$d" ] && cp "$APP_DIR/growing-cousin.desktop" "$d/" \
                && chmod +x "$d/growing-cousin.desktop" \
                && echo "desktop icon -> $d"
done

update-desktop-database "$APP_DIR" 2>/dev/null || true
gtk-update-icon-cache -f -t "$ICON_DIR" 2>/dev/null || true
echo "launcher  -> $APP_DIR/growing-cousin.desktop"
