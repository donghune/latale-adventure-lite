import json
import os
import numpy as np


class ScreenCapture:
    CONFIG_PATH = os.path.expanduser("~/.latale-adventure/config.json")

    def __init__(self):
        self.regions = {}  # name -> {"left": x, "top": y, "width": w, "height": h}
        self.load_config()

    def load_config(self):
        """Load saved regions from config file."""
        if os.path.exists(self.CONFIG_PATH):
            with open(self.CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.regions = data.get("regions", {})

    def save_config(self):
        """Save regions to config file."""
        os.makedirs(os.path.dirname(self.CONFIG_PATH), exist_ok=True)
        data = {}
        if os.path.exists(self.CONFIG_PATH):
            with open(self.CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        data["regions"] = self.regions
        with open(self.CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def set_region(self, name, left, top, width, height):
        """Set a capture region."""
        self.regions[name] = {
            "left": left,
            "top": top,
            "width": width,
            "height": height,
        }
        self.save_config()

    def capture_region(self, name):
        """Capture a named region, returns numpy array (BGR format for OpenCV)."""
        import mss

        if name not in self.regions:
            raise ValueError(f"Region '{name}' is not configured")

        region = self.regions[name]
        monitor = {
            "left": region["left"],
            "top": region["top"],
            "width": region["width"],
            "height": region["height"],
        }

        with mss.mss() as sct:
            screenshot = sct.grab(monitor)
            # mss returns BGRA, convert to BGR numpy array
            img = np.array(screenshot)
            return img[:, :, :3]  # Drop alpha channel

    def has_region(self, name):
        """Check if a region is configured."""
        return name in self.regions
