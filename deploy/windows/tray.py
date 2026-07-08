"""
DIDRepChecker system tray controller.
Starts the API server as a subprocess, shows green/red tray icon.
"""

import subprocess
import threading
import os
import sys
import time
import urllib.request

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    print("ERROR: pystray and Pillow are required. Run: pip install pystray pillow")
    sys.exit(1)

HEALTH_URL = "http://127.0.0.1:8000/health"
CHECK_INTERVAL = 5


def _make_icon(color):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((8, 8, 56, 56), fill=color)
    return img


ICON_GREEN = _make_icon((0, 200, 100, 255))
ICON_RED = _make_icon((220, 50, 50, 255))
ICON_GRAY = _make_icon((128, 128, 128, 255))


class TrayController:
    def __init__(self):
        self.process = None
        self.icon = None

    def start_server(self):
        if self.process and self.process.poll() is None:
            return
        server_exe = os.path.join(os.path.dirname(sys.executable), "didrepchecker-server.exe")
        if not os.path.exists(server_exe):
            server_exe = sys.executable
            args = [sys.executable, "-m", "uvicorn", "did_intel.api:app", "--host", "127.0.0.1", "--port", "8000"]
        else:
            args = [server_exe]
        self.process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def stop_server(self):
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)
            self.process = None

    def _health_loop(self):
        while True:
            try:
                urllib.request.urlopen(HEALTH_URL, timeout=3)
                self.icon.icon = ICON_GREEN
            except Exception:
                self.icon.icon = ICON_RED
            time.sleep(CHECK_INTERVAL)

    def run(self):
        self.start_server()
        self.icon = pystray.Icon(
            "DIDRepChecker",
            ICON_GREEN,
            "DIDRepChecker",
            menu=pystray.Menu(
                pystray.MenuItem("Start Server", lambda: self.start_server()),
                pystray.MenuItem("Stop Server", lambda: self.stop_server()),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit", self._on_exit),
            ),
        )
        threading.Thread(target=self._health_loop, daemon=True).start()
        self.icon.run()

    def _on_exit(self, icon):
        self.stop_server()
        icon.stop()


def main():
    TrayController().run()


if __name__ == "__main__":
    main()
