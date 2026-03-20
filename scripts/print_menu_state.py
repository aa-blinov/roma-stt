"""Одна строка JSON для шапки меню roma-stt.ps1 (без лишнего вывода от uv)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from infrastructure.config_repo import load_config


def main() -> None:
    cfg = load_config(ROOT / "config.yaml")
    mp = cfg.get("whisper_model_path") or ""
    model_stem = Path(mp).stem if mp else ""
    data = {
        "lang": cfg.get("language", "ru"),
        "model_stem": model_stem,
        "hotkey_record": cfg.get("hotkey_record", "Ctrl+F2"),
        "hotkey_stop": cfg.get("hotkey_stop", "Ctrl+F3"),
        "module": cfg.get("module", "cpu"),
    }
    print(json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":
    main()
