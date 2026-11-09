"""Window and asset locations shared by the game modules."""

from pathlib import Path

import pyautogui

 
WIDTH, HEIGHT = pyautogui.size()
HEIGHT -= 80
ASSET_DIR = Path(__file__).resolve().parent / "assets"
