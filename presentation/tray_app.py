"""Tray icon and menu. Presentation layer (Windows)."""

import io
import sys
from collections.abc import Callable
from pathlib import Path

import pystray
from PIL import Image


def _draw_placeholder_icon(size: int = 64) -> Image.Image:
    """Рисует простую иконку микрофона (если SVG недоступен)."""
    from PIL import ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size
    # Фон
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=s // 4, fill=(61, 107, 133))
    # Тело микрофона (прямоугольник со скруглением)
    cx = s // 2
    body = [cx - 6, 12, cx + 6, 38]
    d.rounded_rectangle(body, radius=6, fill=(142, 202, 232), outline=(30, 58, 74))
    # Подставка
    d.ellipse([cx - 10, 40, cx + 10, 48], fill=(142, 202, 232), outline=(30, 58, 74))
    d.line([(cx, 48), (cx, 52)], fill=(142, 202, 232), width=2)
    d.line([(cx - 6, 52), (cx + 6, 52)], fill=(142, 202, 232), width=2)
    # Волны (дуги слева и справа)
    d.arc([8, 20, 20, 44], 90, 270, fill=(142, 202, 232), width=2)
    d.arc([44, 20, 56, 44], 270, 90, fill=(142, 202, 232), width=2)
    return img


def _load_icon_image(icon_path: Path, size: int = 64) -> Image.Image:
    """Load tray icon from file.

    Priority for .svg input:
      1. tray_icon.png / tray_icon.ico alongside the SVG (no extra deps)
      2. cairosvg — only if installed and .png/.ico are absent
      3. Placeholder icon drawn with Pillow
    """
    if not icon_path.exists():
        return _draw_placeholder_icon(size)
    if icon_path.suffix.lower() == ".svg":
        # 1. Prefer pre-rendered PNG/ICO — no cairosvg needed
        for ext in (".png", ".ico"):
            fallback = icon_path.with_suffix(ext)
            if fallback.exists():
                return Image.open(fallback).convert("RGBA")
        # 2. Try cairosvg if available
        try:
            import cairosvg

            png_bytes = cairosvg.svg2png(url=str(icon_path), output_width=size, output_height=size)
            return Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        except Exception:
            pass
        return _draw_placeholder_icon(size)
    return Image.open(icon_path).convert("RGBA")


def create_tray_icon(
    icon_path: str | Path | None = None,
    on_before_exit: Callable[[], None] | None = None,
    hotkey_hint: str = "Ctrl+F9",
) -> pystray.Icon:
    """Create system tray icon with menu. on_before_exit called before exit (e.g. remove PID file)."""
    if icon_path:
        path = Path(icon_path)
        image = _load_icon_image(path)
    else:
        image = Image.new("RGB", (64, 64), color=(80, 80, 80))

    def on_exit(icon: pystray.Icon, item: pystray.MenuItem) -> None:
        if on_before_exit:
            try:
                on_before_exit()
            except Exception:
                pass
        icon.stop()
        sys.exit(0)

    # Без default=True — клик по иконке открывает меню, а не сразу выход
    menu = pystray.Menu(
        pystray.MenuItem(f"Горячая клавиша: {hotkey_hint}", lambda *args: None, enabled=False),
        pystray.MenuItem("Выход", on_exit),
    )
    icon = pystray.Icon("roma-stt", image, f"Roma-STT ({hotkey_hint})", menu)
    return icon
